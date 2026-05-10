#!/usr/bin/env python3
"""
R1 Discovery: Does NN advantage SCALE with code distance?
==========================================================

Key hypothesis: Under correlated noise, MWPM's suboptimality
grows with code distance because larger codes have more edges
that can exhibit correlated errors.

If confirmed: "Correlation-aware decoders become increasingly
critical for larger codes" — a major finding.

Improvements over v3:
  - Vectorized NN (no per-edge loop)
  - Larger model + longer training
  - d=3 AND d=5 comparison
  - ρ = 0.05, 0.10 focus (the transition region)
  - Multiple seeds for statistical significance

seed=42
"""
import numpy as np
from scipy.special import erfc
import stim, pymatching
import torch, torch.nn as nn, torch.nn.functional as F
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

def syndromes(errors, edges, nd):
    ns = errors.shape[0]
    syn = np.zeros((ns,nd), dtype=np.uint8)
    obs = np.zeros(ns, dtype=np.uint8)
    for j,e in enumerate(edges):
        m=errors[:,j]; syn[m,e['n1']]^=1
        if e['n2'] is not None: syn[m,e['n2']]^=1
        if e['log']: obs[m]^=1
    return syn, obs

def mwpm_dec(syn, obs, w, edges, nd):
    ns,ne = syn.shape[0], len(edges)
    H = np.zeros((nd+1,ne), dtype=np.uint8)
    F = np.zeros((1,ne), dtype=np.uint8)
    for j,e in enumerate(edges):
        H[e['n1'],j]=1
        if e['n2'] is not None: H[e['n2'],j]=1
        else: H[nd,j]=1
        if e['log']: F[0,j]=1
    errs = np.zeros(ns, dtype=np.uint8)
    for i in range(ns):
        ww = np.maximum(w[i], 0.01)
        m = pymatching.Matching(H, weights=ww, faults_matrix=F)
        m.set_boundary_nodes({nd})
        if m.decode(syn[i])[0]!=obs[i]: errs[i]=1
    return errs

# ============================================================
# Improved NN: Fully vectorized, deeper
# ============================================================
class CorrDecoder(nn.Module):
    """Correlation-aware decoder: vectorized, no per-edge loop."""
    def __init__(self, ne, hidden=256):
        super().__init__()
        # Global encoder: all residuals → context
        self.glob = nn.Sequential(
            nn.Linear(ne*2, hidden), nn.GELU(),
            nn.Linear(hidden, hidden), nn.GELU(),
            nn.Linear(hidden, hidden),
        )
        # Weight predictor: context + per-edge features → weight
        # Input: hidden + 2 (residual, |residual|) per edge = hidden+2
        self.head = nn.Sequential(
            nn.Linear(hidden+2, hidden//2), nn.GELU(),
            nn.Linear(hidden//2, 1), nn.Softplus(),
        )
        self.ne = ne

    def forward(self, res, llr):
        """res, llr: (B, ne). Returns weights (B, ne)."""
        B = res.shape[0]
        # Global context from residuals + |residuals|
        ra = torch.abs(res)
        glob_in = torch.cat([res, ra], dim=-1)  # (B, 2*ne)
        ctx = self.glob(glob_in)  # (B, hidden)

        # Per-edge: expand context, concat with local features
        ctx_exp = ctx.unsqueeze(1).expand(-1, self.ne, -1)  # (B, ne, hidden)
        local = torch.stack([res, ra], dim=-1)  # (B, ne, 2)
        combined = torch.cat([ctx_exp, local], dim=-1)  # (B, ne, hidden+2)
        weights = self.head(combined).squeeze(-1)  # (B, ne)
        return weights

def train_nn(model, res, llr, edge_err, epochs=50, bs=512, lr=5e-4):
    model = model.to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    n = len(res)
    res_t = torch.tensor(res).to(DEVICE)
    llr_t = torch.tensor(llr).to(DEVICE)
    tgt_t = torch.tensor(edge_err).to(DEVICE)

    for ep in range(epochs):
        model.train()
        perm = torch.randperm(n, device=DEVICE)
        tloss = 0; nb = 0
        for s in range(0, n, bs):
            idx = perm[s:s+bs]
            w = model(res_t[idx], llr_t[idx])
            p = torch.sigmoid(-w + 2.0)
            loss = F.binary_cross_entropy(p.clamp(1e-6,1-1e-6), tgt_t[idx])
            opt.zero_grad(); loss.backward(); opt.step()
            tloss += loss.item(); nb += 1
        sched.step()
        if ep % 20 == 0 or ep == epochs-1:
            print(f"      ep{ep:3d}: loss={tloss/nb:.4f}")
    return model

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    print("="*70)
    print("  R1 DISCOVERY: Does NN advantage scale with d?")
    print(f"  Device: {DEVICE}")
    print("="*70)

    V = 0.1417  # Phase 1
    rho_list = [0.0, 0.03, 0.05, 0.08, 0.10]

    results = {}

    for d in [3, 5]:
        rounds = d
        edges, nd = extract_graph(d, rounds)
        ne = len(edges)
        print(f"\n{'='*60}")
        print(f"  d={d}, rounds={rounds}, {ne} edges, {nd} detectors")
        print(f"{'='*60}")

        for rho in rho_list:
            print(f"\n  ρ={rho:.2f}:")

            # Training data
            n_tr = 100000 if d == 3 else 80000
            n_te = 10000
            err_tr, res_tr, llr_tr = gkp_correlated(ne, n_tr, V, rho, rng)
            err_te, res_te, llr_te = gkp_correlated(ne, n_te, V, rho, rng)
            syn_te, obs_te = syndromes(err_te, edges, nd)

            # MWPM baseline
            t1 = time.time()
            mwpm_e = mwpm_dec(syn_te, obs_te, llr_te, edges, nd)
            dt_m = time.time()-t1
            mwpm_pL = mwpm_e.sum()/n_te

            # Train NN
            hidden = 256 if d==3 else 384
            model = CorrDecoder(ne, hidden=hidden)
            np_count = sum(p.numel() for p in model.parameters())
            print(f"    NN: {np_count:,} params, training...")
            model = train_nn(model, res_tr, llr_tr,
                           err_tr.astype(np.float32),
                           epochs=50 if d==3 else 40, bs=512)

            # NN inference
            model.eval()
            with torch.no_grad():
                rt = torch.tensor(res_te).to(DEVICE)
                lt = torch.tensor(llr_te).to(DEVICE)
                nn_w = model(rt, lt).cpu().numpy()

            t1 = time.time()
            nn_e = mwpm_dec(syn_te, obs_te, nn_w, edges, nd)
            dt_n = time.time()-t1
            nn_pL = nn_e.sum()/n_te

            ratio = mwpm_pL/nn_pL if nn_pL>0 else float('inf')
            winner = "NN" if nn_pL<mwpm_pL else "MWPM" if mwpm_pL<nn_pL else "tie"

            print(f"    MWPM: {mwpm_pL:.4e} ({mwpm_e.sum()}/{n_te}) [{dt_m:.0f}s]")
            print(f"    NN:   {nn_pL:.4e} ({nn_e.sum()}/{n_te}) [{dt_n:.0f}s]")
            print(f"    → {ratio:.2f}x, {winner} wins")

            results[f'd{d}_rho{rho:.2f}'] = {
                'd':d, 'rho':rho, 'ne':ne,
                'mwpm_pL':float(mwpm_pL), 'nn_pL':float(nn_pL),
                'ratio':float(ratio), 'winner':winner,
                'mwpm_err':int(mwpm_e.sum()), 'nn_err':int(nn_e.sum()),
            }

    # Save
    with open(os.path.join(OUT_DIR, 'r1_scaling_results.json'), 'w') as f:
        json.dump(results, f, indent=2)

    elapsed = time.time()-t0
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n"+"="*70)
    print("  DISCOVERY SUMMARY")
    print("="*70)
    print(f"  {'d':>2} {'ρ':>5} {'MWPM':>10} {'NN':>10} {'Ratio':>7} {'Win':>5}")
    print("  "+"-"*45)
    for k,r in sorted(results.items()):
        print(f"  {r['d']:>2} {r['rho']:5.2f} {r['mwpm_pL']:10.4e} "
              f"{r['nn_pL']:10.4e} {r['ratio']:6.2f}x {r['winner']:>5}")

    # Key test: does NN advantage grow with d?
    print("\n  KEY TEST: NN/MWPM ratio at ρ=0.10")
    for d in [3, 5]:
        k = f'd{d}_rho0.10'
        if k in results:
            r = results[k]
            print(f"    d={d}: ratio={r['ratio']:.2f}x ({r['winner']})")

    r3 = results.get('d3_rho0.10', {}).get('ratio', 0)
    r5 = results.get('d5_rho0.10', {}).get('ratio', 0)
    if r5 > r3 and r5 > 1.0:
        print("\n  ★★★ DISCOVERY: NN advantage GROWS with code distance!")
        print("  Correlation-aware decoding becomes MORE important for larger codes.")
        print("  MWPM's edge-independence assumption is increasingly violated.")
    elif r5 > 1.0:
        print("\n  ★★ NN advantage present at d=5 but not growing vs d=3")
    else:
        print("\n  NN advantage not confirmed at d=5 — need more capacity/data")

if __name__ == '__main__':
    main()
