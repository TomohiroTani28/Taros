#!/usr/bin/env python3
"""
R1 v3: Correlation-Aware GKP Decoder
======================================

KEY INSIGHT: For INDEPENDENT GKP noise, analytical LLR is optimal.
NN cannot beat MWPM because the per-edge LLR is a sufficient statistic.

But for CORRELATED noise (common pump RIN, ρ > 0), the analytical
formula is SUBOPTIMAL because it treats edges independently.
The optimal weight for edge j depends on residuals of OTHER edges.

This is the genuine gap where ML can help:
  - MWPM: w_j = f(r_j, V)          ← ignores correlations
  - NN:   w_j = g(r_1,...,r_n, V)   ← captures correlations

Architecture:
  GKP residuals (all edges) → Correlation-aware NN → edge weights → MWPM

We sweep ρ = 0, 0.01, 0.03, 0.05, 0.10 and show:
  - ρ=0: NN ≈ MWPM (no correlation to exploit)
  - ρ>0: NN > MWPM (captures inter-edge correlations)

This directly addresses RESEARCH_REPORT.md §6: "Edge independence assumption"

seed=42
"""

import numpy as np
from scipy.special import erfc
import stim
import pymatching
import torch
import torch.nn as nn
import torch.nn.functional as F
import os
import json
import time

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


def gkp_sample_correlated(n_edges, n_shots, V_eff, rho, rng):
    """Sample GKP noise with inter-edge correlation ρ."""
    sigma = np.sqrt(V_eff)
    if rho <= 0:
        delta = sigma * rng.standard_normal((n_shots, n_edges))
    else:
        indep = sigma * np.sqrt(1-rho) * rng.standard_normal((n_shots, n_edges))
        common = sigma * np.sqrt(rho) * rng.standard_normal((n_shots, 1))
        delta = indep + common

    n_lat = np.rint(delta / SQRT_PI).astype(np.int64)
    errors = (n_lat % 2) != 0
    residual = delta - n_lat * SQRT_PI
    r_abs = np.abs(residual)
    # Analytical LLR (assumes independence — suboptimal when ρ>0)
    llr = np.clip(((SQRT_PI - r_abs)**2 - r_abs**2) / (2*V_eff), -30, 30)
    return errors, residual.astype(np.float32), llr.astype(np.float32)


def compute_syndromes(errors, edges, n_det):
    n_shots = errors.shape[0]
    syn = np.zeros((n_shots, n_det), dtype=np.uint8)
    obs = np.zeros(n_shots, dtype=np.uint8)
    for j, e in enumerate(edges):
        m = errors[:, j]; syn[m, e['n1']] ^= 1
        if e['n2'] is not None: syn[m, e['n2']] ^= 1
        if e['log']: obs[m] ^= 1
    return syn, obs


def mwpm_decode(syn, obs, weights, edges, n_det):
    n_shots, n_edges = syn.shape[0], len(edges)
    bnd = n_det
    H = np.zeros((n_det+1, n_edges), dtype=np.uint8)
    F_mat = np.zeros((1, n_edges), dtype=np.uint8)
    for j, e in enumerate(edges):
        H[e['n1'],j]=1
        if e['n2'] is not None: H[e['n2'],j]=1
        else: H[bnd,j]=1
        if e['log']: F_mat[0,j]=1
    errs = np.zeros(n_shots, dtype=np.uint8)
    for i in range(n_shots):
        w = np.maximum(weights[i], 0.01)
        m = pymatching.Matching(H, weights=w, faults_matrix=F_mat)
        m.set_boundary_nodes({bnd})
        if m.decode(syn[i])[0] != obs[i]: errs[i]=1
    return errs


# ============================================================
# Correlation-Aware Weight Network
# ============================================================
class CorrelationAwareWeights(nn.Module):
    """
    Produces edge weights that account for inter-edge correlations.

    Key difference from per-edge processing:
    ALL residuals are processed together, allowing the network
    to learn correlation patterns.

    Architecture: residuals → global context → per-edge weights
    """
    def __init__(self, n_edges, hidden=128):
        super().__init__()
        # Global context from all residuals
        self.global_enc = nn.Sequential(
            nn.Linear(n_edges, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
        )
        # Per-edge output combining local + global
        self.per_edge = nn.Sequential(
            nn.Linear(hidden + 3, hidden // 2), nn.ReLU(),
            nn.Linear(hidden // 2, 1), nn.Softplus(),
        )
        self.n_edges = n_edges

    def forward(self, residuals, analytical_llr):
        """
        residuals: (batch, n_edges)
        analytical_llr: (batch, n_edges)
        Returns: weights (batch, n_edges)
        """
        # Global context
        ctx = self.global_enc(residuals)  # (batch, hidden)

        # Per-edge features + global context
        r_abs = torch.abs(residuals)
        weights = []
        for j in range(self.n_edges):
            local = torch.stack([
                residuals[:, j], r_abs[:, j], analytical_llr[:, j]
            ], dim=-1)  # (batch, 3)
            combined = torch.cat([ctx, local], dim=-1)  # (batch, hidden+3)
            w_j = self.per_edge(combined)  # (batch, 1)
            weights.append(w_j)

        return torch.cat(weights, dim=-1)  # (batch, n_edges)


# ============================================================
# Main experiment
# ============================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    print("=" * 70)
    print("  R1 v3: Correlation-Aware GKP Decoder")
    print(f"  Device: {DEVICE}")
    print("  Hypothesis: NN beats MWPM ONLY when ρ > 0")
    print("=" * 70)

    d, rounds = 3, 3
    V_eff = 0.1417  # Phase 1
    n_train = 80000
    n_test = 10000

    edges, n_det = extract_graph(d, rounds)
    n_edges = len(edges)
    print(f"\n  d={d}, rounds={rounds}, {n_edges} edges")

    rho_values = [0.0, 0.01, 0.03, 0.05, 0.10, 0.15]
    all_results = {}

    for rho in rho_values:
        print(f"\n{'='*50}")
        print(f"  ρ = {rho:.2f}")
        print(f"{'='*50}")

        # Generate training data
        errors_tr, res_tr, llr_tr = gkp_sample_correlated(
            n_edges, n_train, V_eff, rho, rng)
        syn_tr, obs_tr = compute_syndromes(errors_tr, edges, n_det)

        # Generate test data
        errors_te, res_te, llr_te = gkp_sample_correlated(
            n_edges, n_test, V_eff, rho, rng)
        syn_te, obs_te = compute_syndromes(errors_te, edges, n_det)

        # --- MWPM baseline (analytical LLR, assumes independence) ---
        t1 = time.time()
        mwpm_errs = mwpm_decode(syn_te, obs_te, llr_te, edges, n_det)
        dt_mwpm = time.time() - t1
        mwpm_pL = mwpm_errs.sum() / n_test

        # --- Train correlation-aware NN ---
        model = CorrelationAwareWeights(n_edges, hidden=128).to(DEVICE)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

        # Train: per-edge error prediction (supervised)
        res_t = torch.tensor(res_tr, dtype=torch.float32)
        llr_t = torch.tensor(llr_tr, dtype=torch.float32)
        edge_err_t = torch.tensor(errors_tr.astype(np.float32))

        print(f"  Training NN ({sum(p.numel() for p in model.parameters()):,} params)...")
        model.train()
        for epoch in range(30):
            perm = torch.randperm(n_train)
            total_loss = 0
            for start in range(0, n_train, 1024):
                idx = perm[start:start+1024]
                r = res_t[idx].to(DEVICE)
                l = llr_t[idx].to(DEVICE)
                tgt = edge_err_t[idx].to(DEVICE)

                w = model(r, l)
                probs = torch.sigmoid(-w + 2.0)
                loss = F.binary_cross_entropy(probs.clamp(1e-6, 1-1e-6), tgt)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            if epoch % 10 == 0 or epoch == 29:
                print(f"    epoch {epoch}: loss={total_loss/(n_train//1024):.4f}")

        # --- Evaluate NN weights ---
        model.eval()
        with torch.no_grad():
            r_te_t = torch.tensor(res_te, dtype=torch.float32).to(DEVICE)
            l_te_t = torch.tensor(llr_te, dtype=torch.float32).to(DEVICE)
            nn_weights = model(r_te_t, l_te_t).cpu().numpy()

        t1 = time.time()
        nn_errs = mwpm_decode(syn_te, obs_te, nn_weights, edges, n_det)
        dt_nn = time.time() - t1
        nn_pL = nn_errs.sum() / n_test

        # --- Results ---
        ratio = mwpm_pL / nn_pL if nn_pL > 0 else float('inf')
        winner = "NN" if nn_pL < mwpm_pL else "MWPM" if mwpm_pL < nn_pL else "tie"

        print(f"\n  Results (ρ={rho:.2f}):")
        print(f"    MWPM (analytical): p_L={mwpm_pL:.4e} ({mwpm_errs.sum()}/{n_test})")
        print(f"    NN (corr-aware):   p_L={nn_pL:.4e} ({nn_errs.sum()}/{n_test})")
        print(f"    Ratio: {ratio:.2f}x → {winner} wins")

        all_results[f'rho_{rho:.2f}'] = {
            'rho': rho, 'mwpm_pL': float(mwpm_pL), 'nn_pL': float(nn_pL),
            'ratio': float(ratio), 'winner': winner,
            'mwpm_errors': int(mwpm_errs.sum()), 'nn_errors': int(nn_errs.sum()),
        }

    # Save
    with open(os.path.join(OUT_DIR, 'r1_v3_correlated_results.json'), 'w') as f:
        json.dump(all_results, f, indent=2)

    elapsed = time.time() - t0
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n" + "=" * 70)
    print("  R1 v3 SUMMARY")
    print("  Hypothesis: NN beats MWPM only when ρ > 0")
    print("=" * 70)
    print(f"  {'ρ':>5}  {'MWPM':>10}  {'NN':>10}  {'Ratio':>7}  {'Winner':>6}")
    print("  " + "-" * 48)
    for key, r in all_results.items():
        print(f"  {r['rho']:5.2f}  {r['mwpm_pL']:10.4e}  {r['nn_pL']:10.4e}  "
              f"{r['ratio']:6.2f}x  {r['winner']:>6}")

    # Conclusion
    print("\n  Interpretation:")
    rho0 = all_results.get('rho_0.00', {})
    rho10 = all_results.get('rho_0.10', {})
    if rho0.get('winner') == 'MWPM' and rho10.get('winner') == 'NN':
        print("  ✓ Hypothesis CONFIRMED: NN advantage emerges only with correlations")
        print("  ✓ Analytical LLR is optimal for independent noise")
        print("  ✓ Correlation-aware NN breaks MWPM's edge-independence assumption")
    else:
        print("  Results require further analysis")


if __name__ == '__main__':
    main()
