#!/usr/bin/env python3
"""
R1 v2: FiLM-GKP Weight Adapter + MWPM Decoder
===============================================

CORRECT architecture:
  GKP residuals + V_eff → NN → adaptive edge weights → MWPM → correction

The NN does NOT replace MWPM. Instead, it learns to produce
BETTER edge weights than the analytical LLR formula, especially
under time-varying noise where the analytical formula uses stale V_eff.

This breaks MWPM's scale invariance because:
  - Analytical LLR: w(r,V) = (1/V)g(r) → scale invariant
  - NN weights: w = f_θ(r, V_eff) → can learn V_eff-dependent corrections

Training:
  - Generate samples with KNOWN labels (from syndrome + actual error)
  - Train NN to produce weights that minimize MWPM decoding errors
  - Use REINFORCE or straight-through estimator since MWPM is non-differentiable

Simplified approach for Phase 2:
  - Train NN to predict per-edge error probabilities
  - Convert to MWPM weights: w_j = -log(p_j / (1-p_j))
  - Compare with analytical LLR weights

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


# ============================================================
# Physics (same as before)
# ============================================================
def compute_V_eff(sg, L, Vnl=0.010):
    V_sqz = 10**(-sg/10); eta = 10**(-L/10)
    return eta*V_sqz + (1-eta) + Vnl

def compute_p_phys(V):
    return float(erfc(SQRT_PI/(4*np.sqrt(V/2)))/2)

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


# ============================================================
# Data generation with per-edge labels
# ============================================================
def generate_edge_labeled_data(d, rounds, V_eff_func, n_shots, rng):
    """
    Generate data with per-edge error labels for supervised training.

    V_eff_func: callable(shot_idx) → V_eff for that shot
    Returns residuals, edge_errors, syndromes, obs_flips, V_effs
    """
    edges, n_det = extract_graph(d, rounds)
    n_edges = len(edges)

    # Sample with potentially varying V_eff
    all_residuals = np.zeros((n_shots, n_edges), dtype=np.float32)
    all_errors = np.zeros((n_shots, n_edges), dtype=bool)
    all_llr = np.zeros((n_shots, n_edges), dtype=np.float32)
    V_effs = np.zeros(n_shots, dtype=np.float32)

    for i in range(n_shots):
        V = V_eff_func(i)
        V_effs[i] = V
        sigma = np.sqrt(V)
        delta = sigma * rng.standard_normal(n_edges)
        n_lat = np.rint(delta / SQRT_PI).astype(np.int64)
        all_errors[i] = (n_lat % 2) != 0
        all_residuals[i] = delta - n_lat * SQRT_PI
        r_abs = np.abs(all_residuals[i])
        all_llr[i] = np.clip(((SQRT_PI - r_abs)**2 - r_abs**2) / (2*V), -30, 30)

    # Syndromes
    syndromes = np.zeros((n_shots, n_det), dtype=np.uint8)
    obs_flips = np.zeros(n_shots, dtype=np.uint8)
    for j, e in enumerate(edges):
        m = all_errors[:, j]
        syndromes[m, e['n1']] ^= 1
        if e['n2'] is not None: syndromes[m, e['n2']] ^= 1
        if e['log']: obs_flips[m] ^= 1

    return {
        'residuals': all_residuals,
        'edge_errors': all_errors.astype(np.float32),
        'llr': all_llr,
        'syndromes': syndromes,
        'obs_flips': obs_flips,
        'V_effs': V_effs,
        'edges': edges,
        'n_det': n_det,
    }


# ============================================================
# MWPM decoder (takes arbitrary weights)
# ============================================================
def mwpm_decode_with_weights(syndromes, obs_flips, weights, edges, n_det):
    """Decode using provided per-shot weights."""
    n_shots = syndromes.shape[0]
    n_edges = len(edges)
    bnd = n_det
    H = np.zeros((n_det + 1, n_edges), dtype=np.uint8)
    F = np.zeros((1, n_edges), dtype=np.uint8)
    for j, e in enumerate(edges):
        H[e['n1'], j] = 1
        if e['n2'] is not None: H[e['n2'], j] = 1
        else: H[bnd, j] = 1
        if e['log']: F[0, j] = 1

    logical_errors = np.zeros(n_shots, dtype=np.uint8)
    for i in range(n_shots):
        w = np.maximum(weights[i], 0.01)
        m = pymatching.Matching(H, weights=w, faults_matrix=F)
        m.set_boundary_nodes({bnd})
        pred = m.decode(syndromes[i])
        if pred[0] != obs_flips[i]:
            logical_errors[i] = 1
    return logical_errors


# ============================================================
# FiLM Weight Adapter Network
# ============================================================
class FiLMWeightAdapter(nn.Module):
    """
    Produces adaptive MWPM edge weights from GKP residuals.

    Input: GKP residuals (n_edges,) + V_eff (scalar)
    Output: edge weights (n_edges,) for MWPM

    The key insight: this network can learn V_eff-dependent
    corrections that the analytical LLR formula cannot capture,
    breaking MWPM's scale invariance.
    """
    def __init__(self, n_edges, hidden_dim=64, cond_dim=8):
        super().__init__()
        self.n_edges = n_edges

        # Conditioning on V_eff
        self.cond_enc = nn.Sequential(
            nn.Linear(1, cond_dim), nn.ReLU(),
            nn.Linear(cond_dim, cond_dim), nn.ReLU(),
        )

        # Per-edge feature extraction
        # Each edge gets: (residual, |residual|, analytical_llr)
        self.edge_feat = nn.Sequential(
            nn.Linear(3, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
        )

        # FiLM modulation
        self.film_gamma = nn.Linear(cond_dim, hidden_dim)
        self.film_beta = nn.Linear(cond_dim, hidden_dim)

        # Weight output
        self.weight_head = nn.Sequential(
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
            nn.Softplus(),  # Weights must be positive
        )

    def forward(self, residuals, analytical_llr, V_eff):
        """
        residuals: (batch, n_edges)
        analytical_llr: (batch, n_edges)
        V_eff: (batch,)
        Returns: weights (batch, n_edges) — positive values for MWPM
        """
        batch_size = residuals.shape[0]

        # Conditioning
        cond = self.cond_enc(V_eff.unsqueeze(-1))  # (batch, cond_dim)

        # Per-edge features: (residual, |residual|, analytical_llr)
        r_abs = torch.abs(residuals)
        edge_input = torch.stack([residuals, r_abs, analytical_llr], dim=-1)
        # (batch, n_edges, 3)

        # Process each edge
        h = self.edge_feat(edge_input)  # (batch, n_edges, hidden)

        # FiLM modulation
        gamma = self.film_gamma(cond).unsqueeze(1)  # (batch, 1, hidden)
        beta = self.film_beta(cond).unsqueeze(1)
        h = gamma * h + beta

        # Output weights
        weights = self.weight_head(h).squeeze(-1)  # (batch, n_edges)
        return weights


# ============================================================
# Training via edge-level supervision
# ============================================================
def train_weight_adapter(model, data, epochs=30, lr=1e-3, batch_size=512):
    """
    Train the weight adapter to predict per-edge error probabilities.

    The NN learns: residuals + V_eff → P(edge_error)
    Then weights = -log(p / (1-p)) are used for MWPM.

    We train on per-edge labels (supervised), which is much faster
    than REINFORCE on logical error labels.
    """
    device = DEVICE
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    residuals_t = torch.tensor(data['residuals'], dtype=torch.float32)
    llr_t = torch.tensor(data['llr'], dtype=torch.float32)
    V_t = torch.tensor(data['V_effs'], dtype=torch.float32)
    edge_errors_t = torch.tensor(data['edge_errors'], dtype=torch.float32)

    n = len(residuals_t)
    n_edges = residuals_t.shape[1]

    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(n)
        total_loss = 0
        n_batches = 0

        for start in range(0, n, batch_size):
            idx = perm[start:start+batch_size]
            res = residuals_t[idx].to(device)
            llr = llr_t[idx].to(device)
            V = V_t[idx].to(device)
            targets = edge_errors_t[idx].to(device)

            # Forward: get adaptive weights
            weights = model(res, llr, V)  # (batch, n_edges)

            # Convert weights to probabilities for loss
            # weight = -log(p/(1-p)) → p = 1/(1+exp(weight))
            # But we use softplus output, so weight > 0 always
            # p = sigmoid(-weight) approximately
            probs = torch.sigmoid(-weights + 2.0)  # shift for reasonable range

            # Binary cross-entropy on per-edge error prediction
            loss = F.binary_cross_entropy(
                probs.clamp(1e-6, 1-1e-6), targets, reduction='mean')

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        if epoch % 10 == 0 or epoch == epochs - 1:
            avg_loss = total_loss / n_batches
            print(f"    Epoch {epoch:3d}: loss={avg_loss:.4f}")

    return model


# ============================================================
# Main experiment
# ============================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    print("=" * 70)
    print("  R1 v2: FiLM-GKP Weight Adapter + MWPM")
    print(f"  Device: {DEVICE}")
    print("=" * 70)

    d, rounds = 3, 3
    V_base = compute_V_eff(13.0, 0.39, 0.010)  # Phase 1

    # ========================================
    # Generate training data with MIXED V_eff (for FiLM training)
    # ========================================
    print("\n  Generating mixed-V_eff training data...")
    n_train = 50000

    def V_mixed(i):
        """Random V_eff in [0.10, 0.22] for diverse training."""
        return 0.10 + (i % 100) / 100 * 0.12

    train_data = generate_edge_labeled_data(d, rounds, V_mixed, n_train, rng)
    print(f"    {n_train} shots, {train_data['residuals'].shape[1]} edges")

    # ========================================
    # Train weight adapter
    # ========================================
    n_edges = train_data['residuals'].shape[1]
    model = FiLMWeightAdapter(n_edges, hidden_dim=64, cond_dim=8)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"    Model: {n_params:,} parameters")

    print("\n  Training weight adapter...")
    model = train_weight_adapter(model, train_data, epochs=30, lr=1e-3)

    # ========================================
    # Generate test scenarios
    # ========================================
    print("\n  Generating test scenarios...")
    n_test = 5000

    scenarios = {
        'static': lambda i: V_base,
        'drift': lambda i: V_base + 0.05 * i / n_test,
        'spike': lambda i: V_base * (2.0 if n_test//3 <= i < 2*n_test//3 else 1.0),
        'mismatch': lambda i: V_base * 1.5,  # V_eff 50% higher than expected
    }

    results = {}

    for scenario_name, V_func in scenarios.items():
        print(f"\n  === {scenario_name} ===")
        test_data = generate_edge_labeled_data(d, rounds, V_func, n_test, rng)

        edges = test_data['edges']
        n_det = test_data['n_det']
        syndromes = test_data['syndromes']
        obs_flips = test_data['obs_flips']

        # --- Baseline: Analytical LLR weights (standard soft-info MWPM) ---
        analytical_weights = test_data['llr']
        t1 = time.time()
        mwpm_errors = mwpm_decode_with_weights(
            syndromes, obs_flips, analytical_weights, edges, n_det)
        dt_mwpm = time.time() - t1
        mwpm_pL = mwpm_errors.sum() / n_test

        # --- FiLM-GKP: NN-generated weights ---
        model.eval()
        with torch.no_grad():
            res_t = torch.tensor(test_data['residuals'], dtype=torch.float32).to(DEVICE)
            llr_t = torch.tensor(test_data['llr'], dtype=torch.float32).to(DEVICE)
            # Use NOMINAL V_eff (what the system THINKS V_eff is)
            V_nominal = torch.full((n_test,), V_base, dtype=torch.float32).to(DEVICE)
            nn_weights = model(res_t, llr_t, V_nominal).cpu().numpy()

        t1 = time.time()
        film_errors = mwpm_decode_with_weights(
            syndromes, obs_flips, nn_weights, edges, n_det)
        dt_film = time.time() - t1
        film_pL = film_errors.sum() / n_test

        # --- Comparison ---
        ratio = mwpm_pL / film_pL if film_pL > 0 else float('inf')
        better = "FiLM" if film_pL < mwpm_pL else "MWPM" if mwpm_pL < film_pL else "tie"

        print(f"    MWPM (analytical LLR): p_L={mwpm_pL:.4e} "
              f"({mwpm_errors.sum()}/{n_test}) [{dt_mwpm:.1f}s]")
        print(f"    FiLM-GKP (NN weights): p_L={film_pL:.4e} "
              f"({film_errors.sum()}/{n_test}) [{dt_film:.1f}s]")
        print(f"    Ratio: {ratio:.2f}x → {better} wins")

        results[scenario_name] = {
            'mwpm_pL': float(mwpm_pL),
            'film_pL': float(film_pL),
            'mwpm_errors': int(mwpm_errors.sum()),
            'film_errors': int(film_errors.sum()),
            'n_test': n_test,
            'ratio': float(ratio),
            'better': better,
        }

    # Save
    with open(os.path.join(OUT_DIR, 'r1_v2_results.json'), 'w') as f:
        json.dump(results, f, indent=2)

    elapsed = time.time() - t0
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Final summary
    print("\n" + "=" * 70)
    print("  R1 v2 SUMMARY: FiLM-GKP Weight Adapter vs MWPM Soft-Info")
    print("=" * 70)
    print(f"  {'Scenario':<15} {'MWPM':>10} {'FiLM-GKP':>10} {'Ratio':>8} {'Winner':>8}")
    print("  " + "-" * 55)
    for name, r in results.items():
        mwpm_s = f"{r['mwpm_pL']:.2e}"
        film_s = f"{r['film_pL']:.2e}"
        print(f"  {name:<15} {mwpm_s:>10} {film_s:>10} {r['ratio']:>7.2f}x {r['better']:>8}")


if __name__ == '__main__':
    main()
