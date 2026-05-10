#!/usr/bin/env python3
"""
R1 GNN: Graph Neural Network Decoder for Correlated GKP Noise
==============================================================

Why GNN solves the d=5 scaling problem:
  - MLP: treats all 334 edges as flat vector → can't learn graph structure
  - GNN: operates on the matching graph topology → scales naturally with d
  - Message passing propagates correlation information along graph edges
  - Number of parameters is INDEPENDENT of graph size

Architecture:
  1. Build matching graph G = (V_detectors, E_edges) from Stim DEM
  2. Node features: aggregated residuals of incident edges
  3. Edge features: (residual, |residual|, analytical_llr)
  4. GNN message passing: nodes exchange information with neighbors
  5. Edge output: adaptive MWPM weights

Key insight: Correlations create patterns in NEIGHBORING edges' residuals.
GNN can capture these local patterns via message passing, while MLP cannot
efficiently capture the graph-structured correlations.

seed=42
"""
import numpy as np
from scipy.special import erfc
import stim, pymatching
import torch, torch.nn as nn, torch.nn.functional as F
from torch_geometric.nn import GCNConv, GATConv
from torch_geometric.data import Data, Batch
import os, json, time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
DEVICE = 'mps' if torch.backends.mps.is_available() else 'cpu'


# ============================================================
# Physics & Graph (reused)
# ============================================================
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


def build_pyg_graph(edges, n_det):
    """
    Build PyG graph structure from Stim DEM edges.

    We model this as a LINE GRAPH: each DEM edge becomes a NODE,
    and two DEM edges share a PyG edge if they share a detector.

    This is natural because:
    - MWPM operates on edges (error mechanisms)
    - We want to predict per-edge weights
    - Correlations between edges sharing a detector are most important
    """
    n_edges = len(edges)
    boundary = n_det  # virtual boundary node

    # Build adjacency: two DEM edges are connected if they share a detector
    # (including boundary)
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

    edge_index = torch.tensor([src, dst], dtype=torch.long)
    return edge_index


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
# GNN Decoder
# ============================================================
class GNNWeightDecoder(nn.Module):
    """
    GNN that operates on the line graph of the matching graph.

    Each node = one DEM edge (error mechanism).
    Node features = (residual, |residual|, analytical_llr)
    GNN message passing allows each edge to see its neighbors' residuals.
    Output = MWPM weight per edge.

    Key property: parameter count is INDEPENDENT of graph size.
    Same model works for d=3 (66 nodes) and d=5 (334 nodes).
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
            nn.Linear(hidden, hidden//2),
            nn.GELU(),
            nn.Linear(hidden//2, 1),
            nn.Softplus(),  # positive weights
        )

    def forward(self, x, edge_index):
        """
        x: (n_nodes, 3) — per-edge features
        edge_index: (2, n_pyg_edges) — line graph adjacency
        Returns: (n_nodes, 1) — MWPM weights
        """
        h = F.gelu(self.input_proj(x))
        for conv, norm in zip(self.convs, self.norms):
            h = norm(h + F.gelu(conv(h, edge_index)))  # residual + GCN
        return self.output(h)


# ============================================================
# Training
# ============================================================
def train_gnn(model, edge_index, res_train, llr_train, err_train,
              epochs=60, bs=256, lr=1e-3):
    """Train GNN on batches of shots."""
    model = model.to(DEVICE)
    edge_index = edge_index.to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)

    n_shots = len(res_train)
    ne = res_train.shape[1]

    for ep in range(epochs):
        model.train()
        perm = np.random.permutation(n_shots)
        total_loss = 0; nb = 0

        for start in range(0, n_shots, bs):
            idx = perm[start:start+bs]
            batch_size = len(idx)

            # Build batch: stack node features for each shot
            res_b = torch.tensor(res_train[idx], dtype=torch.float32)  # (bs, ne)
            llr_b = torch.tensor(llr_train[idx], dtype=torch.float32)
            tgt_b = torch.tensor(err_train[idx], dtype=torch.float32)

            # Process each shot in batch
            total_batch_loss = 0
            for bi in range(batch_size):
                r = res_b[bi]
                ra = torch.abs(r)
                l = llr_b[bi]
                x = torch.stack([r, ra, l], dim=-1).to(DEVICE)  # (ne, 3)
                target = tgt_b[bi].to(DEVICE)  # (ne,)

                w = model(x, edge_index).squeeze(-1)  # (ne,)
                probs = torch.sigmoid(-w + 2.0)
                loss = F.binary_cross_entropy(
                    probs.clamp(1e-6, 1-1e-6), target)
                total_batch_loss = total_batch_loss + loss

            avg_loss = total_batch_loss / batch_size
            opt.zero_grad()
            avg_loss.backward()
            opt.step()
            total_loss += avg_loss.item(); nb += 1

        sched.step()
        if ep % 20 == 0 or ep == epochs-1:
            print(f"      ep{ep:3d}: loss={total_loss/nb:.4f}")

    return model


def gnn_predict(model, edge_index, res_test, llr_test):
    """Get NN weights for test data."""
    model.eval()
    edge_index = edge_index.to(DEVICE)
    n_shots = len(res_test)
    ne = res_test.shape[1]
    all_weights = np.zeros((n_shots, ne), dtype=np.float32)

    with torch.no_grad():
        for i in range(n_shots):
            r = torch.tensor(res_test[i], dtype=torch.float32)
            ra = torch.abs(r)
            l = torch.tensor(llr_test[i], dtype=torch.float32)
            x = torch.stack([r, ra, l], dim=-1).to(DEVICE)
            w = model(x, edge_index).squeeze(-1).cpu().numpy()
            all_weights[i] = w

    return all_weights


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    print("="*70)
    print("  R1 GNN: Graph Neural Network Decoder")
    print(f"  Device: {DEVICE}")
    print("  Key: same model architecture for d=3 AND d=5")
    print("="*70)

    V = 0.1417  # Phase 1
    rho_list = [0.0, 0.05, 0.08, 0.10]
    results = {}

    for d in [3, 5]:
        rounds = d
        edges, nd = extract_graph(d, rounds)
        ne = len(edges)
        edge_index = build_pyg_graph(edges, nd)

        print(f"\n{'='*60}")
        print(f"  d={d}, {ne} DEM edges, {edge_index.shape[1]} PyG edges")
        print(f"{'='*60}")

        for rho in rho_list:
            print(f"\n  ρ={rho:.2f}:")

            # Data
            n_tr = 50000 if d==3 else 30000
            n_te = 10000 if d==3 else 5000
            err_tr, res_tr, llr_tr = gkp_correlated(ne, n_tr, V, rho, rng)
            err_te, res_te, llr_te = gkp_correlated(ne, n_te, V, rho, rng)
            syn_te, obs_te = compute_syndromes(err_te, edges, nd)

            # MWPM baseline
            t1 = time.time()
            mwpm_e = mwpm_dec(syn_te, obs_te, llr_te, edges, nd)
            dt_m = time.time()-t1
            mwpm_pL = mwpm_e.sum()/n_te

            # Train GNN (same architecture for both d=3 and d=5!)
            model = GNNWeightDecoder(in_features=3, hidden=64, n_layers=4)
            np_count = sum(p.numel() for p in model.parameters())
            print(f"    GNN: {np_count:,} params (same for all d)")

            ep = 60 if d==3 else 40
            bs = 256 if d==3 else 128
            model = train_gnn(model, edge_index, res_tr, llr_tr,
                            err_tr.astype(np.float32),
                            epochs=ep, bs=bs)

            # GNN inference
            t1 = time.time()
            gnn_w = gnn_predict(model, edge_index, res_te, llr_te)
            dt_gnn_inf = time.time()-t1

            # MWPM with GNN weights
            t1 = time.time()
            gnn_e = mwpm_dec(syn_te, obs_te, gnn_w, edges, nd)
            dt_gnn_dec = time.time()-t1
            gnn_pL = gnn_e.sum()/n_te

            ratio = mwpm_pL/gnn_pL if gnn_pL>0 else float('inf')
            winner = "GNN" if gnn_pL<mwpm_pL else "MWPM" if mwpm_pL<gnn_pL else "tie"

            print(f"    MWPM: {mwpm_pL:.4e} ({mwpm_e.sum()}/{n_te}) [{dt_m:.0f}s]")
            print(f"    GNN:  {gnn_pL:.4e} ({gnn_e.sum()}/{n_te}) "
                  f"[inf:{dt_gnn_inf:.0f}s dec:{dt_gnn_dec:.0f}s]")
            print(f"    → {ratio:.2f}x, {winner} wins")

            results[f'd{d}_rho{rho:.2f}'] = {
                'd':d, 'rho':rho, 'ne':ne, 'n_params':np_count,
                'mwpm_pL':float(mwpm_pL), 'gnn_pL':float(gnn_pL),
                'ratio':float(ratio), 'winner':winner,
                'mwpm_err':int(mwpm_e.sum()), 'gnn_err':int(gnn_e.sum()),
                'n_test':n_te,
            }

    # Save
    with open(os.path.join(OUT_DIR, 'r1_gnn_results.json'), 'w') as f:
        json.dump(results, f, indent=2)

    elapsed = time.time()-t0
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n"+"="*70)
    print("  GNN DECODER SUMMARY")
    print("  Same architecture (21K params) for d=3 AND d=5")
    print("="*70)
    print(f"  {'d':>2} {'ρ':>5} {'MWPM':>10} {'GNN':>10} {'Ratio':>7} {'Win':>5}")
    print("  "+"-"*45)
    for k in sorted(results.keys()):
        r = results[k]
        print(f"  {r['d']:>2} {r['rho']:5.2f} {r['mwpm_pL']:10.4e} "
              f"{r['gnn_pL']:10.4e} {r['ratio']:6.2f}x {r['winner']:>5}")

    # Scaling test
    print("\n  SCALING TEST: GNN/MWPM ratio at ρ=0.10")
    for d in [3, 5]:
        k = f'd{d}_rho0.10'
        if k in results:
            r = results[k]
            print(f"    d={d}: ratio={r['ratio']:.2f}x ({r['winner']})")

    r3 = results.get('d3_rho0.10', {}).get('ratio', 0)
    r5 = results.get('d5_rho0.10', {}).get('ratio', 0)
    if r5 > 1.0 and r3 > 1.0:
        if r5 > r3:
            print("\n  ★★★ DISCOVERY: GNN advantage GROWS with d!")
        else:
            print("\n  ★★ GNN beats MWPM at BOTH d=3 and d=5")
    elif r5 > 1.0:
        print("\n  ★★ GNN beats MWPM at d=5 (but not d=3)")
    elif r3 > 1.0:
        print("\n  ★ GNN beats MWPM at d=3 only — d=5 needs more work")
    else:
        print("\n  GNN did not beat MWPM — architecture/training needs revision")


if __name__ == '__main__':
    main()
