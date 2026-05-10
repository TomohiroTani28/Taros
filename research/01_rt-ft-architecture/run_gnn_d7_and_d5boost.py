#!/usr/bin/env python3
"""
GNN d=7 (1 point: rho=0.10) + d=5 statistics boost (30K test shots)
====================================================================
Runs per-rho trained GNN at:
  - d=7, rho=0.10 (new: GNN advantage scaling claim)
  - d=5, rho={0.08, 0.10, 0.15} with 30K test (boost from 5K)

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


def extract_graph(d, rounds):
    c = stim.Circuit.generated('surface_code:rotated_memory_z',
        rounds=rounds, distance=d,
        before_round_data_depolarization=0.01,
        before_measure_flip_probability=0.01)
    dem = c.detector_error_model(decompose_errors=True)
    edges = []
    for inst in dem.flattened():
        if inst.type != 'error': continue
        dets, has_log = [], False
        for t in inst.targets_copy():
            if t.is_relative_detector_id(): dets.append(t.val)
            elif t.is_logical_observable_id(): has_log = True
        if len(dets)==1: edges.append({'n1':dets[0],'n2':None,'log':has_log})
        elif len(dets)==2: edges.append({'n1':dets[0],'n2':dets[1],'log':has_log})
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
            for j in range(i+1, len(edge_list)):
                src.extend([edge_list[i], edge_list[j]])
                dst.extend([edge_list[j], edge_list[i]])
    return torch.tensor([src, dst], dtype=torch.long)


def gkp_correlated(ne, ns, V, rho, rng):
    sig = np.sqrt(V)
    if rho <= 0:
        d = sig * rng.standard_normal((ns, ne))
    else:
        d = sig*(np.sqrt(1-rho)*rng.standard_normal((ns,ne)) +
                 np.sqrt(rho)*rng.standard_normal((ns,1)))
    nl = np.rint(d/SQRT_PI).astype(np.int64)
    err = (nl%2)!=0
    res = d - nl*SQRT_PI
    ra = np.abs(res)
    llr = np.clip(((SQRT_PI-ra)**2-ra**2)/(2*V), -30, 30)
    return err, res.astype(np.float32), llr.astype(np.float32)


def compute_syndromes(errors, edges, nd):
    ns = errors.shape[0]
    syn = np.zeros((ns,nd), dtype=np.uint8)
    obs = np.zeros(ns, dtype=np.uint8)
    for j,e in enumerate(edges):
        m=errors[:,j]; syn[m,e['n1']]^=1
        if e['n2'] is not None: syn[m,e['n2']]^=1
        if e['log']: obs[m]^=1
    return syn, obs


def mwpm_dec(syn, obs, w, edges, nd):
    ns, ne = syn.shape[0], len(edges)
    H = np.zeros((nd+1,ne), dtype=np.uint8)
    Fm = np.zeros((1,ne), dtype=np.uint8)
    for j,e in enumerate(edges):
        H[e['n1'],j]=1
        if e['n2'] is not None: H[e['n2'],j]=1
        else: H[nd,j]=1
        if e['log']: Fm[0,j]=1
    errs = np.zeros(ns, dtype=np.uint8)
    for i in range(ns):
        ww = np.maximum(w[i], 0.01)
        m = pymatching.Matching(H, weights=ww, faults_matrix=Fm)
        m.set_boundary_nodes({nd})
        if m.decode(syn[i])[0]!=obs[i]: errs[i]=1
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


def _clear_mps_cache():
    if DEVICE == 'mps':
        torch.mps.empty_cache()
    gc.collect()


def make_batch(res, llr, edge_index_t, ne, device, start, end):
    bs = end - start
    r = torch.tensor(res[start:end], dtype=torch.float32)
    l = torch.tensor(llr[start:end], dtype=torch.float32)
    ra = torch.abs(r)
    x = torch.stack([r.reshape(-1), ra.reshape(-1), l.reshape(-1)], dim=-1)
    ei_list = [edge_index_t + i * ne for i in range(bs)]
    ei = torch.cat(ei_list, dim=1)
    return x.to(device), ei.to(device), None


def train_gnn(model, edge_index, res_train, llr_train, err_train, ne, epochs=40, bs=64):
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
            x, ei, _ = make_batch(res_s, llr_s, edge_index, ne, DEVICE, start, end)
            tgt = torch.tensor(err_s[start:end].reshape(-1), dtype=torch.float32).to(DEVICE)
            w = model(x, ei)
            probs = torch.sigmoid(-w + 2.0)
            loss = F.binary_cross_entropy(probs.clamp(1e-6, 1-1e-6), tgt)
            opt.zero_grad(); loss.backward(); opt.step()
            total_loss += loss.item(); nb += 1
            del x, ei, tgt, w, probs, loss
        sched.step()
        _clear_mps_cache()
        if ep % 10 == 0 or ep == epochs-1:
            print(f"      ep{ep:3d}: loss={total_loss/nb:.4f}")
    return model


def gnn_predict(model, edge_index, res_test, llr_test, ne, bs=256):
    model.eval()
    n = len(res_test)
    all_weights = np.zeros((n, ne), dtype=np.float32)
    with torch.no_grad():
        for start in range(0, n, bs):
            end = min(start + bs, n)
            x, ei, _ = make_batch(res_test, llr_test, edge_index, ne, DEVICE, start, end)
            w = model(x, ei).cpu().numpy()
            all_weights[start:end] = w.reshape(end - start, ne)
            del x, ei, w
    _clear_mps_cache()
    return all_weights


def run_condition(d, rho, n_train, n_test, rng, V=0.1417):
    """Run one (d, rho) condition: train GNN, evaluate both decoders."""
    rounds = d
    edges, nd = extract_graph(d, rounds)
    ne = len(edges)
    edge_index = build_line_graph_edges(edges, nd)

    print(f"\n  d={d}, rho={rho:.2f}, {ne} edges, train={n_train}, test={n_test}")

    # Generate data
    err_tr, res_tr, llr_tr = gkp_correlated(ne, n_train, V, rho, rng)
    err_te, res_te, llr_te = gkp_correlated(ne, n_test, V, rho, rng)
    syn_te, obs_te = compute_syndromes(err_te, edges, nd)

    # MWPM baseline
    t1 = time.time()
    mwpm_e = mwpm_dec(syn_te, obs_te, llr_te, edges, nd)
    dt_m = time.time()-t1
    mwpm_pL = float(mwpm_e.sum()/n_test)
    print(f"    MWPM: {mwpm_pL:.4e} ({mwpm_e.sum()}/{n_test}) [{dt_m:.0f}s]")

    # Train GNN
    model = GNNLite(in_features=3, hidden=32, n_layers=3)
    np_count = sum(p.numel() for p in model.parameters())

    train_bs = 256 if d==3 else (64 if d==5 else 32)
    t1 = time.time()
    model = train_gnn(model, edge_index, res_tr, llr_tr,
                      err_tr.astype(np.float32), ne, epochs=40, bs=train_bs)
    dt_train = time.time()-t1
    print(f"    Train: {dt_train:.0f}s")

    # GNN predict + decode
    t1 = time.time()
    gnn_w = gnn_predict(model, edge_index, res_te, llr_te, ne,
                        bs=256 if d<=5 else 128)
    dt_inf = time.time()-t1

    t1 = time.time()
    gnn_e = mwpm_dec(syn_te, obs_te, gnn_w, edges, nd)
    dt_dec = time.time()-t1
    gnn_pL = float(gnn_e.sum()/n_test)

    ratio = mwpm_pL/gnn_pL if gnn_pL>0 else float('inf')
    winner = "GNN" if gnn_pL<mwpm_pL else "MWPM"
    print(f"    GNN:  {gnn_pL:.4e} ({gnn_e.sum()}/{n_test}) "
          f"[inf:{dt_inf:.0f}s dec:{dt_dec:.0f}s]")
    print(f"    -> {ratio:.2f}x, {winner} wins")

    _clear_mps_cache()
    del model

    return {
        'd': d, 'rho': rho, 'ne': ne, 'n_params': np_count,
        'mwpm_pL': mwpm_pL, 'gnn_pL': gnn_pL,
        'ratio': ratio, 'winner': winner,
        'mwpm_err': int(mwpm_e.sum()), 'gnn_err': int(gnn_e.sum()),
        'n_train': n_train, 'n_test': n_test,
        'train_time': dt_train, 'infer_time': dt_inf,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    print("="*70)
    print("  GNN d=7 + d=5 statistics boost")
    print(f"  Device: {DEVICE}")
    print("="*70)

    results = {}

    # === d=5 statistics boost: 30K test (was 5K) ===
    for rho in [0.08, 0.10, 0.15]:
        r = run_condition(d=5, rho=rho, n_train=5000, n_test=30000, rng=rng)
        results[f'd5_rho{rho:.2f}_boost'] = r
        with open(os.path.join(OUT_DIR, 'r1_gnn_d7_boost.json'), 'w') as f:
            json.dump(results, f, indent=2)

    # === d=7: key point rho=0.10 ===
    # Also rho=0.0 for baseline comparison
    for rho in [0.0, 0.10]:
        r = run_condition(d=7, rho=rho, n_train=2000, n_test=10000, rng=rng)
        results[f'd7_rho{rho:.2f}'] = r
        with open(os.path.join(OUT_DIR, 'r1_gnn_d7_boost.json'), 'w') as f:
            json.dump(results, f, indent=2)

    elapsed = time.time()-t0
    print(f"\n{'='*70}")
    print(f"  TOTAL: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print("="*70)

    # Summary
    print(f"\n  {'d':>2} {'rho':>5} {'MWPM':>10} {'GNN':>10} {'Ratio':>7} {'Err':>5} {'Win':>5}")
    print("  "+"-"*55)
    for k in sorted(results.keys()):
        r = results[k]
        print(f"  {r['d']:>2} {r['rho']:5.2f} {r['mwpm_pL']:10.4e} "
              f"{r['gnn_pL']:10.4e} {r['ratio']:6.2f}x {r['gnn_err']:5d} {r['winner']:>5}")

    # Scaling check
    print("\n  SCALING CHECK (rho=0.10):")
    for dk in ['d5_rho0.10_boost', 'd7_rho0.10']:
        if dk in results:
            r = results[dk]
            print(f"    d={r['d']}: advantage={r['ratio']:.2f}x "
                  f"(MWPM={r['mwpm_pL']:.4e}, GNN={r['gnn_pL']:.4e})")


if __name__ == '__main__':
    main()
