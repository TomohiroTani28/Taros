#!/usr/bin/env python3
"""
Exp-A2: Code Distance Scaling for Room-Temperature FT Photonic Architecture
============================================================================

Theme 1 — Track A: End-to-End QEC Simulation

Goal: Verify that the TAROS CV Pure Portable architecture achieves
      fault-tolerant error suppression across code distances d=3,5,7,9
      at the three design operating points.

Physics model:
  - GKP displacement noise via beamsplitter model
  - V_eff = η × V_sqz + (1-η) + V_non_loss
  - Soft-info MWPM decoder (per-edge log-likelihood from GKP residuals)
  - Code-capacity noise model (single round)

Operating points:
  Phase 1      : σ_gen=13dB, L=0.39dB, V_nl=0.010 → σ_eff=8.5dB
  Phase 2+ Real: σ_gen=13dB, L=0.27dB, V_nl=0.010 → σ_eff=9.3dB
  Phase 2+ Lim : σ_gen=13dB, L=0.15dB, V_nl=0.000 → σ_eff=10.8dB

Outputs:
  - Distance scaling plot (p_L vs d) for each operating point
  - Threshold crossing plot (p_L vs p_phys) for each d
  - Scaling law fit: p_L = A × (p/p_th)^((d+1)/2)
  - JSON data for reproducibility

seed=42, all results reproducible.
"""

import numpy as np
from scipy.special import erfc
from scipy.optimize import curve_fit
import stim
import pymatching
import json
import os
import time
import sys

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')


# ============================================================
# Physics: Taros CV Noise Model
# ============================================================
def compute_V_eff(sigma_gen_dB, L_dB, V_non_loss=0.010):
    """Beamsplitter model: V_eff = η V_sqz + (1-η) + V_nl"""
    V_sqz = 10.0 ** (-sigma_gen_dB / 10.0)
    eta = 10.0 ** (-L_dB / 10.0)
    return eta * V_sqz + (1.0 - eta) + V_non_loss


def compute_sigma_eff(V_eff):
    """Effective squeezing in dB"""
    return -10.0 * np.log10(V_eff)


def compute_p_phys(V_eff):
    """GKP physical error rate (macronode BS noise folding)"""
    return float(erfc(SQRT_PI / (4.0 * np.sqrt(V_eff / 2.0))) / 2.0)


# ============================================================
# TAROS Operating Points
# ============================================================
OPERATING_POINTS = {
    'Phase 1 (L=0.39dB)': {
        'sigma_gen': 13.0, 'L_dB': 0.39, 'V_nl': 0.010,
        'color': '#e74c3c', 'marker': 'o',
    },
    'Phase 2+ Real (L=0.27dB)': {
        'sigma_gen': 13.0, 'L_dB': 0.27, 'V_nl': 0.010,
        'color': '#2ecc71', 'marker': 's',
    },
    'Phase 2+ Limit (L=0.15dB)': {
        'sigma_gen': 13.0, 'L_dB': 0.15, 'V_nl': 0.000,
        'color': '#3498db', 'marker': 'D',
    },
}


# ============================================================
# Matching Graph from Stim DEM
# ============================================================
def extract_matching_graph(d):
    """Extract matching graph structure from Stim's rotated surface code DEM."""
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

        if len(dets) == 1:
            edges.append({'node1': dets[0], 'node2': None, 'has_logical': has_logical})
        elif len(dets) == 2:
            edges.append({'node1': dets[0], 'node2': dets[1], 'has_logical': has_logical})

    return edges, dem.num_detectors


# ============================================================
# GKP Noise Sampling + Syndrome + Decoding
# ============================================================
def gkp_sample_batch(n_edges, n_shots, V_eff, rng):
    """Sample GKP displacement noise. Returns errors and log-likelihood ratios."""
    sigma = np.sqrt(V_eff)
    delta = sigma * rng.standard_normal((n_shots, n_edges))
    n_lattice = np.rint(delta / SQRT_PI).astype(np.int64)
    errors = (n_lattice % 2) != 0
    residual = delta - n_lattice * SQRT_PI
    r_abs = np.abs(residual)
    log_lr = ((SQRT_PI - r_abs) ** 2 - r_abs ** 2) / (2.0 * V_eff)
    log_lr = np.clip(log_lr, -30, 30)
    return errors, log_lr


def compute_syndromes_batch(errors, edges, n_detectors):
    """Compute detection events and observable flips."""
    n_shots = errors.shape[0]
    syndromes = np.zeros((n_shots, n_detectors), dtype=np.uint8)
    obs_flips = np.zeros(n_shots, dtype=np.uint8)
    for j, edge in enumerate(edges):
        mask = errors[:, j]
        syndromes[mask, edge['node1']] ^= 1
        if edge['node2'] is not None:
            syndromes[mask, edge['node2']] ^= 1
        if edge['has_logical']:
            obs_flips[mask] ^= 1
    return syndromes, obs_flips


def build_matching(edges, n_detectors, weights):
    """Build PyMatching decoder."""
    n_edges = len(edges)
    boundary = n_detectors
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
# Core Simulation
# ============================================================
def run_single(d, V_eff, n_shots, rng, use_soft_info=True):
    """Run surface code QEC simulation at given distance and noise level.

    Returns dict with p_L, n_errors, n_shots, etc.
    """
    edges, n_det = extract_matching_graph(d)
    n_edges = len(edges)
    p_phys = compute_p_phys(V_eff)

    errors, log_lr = gkp_sample_batch(n_edges, n_shots, V_eff, rng)
    syndromes, obs_flips = compute_syndromes_batch(errors, edges, n_det)

    n_logical_errors = 0

    if use_soft_info:
        # Soft-info MWPM: per-shot edge weights from GKP residuals
        for i in range(n_shots):
            soft_w = np.maximum(log_lr[i], 0.01)
            matching = build_matching(edges, n_det, soft_w)
            pred = matching.decode(syndromes[i])
            if pred[0] != obs_flips[i]:
                n_logical_errors += 1
    else:
        # Hard-decision MWPM: uniform weights
        uniform_w = np.full(n_edges, max(-np.log(p_phys / (1 - p_phys)), 0.01))
        matching = build_matching(edges, n_det, uniform_w)
        for i in range(n_shots):
            pred = matching.decode(syndromes[i])
            if pred[0] != obs_flips[i]:
                n_logical_errors += 1

    p_L = n_logical_errors / n_shots
    return {
        'd': d,
        'V_eff': float(V_eff),
        'sigma_eff_dB': float(compute_sigma_eff(V_eff)),
        'p_phys': float(p_phys),
        'n_shots': n_shots,
        'n_errors': n_logical_errors,
        'p_L': float(p_L),
        'soft_info': use_soft_info,
    }


# ============================================================
# Exp-A2: Distance Scaling at TAROS Operating Points
# ============================================================
def run_exp_a2(rng):
    """Sweep d=3,5,7,9 at three TAROS operating points."""
    print("=" * 70)
    print("  Exp-A2: Code Distance Scaling — TAROS Operating Points")
    print("=" * 70)

    distances = [3, 5, 7, 9]

    # Adaptive shot counts: more shots for lower error rates
    def get_n_shots(d, sigma_eff_dB):
        if sigma_eff_dB > 10.0:
            # Very low error rate — need many shots
            return {3: 500_000, 5: 1_000_000, 7: 2_000_000, 9: 2_000_000}[d]
        elif sigma_eff_dB > 9.0:
            return {3: 300_000, 5: 500_000, 7: 1_000_000, 9: 1_000_000}[d]
        else:
            return {3: 200_000, 5: 300_000, 7: 500_000, 9: 500_000}[d]

    results = {}

    for name, params in OPERATING_POINTS.items():
        V_eff = compute_V_eff(params['sigma_gen'], params['L_dB'], params['V_nl'])
        sigma_eff = compute_sigma_eff(V_eff)
        p_phys = compute_p_phys(V_eff)

        print(f"\n--- {name} ---")
        print(f"  V_eff={V_eff:.4f} SNU, σ_eff={sigma_eff:.1f}dB, p_phys={p_phys:.4e}")

        point_results = []
        for d in distances:
            n_shots = get_n_shots(d, sigma_eff)
            t0 = time.time()

            # Soft-info MWPM
            r_soft = run_single(d, V_eff, n_shots, rng, use_soft_info=True)
            elapsed = time.time() - t0

            # Also run hard-decision for comparison at d=3
            r_hard = None
            if d == 3:
                r_hard = run_single(d, V_eff, min(n_shots, 200_000), rng, use_soft_info=False)

            ratio_str = ""
            if r_hard and r_soft['p_L'] > 0:
                ratio = r_hard['p_L'] / r_soft['p_L']
                ratio_str = f"  hard/soft={ratio:.1f}x"

            p_L_str = f"{r_soft['p_L']:.2e}" if r_soft['p_L'] > 0 else "<1/{:,}".format(n_shots)
            print(f"  d={d}: p_L={p_L_str} ({r_soft['n_errors']}/{n_shots})"
                  f"{ratio_str}  [{elapsed:.1f}s]")

            entry = {
                'soft': r_soft,
                'hard': r_hard,
            }
            point_results.append(entry)

        results[name] = {
            'params': {
                'sigma_gen': params['sigma_gen'],
                'L_dB': params['L_dB'],
                'V_nl': params['V_nl'],
                'V_eff': float(V_eff),
                'sigma_eff_dB': float(sigma_eff),
                'p_phys': float(p_phys),
            },
            'distances': point_results,
        }

    return results


# ============================================================
# Exp-A2b: Loss Sweep for Threshold Determination
# ============================================================
def run_exp_a2b(rng):
    """Sweep loss at d=3,5,7 to find threshold crossing."""
    print("\n" + "=" * 70)
    print("  Exp-A2b: Loss Sweep — Threshold Crossing")
    print("=" * 70)

    distances = [3, 5, 7]
    # Sweep L from 0.1 to 1.5 dB (covering sub-threshold to above-threshold)
    L_values = [0.10, 0.15, 0.20, 0.27, 0.35, 0.45, 0.55, 0.70, 0.90, 1.10, 1.30]
    sigma_gen = 13.0
    V_nl = 0.010

    results = []

    for L_dB in L_values:
        V_eff = compute_V_eff(sigma_gen, L_dB, V_nl)
        sigma_eff = compute_sigma_eff(V_eff)
        p_phys = compute_p_phys(V_eff)

        if p_phys > 0.10:
            continue  # Skip above 10% — too noisy

        print(f"\n  L={L_dB:.2f}dB  σ_eff={sigma_eff:.1f}dB  p_phys={p_phys:.4e}")

        for d in distances:
            # More shots for lower error rates
            if p_phys < 0.003:
                n_shots = {3: 500_000, 5: 1_000_000, 7: 2_000_000}[d]
            elif p_phys < 0.01:
                n_shots = {3: 200_000, 5: 500_000, 7: 500_000}[d]
            else:
                n_shots = {3: 100_000, 5: 200_000, 7: 200_000}[d]

            t0 = time.time()
            r = run_single(d, V_eff, n_shots, rng, use_soft_info=True)
            elapsed = time.time() - t0

            p_L_str = f"{r['p_L']:.2e}" if r['p_L'] > 0 else f"<1/{n_shots:,}"
            print(f"    d={d}: p_L={p_L_str} ({r['n_errors']}/{n_shots})  [{elapsed:.1f}s]")

            results.append({
                'L_dB': L_dB,
                'sigma_eff_dB': float(sigma_eff),
                **r,
            })

    return results


# ============================================================
# Scaling Law Fit
# ============================================================
def fit_scaling_law(results_a2):
    """Fit p_L = A × (p/p_th)^((d+1)/2) to determine A and p_th."""
    print("\n" + "=" * 70)
    print("  Scaling Law Fit: p_L = A × (p/p_th)^((d+1)/2)")
    print("=" * 70)

    fits = {}

    for name, data in results_a2.items():
        p_phys = data['params']['p_phys']
        ds = []
        p_Ls = []

        for entry in data['distances']:
            r = entry['soft']
            if r['p_L'] > 0 and r['n_errors'] >= 3:  # Need minimum statistics
                ds.append(r['d'])
                p_Ls.append(r['p_L'])

        if len(ds) < 2:
            print(f"\n  {name}: insufficient data for fit")
            continue

        ds = np.array(ds)
        p_Ls = np.array(p_Ls)

        # Fit: log(p_L) = log(A) + ((d+1)/2) × log(p/p_th)
        # With p_phys fixed, fit A and p_th
        def model(d_arr, log_A, log_p_ratio):
            return log_A + ((d_arr + 1) / 2.0) * log_p_ratio

        try:
            popt, pcov = curve_fit(
                model,
                ds, np.log(p_Ls),
                p0=[np.log(0.03), np.log(0.3)],
            )
            A_fit = np.exp(popt[0])
            p_ratio_fit = np.exp(popt[1])  # p/p_th
            p_th_fit = p_phys / p_ratio_fit

            # Lambda (suppression factor)
            Lambda = 1.0 / p_ratio_fit

            perr = np.sqrt(np.diag(pcov))

            print(f"\n  {name}:")
            print(f"    A = {A_fit:.4f}")
            print(f"    p/p_th = {p_ratio_fit:.4f}")
            print(f"    p_th (inferred) = {p_th_fit:.4e}")
            print(f"    Λ = 1/(p/p_th) = {Lambda:.2f}")
            print(f"    Residuals: {np.sqrt(np.mean((model(ds, *popt) - np.log(p_Ls))**2)):.3f}")

            fits[name] = {
                'A': float(A_fit),
                'p_ratio': float(p_ratio_fit),
                'p_th': float(p_th_fit),
                'Lambda': float(Lambda),
                'ds': ds.tolist(),
                'p_Ls': p_Ls.tolist(),
            }
        except Exception as e:
            print(f"\n  {name}: fit failed — {e}")

    return fits


# ============================================================
# Design Document Verification
# ============================================================
def verify_design_values(results_a2):
    """Compare simulation results with design document predictions."""
    print("\n" + "=" * 70)
    print("  Design Document Verification")
    print("=" * 70)

    # Expected values from design/13_performance.md and 06_noise-budget.md
    expected = {
        'Phase 1 (L=0.39dB)': {
            'sigma_eff': 8.5, 'p_phys': 9.3e-3,
            'p_L_d7_MWPM': 4.4e-3,  # break-even boundary
        },
        'Phase 2+ Real (L=0.27dB)': {
            'sigma_eff': 9.3, 'p_phys': 4.9e-3,
            'p_L_d7_MWPM': 3.3e-4,  # product spec
        },
        'Phase 2+ Limit (L=0.15dB)': {
            'sigma_eff': 10.8, 'p_phys': 1.0e-3,
            'p_L_d7_MWPM': 6.1e-7,  # theoretical limit
        },
    }

    for name, data in results_a2.items():
        if name not in expected:
            continue
        exp = expected[name]
        params = data['params']

        print(f"\n  {name}:")
        print(f"    σ_eff: design={exp['sigma_eff']:.1f}dB, sim={params['sigma_eff_dB']:.1f}dB"
              f"  {'OK' if abs(params['sigma_eff_dB'] - exp['sigma_eff']) < 0.2 else 'MISMATCH'}")
        print(f"    p_phys: design={exp['p_phys']:.2e}, sim={params['p_phys']:.2e}"
              f"  ratio={params['p_phys']/exp['p_phys']:.2f}")

        # Find d=7 result
        for entry in data['distances']:
            r = entry['soft']
            if r['d'] == 7:
                if r['p_L'] > 0:
                    ratio = r['p_L'] / exp['p_L_d7_MWPM']
                    print(f"    p_L(d=7): design={exp['p_L_d7_MWPM']:.2e}, sim={r['p_L']:.2e}"
                          f"  ratio={ratio:.2f}"
                          f"  {'OK (within 3x)' if 0.3 < ratio < 3.0 else 'CHECK'}")
                else:
                    print(f"    p_L(d=7): design={exp['p_L_d7_MWPM']:.2e}, sim=0"
                          f"  (no errors in {r['n_shots']:,} shots)")


# ============================================================
# Visualization
# ============================================================
def plot_results(results_a2, results_a2b, fits):
    """Generate publication-quality plots."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available — skipping plots")
        return

    plt.rcParams.update({
        'font.size': 11, 'axes.grid': True, 'grid.alpha': 0.3,
        'figure.dpi': 150,
    })

    # --- Fig 1: Distance Scaling ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('Exp-A2: GKP Surface Code Distance Scaling\n'
                 'Room-Temperature CV Photonic Architecture (Soft-Info MWPM)',
                 fontsize=13, fontweight='bold')

    for ax_idx, (name, data) in enumerate(results_a2.items()):
        ax = axes[ax_idx]
        params = data['params']

        ds = []
        p_Ls = []
        n_errors_list = []
        for entry in data['distances']:
            r = entry['soft']
            ds.append(r['d'])
            p_Ls.append(r['p_L'] if r['p_L'] > 0 else 1.0 / r['n_shots'])
            n_errors_list.append(r['n_errors'])

        color = OPERATING_POINTS[name]['color']
        marker = OPERATING_POINTS[name]['marker']

        ax.semilogy(ds, p_Ls, f'-{marker}', color=color, lw=2, ms=8,
                    label=f'Soft-info MWPM')

        # Annotate with error counts
        for i, (d, pL, ne) in enumerate(zip(ds, p_Ls, n_errors_list)):
            if ne > 0:
                ax.annotate(f'{ne}err', (d, pL), textcoords='offset points',
                            xytext=(5, 5), fontsize=8, color='gray')

        # Scaling law fit overlay
        if name in fits:
            f = fits[name]
            d_cont = np.linspace(2.5, 9.5, 50)
            p_L_fit = f['A'] * f['p_ratio'] ** ((d_cont + 1) / 2)
            ax.semilogy(d_cont, p_L_fit, '--', color=color, alpha=0.5, lw=1,
                        label=f'Fit: Λ={f["Lambda"]:.1f}')

        # Reference lines
        ax.axhline(1e-3, color='gray', ls=':', alpha=0.5, label='p_L=10⁻³')
        ax.axhline(1e-6, color='gray', ls='-.', alpha=0.3)

        ax.set_xlabel('Code Distance d')
        ax.set_ylabel('Logical Error Rate $p_L$')
        ax.set_title(f'{name}\nσ_eff={params["sigma_eff_dB"]:.1f}dB, '
                     f'p_phys={params["p_phys"]:.2e}')
        ax.set_xticks([3, 5, 7, 9])
        ax.set_ylim(bottom=1e-8)
        ax.legend(fontsize=9)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_a2_distance_scaling.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"\n  Saved: {path}")

    # --- Fig 2: Threshold Crossing ---
    if results_a2b:
        fig, ax = plt.subplots(figsize=(9, 6))
        fig.suptitle('Exp-A2b: Threshold Crossing\n'
                     'GKP Surface Code with Soft-Info MWPM (σ_gen=13dB)',
                     fontsize=13, fontweight='bold')

        colors_d = {3: '#e74c3c', 5: '#f39c12', 7: '#2ecc71', 9: '#3498db'}
        markers_d = {3: 'o', 5: 's', 7: 'D', 9: '^'}

        for d in [3, 5, 7]:
            pp = [r['p_phys'] for r in results_a2b if r['d'] == d and r['p_L'] > 0]
            pL = [r['p_L'] for r in results_a2b if r['d'] == d and r['p_L'] > 0]
            if pp:
                ax.loglog(pp, pL, f'-{markers_d[d]}', color=colors_d[d],
                          lw=2, ms=7, label=f'd={d}')

        # Mark TAROS operating points
        for name, params in OPERATING_POINTS.items():
            V = compute_V_eff(params['sigma_gen'], params['L_dB'], params['V_nl'])
            p = compute_p_phys(V)
            ax.axvline(p, color='gray', ls=':', alpha=0.3)
            ax.text(p, ax.get_ylim()[0] * 3, name.split('(')[0].strip(),
                    rotation=90, fontsize=7, color='gray', va='bottom')

        # p_L = p_phys line (break-even)
        pp_range = np.logspace(-4, -1, 50)
        ax.loglog(pp_range, pp_range, 'k--', alpha=0.3, label='p_L = p_phys')

        ax.set_xlabel('Physical Error Rate $p_{phys}$')
        ax.set_ylabel('Logical Error Rate $p_L$')
        ax.legend()
        ax.set_xlim(5e-4, 0.1)

        plt.tight_layout()
        path = os.path.join(OUT_DIR, 'fig_a2b_threshold.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved: {path}")

    # --- Fig 3: Combined Summary ---
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.suptitle('TAROS Room-Temperature FT Architecture\n'
                 'Logical Error Rate vs Code Distance (All Phases)',
                 fontsize=13, fontweight='bold')

    for name, data in results_a2.items():
        params = data['params']
        ds = []
        p_Ls = []
        for entry in data['distances']:
            r = entry['soft']
            if r['p_L'] > 0:
                ds.append(r['d'])
                p_Ls.append(r['p_L'])

        color = OPERATING_POINTS[name]['color']
        marker = OPERATING_POINTS[name]['marker']
        short_name = name.split('(')[0].strip()

        if ds:
            ax.semilogy(ds, p_Ls, f'-{marker}', color=color, lw=2.5, ms=10,
                        label=f'{short_name} (σ_eff={params["sigma_eff_dB"]:.1f}dB)')

    ax.axhline(1e-3, color='gray', ls=':', alpha=0.5, lw=1)
    ax.text(9.2, 1e-3, 'Product spec\n(p_L ≤ 10⁻³)', fontsize=8, color='gray', va='center')
    ax.axhline(1e-6, color='gray', ls='-.', alpha=0.3, lw=1)
    ax.text(9.2, 1e-6, 'High-perf', fontsize=8, color='gray', va='center')

    ax.set_xlabel('Code Distance d', fontsize=12)
    ax.set_ylabel('Logical Error Rate $p_L$', fontsize=12)
    ax.set_xticks([3, 5, 7, 9])
    ax.legend(fontsize=10, loc='upper right')
    ax.set_ylim(bottom=1e-8)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_a2_summary.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {path}")


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)

    print("\n  TAROS Theme 1 — Track A: Room-Temperature FT Photonic Architecture")
    print("  Exp-A2: Code Distance Scaling Simulation")
    print(f"  Stim {stim.__version__}, PyMatching {pymatching.__version__}")
    print()

    # Print operating points
    print("  Operating Points:")
    for name, params in OPERATING_POINTS.items():
        V = compute_V_eff(params['sigma_gen'], params['L_dB'], params['V_nl'])
        print(f"    {name}: σ_eff={compute_sigma_eff(V):.1f}dB, "
              f"p_phys={compute_p_phys(V):.4e}")

    t_start = time.time()

    # Run experiments
    results_a2 = run_exp_a2(rng)
    results_a2b = run_exp_a2b(rng)

    # Fit scaling law
    fits = fit_scaling_law(results_a2)

    # Verify against design documents
    verify_design_values(results_a2)

    # Save results
    all_data = {
        'exp_a2': {},
        'exp_a2b': results_a2b,
        'fits': fits,
        'metadata': {
            'seed': 42,
            'stim_version': stim.__version__,
            'pymatching_version': pymatching.__version__,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        },
    }
    # Convert exp_a2 for JSON serialization
    for name, data in results_a2.items():
        all_data['exp_a2'][name] = data

    json_path = os.path.join(OUT_DIR, 'exp_a2_results.json')
    with open(json_path, 'w') as f:
        json.dump(all_data, f, indent=2, default=str)
    print(f"\n  Saved: {json_path}")

    # Plot
    plot_results(results_a2, results_a2b, fits)

    elapsed = time.time() - t_start
    print(f"\n  Total time: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Final summary
    print("\n" + "=" * 70)
    print("  SUMMARY: Room-Temperature FT Architecture Verification")
    print("=" * 70)

    for name, data in results_a2.items():
        params = data['params']
        print(f"\n  {name} (σ_eff={params['sigma_eff_dB']:.1f}dB):")
        for entry in data['distances']:
            r = entry['soft']
            p_L_str = f"{r['p_L']:.2e}" if r['p_L'] > 0 else f"<{1/r['n_shots']:.1e}"
            status = ""
            if r['d'] == 7:
                if r['p_L'] > 0 and r['p_L'] < 1e-3:
                    status = "  << PRODUCT SPEC MET"
                elif r['p_L'] > 0 and r['p_L'] < 0.01:
                    status = "  << BREAK-EVEN"
                elif r['p_L'] == 0:
                    status = "  << NO ERRORS (needs more shots)"
            print(f"    d={r['d']}: p_L = {p_L_str}{status}")

    if fits:
        print("\n  Scaling Law (p_L = A × (p/p_th)^((d+1)/2)):")
        for name, f in fits.items():
            print(f"    {name}: A={f['A']:.4f}, p_th={f['p_th']:.4e}, Λ={f['Lambda']:.1f}")


if __name__ == '__main__':
    main()
