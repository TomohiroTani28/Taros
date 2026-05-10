#!/usr/bin/env python3
"""
Exp-A3b: GKP Multi-Round QEC with Soft-Info MWPM
=================================================

The definitive CV-specific simulation:
  - GKP displacement noise (NOT depolarizing)
  - Multi-round syndrome extraction (d rounds)
  - Soft-info MWPM (per-edge LLR from GKP residuals)
  - p_meas = p_data (CV homodyne: measurement noise = data noise)

This bridges Exp-A2 (GKP soft-info, code-capacity) and
Exp-A3 (multi-round, hard-decision). The combination gives
the physically correct prediction for CV homodyne QEC.

Approach:
  1. Extract 3D matching graph from Stim's multi-round DEM
  2. Classify edges as space-like (data) or time-like (measurement)
  3. Sample GKP displacement noise for ALL edges (V_eff for both)
  4. Compute per-edge soft-info LLR
  5. Decode with PyMatching (per-shot weights)

seed=42
"""

import numpy as np
from scipy.special import erfc
import stim
import pymatching
import json
import os
import time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')


def compute_V_eff(sigma_gen_dB, L_dB, V_non_loss=0.010):
    V_sqz = 10.0 ** (-sigma_gen_dB / 10.0)
    eta = 10.0 ** (-L_dB / 10.0)
    return eta * V_sqz + (1.0 - eta) + V_non_loss


def compute_sigma_eff(V_eff):
    return -10.0 * np.log10(V_eff)


def compute_p_phys(V_eff):
    return float(erfc(SQRT_PI / (4.0 * np.sqrt(V_eff / 2.0))) / 2.0)


# ============================================================
# Extract 3D matching graph from multi-round DEM
# ============================================================
def extract_multiround_graph(d, rounds=None):
    """
    Extract matching graph from Stim's multi-round surface code DEM.

    Uses a dummy error rate — we only need the graph structure,
    not the probabilities (we replace them with GKP noise).
    """
    if rounds is None:
        rounds = d

    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        rounds=rounds,
        distance=d,
        before_round_data_depolarization=0.01,
        before_measure_flip_probability=0.01,
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

    n_det = dem.num_detectors
    return edges, n_det


# ============================================================
# GKP noise sampling
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
    """Build PyMatching decoder with given weights."""
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
# Core: Multi-round GKP QEC with soft-info
# ============================================================
def run_multiround_gkp(d, V_eff, n_shots, rng, rounds=None, use_soft_info=True):
    """
    Multi-round GKP surface code QEC.

    Key CV physics: ALL edges (space-like and time-like) have
    GKP displacement noise with the same V_eff, because homodyne
    measurement noise has the same origin as data qubit noise.
    """
    if rounds is None:
        rounds = d

    edges, n_det = extract_multiround_graph(d, rounds)
    n_edges = len(edges)
    p_phys = compute_p_phys(V_eff)

    # Sample GKP noise for ALL edges (data + measurement)
    errors, log_lr = gkp_sample_batch(n_edges, n_shots, V_eff, rng)
    syndromes, obs_flips = compute_syndromes_batch(errors, edges, n_det)

    n_logical_errors = 0

    if use_soft_info:
        for i in range(n_shots):
            soft_w = np.maximum(log_lr[i], 0.01)
            matching = build_matching(edges, n_det, soft_w)
            pred = matching.decode(syndromes[i])
            if pred[0] != obs_flips[i]:
                n_logical_errors += 1
    else:
        uniform_w = np.full(n_edges, max(-np.log(p_phys / (1 - p_phys)), 0.01))
        matching = build_matching(edges, n_det, uniform_w)
        for i in range(n_shots):
            pred = matching.decode(syndromes[i])
            if pred[0] != obs_flips[i]:
                n_logical_errors += 1

    p_L = n_logical_errors / n_shots
    return {
        'd': d,
        'rounds': rounds,
        'V_eff': float(V_eff),
        'sigma_eff_dB': float(compute_sigma_eff(V_eff)),
        'p_phys': float(p_phys),
        'n_shots': n_shots,
        'n_errors': n_logical_errors,
        'p_L': float(p_L),
        'soft_info': use_soft_info,
        'n_edges': n_edges,
        'n_detectors': n_det,
    }


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t_start = time.time()

    print("=" * 70)
    print("  Exp-A3b: GKP Multi-Round QEC with Soft-Info MWPM")
    print("  The Definitive CV-Specific Simulation")
    print("=" * 70)

    points = [
        ('Phase 1',        13.0, 0.39, 0.010),
        ('Phase 2+ Real',  13.0, 0.27, 0.010),
        ('Phase 2+ Limit', 13.0, 0.15, 0.000),
    ]

    distances = [3, 5, 7]
    all_results = {}

    # ========================================
    # Part 1: Multi-round with soft-info at TAROS operating points
    # ========================================
    print("\n--- Part 1: GKP Multi-Round Soft-Info MWPM ---\n")

    for name, sg, L, Vnl in points:
        V = compute_V_eff(sg, L, Vnl)
        p = compute_p_phys(V)
        s = compute_sigma_eff(V)
        print(f"\n{'='*55}")
        print(f"  {name}: σ_eff={s:.1f}dB, p_phys={p:.4e}")
        print(f"{'='*55}")

        point_data = []
        for d in distances:
            n_shots = 100_000 if p > 0.003 else 200_000

            # Multi-round soft-info (CV-correct model)
            t0 = time.time()
            r_soft = run_multiround_gkp(d, V, n_shots, rng,
                                        rounds=d, use_soft_info=True)
            dt_soft = time.time() - t0

            # Multi-round hard-decision (for comparison)
            t0 = time.time()
            r_hard = run_multiround_gkp(d, V, min(n_shots, 50_000), rng,
                                        rounds=d, use_soft_info=False)
            dt_hard = time.time() - t0

            # Code-capacity soft-info (for ratio)
            r_cc = run_multiround_gkp(d, V, n_shots, rng,
                                      rounds=1, use_soft_info=True)

            pL_soft = f"{r_soft['p_L']:.2e}" if r_soft['p_L'] > 0 else f"<{1/n_shots:.1e}"
            pL_hard = f"{r_hard['p_L']:.2e}" if r_hard['p_L'] > 0 else f"<{1/r_hard['n_shots']:.1e}"
            pL_cc   = f"{r_cc['p_L']:.2e}" if r_cc['p_L'] > 0 else f"<{1/n_shots:.1e}"

            # Ratios
            ratio_str = ""
            if r_soft['p_L'] > 0 and r_hard['p_L'] > 0:
                ratio = r_hard['p_L'] / r_soft['p_L']
                ratio_str = f"  soft-info gain={ratio:.1f}x"

            mr_cc_str = ""
            if r_soft['p_L'] > 0 and r_cc['p_L'] > 0:
                mr_ratio = r_soft['p_L'] / r_cc['p_L']
                mr_cc_str = f"  MR/CC={mr_ratio:.1f}x"

            print(f"  d={d} ({r_soft['n_edges']} edges, {d} rounds):")
            print(f"    CC soft-info:  {pL_cc}  [{r_cc['n_errors']}/{n_shots}]")
            print(f"    MR hard:       {pL_hard}  [{r_hard['n_errors']}/{r_hard['n_shots']}]")
            print(f"    MR soft-info:  {pL_soft}  [{r_soft['n_errors']}/{n_shots}]"
                  f"{ratio_str}{mr_cc_str}  [{dt_soft:.1f}s]")

            point_data.append({
                'cc_soft': r_cc,
                'mr_hard': r_hard,
                'mr_soft': r_soft,
            })

        all_results[name] = {
            'params': {'sigma_eff': float(s), 'p_phys': float(p), 'L_dB': L},
            'data': point_data,
        }

    # ========================================
    # Part 2: Loss sweep (multi-round soft-info)
    # ========================================
    print("\n\n--- Part 2: Threshold Sweep (GKP Multi-Round Soft-Info) ---\n")

    threshold_data = []
    for L_dB in [0.10, 0.15, 0.20, 0.27, 0.35, 0.50, 0.70, 1.00, 1.30]:
        V = compute_V_eff(13.0, L_dB, 0.010)
        p = compute_p_phys(V)
        s = compute_sigma_eff(V)
        if p > 0.08:
            continue

        print(f"  L={L_dB:.2f}dB  σ_eff={s:.1f}dB  p_phys={p:.4e}")
        for d in [3, 5, 7]:
            ns = 50_000 if p > 0.01 else 100_000
            r = run_multiround_gkp(d, V, ns, rng, rounds=d, use_soft_info=True)
            pL = f"{r['p_L']:.2e}" if r['p_L'] > 0 else f"<{1/ns:.1e}"
            print(f"    d={d}: p_L={pL} ({r['n_errors']}/{ns})")
            threshold_data.append({**r, 'L_dB': L_dB})

    # ========================================
    # Save
    # ========================================
    save = {
        'operating_points': {k: v for k, v in all_results.items()},
        'threshold': threshold_data,
        'metadata': {
            'seed': 42,
            'description': 'GKP multi-round with soft-info MWPM — CV-correct model',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        },
    }
    json_path = os.path.join(OUT_DIR, 'exp_a3b_results.json')
    with open(json_path, 'w') as f:
        json.dump(save, f, indent=2, default=str)
    print(f"\n  Saved: {json_path}")

    # ========================================
    # Plots
    # ========================================
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.rcParams.update({'font.size': 11, 'axes.grid': True, 'grid.alpha': 0.3})

        # Fig: Comprehensive 4-model comparison
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        fig.suptitle('Exp-A3b: CV-Correct QEC Model — GKP Multi-Round + Soft-Info MWPM\n'
                     'Four Models: CC-Hard, CC-Soft, MR-Hard, MR-Soft (seed=42)',
                     fontsize=13, fontweight='bold')

        colors_model = {
            'cc_soft': '#3498db',
            'mr_hard': '#e67e22',
            'mr_soft': '#e74c3c',
        }
        labels_model = {
            'cc_soft': 'Code-cap + Soft-info',
            'mr_hard': 'Multi-round + Hard',
            'mr_soft': 'Multi-round + Soft-info (CV model)',
        }
        markers_model = {
            'cc_soft': 'o',
            'mr_hard': 's',
            'mr_soft': 'D',
        }

        for ax_idx, (name, data) in enumerate(all_results.items()):
            ax = axes[ax_idx]
            params = data['params']

            for model_key in ['cc_soft', 'mr_hard', 'mr_soft']:
                ds, pLs = [], []
                for entry in data['data']:
                    r = entry[model_key]
                    if r['p_L'] > 0:
                        ds.append(r['d'])
                        pLs.append(r['p_L'])
                if ds:
                    ax.semilogy(ds, pLs,
                               f'-{markers_model[model_key]}',
                               color=colors_model[model_key],
                               lw=2, ms=8, label=labels_model[model_key])

            ax.axhline(1e-3, color='gray', ls=':', alpha=0.4)
            ax.set_xlabel('Code Distance d')
            ax.set_ylabel('Logical Error Rate $p_L$')
            ax.set_title(f'{name}\nσ_eff={params["sigma_eff"]:.1f}dB')
            ax.set_xticks([3, 5, 7])
            ax.legend(fontsize=8)
            if ax.get_ylim()[0] < 1e-7:
                ax.set_ylim(bottom=1e-7)

        plt.tight_layout()
        path = os.path.join(OUT_DIR, 'fig_a3b_cv_correct.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Plot: {path}")

        # Fig: Threshold (GKP multi-round soft-info)
        fig, ax = plt.subplots(figsize=(9, 6))
        colors_d = {3: '#e74c3c', 5: '#f39c12', 7: '#2ecc71'}
        for d in [3, 5, 7]:
            subset = [r for r in threshold_data if r['d'] == d and r['p_L'] > 0]
            if subset:
                pp = [r['p_phys'] for r in subset]
                pL = [r['p_L'] for r in subset]
                ax.loglog(pp, pL, '-o', color=colors_d[d], lw=2, ms=7, label=f'd={d}')

        pp_ref = np.logspace(-4, -0.5, 50)
        ax.loglog(pp_ref, pp_ref, 'k--', alpha=0.2, label='p_L = p_phys')
        ax.set_xlabel('Physical Error Rate $p_{phys}$')
        ax.set_ylabel('Logical Error Rate $p_L$')
        ax.set_title('GKP Multi-Round Soft-Info MWPM — Threshold\n'
                     '(CV-correct phenomenological model, σ_gen=13dB)',
                     fontweight='bold')
        ax.legend()
        plt.tight_layout()
        path = os.path.join(OUT_DIR, 'fig_a3b_threshold.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Plot: {path}")

    except ImportError:
        print("  matplotlib not available")

    elapsed = time.time() - t_start
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # ========================================
    # Final Summary Table
    # ========================================
    print("\n" + "=" * 70)
    print("  DEFINITIVE RESULTS: CV-Correct QEC Model")
    print("  (GKP displacement noise + multi-round + soft-info MWPM)")
    print("=" * 70)

    print(f"\n  {'Phase':<22} {'d':>2}  {'CC+Soft':>10}  {'MR+Hard':>10}  "
          f"{'MR+Soft':>10}  {'Design doc':>10}")
    print("  " + "-" * 72)

    design_ref = {
        'Phase 1':        {7: 4.4e-3},
        'Phase 2+ Real':  {7: 3.3e-4},
        'Phase 2+ Limit': {7: 6.1e-7},
    }

    for name, data in all_results.items():
        for entry in data['data']:
            d = entry['mr_soft']['d']
            cc = entry['cc_soft']['p_L']
            hard = entry['mr_hard']['p_L']
            soft = entry['mr_soft']['p_L']
            design = design_ref.get(name, {}).get(d, None)

            cc_s = f"{cc:.2e}" if cc > 0 else f"<{1/entry['cc_soft']['n_shots']:.0e}"
            hard_s = f"{hard:.2e}" if hard > 0 else f"<{1/entry['mr_hard']['n_shots']:.0e}"
            soft_s = f"{soft:.2e}" if soft > 0 else f"<{1/entry['mr_soft']['n_shots']:.0e}"
            design_s = f"{design:.2e}" if design else "—"

            marker = ""
            if d == 7 and soft > 0 and soft < 1e-3:
                marker = " << PRODUCT"
            elif d == 7 and soft == 0:
                marker = " << EXCELLENT"

            print(f"  {name:<22} d={d}  {cc_s:>10}  {hard_s:>10}  "
                  f"{soft_s:>10}  {design_s:>10}{marker}")


if __name__ == '__main__':
    main()
