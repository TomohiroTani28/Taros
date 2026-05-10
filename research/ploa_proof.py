#!/usr/bin/env python3
"""
PLOA Rigorous Proof — Full Surface Code Decoding
=================================================

Stim (graph structure) + PyMatching (MWPM decoder) + GKP noise model

Comparison:
  Static  — uniform edge weights, hard-decision MWPM
  PLOA    — per-measurement soft weights from GKP homodyne residuals

Key difference from ploa_simulator.py:
  This script performs ACTUAL surface code decoding (not scaling formula).
  Each shot: sample GKP noise → compute syndrome → MWPM decode → check logical error.
"""

import numpy as np
from scipy.special import erfc
import stim
import pymatching
import matplotlib.pyplot as plt
import json
import os
import time

SQRT_PI = np.sqrt(np.pi)


# ============================================================
# Taros Physical Parameters
# ============================================================
def compute_V_eff(sigma_gen_dB, L_dB, V_non_loss=0.010):
    V_sqz = 10.0 ** (-sigma_gen_dB / 10.0)
    eta = 10.0 ** (-L_dB / 10.0)
    return eta * V_sqz + (1.0 - eta) + V_non_loss


def compute_p_phys(V_eff):
    return float(erfc(SQRT_PI / (4.0 * np.sqrt(V_eff / 2.0))) / 2.0)


# ============================================================
# Matching Graph from Stim DEM
# ============================================================
def extract_matching_graph(d):
    """
    Extract matching graph structure from stim's surface code DEM.

    Returns:
        edges: list of dicts {node1, node2, has_logical}
            node2 == None means boundary edge
        n_detectors: number of detector nodes
    """
    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        rounds=1, distance=d,
        before_round_data_depolarization=0.01,
    )
    dem = circuit.detector_error_model(decompose_errors=True)

    edges = []
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        dets = []
        has_logical = False
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                dets.append(t.val)
            elif t.is_logical_observable_id():
                has_logical = True

        if len(dets) == 0:
            continue
        elif len(dets) == 1:
            edges.append({
                'node1': dets[0], 'node2': None, 'has_logical': has_logical
            })
        elif len(dets) == 2:
            edges.append({
                'node1': dets[0], 'node2': dets[1], 'has_logical': has_logical
            })

    n_det = dem.num_detectors
    return edges, n_det


# ============================================================
# GKP Noise Sampling
# ============================================================
def gkp_sample_batch(n_edges, n_shots, V_eff, rng):
    """
    Sample GKP displacement noise for n_edges × n_shots.

    Returns:
        errors:  (n_shots, n_edges) bool
        log_lr:  (n_shots, n_edges) float — log(P(correct|r)/P(error|r))
    """
    sigma = np.sqrt(V_eff)
    delta = sigma * rng.standard_normal((n_shots, n_edges))

    # Nearest GKP lattice point
    n_lattice = np.rint(delta / SQRT_PI).astype(np.int64)

    # Error: crossed to odd lattice point
    errors = (n_lattice % 2) != 0

    # Residual
    residual = delta - n_lattice * SQRT_PI

    # Log-likelihood ratio
    r_abs = np.abs(residual)
    log_lr = ((SQRT_PI - r_abs) ** 2 - r_abs ** 2) / (2.0 * V_eff)
    log_lr = np.clip(log_lr, -30, 30)

    return errors, log_lr


# ============================================================
# Syndrome Computation
# ============================================================
def compute_syndromes_batch(errors, edges, n_detectors):
    """
    Compute detection events and observable flips for a batch of shots.

    Args:
        errors: (n_shots, n_edges) bool
        edges: list of edge dicts
        n_detectors: int

    Returns:
        syndromes: (n_shots, n_detectors) uint8
        obs_flips: (n_shots,) uint8
    """
    n_shots, n_edges = errors.shape
    syndromes = np.zeros((n_shots, n_detectors), dtype=np.uint8)
    obs_flips = np.zeros(n_shots, dtype=np.uint8)

    for j, edge in enumerate(edges):
        mask = errors[:, j]  # (n_shots,) bool
        syndromes[mask, edge['node1']] ^= 1
        if edge['node2'] is not None:
            syndromes[mask, edge['node2']] ^= 1
        if edge['has_logical']:
            obs_flips[mask] ^= 1

    return syndromes, obs_flips


# ============================================================
# Build PyMatching Decoder
# ============================================================
def build_matching(edges, n_detectors, weights):
    """
    Build PyMatching Matching object from edge list.

    Args:
        edges: list of edge dicts
        n_detectors: int
        weights: (n_edges,) float — MWPM edge weights
    """
    n_edges = len(edges)
    boundary = n_detectors  # virtual boundary node

    # Check matrix: (n_detectors+1) × n_edges
    H = np.zeros((n_detectors + 1, n_edges), dtype=np.uint8)
    faults = np.zeros((1, n_edges), dtype=np.uint8)

    for j, edge in enumerate(edges):
        H[edge['node1'], j] = 1
        if edge['node2'] is not None:
            H[edge['node2'], j] = 1
        else:
            H[boundary, j] = 1
        if edge['has_logical']:
            faults[0, j] = 1

    m = pymatching.Matching(H, weights=weights, faults_matrix=faults)
    m.set_boundary_nodes({boundary})
    return m


# ============================================================
# Main Comparison: Static vs PLOA
# ============================================================
def run_comparison(d, V_eff, n_shots, rng, label=""):
    """
    Run full surface code decoding comparison.

    Returns dict with static_pL, ploa_pL, p_phys, etc.
    """
    edges, n_det = extract_matching_graph(d)
    n_edges = len(edges)
    p_phys = compute_p_phys(V_eff)

    # --- Sample all GKP noise at once ---
    errors, log_lr = gkp_sample_batch(n_edges, n_shots, V_eff, rng)
    syndromes, obs_flips = compute_syndromes_batch(errors, edges, n_det)

    # --- Static decoder: uniform weights ---
    uniform_w = np.full(n_edges, max(-np.log(p_phys / (1 - p_phys)), 0.01))
    matching_static = build_matching(edges, n_det, uniform_w)

    static_errors = 0
    ploa_errors = 0

    t0 = time.time()
    for i in range(n_shots):
        syn = syndromes[i]
        actual_obs = obs_flips[i]

        # Static decode
        pred_s = matching_static.decode(syn)
        if pred_s[0] != actual_obs:
            static_errors += 1

        # PLOA decode: per-edge soft weights from GKP measurement
        soft_w = np.maximum(log_lr[i], 0.01)
        matching_ploa = build_matching(edges, n_det, soft_w)
        pred_p = matching_ploa.decode(syn)
        if pred_p[0] != actual_obs:
            ploa_errors += 1

    elapsed = time.time() - t0

    result = {
        'd': d,
        'V_eff': V_eff,
        'p_phys': p_phys,
        'n_shots': n_shots,
        'n_edges': n_edges,
        'static_pL': static_errors / n_shots,
        'ploa_pL': ploa_errors / n_shots,
        'static_errors': static_errors,
        'ploa_errors': ploa_errors,
        'time_s': elapsed,
    }

    ratio = (static_errors / max(ploa_errors, 1))
    print(f"  {label}d={d}  V_eff={V_eff:.4f}  p_phys={p_phys:.4e}  "
          f"Static={static_errors}/{n_shots} ({result['static_pL']:.2e})  "
          f"PLOA={ploa_errors}/{n_shots} ({result['ploa_pL']:.2e})  "
          f"ratio={ratio:.1f}x  [{elapsed:.1f}s]")

    return result


# ============================================================
# Experiment Suite
# ============================================================
def run_all_experiments():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(42)

    print("=" * 75)
    print("  PLOA Rigorous Proof — Stim + PyMatching Surface Code Simulation")
    print("=" * 75)

    # Taros parameters
    sigma_gen = 13.0
    V_non_loss = 0.010
    all_results = []

    # --------------------------------------------------------
    # Experiment 1: Fixed L=0.27dB, vary code distance
    # --------------------------------------------------------
    print("\n[Exp 1] Code distance scaling at L=0.27dB (Phase 2+ PIC)")
    L_dB = 0.27
    V_eff = compute_V_eff(sigma_gen, L_dB, V_non_loss)
    p_phys = compute_p_phys(V_eff)
    print(f"  sigma_eff={-10*np.log10(V_eff):.1f}dB  p_phys={p_phys:.4e}")

    exp1 = []
    for d in [3, 5, 7]:
        n_shots = {3: 200_000, 5: 200_000, 7: 100_000}[d]
        r = run_comparison(d, V_eff, n_shots, rng, label="[E1] ")
        exp1.append(r)

    # --------------------------------------------------------
    # Experiment 2: Fixed d=5, vary loss
    # --------------------------------------------------------
    print("\n[Exp 2] Loss sweep at d=5")
    exp2 = []
    for L in [0.15, 0.20, 0.27, 0.35, 0.40]:
        V = compute_V_eff(sigma_gen, L, V_non_loss)
        r = run_comparison(5, V, 200_000, rng, label=f"[E2 L={L:.2f}] ")
        exp2.append(r)

    # --------------------------------------------------------
    # Experiment 3: High-loss regime (stress test)
    # --------------------------------------------------------
    print("\n[Exp 3] High-loss stress test d=3")
    exp3 = []
    for L in [0.50, 0.60, 0.70, 0.80, 0.90, 1.00]:
        V = compute_V_eff(sigma_gen, L, V_non_loss)
        p = compute_p_phys(V)
        if p > 0.15:
            continue
        r = run_comparison(3, V, 200_000, rng, label=f"[E3 L={L:.2f}] ")
        exp3.append(r)

    all_results = {'exp1': exp1, 'exp2': exp2, 'exp3': exp3}

    # --------------------------------------------------------
    # Plot results
    # --------------------------------------------------------
    plot_results(all_results, out_dir)
    save_results(all_results, out_dir)

    # Summary
    print("\n" + "=" * 75)
    print("  SUMMARY")
    print("=" * 75)
    for exp_name, results in all_results.items():
        for r in results:
            if r['ploa_pL'] > 0:
                ratio = r['static_pL'] / r['ploa_pL']
            else:
                ratio = float('inf')
            print(f"  {exp_name} d={r['d']} p_phys={r['p_phys']:.4e}: "
                  f"Static {r['static_pL']:.2e} / PLOA {r['ploa_pL']:.2e} "
                  f"= {ratio:.1f}x")


# ============================================================
# Visualization
# ============================================================
def plot_results(all_results, out_dir):
    plt.rcParams.update({'font.size': 11, 'axes.grid': True, 'grid.alpha': 0.3})

    # --- Exp 1: Distance scaling ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    fig.suptitle('PLOA Rigorous Proof — Stim + PyMatching\n'
                 'GKP Surface Code: Static vs Soft-Info MWPM',
                 fontsize=13, fontweight='bold')

    exp1 = all_results['exp1']
    if exp1:
        ds = [r['d'] for r in exp1]
        s_pL = [max(r['static_pL'], 1e-7) for r in exp1]
        p_pL = [max(r['ploa_pL'], 1e-7) for r in exp1]

        ax = axes[0]
        ax.semilogy(ds, s_pL, 'r-o', lw=2, ms=8, label='Static (uniform weights)')
        ax.semilogy(ds, p_pL, 'b-s', lw=2, ms=8, label='PLOA (soft weights)')
        ax.set_xlabel('Code Distance d')
        ax.set_ylabel('Logical Error Rate $p_L$')
        ax.set_title(f'Distance Scaling (L=0.27dB, p_phys={exp1[0]["p_phys"]:.4e})')
        ax.legend()

    # --- Exp 2: Loss sweep ---
    exp2 = all_results['exp2']
    if exp2:
        Ls = [-10 * np.log10(
            10 ** (-r['V_eff'] * 0)  # reconstruct L from V_eff... just use p_phys
        ) for r in exp2]
        pp = [r['p_phys'] for r in exp2]
        s_pL = [max(r['static_pL'], 1e-7) for r in exp2]
        p_pL = [max(r['ploa_pL'], 1e-7) for r in exp2]

        ax = axes[1]
        ax.semilogy(pp, s_pL, 'r-o', lw=2, ms=8, label='Static')
        ax.semilogy(pp, p_pL, 'b-s', lw=2, ms=8, label='PLOA')
        ax.set_xlabel('Physical Error Rate $p_{phys}$')
        ax.set_ylabel('Logical Error Rate $p_L$')
        ax.set_title('Loss Sweep (d=5)')
        ax.legend()

    plt.tight_layout()
    path = os.path.join(out_dir, 'fig5_rigorous_proof.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"\n  Saved: {path}")

    # --- Exp 3: Stress test ---
    exp3 = all_results['exp3']
    if exp3:
        fig, ax = plt.subplots(figsize=(8, 5.5))
        pp = [r['p_phys'] for r in exp3]
        s_pL = [max(r['static_pL'], 1e-7) for r in exp3]
        p_pL = [max(r['ploa_pL'], 1e-7) for r in exp3]

        ax.semilogy(pp, s_pL, 'r-o', lw=2, ms=8, label='Static')
        ax.semilogy(pp, p_pL, 'b-s', lw=2, ms=8, label='PLOA')
        ax.set_xlabel('Physical Error Rate $p_{phys}$')
        ax.set_ylabel('Logical Error Rate $p_L$')
        ax.set_title('High-Loss Stress Test (d=3)\nGKP Surface Code: Static vs PLOA',
                     fontweight='bold')
        ax.legend()
        plt.tight_layout()
        path = os.path.join(out_dir, 'fig6_stress_test.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved: {path}")


def save_results(all_results, out_dir):
    # Convert to JSON-serializable
    data = {}
    for key, results in all_results.items():
        data[key] = []
        for r in results:
            data[key].append({k: v for k, v in r.items()})

    path = os.path.join(out_dir, 'rigorous_results.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  Saved: {path}")


if __name__ == '__main__':
    run_all_experiments()
