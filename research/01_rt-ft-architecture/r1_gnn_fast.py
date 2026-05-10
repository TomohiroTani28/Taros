#!/usr/bin/env python3
"""
R1 GNN Fast: Batched Graph Neural Network Decoder
==================================================

Fixed version of r1_gnn_decoder.py with proper batching.
Original problem: per-shot GNN forward pass → 200+ min.
Fix: batch all shots into a single large graph via PyG Batch.

Architecture (same as original):
  - Line graph: each DEM edge → GNN node
  - GNN message passing captures correlations between neighboring edges
  - Parameter count independent of graph size (works for d=3 and d=5)

seed=42
"""
import numpy as np
from scipy.special import erfc
import stim, pymatching
import torch, torch.nn as nn, torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data, Batch
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
    """Build line graph adjacency: two DEM edges connected if they share a detector."""
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


# ============================================================
# GNN Decoder (same architecture, batched execution)
# ============================================================
class GNNWeightDecoder(nn.Module):
    """
    GNN on line graph. Parameter count independent of graph size.
    Same model for d=3 (66 nodes) and d=5 (334 nodes).
    """
    def __init__(self, in_features=3, hidden=64, n_layers=4):
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

    def forward(self, x, edge_index, batch=None):
        h = F.gelu(self.input_proj(x))
        for conv, norm in zip(self.convs, self.norms):
            h = norm(h + F.gelu(conv(h, edge_index)))
        return self.output(h).squeeze(-1)


def make_batch(res, llr, edge_index_template, ne, device, start, end):
    """Create a PyG Batch from a slice of shots — fully vectorized."""
    bs = end - start
    # Node features: (res, |res|, llr) per edge per shot
    r = torch.tensor(res[start:end], dtype=torch.float32)  # (bs, ne)
    l = torch.tensor(llr[start:end], dtype=torch.float32)
    ra = torch.abs(r)
    # Stack into (bs*ne, 3)
    x = torch.stack([r.reshape(-1), ra.reshape(-1), l.reshape(-1)], dim=-1)

    # Replicate edge_index for each shot with offset
    n_pyg_edges = edge_index_template.shape[1]
    offsets = torch.arange(bs, dtype=torch.long).unsqueeze(1) * ne  # (bs, 1)
    # (2, n_pyg_edges) → (2, bs*n_pyg_edges)
    ei = edge_index_template.unsqueeze(0).expand(bs, -1, -1)  # (bs, 2, n_pyg_edges)
    ei = ei + offsets.unsqueeze(1)  # broadcast offset
    ei = ei.reshape(2, -1) if bs > 0 else edge_index_template

    # Fix reshape: (bs, 2, n_pyg_edges) → need (2, bs*n_pyg_edges)
    ei_list = []
    for i in range(bs):
        ei_list.append(edge_index_template + i * ne)
    ei = torch.cat(ei_list, dim=1)

    batch_idx = torch.arange(bs, dtype=torch.long).repeat_interleave(ne)
    return x.to(device), ei.to(device), batch_idx.to(device)


def train_gnn(model, edge_index, res_train, llr_train, err_train,
              ne, epochs=60, bs=512, lr=1e-3):
    """Train GNN with proper batching."""
    model = model.to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    n = len(res_train)

    for ep in range(epochs):
        model.train()
        perm = np.random.permutation(n)
        res_s = res_train[perm]
        llr_s = llr_train[perm]
        err_s = err_train[perm]
        total_loss = 0; nb = 0

        for start in range(0, n, bs):
            end = min(start + bs, n)
            x, ei, batch_idx = make_batch(res_s, llr_s, edge_index, ne, DEVICE, start, end)
            tgt = torch.tensor(err_s[start:end].reshape(-1), dtype=torch.float32).to(DEVICE)

            w = model(x, ei)  # (bs*ne,)
            probs = torch.sigmoid(-w + 2.0)
            loss = F.binary_cross_entropy(probs.clamp(1e-6, 1-1e-6), tgt)

            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item(); nb += 1

        sched.step()
        if ep % 10 == 0 or ep == epochs-1:
            print(f"      ep{ep:3d}: loss={total_loss/nb:.4f}")

    return model


def gnn_predict(model, edge_index, res_test, llr_test, ne, bs=1024):
    """Batched GNN inference."""
    model.eval()
    n = len(res_test)
    all_weights = np.zeros((n, ne), dtype=np.float32)

    with torch.no_grad():
        for start in range(0, n, bs):
            end = min(start + bs, n)
            x, ei, batch_idx = make_batch(res_test, llr_test, edge_index, ne, DEVICE, start, end)
            w = model(x, ei).cpu().numpy()  # ((end-start)*ne,)
            all_weights[start:end] = w.reshape(end - start, ne)

    return all_weights


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    print("="*70)
    print("  R1 GNN FAST: Batched Graph Neural Network Decoder")
    print(f"  Device: {DEVICE}")
    print("  Key: batched execution, same model for d=3 and d=5")
    print("="*70)

    V = 0.1417  # Phase 1
    rho_list = [0.0, 0.05, 0.08, 0.10]
    results = {}

    for d in [3, 5]:
        rounds = d
        edges, nd = extract_graph(d, rounds)
        ne = len(edges)
        edge_index = build_line_graph_edges(edges, nd)

        print(f"\n{'='*60}")
        print(f"  d={d}, {ne} DEM edges, {edge_index.shape[1]} line-graph edges")
        print(f"{'='*60}")

        for rho in rho_list:
            print(f"\n  rho={rho:.2f}:")

            # Data — more for d=3, less for d=5 (MWPM decode is slow)
            n_tr = 80000 if d==3 else 50000
            n_te = 10000 if d==3 else 5000
            err_tr, res_tr, llr_tr = gkp_correlated(ne, n_tr, V, rho, rng)
            err_te, res_te, llr_te = gkp_correlated(ne, n_te, V, rho, rng)
            syn_te, obs_te = compute_syndromes(err_te, edges, nd)

            # MWPM baseline
            print(f"    MWPM decoding {n_te} shots...")
            t1 = time.time()
            mwpm_e = mwpm_dec(syn_te, obs_te, llr_te, edges, nd)
            dt_m = time.time()-t1
            mwpm_pL = mwpm_e.sum()/n_te
            print(f"    MWPM: {mwpm_pL:.4e} ({mwpm_e.sum()}/{n_te}) [{dt_m:.0f}s]")

            # Train GNN
            model = GNNWeightDecoder(in_features=3, hidden=64, n_layers=4)
            np_count = sum(p.numel() for p in model.parameters())
            print(f"    GNN: {np_count:,} params, training...")

            ep = 40 if d==3 else 30
            train_bs = 512 if d==3 else 256
            t1 = time.time()
            model = train_gnn(model, edge_index, res_tr, llr_tr,
                            err_tr.astype(np.float32), ne,
                            epochs=ep, bs=train_bs)
            dt_train = time.time()-t1
            print(f"    Training: {dt_train:.0f}s")

            # GNN inference (batched)
            t1 = time.time()
            gnn_w = gnn_predict(model, edge_index, res_te, llr_te, ne)
            dt_inf = time.time()-t1
            print(f"    GNN inference: {dt_inf:.0f}s")

            # MWPM with GNN weights
            t1 = time.time()
            gnn_e = mwpm_dec(syn_te, obs_te, gnn_w, edges, nd)
            dt_dec = time.time()-t1
            gnn_pL = gnn_e.sum()/n_te

            ratio = mwpm_pL/gnn_pL if gnn_pL>0 else float('inf')
            winner = "GNN" if gnn_pL<mwpm_pL else "MWPM" if mwpm_pL<gnn_pL else "tie"

            print(f"    GNN:  {gnn_pL:.4e} ({gnn_e.sum()}/{n_te}) [dec:{dt_dec:.0f}s]")
            print(f"    -> {ratio:.2f}x, {winner} wins")

            results[f'd{d}_rho{rho:.2f}'] = {
                'd':d, 'rho':rho, 'ne':ne, 'n_params':np_count,
                'mwpm_pL':float(mwpm_pL), 'gnn_pL':float(gnn_pL),
                'ratio':float(ratio), 'winner':winner,
                'mwpm_err':int(mwpm_e.sum()), 'gnn_err':int(gnn_e.sum()),
                'n_test':n_te, 'train_time':dt_train, 'infer_time':dt_inf,
            }

            # Save incrementally
            with open(os.path.join(OUT_DIR, 'r1_gnn_fast_results.json'), 'w') as f:
                json.dump(results, f, indent=2)

    elapsed = time.time()-t0
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n"+"="*70)
    print("  GNN DECODER SUMMARY (BATCHED)")
    print("="*70)
    print(f"  {'d':>2} {'rho':>5} {'MWPM':>10} {'GNN':>10} {'Ratio':>7} {'Win':>5}")
    print("  "+"-"*45)
    for k in sorted(results.keys()):
        r = results[k]
        print(f"  {r['d']:>2} {r['rho']:5.2f} {r['mwpm_pL']:10.4e} "
              f"{r['gnn_pL']:10.4e} {r['ratio']:6.2f}x {r['winner']:>5}")

    # Scaling test
    print("\n  SCALING TEST: GNN/MWPM ratio at rho=0.10")
    for d in [3, 5]:
        k = f'd{d}_rho0.10'
        if k in results:
            r = results[k]
            print(f"    d={d}: ratio={r['ratio']:.2f}x ({r['winner']})")

    r3 = results.get('d3_rho0.10', {}).get('ratio', 0)
    r5 = results.get('d5_rho0.10', {}).get('ratio', 0)
    if r5 > 1.0 and r3 > 1.0:
        if r5 > r3:
            print("\n  *** DISCOVERY: GNN advantage GROWS with d!")
        else:
            print("\n  ** GNN beats MWPM at BOTH d=3 and d=5")
    elif r5 > 1.0:
        print("\n  ** GNN beats MWPM at d=5 (but not d=3)")
    elif r3 > 1.0:
        print("\n  * GNN beats MWPM at d=3 only")
    else:
        print("\n  GNN did not beat MWPM")


if __name__ == '__main__':
    main()
