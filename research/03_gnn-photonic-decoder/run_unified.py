#!/usr/bin/env python3
"""
Unified GNN decoder experiment: d=3,5,7 × 3 decoders × 6+1 ρ
================================================================
Paper-quality data with consistent parameters across all distances.

Experiments:
  1. Per-ρ GNN vs vanilla MWPM (Table I)
  2. Correlated MWPM baseline (Table: corr MWPM)
  3. Mixed-ρ GNN + OOD evaluation (Table II)

Parameters:
  d=3: n_train=5000, n_test=30000
  d=5: n_train=5000, n_test=30000
  d=7: n_train=3000, n_test=10000
  epochs=40, seed=42, Phase 1 (σ_eff=8.5dB, V_eff=0.1417)

Output: results/unified_*.json (incremental save)
"""
import gc
import numpy as np
from scipy.special import erfc
import stim, pymatching
import torch, torch.nn as nn, torch.nn.functional as F
from torch_geometric.nn import GCNConv
import os, json, time, sys

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
DEVICE = 'mps' if torch.backends.mps.is_available() else 'cpu'
SEED = 42

# Unified parameters
V_EFF = 0.1417  # Phase 1: σ_eff = 8.5 dB
RHO_LIST = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15]
RHO_OOD = 0.20

CONFIGS = {
    3: {'n_train': 5000, 'n_test': 30000, 'rounds': 3, 'epochs': 40, 'bs': 64},
    5: {'n_train': 5000, 'n_test': 30000, 'rounds': 5, 'epochs': 40, 'bs': 32},
    7: {'n_train': 3000, 'n_test': 10000, 'rounds': 7, 'epochs': 40, 'bs': 16},
}


# ─── Graph extraction ───

def extract_graph(d, rounds):
    c = stim.Circuit.generated('surface_code:rotated_memory_z',
        rounds=rounds, distance=d,
        before_round_data_depolarization=0.01,
        before_measure_flip_probability=0.01)
    dem = c.detector_error_model(decompose_errors=True)
    edges = []
    for inst in dem.flattened():
        if inst.type != 'error':
            continue
        dets, has_log = [], False
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                dets.append(t.val)
            elif t.is_logical_observable_id():
                has_log = True
        if len(dets) == 1:
            edges.append({'n1': dets[0], 'n2': None, 'log': has_log})
        elif len(dets) == 2:
            edges.append({'n1': dets[0], 'n2': dets[1], 'log': has_log})
    return edges, dem.num_detectors


def build_line_graph_edges(edges, n_det):
    boundary = n_det
    det_to_edges = {}
    for j, e in enumerate(edges):
        for node in [e['n1'], e['n2'] if e['n2'] is not None else boundary]:
            if node not in det_to_edges:
                det_to_edges[node] = []
            det_to_edges[node].append(j)
    src, dst = [], []
    for node, edge_list in det_to_edges.items():
        for i in range(len(edge_list)):
            for j in range(i + 1, len(edge_list)):
                src.extend([edge_list[i], edge_list[j]])
                dst.extend([edge_list[j], edge_list[i]])
    return torch.tensor([src, dst], dtype=torch.long)


# ─── Noise model ───

def gkp_correlated(ne, ns, v_eff, rho, rng):
    sig = np.sqrt(v_eff)
    if rho <= 0:
        disp = sig * rng.standard_normal((ns, ne))
    else:
        disp = sig * (np.sqrt(1 - rho) * rng.standard_normal((ns, ne)) +
                      np.sqrt(rho) * rng.standard_normal((ns, 1)))
    nl = np.rint(disp / SQRT_PI).astype(np.int64)
    err = (nl % 2) != 0
    res = disp - nl * SQRT_PI
    ra = np.abs(res)
    llr = np.clip(((SQRT_PI - ra)**2 - ra**2) / (2 * v_eff), -30, 30)
    return err, res.astype(np.float32), llr.astype(np.float32)


# ─── Syndrome / decoding ───

def compute_syndromes(errors, edges, nd):
    ns = errors.shape[0]
    syn = np.zeros((ns, nd), dtype=np.uint8)
    obs = np.zeros(ns, dtype=np.uint8)
    for j, e in enumerate(edges):
        m = errors[:, j]
        syn[m, e['n1']] ^= 1
        if e['n2'] is not None:
            syn[m, e['n2']] ^= 1
        if e['log']:
            obs[m] ^= 1
    return syn, obs


def build_matching_matrices(edges, nd):
    ne = len(edges)
    h_mat = np.zeros((nd + 1, ne), dtype=np.uint8)
    f_mat = np.zeros((1, ne), dtype=np.uint8)
    for j, e in enumerate(edges):
        h_mat[e['n1'], j] = 1
        if e['n2'] is not None:
            h_mat[e['n2'], j] = 1
        else:
            h_mat[nd, j] = 1
        if e['log']:
            f_mat[0, j] = 1
    return h_mat, f_mat


def mwpm_decode_batch(syn, obs, weights, h_mat, f_mat, nd):
    """Decode batch with per-shot weights."""
    ns = syn.shape[0]
    errs = np.zeros(ns, dtype=np.uint8)
    for i in range(ns):
        ww = np.maximum(weights[i], 0.01)
        m = pymatching.Matching(h_mat, weights=ww, faults_matrix=f_mat)
        m.set_boundary_nodes({nd})
        if m.decode(syn[i])[0] != obs[i]:
            errs[i] = 1
    return errs


def mwpm_decode_uniform(syn, obs, weights_1d, h_mat, f_mat, nd):
    """Decode batch with uniform weights (same for all shots)."""
    ww = np.maximum(weights_1d, 0.01)
    m = pymatching.Matching(h_mat, weights=ww, faults_matrix=f_mat)
    m.set_boundary_nodes({nd})
    ns = syn.shape[0]
    errs = np.zeros(ns, dtype=np.uint8)
    for i in range(ns):
        if m.decode(syn[i])[0] != obs[i]:
            errs[i] = 1
    return errs


def corr_mwpm_decode(syn, obs, res, llr, h_mat, f_mat, nd, ne):
    """Correlated MWPM: subtract estimated common-mode, recompute LLR."""
    ns = syn.shape[0]
    common = np.mean(res, axis=1, keepdims=True)
    res_corr = res - common
    ra = np.abs(res_corr)
    llr_corr = np.clip(((SQRT_PI - ra)**2 - ra**2) / (2 * V_EFF), -30, 30)
    return mwpm_decode_batch(syn, obs, llr_corr, h_mat, f_mat, nd)


# ─── GNN ───

class GNNLite(nn.Module):
    def __init__(self, in_features=3, hidden=32, n_layers=3):
        super().__init__()
        self.input_proj = nn.Linear(in_features, hidden)
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()
        for _ in range(n_layers):
            self.convs.append(GCNConv(hidden, hidden))
            self.norms.append(nn.LayerNorm(hidden))
        self.output = nn.Sequential(
            nn.Linear(hidden, hidden // 2), nn.GELU(),
            nn.Linear(hidden // 2, 1), nn.Softplus(),
        )

    def forward(self, x, edge_index):
        h = F.gelu(self.input_proj(x))
        for conv, norm in zip(self.convs, self.norms):
            h = norm(h + F.gelu(conv(h, edge_index)))
        return self.output(h).squeeze(-1)


def _clear():
    if DEVICE == 'mps':
        torch.mps.empty_cache()
    gc.collect()


def make_batch(res, llr, edge_index_t, ne, device, start, end):
    r = torch.tensor(res[start:end], dtype=torch.float32)
    l = torch.tensor(llr[start:end], dtype=torch.float32)
    ra = torch.abs(r)
    x = torch.stack([r.reshape(-1), ra.reshape(-1), l.reshape(-1)], dim=-1)
    bs = end - start
    ei = torch.cat([edge_index_t + i * ne for i in range(bs)], dim=1)
    return x.to(device), ei.to(device)


def train_gnn(model, edge_index, res_tr, llr_tr, err_tr, ne, epochs=40, bs=32):
    model = model.to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    n = len(res_tr)
    for ep in range(epochs):
        model.train()
        perm = np.random.permutation(n)
        res_s, llr_s, err_s = res_tr[perm], llr_tr[perm], err_tr[perm]
        total_loss = 0
        nb = 0
        for start in range(0, n, bs):
            end = min(start + bs, n)
            x, ei = make_batch(res_s, llr_s, edge_index, ne, DEVICE, start, end)
            tgt = torch.tensor(err_s[start:end].reshape(-1),
                               dtype=torch.float32).to(DEVICE)
            w = model(x, ei)
            probs = torch.sigmoid(-w + 2.0)
            loss = F.binary_cross_entropy(probs.clamp(1e-6, 1 - 1e-6), tgt)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item()
            nb += 1
            del x, ei, tgt, w, probs, loss
        sched.step()
        _clear()
        if ep % 10 == 0 or ep == epochs - 1:
            print(f"        ep{ep:3d}: loss={total_loss / nb:.4f}")
    return model


def gnn_predict(model, edge_index, res_te, llr_te, ne, bs=128):
    model.eval()
    n = len(res_te)
    all_w = np.zeros((n, ne), dtype=np.float32)
    with torch.no_grad():
        for start in range(0, n, bs):
            end = min(start + bs, n)
            x, ei = make_batch(res_te, llr_te, edge_index, ne, DEVICE, start, end)
            w = model(x, ei).cpu().numpy()
            all_w[start:end] = w.reshape(end - start, ne)
            del x, ei, w
    _clear()
    return all_w


# ─── Save helper ───

def save_json(name, data):
    path = os.path.join(OUT_DIR, name)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"    [saved {name}]")


# ─── Experiment 1: Per-ρ GNN + vanilla MWPM + corr MWPM ───

def run_per_rho(d, cfg, rng):
    print(f"\n{'#' * 70}")
    print(f"  EXPERIMENT 1: Per-ρ GNN — d={d}")
    print(f"  n_train={cfg['n_train']}, n_test={cfg['n_test']}, epochs={cfg['epochs']}")
    print(f"{'#' * 70}")

    edges, nd = extract_graph(d, cfg['rounds'])
    ne = len(edges)
    edge_index = build_line_graph_edges(edges, nd)
    h_mat, f_mat = build_matching_matrices(edges, nd)
    print(f"  {ne} DEM edges, {edge_index.shape[1]} line-graph edges\n")

    per_rho_results = {}
    corr_results = {}

    for rho in RHO_LIST:
        key = f"d{d}_rho{rho:.2f}"
        print(f"  ── ρ={rho:.2f} ──")

        # Generate data
        err_tr, res_tr, llr_tr = gkp_correlated(ne, cfg['n_train'], V_EFF, rho, rng)
        err_te, res_te, llr_te = gkp_correlated(ne, cfg['n_test'], V_EFF, rho, rng)
        syn_te, obs_te = compute_syndromes(err_te, edges, nd)

        # Vanilla MWPM (per-shot LLR weights)
        t1 = time.time()
        mwpm_e = mwpm_decode_batch(syn_te, obs_te, llr_te, h_mat, f_mat, nd)
        dt_mwpm = time.time() - t1
        mwpm_pL = float(mwpm_e.sum() / cfg['n_test'])
        print(f"    MWPM:      {mwpm_pL:.4e} ({mwpm_e.sum()}/{cfg['n_test']}) [{dt_mwpm:.0f}s]")

        # Correlated MWPM
        t1 = time.time()
        corr_e = corr_mwpm_decode(syn_te, obs_te, res_te, llr_te, h_mat, f_mat, nd, ne)
        dt_corr = time.time() - t1
        corr_pL = float(corr_e.sum() / cfg['n_test'])
        corr_improve = mwpm_pL / corr_pL if corr_pL > 0 else float('inf')
        print(f"    Corr MWPM: {corr_pL:.4e} ({corr_e.sum()}/{cfg['n_test']}) "
              f"[{dt_corr:.0f}s] improve={corr_improve:.2f}x")

        corr_results[key] = {
            'd': d, 'rho': rho,
            'mwpm_std_pL': mwpm_pL, 'mwpm_corr_pL': corr_pL,
            'improve_factor': corr_improve,
            'mwpm_err': int(mwpm_e.sum()), 'corr_err': int(corr_e.sum()),
            'n_test': cfg['n_test'],
        }

        # Train per-ρ GNN
        model = GNNLite()
        n_params = sum(p.numel() for p in model.parameters())
        t1 = time.time()
        model = train_gnn(model, edge_index, res_tr, llr_tr,
                          err_tr.astype(np.float32), ne,
                          epochs=cfg['epochs'], bs=cfg['bs'])
        dt_train = time.time() - t1
        print(f"    Train:     {dt_train:.0f}s ({dt_train / 60:.1f}min)")

        # GNN predict + decode
        t1 = time.time()
        gnn_w = gnn_predict(model, edge_index, res_te, llr_te, ne)
        dt_inf = time.time() - t1
        t1 = time.time()
        gnn_e = mwpm_decode_batch(syn_te, obs_te, gnn_w, h_mat, f_mat, nd)
        dt_dec = time.time() - t1
        gnn_pL = float(gnn_e.sum() / cfg['n_test'])

        ratio = mwpm_pL / gnn_pL if gnn_pL > 0 else float('inf')
        winner = "GNN" if gnn_pL < mwpm_pL else "MWPM" if mwpm_pL < gnn_pL else "tie"
        print(f"    GNN:       {gnn_pL:.4e} ({gnn_e.sum()}/{cfg['n_test']}) "
              f"[inf:{dt_inf:.0f}s dec:{dt_dec:.0f}s] -> {ratio:.2f}x {winner}")

        per_rho_results[key] = {
            'd': d, 'rho': rho, 'ne': ne, 'n_params': n_params,
            'mwpm_pL': mwpm_pL, 'gnn_pL': gnn_pL,
            'ratio': ratio, 'winner': winner,
            'mwpm_err': int(mwpm_e.sum()), 'gnn_err': int(gnn_e.sum()),
            'n_train': cfg['n_train'], 'n_test': cfg['n_test'],
            'train_time': dt_train, 'infer_time': dt_inf,
        }

        # Incremental save
        save_json('unified_per_rho.json', per_rho_results)
        save_json('unified_corr_mwpm.json', corr_results)

        _clear()
        del model

    return per_rho_results, corr_results, edges, nd, ne, edge_index, h_mat, f_mat


# ─── Experiment 2: Mixed-ρ GNN + OOD ───

def run_mixed_rho(d, cfg, edges, nd, ne, edge_index, h_mat, f_mat, rng):
    print(f"\n{'#' * 70}")
    print(f"  EXPERIMENT 2: Mixed-ρ GNN — d={d}")
    print(f"{'#' * 70}")

    # Generate mixed training data
    n_per_rho = cfg['n_train'] // len(RHO_LIST)
    all_res, all_llr, all_err = [], [], []
    for rho in RHO_LIST:
        err, res, llr = gkp_correlated(ne, n_per_rho, V_EFF, rho, rng)
        all_err.append(err.astype(np.float32))
        all_res.append(res)
        all_llr.append(llr)
    res_tr = np.concatenate(all_res)
    llr_tr = np.concatenate(all_llr)
    err_tr = np.concatenate(all_err)

    # Shuffle
    perm = rng.permutation(len(res_tr))
    res_tr, llr_tr, err_tr = res_tr[perm], llr_tr[perm], err_tr[perm]

    # Train single mixed model
    model = GNNLite()
    t1 = time.time()
    model = train_gnn(model, edge_index, res_tr, llr_tr, err_tr, ne,
                      epochs=cfg['epochs'], bs=cfg['bs'])
    dt_train = time.time() - t1
    print(f"  Mixed train: {dt_train:.0f}s ({dt_train / 60:.1f}min)")

    # Evaluate on all ρ + OOD
    mixed_results = {}
    eval_rhos = RHO_LIST + [RHO_OOD]

    for rho in eval_rhos:
        key = f"d{d}_eval{rho:.2f}"
        ood = rho == RHO_OOD
        print(f"\n  ── eval ρ={rho:.2f} {'(OOD)' if ood else ''} ──")

        err_te, res_te, llr_te = gkp_correlated(ne, cfg['n_test'], V_EFF, rho, rng)
        syn_te, obs_te = compute_syndromes(err_te, edges, nd)

        # MWPM baseline
        mwpm_e = mwpm_decode_batch(syn_te, obs_te, llr_te, h_mat, f_mat, nd)
        mwpm_pL = float(mwpm_e.sum() / cfg['n_test'])

        # Mixed GNN
        gnn_w = gnn_predict(model, edge_index, res_te, llr_te, ne)
        gnn_e = mwpm_decode_batch(syn_te, obs_te, gnn_w, h_mat, f_mat, nd)
        gnn_pL = float(gnn_e.sum() / cfg['n_test'])

        ratio = mwpm_pL / gnn_pL if gnn_pL > 0 else float('inf')
        winner = "MIX" if gnn_pL < mwpm_pL else "MWPM" if mwpm_pL < gnn_pL else "tie"
        print(f"    MWPM: {mwpm_pL:.4e} ({mwpm_e.sum()})  "
              f"Mixed-GNN: {gnn_pL:.4e} ({gnn_e.sum()})  -> {ratio:.2f}x {winner}")

        mixed_results[key] = {
            'd': d, 'rho_eval': rho, 'rho_train': 'mixed',
            'mwpm_pL': mwpm_pL, 'gnn_mixed_pL': gnn_pL,
            'mix_ratio': ratio, 'mix_winner': winner,
            'mwpm_err': int(mwpm_e.sum()), 'gnn_err': int(gnn_e.sum()),
            'n_test': cfg['n_test'],
            'out_of_distribution': ood,
        }
        save_json('unified_mixed_rho.json', mixed_results)

    _clear()
    del model
    return mixed_results


# ─── Main ───

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t_global = time.time()

    print("=" * 70)
    print("  UNIFIED GNN DECODER EXPERIMENT")
    print(f"  Device: {DEVICE}")
    print(f"  V_eff={V_EFF}, ρ={RHO_LIST}+OOD={RHO_OOD}")
    print(f"  seed={SEED}")
    for d, cfg in CONFIGS.items():
        print(f"  d={d}: n_train={cfg['n_train']}, n_test={cfg['n_test']}, "
              f"rounds={cfg['rounds']}, epochs={cfg['epochs']}")
    print("=" * 70)

    rng = np.random.default_rng(SEED)
    all_per_rho = {}
    all_corr = {}
    all_mixed = {}

    for d in [3, 5, 7]:
        cfg = CONFIGS[d]
        t_d = time.time()

        # Experiment 1: per-ρ + corr MWPM
        per_rho, corr, edges, nd, ne, edge_index, h_mat, f_mat = \
            run_per_rho(d, cfg, rng)
        all_per_rho.update(per_rho)
        all_corr.update(corr)

        # Save accumulated
        save_json('unified_per_rho.json', all_per_rho)
        save_json('unified_corr_mwpm.json', all_corr)

        # Experiment 2: mixed-ρ
        mixed = run_mixed_rho(d, cfg, edges, nd, ne, edge_index, h_mat, f_mat, rng)
        all_mixed.update(mixed)
        save_json('unified_mixed_rho.json', all_mixed)

        dt_d = time.time() - t_d
        print(f"\n  d={d} total: {dt_d:.0f}s ({dt_d / 3600:.1f}h)")

    elapsed = time.time() - t_global
    print(f"\n{'=' * 70}")
    print(f"  ALL DONE: {elapsed:.0f}s ({elapsed / 3600:.1f}h)")
    print(f"{'=' * 70}")

    # Final summary table
    print(f"\n  === Per-ρ GNN Summary ===")
    print(f"  {'d':>3} {'ρ':>5} {'MWPM':>10} {'GNN':>10} {'Ratio':>7} "
          f"{'M_err':>6} {'G_err':>6}")
    print("  " + "-" * 55)
    for k in sorted(all_per_rho.keys()):
        r = all_per_rho[k]
        print(f"  {r['d']:3d} {r['rho']:5.2f} {r['mwpm_pL']:10.4e} "
              f"{r['gnn_pL']:10.4e} {r['ratio']:6.2f}x "
              f"{r['mwpm_err']:6d} {r['gnn_err']:6d}")

    print(f"\n  === Mixed-ρ GNN Summary ===")
    print(f"  {'d':>3} {'ρ':>5} {'MWPM':>10} {'MixGNN':>10} {'Ratio':>7} {'OOD':>4}")
    print("  " + "-" * 50)
    for k in sorted(all_mixed.keys()):
        r = all_mixed[k]
        ood = "***" if r['out_of_distribution'] else ""
        print(f"  {r['d']:3d} {r['rho_eval']:5.2f} {r['mwpm_pL']:10.4e} "
              f"{r['gnn_mixed_pL']:10.4e} {r['mix_ratio']:6.2f}x {ood}")


if __name__ == '__main__':
    main()
