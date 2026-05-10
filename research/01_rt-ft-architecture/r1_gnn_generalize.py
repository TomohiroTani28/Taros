#!/usr/bin/env python3
"""
R1 GNN Generalization: Train at ρ_train, evaluate across ρ_test
================================================================

Key experiment: Does a GNN decoder trained under one noise condition
generalize to unseen correlation levels?

If yes → "hardware adaptive decoder" claim is justified.
The GNN learns the *structure* of correlated noise, not just one ρ point.

Protocol:
  - Train GNN on ρ=0.05 (moderate, within design spec)
  - Evaluate on ρ = 0.00, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20
  - Compare with MWPM (retrained weights at each ρ)
  - d=3 (fast) and d=5

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
        if ep % 10 == 0 or ep == epochs-1:
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
    rho_train = 0.05
    rho_eval = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]
    results = {}

    print("=" * 70)
    print(f"  R1 GNN Generalization: Train ρ={rho_train}, eval ρ={rho_eval}")
    print(f"  Device: {DEVICE}")
    print("=" * 70)

    for d in [3, 5]:
        rounds = d
        edges, nd = extract_graph(d, rounds)
        ne = len(edges)
        edge_index = build_line_graph_edges(edges, nd)

        n_tr = 10000 if d == 3 else 3000
        n_te = 10000 if d == 3 else 5000
        bs_train = 256 if d == 3 else 64

        print(f"\n{'='*60}")
        print(f"  d={d}: Training GNN on ρ={rho_train} ({n_tr} samples)")
        print(f"{'='*60}")

        # Train on ρ_train only
        err_tr, res_tr, llr_tr = gkp_correlated(ne, n_tr, V, rho_train, rng)

        model = GNNLite(in_features=3, hidden=32, n_layers=3)
        n_params = sum(p.numel() for p in model.parameters())
        print(f"  Model: {n_params:,} params")

        t1 = time.time()
        model = train_gnn(model, edge_index, res_tr, llr_tr,
                          err_tr.astype(np.float32), ne,
                          epochs=40, bs=bs_train)
        dt_train = time.time() - t1
        print(f"  Training done: {dt_train:.0f}s ({dt_train/60:.1f}min)")

        # Evaluate on all ρ values
        print(f"\n  {'ρ_eval':>6} {'MWPM':>10} {'GNN(gen)':>10} {'Ratio':>7} {'Win':>5}")
        print("  " + "-" * 48)

        for rho_e in rho_eval:
            err_te, res_te, llr_te = gkp_correlated(ne, n_te, V, rho_e, rng)
            syn_te, obs_te = compute_syndromes(err_te, edges, nd)

            # MWPM with true-ρ soft-info weights
            mwpm_errs = mwpm_decode(syn_te, obs_te, llr_te, edges, nd)
            mwpm_pl = mwpm_errs.sum() / n_te

            # GNN (trained on ρ_train, tested on ρ_eval)
            gnn_w = gnn_predict(model, edge_index, res_te, llr_te, ne)
            gnn_errs = mwpm_decode(syn_te, obs_te, gnn_w, edges, nd)
            gnn_pl = gnn_errs.sum() / n_te

            ratio = mwpm_pl / gnn_pl if gnn_pl > 0 else float('inf')
            winner = "GNN" if gnn_pl < mwpm_pl else "MWPM"

            ood = "" if rho_e == rho_train else " (OOD)"
            print(f"  {rho_e:6.2f} {mwpm_pl:10.4e} {gnn_pl:10.4e} "
                  f"{ratio:6.2f}× {winner:>5}{ood}")

            results[f'd{d}_train{rho_train}_eval{rho_e:.2f}'] = {
                'd': d, 'rho_train': rho_train, 'rho_eval': rho_e,
                'mwpm_pL': float(mwpm_pl), 'gnn_pL': float(gnn_pl),
                'ratio': float(ratio), 'winner': winner,
                'n_train': n_tr, 'n_test': n_te,
                'out_of_distribution': rho_e != rho_train,
            }

            # Save incrementally
            with open(os.path.join(OUT_DIR, 'r1_generalization_results.json'), 'w') as f:
                json.dump(results, f, indent=2)

        _clear_cache()
        del model

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  TOTAL: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"{'='*70}")

    # Summary: scaling of generalization advantage
    print("\n  KEY: Does GNN advantage generalize to unseen ρ?")
    for d in [3, 5]:
        print(f"\n  d={d}:")
        for rho_e in rho_eval:
            key = f'd{d}_train{rho_train}_eval{rho_e:.2f}'
            if key in results:
                r = results[key]
                ood = "OOD" if r['out_of_distribution'] else "IID"
                print(f"    ρ={rho_e:.2f} [{ood}]: {r['winner']} {r['ratio']:.2f}×")


if __name__ == '__main__':
    main()
