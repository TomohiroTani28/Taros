#!/usr/bin/env python3
"""
Exp-B3: Drift-Adaptive Decoder
================================

Photonic Quantum Digital Twin — Experiment 3 (Core Contribution)

Goal: Demonstrate that adapting MWPM decoder weights to the estimated
      V_eff(t) maintains fault tolerance under drift, while a static
      decoder fails.

Three decoders compared:
  1. Static: Fixed weights from initial V_eff(t=0)
  2. Adaptive: Weights updated using syndrome-estimated V_eff(t)
  3. Oracle: Weights from true V_eff(t) (theoretical optimum)

Key result: Adaptive decoder extends fault-tolerance lifetime by N×
           compared to static decoder, approaching oracle performance.

seed=42
"""

import numpy as np
from scipy.special import erfc
import stim
import pymatching
import json
import os
import time
import sys

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')


# ============================================================
# Physics
# ============================================================
def compute_V_eff(sigma_gen_dB, L_dB, V_non_loss=0.010):
    V_sqz = 10.0 ** (-sigma_gen_dB / 10.0)
    eta = 10.0 ** (-L_dB / 10.0)
    return eta * V_sqz + (1.0 - eta) + V_non_loss


def compute_sigma_eff(V_eff):
    return -10.0 * np.log10(V_eff)


def compute_p_phys(V_eff):
    return float(erfc(SQRT_PI / (4.0 * np.sqrt(V_eff / 2.0))) / 2.0)


# ============================================================
# Graph extraction
# ============================================================
def extract_matching_graph(d, rounds=None):
    if rounds is None:
        rounds = d
    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        rounds=rounds, distance=d,
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
    return edges, dem.num_detectors


# ============================================================
# Online V_eff estimator (best from Exp-B2: Kalman filter)
# ============================================================
class KalmanEstimator:
    def __init__(self, V_eff_init, process_noise=1e-6):
        self.x = V_eff_init
        self.P = 1e-4
        self.Q = process_noise

    def update(self, residuals):
        n = len(residuals)
        z = np.var(residuals)
        if z < np.pi / 3:
            z = z / (1.0 - 2.0 * z / np.pi)
        R = 2.0 * self.x ** 2 / max(n, 1)
        P_pred = self.P + self.Q
        K = P_pred / (P_pred + R)
        self.x = self.x + K * (z - self.x)
        self.P = (1.0 - K) * P_pred
        self.x = max(self.x, 0.01)
        return self.x


# ============================================================
# QEC with selectable decoder mode
# ============================================================
def run_qec_adaptive(edges, n_det, V_eff_true, V_eff_decoder,
                     n_shots, rng, use_soft_info=True):
    """
    Run QEC with noise at V_eff_true but decoder calibrated to V_eff_decoder.

    This models the mismatch between actual hardware noise and decoder's
    assumed noise level. The adaptive decoder minimizes this mismatch.

    Returns: (p_L, residuals_flat)
    """
    n_edges = len(edges)

    # Sample noise at TRUE V_eff
    sigma_true = np.sqrt(V_eff_true)
    delta = sigma_true * rng.standard_normal((n_shots, n_edges))
    n_lattice = np.rint(delta / SQRT_PI).astype(np.int64)
    errors = (n_lattice % 2) != 0
    residual = delta - n_lattice * SQRT_PI

    # Syndromes
    syndromes = np.zeros((n_shots, n_det), dtype=np.uint8)
    obs_flips = np.zeros(n_shots, dtype=np.uint8)
    for j, edge in enumerate(edges):
        mask = errors[:, j]
        syndromes[mask, edge['node1']] ^= 1
        if edge['node2'] is not None:
            syndromes[mask, edge['node2']] ^= 1
        if edge['has_logical']:
            obs_flips[mask] ^= 1

    # Decode using DECODER's V_eff for LLR weights
    n_logical_errors = 0

    if use_soft_info:
        r_abs = np.abs(residual)
        # LLR computed with decoder's V_eff (may differ from true)
        log_lr = ((SQRT_PI - r_abs) ** 2 - r_abs ** 2) / (2.0 * V_eff_decoder)
        log_lr = np.clip(log_lr, -30, 30)

        for i in range(n_shots):
            soft_w = np.maximum(log_lr[i], 0.01)
            boundary = n_det
            H = np.zeros((n_det + 1, n_edges), dtype=np.uint8)
            faults = np.zeros((1, n_edges), dtype=np.uint8)
            for j, edge in enumerate(edges):
                H[edge['node1'], j] = 1
                if edge['node2'] is not None:
                    H[edge['node2'], j] = 1
                else:
                    H[boundary, j] = 1
                if edge['has_logical']:
                    faults[0, j] = 1
            m = pymatching.Matching(H, weights=soft_w, faults_matrix=faults)
            m.set_boundary_nodes({boundary})
            pred = m.decode(syndromes[i])
            if pred[0] != obs_flips[i]:
                n_logical_errors += 1
    else:
        p_phys = compute_p_phys(V_eff_decoder)
        uniform_w = np.full(n_edges, max(-np.log(p_phys / (1 - p_phys)), 0.01))
        boundary = n_det
        H = np.zeros((n_det + 1, n_edges), dtype=np.uint8)
        faults = np.zeros((1, n_edges), dtype=np.uint8)
        for j, edge in enumerate(edges):
            H[edge['node1'], j] = 1
            if edge['node2'] is not None:
                H[edge['node2'], j] = 1
            else:
                H[boundary, j] = 1
            if edge['has_logical']:
                faults[0, j] = 1
        m = pymatching.Matching(H, weights=uniform_w, faults_matrix=faults)
        m.set_boundary_nodes({boundary})
        for i in range(n_shots):
            pred = m.decode(syndromes[i])
            if pred[0] != obs_flips[i]:
                n_logical_errors += 1

    p_L = n_logical_errors / n_shots
    # Return flat residuals for estimator
    residuals_flat = residual.flatten()
    return p_L, residuals_flat


# ============================================================
# Exp-B3: Adaptive vs Static vs Oracle Decoder
# ============================================================
def run_exp_b3(rng):
    print("=" * 70)
    print("  Exp-B3: Drift-Adaptive Decoder")
    print("=" * 70)

    d = 5
    n_shots_per_window = 1000
    duration_s = 300.0
    window_s = 1.0
    n_windows = int(duration_s / window_s)

    edges, n_det = extract_matching_graph(d, rounds=d)
    print(f"  Code: d={d}, {len(edges)} edges, {n_det} detectors")

    # Generate drift trajectories
    from exp_b1_drift_model import PhotonicDriftSimulator

    results = {}

    for scenario in ['slow_thermal', 'fast_pll', 'sudden_event']:
        print(f"\n--- Scenario: {scenario} ---")

        drift_rng = np.random.default_rng(42)
        sim = PhotonicDriftSimulator(scenario, dt=0.01, rng=drift_rng)
        traj = sim.generate_trajectory(duration_s)

        # Subsample to window resolution
        fine_dt = 0.01
        step_per_window = int(window_s / fine_dt)

        V_eff_true_arr = np.zeros(n_windows)
        for w in range(n_windows):
            idx = min(int((w + 0.5) * step_per_window), len(traj['V_eff']) - 1)
            V_eff_true_arr[w] = traj['V_eff'][idx]

        V_eff_initial = V_eff_true_arr[0]

        # Initialize Kalman estimator
        estimator = KalmanEstimator(V_eff_initial, process_noise=1e-6)

        # Storage
        p_L_static = np.zeros(n_windows)
        p_L_adaptive = np.zeros(n_windows)
        p_L_oracle = np.zeros(n_windows)
        V_eff_estimated = np.zeros(n_windows)

        t0 = time.time()

        for w in range(n_windows):
            V_true = V_eff_true_arr[w]
            V_est = estimator.x  # Current estimate before this window

            # 1. Static decoder (uses V_eff at t=0)
            pL_s, _ = run_qec_adaptive(
                edges, n_det, V_true, V_eff_initial,
                n_shots_per_window, rng, use_soft_info=True
            )
            p_L_static[w] = pL_s

            # 2. Adaptive decoder (uses estimated V_eff)
            pL_a, residuals = run_qec_adaptive(
                edges, n_det, V_true, V_est,
                n_shots_per_window, rng, use_soft_info=True
            )
            p_L_adaptive[w] = pL_a

            # 3. Oracle decoder (uses true V_eff)
            pL_o, _ = run_qec_adaptive(
                edges, n_det, V_true, V_true,
                n_shots_per_window, rng, use_soft_info=True
            )
            p_L_oracle[w] = pL_o

            # Update estimator with residuals from adaptive run
            # Use a subsample of residuals for efficiency
            estimator.update(residuals[:5000])
            V_eff_estimated[w] = estimator.x

            if w % 50 == 0 or w == n_windows - 1:
                elapsed = time.time() - t0
                print(f"  t={w}s: V_true={V_true:.5f}, V_est={V_eff_estimated[w]:.5f}, "
                      f"p_L: static={pL_s:.4e}, adaptive={pL_a:.4e}, "
                      f"oracle={pL_o:.4e}  [{elapsed:.1f}s]")

        # Compute fault-tolerance lifetimes
        def find_ft_lifetime(p_L_arr, threshold=1e-3):
            # Use smoothed version (rolling mean over 10 windows) to avoid noise
            kernel = min(10, len(p_L_arr))
            smoothed = np.convolve(p_L_arr, np.ones(kernel)/kernel, mode='valid')
            crossings = np.where(smoothed > threshold)[0]
            return float(crossings[0]) if len(crossings) > 0 else None

        ft_static = find_ft_lifetime(p_L_static)
        ft_adaptive = find_ft_lifetime(p_L_adaptive)
        ft_oracle = find_ft_lifetime(p_L_oracle)

        # Extension factor
        if ft_static and ft_adaptive:
            extension = ft_adaptive / ft_static
        elif ft_static and not ft_adaptive:
            extension = float('inf')  # Adaptive never fails
        else:
            extension = None

        ft_str = lambda x: f"{x:.0f}s" if x else ">300s"
        print(f"\n  FT lifetime: static={ft_str(ft_static)}, "
              f"adaptive={ft_str(ft_adaptive)}, oracle={ft_str(ft_oracle)}")
        if extension:
            ext_str = f"{extension:.1f}x" if extension != float('inf') else ">∞"
            print(f"  Extension factor: {ext_str}")

        # Estimation accuracy
        rel_err = np.abs(V_eff_estimated - V_eff_true_arr) / V_eff_true_arr
        print(f"  V_eff estimation: mean_err={np.mean(rel_err[10:]):.3%}, "
              f"p95={np.percentile(rel_err[10:], 95):.3%}")

        results[scenario] = {
            'time': np.arange(n_windows).tolist(),
            'V_eff_true': V_eff_true_arr.tolist(),
            'V_eff_estimated': V_eff_estimated.tolist(),
            'p_L_static': p_L_static.tolist(),
            'p_L_adaptive': p_L_adaptive.tolist(),
            'p_L_oracle': p_L_oracle.tolist(),
            'ft_lifetime_static': ft_static,
            'ft_lifetime_adaptive': ft_adaptive,
            'ft_lifetime_oracle': ft_oracle,
            'extension_factor': extension if extension != float('inf') else 'inf',
            'estimation_mean_error': float(np.mean(rel_err[10:])),
            'd': d,
            'n_shots_per_window': n_shots_per_window,
        }

    return results


# ============================================================
# Visualization
# ============================================================
def plot_results(results):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available")
        return

    plt.rcParams.update({
        'font.size': 11, 'axes.grid': True, 'grid.alpha': 0.3,
    })

    scenarios = ['slow_thermal', 'fast_pll', 'sudden_event']
    titles = ['Slow Thermal Drift', 'Fast PLL Fluctuation', 'Sudden Event']

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('Exp-B3: Drift-Adaptive Decoder — Static vs Adaptive vs Oracle\n'
                 'Photonic Quantum Digital Twin (d=5, soft-info MWPM)',
                 fontsize=14, fontweight='bold')

    for col, (scenario, title) in enumerate(zip(scenarios, titles)):
        data = results[scenario]
        t = np.array(data['time'])

        # Row 1: V_eff tracking
        ax = axes[0, col]
        ax.plot(t, data['V_eff_true'], 'k-', lw=2, alpha=0.7, label='True')
        ax.plot(t, data['V_eff_estimated'], '#9b59b6', lw=1, alpha=0.7,
                label='Estimated (Kalman)')
        ax.set_ylabel('$V_{eff}$ (SNU)')
        ax.set_title(title)
        ax.legend(fontsize=8)

        # Row 2: p_L(t) comparison
        ax = axes[1, col]
        # Smooth for visibility
        kernel = 10
        def smooth(arr):
            return np.convolve(arr, np.ones(kernel)/kernel, mode='valid')

        t_sm = t[:len(smooth(np.array(data['p_L_static'])))]
        p_static_sm = smooth(np.array(data['p_L_static']))
        p_adapt_sm = smooth(np.array(data['p_L_adaptive']))
        p_oracle_sm = smooth(np.array(data['p_L_oracle']))

        # Replace zeros for log plot
        floor = 1e-5
        p_static_sm = np.maximum(p_static_sm, floor)
        p_adapt_sm = np.maximum(p_adapt_sm, floor)
        p_oracle_sm = np.maximum(p_oracle_sm, floor)

        ax.semilogy(t_sm, p_static_sm, '#e74c3c', lw=1.5, alpha=0.8, label='Static')
        ax.semilogy(t_sm, p_adapt_sm, '#2ecc71', lw=2, alpha=0.9, label='Adaptive (twin)')
        ax.semilogy(t_sm, p_oracle_sm, '#3498db', lw=1, ls='--', alpha=0.6, label='Oracle')
        ax.axhline(1e-3, color='red', ls='--', alpha=0.5, label='$10^{-3}$ threshold')
        ax.set_ylabel('$p_L$ (smoothed)')
        ax.set_xlabel('Time (s)')
        ax.set_ylim(1e-5, 1e-1)
        ax.legend(fontsize=7)

        # Annotate FT lifetimes
        ft_s = data['ft_lifetime_static']
        ft_a = data['ft_lifetime_adaptive']
        if ft_s:
            ax.axvline(ft_s, color='#e74c3c', ls=':', alpha=0.3)
        if ft_a:
            ax.axvline(ft_a, color='#2ecc71', ls=':', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_b3_adaptive_decoder.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  Saved: {path}")


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)

    print("\n  Photonic Quantum Digital Twin — Theme 2")
    print("  Exp-B3: Drift-Adaptive Decoder")
    print(f"  Stim {stim.__version__}, PyMatching {pymatching.__version__}")
    print()

    t_start = time.time()
    results = run_exp_b3(rng)

    # Save
    json_path = os.path.join(OUT_DIR, 'exp_b3_results.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved: {json_path}")

    plot_results(results)

    elapsed = time.time() - t_start
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY: Drift-Adaptive Decoder Performance")
    print("=" * 70)
    print(f"\n  {'Scenario':<20} {'Static FT':>12} {'Adaptive FT':>12} "
          f"{'Oracle FT':>12} {'Extension':>10}")
    print("  " + "-" * 68)
    for scenario, data in results.items():
        ft_s = data['ft_lifetime_static']
        ft_a = data['ft_lifetime_adaptive']
        ft_o = data['ft_lifetime_oracle']
        ext = data['extension_factor']

        def fmt(x): return f"{x:.0f}s" if x else ">300s"
        ext_str = f"{ext:.1f}x" if ext and ext != 'inf' else ">inf"

        print(f"  {scenario:<20} {fmt(ft_s):>12} {fmt(ft_a):>12} "
              f"{fmt(ft_o):>12} {ext_str:>10}")


if __name__ == '__main__':
    main()
