#!/usr/bin/env python3
"""
R1 GNN Mixed-ρ Training: Train on mixed ρ distribution, eval all ρ
===================================================================

Motivation: Single-ρ training (r1_gnn_generalize.py) showed limited
OOD generalization at d=5. Mixed-ρ training exposes the GNN to the
full range of correlation structures during training, enabling true
"hardware adaptive" decoding.

Protocol:
  - Training data: uniform mix of ρ ∈ {0.00, 0.03, 0.05, 0.08, 0.10, 0.15}
  - Each ρ contributes equal samples to training set
  - Evaluate on all ρ + OOD ρ=0.20
  - Compare: mixed-GNN vs per-ρ MWPM vs per-ρ GNN (from r1_gnn_lite)

seed=42
"""
import gc
import numpy as np
from scipy.special import erfc
import stim, pymatching
import torch, torch.nn as nn, torch.nn.functional as F
from torch_geometric.nn import GCNConv
import os, json, time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
DEVICE = 'mps' if torch.backends.mps.is_available() else 'cpu'


def _clear_cache():
    if DEVICE == 'mps':
        torch.mps.empty_cache()
    gc.collect()


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
            for k in range(i+1, len(edge_list)):
                src.extend([edge_list[i], edge_list[k]])
                dst.extend([edge_list[k], edge_list[i]])
    return torch.tensor([src, dst], dtype=torch.long)


def gkp_correlated(ne, ns, V, rho, rng):
    sig = np.sqrt(V)
    if rho <= 0:
        d = sig * rng.standard_normal((ns, ne))
    else:
        d = sig * (np.sqrt(1-rho) * rng.standard_normal((ns, ne)) +
                   np.sqrt(rho) * rng.standard_normal((ns, 1)))
    nl = np.rint(d / SQRT_PI).astype(np.int64)
    err = (nl % 2) != 0
    res = d - nl * SQRT_PI
    ra = np.abs(res)
    llr = np.clip(((SQRT_PI - ra)**2 - ra**2) / (2*V), -30, 30)
    return err, res.astype(np.float32), llr.astype(np.float32)


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


def mwpm_decode(syn, obs, weights, edges, nd):
    ns, ne = syn.shape[0], len(edges)
    H = np.zeros((nd+1, ne), dtype=np.uint8)
    Fm = np.zeros((1, ne), dtype=np.uint8)
    for j, e in enumerate(edges):
        H[e['n1'], j] = 1
        if e['n2'] is not None:
            H[e['n2'], j] = 1
        else:
            H[nd, j] = 1
        if e['log']:
            Fm[0, j] = 1
    errs = np.zeros(ns, dtype=np.uint8)
    for i in range(ns):
        ww = np.maximum(weights[i], 0.01)
        m = pymatching.Matching(H, weights=ww, faults_matrix=Fm)
        m.set_boundary_nodes({nd})
        if m.decode(syn[i])[0] != obs[i]:
            errs[i] = 1
    return errs


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
            nn.Linear(hidden, hidden//2), nn.GELU(),
            nn.Linear(hidden//2, 1), nn.Softplus(),
        )

    def forward(self, x, edge_index):
        h = F.gelu(self.input_proj(x))
        for conv, norm in zip(self.convs, self.norms):
            h = norm(h + F.gelu(conv(h, edge_index)))
        return self.output(h).squeeze(-1)


def make_batch(res, llr, edge_index_t, ne, device, start, end):
    bs = end - start
    r = torch.tensor(res[start:end], dtype=torch.float32)
    l = torch.tensor(llr[start:end], dtype=torch.float32)
    ra = torch.abs(r)
    x = torch.stack([r.reshape(-1), ra.reshape(-1), l.reshape(-1)], dim=-1)
    ei_list = [edge_index_t + i * ne for i in range(bs)]
    ei = torch.cat(ei_list, dim=1)
    return x.to(device), ei.to(device)


def train_gnn(model, edge_index, res_train, llr_train, err_train,
              ne, epochs=40, bs=256):
    model = model.to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    n = len(res_train)

    for ep in range(epochs):
        model.train()
        perm = np.random.permutation(n)
        res_s, llr_s, err_s = res_train[perm], llr_train[perm], err_train[perm]
        total_loss = 0; nb = 0

        for start in range(0, n, bs):
            end = min(start + bs, n)
            x, ei = make_batch(res_s, llr_s, edge_index, ne, DEVICE, start, end)
            tgt = torch.tensor(err_s[start:end].reshape(-1),
                               dtype=torch.float32).to(DEVICE)
            w = model(x, ei)
            probs = torch.sigmoid(-w + 2.0)
            loss = F.binary_cross_entropy(probs.clamp(1e-6, 1-1e-6), tgt)
            opt.zero_grad(); loss.backward(); opt.step()
            total_loss += loss.item(); nb += 1
            del x, ei, tgt, w, probs, loss

        sched.step()
        _clear_cache()
        if ep % 10 == 0 or ep == epochs - 1:
            print(f"      ep{ep:3d}: loss={total_loss/nb:.4f}")

    return model


def gnn_predict(model, edge_index, res_test, llr_test, ne, bs=512):
    model.eval()
    n = len(res_test)
    all_weights = np.zeros((n, ne), dtype=np.float32)
    with torch.no_grad():
        for start in range(0, n, bs):
            end = min(start + bs, n)
            x, ei = make_batch(res_test, llr_test, edge_index, ne, DEVICE,
                               start, end)
            w = model(x, ei).cpu().numpy()
            all_weights[start:end] = w.reshape(end - start, ne)
            del x, ei
    _clear_cache()
    return all_weights


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    V = 0.1417  # Phase 1 (σ_eff=8.5dB)
    rho_train_set = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15]
    rho_eval = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]
    results = {}

    print("=" * 70)
    print(f"  R1 GNN Mixed-ρ: Train on ρ∈{rho_train_set}")
    print(f"  Eval on ρ∈{rho_eval}")
    print(f"  Device: {DEVICE}")
    print("=" * 70)

    for d in [3, 5]:
        rounds = d
        edges, nd = extract_graph(d, rounds)
        ne = len(edges)
        edge_index = build_line_graph_edges(edges, nd)

        # Per-ρ sample count: total ~same as per-ρ training
        samples_per_rho = 2000 if d == 3 else 600
        n_total = samples_per_rho * len(rho_train_set)
        n_te = 10000 if d == 3 else 5000
        bs_train = 256 if d == 3 else 64

        print(f"\n{'='*60}")
        print(f"  d={d}: Mixed-ρ training ({samples_per_rho}/ρ × {len(rho_train_set)} = {n_total} total)")
        print(f"{'='*60}")

        # Generate mixed training data
        all_err, all_res, all_llr = [], [], []
        for rho in rho_train_set:
            err, res, llr = gkp_correlated(ne, samples_per_rho, V, rho, rng)
            all_err.append(err)
            all_res.append(res)
            all_llr.append(llr)

        err_tr = np.concatenate(all_err, axis=0)
        res_tr = np.concatenate(all_res, axis=0)
        llr_tr = np.concatenate(all_llr, axis=0)

        # Shuffle
        perm = rng.permutation(n_total)
        err_tr, res_tr, llr_tr = err_tr[perm], res_tr[perm], llr_tr[perm]

        print(f"  Training data: {n_total} samples (shuffled mix)")

        model = GNNLite(in_features=3, hidden=32, n_layers=3)
        n_params = sum(p.numel() for p in model.parameters())
        print(f"  Model: {n_params:,} params")

        t1 = time.time()
        model = train_gnn(model, edge_index, res_tr, llr_tr,
                          err_tr.astype(np.float32), ne,
                          epochs=40, bs=bs_train)
        dt_train = time.time() - t1
        print(f"  Training done: {dt_train:.0f}s ({dt_train/60:.1f}min)")

        # Load per-ρ GNN results for comparison
        per_rho_gnn = {}
        try:
            with open(os.path.join(OUT_DIR, 'r1_gnn_lite_results.json')) as f:
                lite_data = json.load(f)
            for key, val in lite_data.items():
                if key.startswith(f'd{d}_'):
                    per_rho_gnn[val['rho']] = val
        except FileNotFoundError:
            pass

        # Evaluate
        print(f"\n  {'ρ':>5} {'MWPM':>10} {'GNN-mix':>10} {'GNN-per':>10} "
              f"{'Mix/M':>7} {'Per/M':>7}")
        print("  " + "-" * 62)

        for rho_e in rho_eval:
            err_te, res_te, llr_te = gkp_correlated(ne, n_te, V, rho_e, rng)
            syn_te, obs_te = compute_syndromes(err_te, edges, nd)

            # MWPM
            mwpm_errs = mwpm_decode(syn_te, obs_te, llr_te, edges, nd)
            mwpm_pl = mwpm_errs.sum() / n_te

            # Mixed GNN
            gnn_w = gnn_predict(model, edge_index, res_te, llr_te, ne)
            gnn_errs = mwpm_decode(syn_te, obs_te, gnn_w, edges, nd)
            mix_pl = gnn_errs.sum() / n_te

            mix_ratio = mwpm_pl / mix_pl if mix_pl > 0 else float('inf')

            # Per-ρ GNN reference
            per_pl_str = "—"
            per_ratio_str = "—"
            per_pl = None
            if rho_e in per_rho_gnn:
                per_pl = per_rho_gnn[rho_e]['gnn_pL']
                per_pl_str = f"{per_pl:.4e}"
                per_ratio = mwpm_pl / per_pl if per_pl > 0 else float('inf')
                per_ratio_str = f"{per_ratio:.2f}×"

            ood = " *" if rho_e not in rho_train_set else ""
            mix_winner = "MIX" if mix_pl < mwpm_pl else "MWPM"

            print(f"  {rho_e:5.2f} {mwpm_pl:10.4e} {mix_pl:10.4e} {per_pl_str:>10} "
                  f"{mix_ratio:6.2f}× {per_ratio_str:>7} {mix_winner}{ood}")

            results[f'd{d}_eval{rho_e:.2f}'] = {
                'd': d, 'rho_eval': rho_e,
                'rho_train': 'mixed',
                'mwpm_pL': float(mwpm_pl),
                'gnn_mixed_pL': float(mix_pl),
                'gnn_per_rho_pL': float(per_pl) if per_pl is not None else None,
                'mix_ratio': float(mix_ratio),
                'mix_winner': mix_winner,
                'mwpm_err': int(mwpm_errs.sum()),
                'gnn_err': int(gnn_errs.sum()),
                'n_test': n_te,
                'out_of_distribution': rho_e not in rho_train_set,
            }

            # Save incrementally
            with open(os.path.join(OUT_DIR, 'r1_mixed_results.json'), 'w') as f:
                json.dump(results, f, indent=2)

        _clear_cache()
        del model

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  TOTAL: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"{'='*70}")

    # Summary
    print("\n  KEY: Mixed-ρ GNN vs per-ρ GNN vs MWPM")
    for d in [3, 5]:
        print(f"\n  d={d}:")
        for rho_e in rho_eval:
            key = f'd{d}_eval{rho_e:.2f}'
            if key in results:
                r = results[key]
                ood = " (OOD)" if r['out_of_distribution'] else ""
                print(f"    ρ={rho_e:.2f}: mixed {r['mix_ratio']:.2f}× "
                      f"| {r['mix_winner']}{ood}")


if __name__ == '__main__':
    main()
