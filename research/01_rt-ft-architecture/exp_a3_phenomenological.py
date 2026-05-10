#!/usr/bin/env python3
"""
Exp-A3: Phenomenological Noise Model — Multi-Round QEC
======================================================

Key question: How much does the code-capacity advantage degrade
when we include multiple syndrome rounds (time-like errors)?

In CV homodyne QEC, "measurement errors" arise from:
  - GKP displacement noise on ancilla qubits (same as data qubit noise)
  - Feedforward delay introducing time-correlated errors
  - Phase drift between rounds

This experiment compares:
  1. Code-capacity (1 round) — Exp-A2 baseline
  2. Phenomenological (d rounds, with measurement noise)
  3. Circuit-level approximation (d rounds, gate-level noise)

For CV systems, the measurement noise rate equals the data noise rate
(homodyne always succeeds), so we use p_meas = p_data = p_phys(V_eff).

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
# Stim circuit-based simulation (phenomenological)
# ============================================================
def run_stim_phenomenological(d, p_phys, n_shots, rounds=None):
    """
    Use Stim's built-in surface code with phenomenological noise.

    In phenomenological model:
      - Data errors: depolarization with rate p
      - Measurement errors: flip with rate p
      - rounds = d (standard for threshold estimation)

    Returns p_L (logical error rate).
    """
    if rounds is None:
        rounds = d

    # Build circuit with phenomenological-like noise
    # Stim's "surface_code:rotated_memory_z" with:
    #   before_round_data_depolarization = p (data errors per round)
    #   before_measure_flip_probability = p (measurement errors)
    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        rounds=rounds,
        distance=d,
        before_round_data_depolarization=p_phys,
        before_measure_flip_probability=p_phys,
    )

    # Sample and decode
    sampler = circuit.compile_detector_sampler()
    detection_events, observable_flips = sampler.sample(
        shots=n_shots, separate_observables=True
    )

    # Build matching from DEM
    dem = circuit.detector_error_model(decompose_errors=True)
    matcher = pymatching.Matching.from_detector_error_model(dem)

    # Decode
    predictions = matcher.decode_batch(detection_events)
    n_errors = np.sum(predictions != observable_flips)
    p_L = n_errors / n_shots

    return {
        'd': d,
        'rounds': rounds,
        'p_phys': float(p_phys),
        'n_shots': n_shots,
        'n_errors': int(n_errors),
        'p_L': float(p_L),
        'model': 'phenomenological',
    }


def run_stim_code_capacity(d, p_phys, n_shots):
    """Code-capacity (1 round) for comparison using Stim's batch decoder."""
    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        rounds=1,
        distance=d,
        before_round_data_depolarization=p_phys,
    )

    sampler = circuit.compile_detector_sampler()
    detection_events, observable_flips = sampler.sample(
        shots=n_shots, separate_observables=True
    )

    dem = circuit.detector_error_model(decompose_errors=True)
    matcher = pymatching.Matching.from_detector_error_model(dem)
    predictions = matcher.decode_batch(detection_events)
    n_errors = np.sum(predictions != observable_flips)

    return {
        'd': d,
        'rounds': 1,
        'p_phys': float(p_phys),
        'n_shots': n_shots,
        'n_errors': int(n_errors),
        'p_L': float(n_errors / n_shots),
        'model': 'code_capacity',
    }


def run_stim_circuit_level(d, p_phys, n_shots, rounds=None):
    """
    Circuit-level noise using Stim's full gate-level noise model.
    This is the most realistic model for comparison.
    """
    if rounds is None:
        rounds = d

    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        rounds=rounds,
        distance=d,
        after_clifford_depolarization=p_phys,
        after_reset_flip_probability=p_phys * 0.1,
        before_measure_flip_probability=p_phys * 0.1,
        before_round_data_depolarization=p_phys,
    )

    sampler = circuit.compile_detector_sampler()
    detection_events, observable_flips = sampler.sample(
        shots=n_shots, separate_observables=True
    )

    dem = circuit.detector_error_model(decompose_errors=True)
    matcher = pymatching.Matching.from_detector_error_model(dem)
    predictions = matcher.decode_batch(detection_events)
    n_errors = np.sum(predictions != observable_flips)

    return {
        'd': d,
        'rounds': rounds,
        'p_phys': float(p_phys),
        'n_shots': n_shots,
        'n_errors': int(n_errors),
        'p_L': float(n_errors / n_shots),
        'model': 'circuit_level',
    }


# ============================================================
# Main experiments
# ============================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t_start = time.time()

    print("=" * 70)
    print("  Exp-A3: Phenomenological vs Code-Capacity vs Circuit-Level")
    print("  Room-Temperature FT Photonic Architecture")
    print("=" * 70)

    # TAROS operating points
    points = [
        ('Phase 1', 13.0, 0.39, 0.010),
        ('Phase 2+ Real', 13.0, 0.27, 0.010),
        ('Phase 2+ Limit', 13.0, 0.15, 0.000),
    ]

    distances = [3, 5, 7]
    all_results = {}

    # ========================================
    # Part 1: Three-model comparison at TAROS operating points
    # ========================================
    print("\n--- Part 1: Three-Model Comparison ---\n")

    for name, sg, L, Vnl in points:
        V = compute_V_eff(sg, L, Vnl)
        p = compute_p_phys(V)
        s = compute_sigma_eff(V)
        print(f"\n{'='*50}")
        print(f"  {name}: σ_eff={s:.1f}dB, p_phys={p:.4e}")
        print(f"{'='*50}")

        results = {'params': {'sigma_eff': float(s), 'p_phys': float(p), 'L_dB': L}}
        results['data'] = []

        for d in distances:
            # Shot counts: need enough for statistics
            n_base = 200_000 if p > 0.003 else 500_000

            print(f"\n  d={d}:")

            # Code-capacity (fast batch decode)
            t0 = time.time()
            r_cc = run_stim_code_capacity(d, p, n_base)
            dt = time.time() - t0
            pL_cc = f"{r_cc['p_L']:.2e}" if r_cc['p_L'] > 0 else f"<{1/n_base:.1e}"
            print(f"    Code-capacity (1 round):     p_L={pL_cc} "
                  f"({r_cc['n_errors']}/{n_base})  [{dt:.1f}s]")

            # Phenomenological (d rounds)
            t0 = time.time()
            r_ph = run_stim_phenomenological(d, p, n_base, rounds=d)
            dt = time.time() - t0
            pL_ph = f"{r_ph['p_L']:.2e}" if r_ph['p_L'] > 0 else f"<{1/n_base:.1e}"
            print(f"    Phenomenological ({d} rounds): p_L={pL_ph} "
                  f"({r_ph['n_errors']}/{n_base})  [{dt:.1f}s]")

            # Circuit-level (d rounds)
            t0 = time.time()
            r_cl = run_stim_circuit_level(d, p, n_base, rounds=d)
            dt = time.time() - t0
            pL_cl = f"{r_cl['p_L']:.2e}" if r_cl['p_L'] > 0 else f"<{1/n_base:.1e}"
            print(f"    Circuit-level ({d} rounds):   p_L={pL_cl} "
                  f"({r_cl['n_errors']}/{n_base})  [{dt:.1f}s]")

            # Degradation ratio
            if r_cc['p_L'] > 0 and r_ph['p_L'] > 0:
                ratio = r_ph['p_L'] / r_cc['p_L']
                print(f"    Phenomenological/CC ratio: {ratio:.1f}x")
            if r_cc['p_L'] > 0 and r_cl['p_L'] > 0:
                ratio = r_cl['p_L'] / r_cc['p_L']
                print(f"    Circuit-level/CC ratio:    {ratio:.1f}x")

            results['data'].append({
                'code_capacity': r_cc,
                'phenomenological': r_ph,
                'circuit_level': r_cl,
            })

        all_results[name] = results

    # ========================================
    # Part 2: Threshold sweep (phenomenological)
    # ========================================
    print("\n\n--- Part 2: Phenomenological Threshold Sweep ---\n")

    threshold_phenom = []
    threshold_circuit = []

    for L_dB in [0.15, 0.27, 0.39, 0.50, 0.70, 1.00, 1.30, 1.60]:
        V = compute_V_eff(13.0, L_dB, 0.010)
        p = compute_p_phys(V)
        s = compute_sigma_eff(V)
        if p > 0.10:
            continue

        print(f"  L={L_dB:.2f}dB  σ_eff={s:.1f}dB  p_phys={p:.4e}")

        for d in [3, 5, 7]:
            n = 100_000 if p > 0.005 else 200_000

            r_ph = run_stim_phenomenological(d, p, n, rounds=d)
            r_cl = run_stim_circuit_level(d, p, n, rounds=d)

            pL_ph = f"{r_ph['p_L']:.2e}" if r_ph['p_L'] > 0 else f"<{1/n:.1e}"
            pL_cl = f"{r_cl['p_L']:.2e}" if r_cl['p_L'] > 0 else f"<{1/n:.1e}"
            print(f"    d={d}: phenom={pL_ph}  circuit={pL_cl}")

            threshold_phenom.append({**r_ph, 'L_dB': L_dB, 'sigma_eff': float(s)})
            threshold_circuit.append({**r_cl, 'L_dB': L_dB, 'sigma_eff': float(s)})

    # ========================================
    # Part 3: CV-specific analysis
    # ========================================
    print("\n\n--- Part 3: CV-Specific Measurement Error Analysis ---\n")
    print("  In CV homodyne QEC:")
    print("  - Measurement ALWAYS succeeds (no photon loss detection issue)")
    print("  - 'Measurement error' = GKP displacement noise on ancilla")
    print("  - p_meas = p_data (same physical mechanism)")
    print("  - → phenomenological with p_meas = p_data is the correct CV model")
    print()

    # Compare p_meas = p_data vs p_meas = p_data/10 (DV-like)
    cv_analysis = []
    print("  p_meas sensitivity (Phase 1, d=5):")
    V_p1 = compute_V_eff(13.0, 0.39, 0.010)
    p_p1 = compute_p_phys(V_p1)

    for meas_factor in [0.0, 0.1, 0.3, 0.5, 1.0]:
        p_meas = p_p1 * meas_factor
        circuit = stim.Circuit.generated(
            "surface_code:rotated_memory_z",
            rounds=5, distance=5,
            before_round_data_depolarization=p_p1,
            before_measure_flip_probability=p_meas,
        )
        sampler = circuit.compile_detector_sampler()
        det, obs = sampler.sample(shots=200_000, separate_observables=True)
        dem = circuit.detector_error_model(decompose_errors=True)
        matcher = pymatching.Matching.from_detector_error_model(dem)
        pred = matcher.decode_batch(det)
        n_err = int(np.sum(pred != obs))
        p_L = n_err / 200_000

        label = "code-cap" if meas_factor == 0.0 else f"p_m={meas_factor:.1f}p"
        pL_str = f"{p_L:.2e}" if p_L > 0 else "<5e-06"
        print(f"    {label:12s}: p_L={pL_str} ({n_err}/200K)")
        cv_analysis.append({
            'meas_factor': meas_factor,
            'p_meas': float(p_meas),
            'p_L': float(p_L),
            'n_errors': n_err,
        })

    # Save all results
    save_data = {
        'comparison': {k: v for k, v in all_results.items()},
        'threshold_phenom': threshold_phenom,
        'threshold_circuit': threshold_circuit,
        'cv_analysis': cv_analysis,
        'metadata': {
            'seed': 'stim_internal',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        },
    }
    json_path = os.path.join(OUT_DIR, 'exp_a3_results.json')
    with open(json_path, 'w') as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\n  Saved: {json_path}")

    # ========================================
    # Plots
    # ========================================
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.rcParams.update({'font.size': 11, 'axes.grid': True, 'grid.alpha': 0.3})

        # Fig 1: Three-model comparison
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        fig.suptitle('Exp-A3: Code-Capacity vs Phenomenological vs Circuit-Level\n'
                     'GKP Surface Code (Hard-Decision MWPM via Stim+PyMatching)',
                     fontsize=13, fontweight='bold')

        colors = {'Phase 1': '#e74c3c', 'Phase 2+ Real': '#2ecc71', 'Phase 2+ Limit': '#3498db'}

        for ax_idx, (name, data) in enumerate(all_results.items()):
            ax = axes[ax_idx]
            params = data['params']

            for model, style, label in [
                ('code_capacity', '-o', 'Code-capacity (1 round)'),
                ('phenomenological', '-s', f'Phenomenological (d rounds)'),
                ('circuit_level', '-D', f'Circuit-level (d rounds)'),
            ]:
                ds, pLs = [], []
                for entry in data['data']:
                    r = entry[model]
                    if r['p_L'] > 0:
                        ds.append(r['d'])
                        pLs.append(r['p_L'])
                if ds:
                    ax.semilogy(ds, pLs, style, lw=2, ms=8, label=label)

            ax.axhline(1e-3, color='gray', ls=':', alpha=0.4)
            ax.set_xlabel('Code Distance d')
            ax.set_ylabel('Logical Error Rate $p_L$')
            ax.set_title(f'{name}\nσ_eff={params["sigma_eff"]:.1f}dB, p_phys={params["p_phys"]:.2e}')
            ax.set_xticks([3, 5, 7])
            ax.legend(fontsize=8)
            if ax.get_ylim()[0] < 1e-7:
                ax.set_ylim(bottom=1e-7)

        plt.tight_layout()
        path = os.path.join(OUT_DIR, 'fig_a3_model_comparison.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Plot: {path}")

        # Fig 2: Threshold crossing (phenomenological + circuit-level)
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle('Exp-A3: Threshold Crossing\nPhenomenological vs Circuit-Level',
                     fontsize=13, fontweight='bold')

        colors_d = {3: '#e74c3c', 5: '#f39c12', 7: '#2ecc71'}
        for ax_idx, (thresh_data, title) in enumerate([
            (threshold_phenom, 'Phenomenological'),
            (threshold_circuit, 'Circuit-Level'),
        ]):
            ax = axes[ax_idx]
            for d in [3, 5, 7]:
                subset = [r for r in thresh_data if r['d'] == d and r['p_L'] > 0]
                if subset:
                    pp = [r['p_phys'] for r in subset]
                    pL = [r['p_L'] for r in subset]
                    ax.loglog(pp, pL, '-o', color=colors_d[d], lw=2, ms=7, label=f'd={d}')

            pp_ref = np.logspace(-4, -0.5, 50)
            ax.loglog(pp_ref, pp_ref, 'k--', alpha=0.2, label='p_L = p_phys')
            ax.set_xlabel('Physical Error Rate $p_{phys}$')
            ax.set_ylabel('Logical Error Rate $p_L$')
            ax.set_title(title)
            ax.legend()

        plt.tight_layout()
        path = os.path.join(OUT_DIR, 'fig_a3_threshold.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Plot: {path}")

        # Fig 3: CV measurement error sensitivity
        fig, ax = plt.subplots(figsize=(8, 5))
        mf = [r['meas_factor'] for r in cv_analysis]
        pL = [r['p_L'] if r['p_L'] > 0 else 2.5e-6 for r in cv_analysis]
        ax.semilogy(mf, pL, '-o', lw=2.5, ms=10, color='#3498db')
        ax.set_xlabel('Measurement Error Factor ($p_{meas} / p_{data}$)', fontsize=12)
        ax.set_ylabel('Logical Error Rate $p_L$', fontsize=12)
        ax.set_title('CV-Specific: Measurement Error Sensitivity\n'
                     f'Phase 1, d=5, p_data={p_p1:.4e}', fontweight='bold')
        ax.axvline(1.0, color='red', ls='--', alpha=0.5, label='CV: p_meas = p_data')
        ax.axvline(0.0, color='blue', ls='--', alpha=0.5, label='Code-capacity (p_meas=0)')
        ax.legend()
        plt.tight_layout()
        path = os.path.join(OUT_DIR, 'fig_a3_cv_sensitivity.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Plot: {path}")

    except ImportError:
        print("  matplotlib not available")

    elapsed = time.time() - t_start
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for name, data in all_results.items():
        params = data['params']
        print(f"\n  {name} (σ_eff={params['sigma_eff']:.1f}dB):")
        for entry in data['data']:
            d = entry['code_capacity']['d']
            results_line = []
            for model in ['code_capacity', 'phenomenological', 'circuit_level']:
                r = entry[model]
                if r['p_L'] > 0:
                    results_line.append(f"{model[:6]}={r['p_L']:.2e}")
                else:
                    results_line.append(f"{model[:6]}<{1/r['n_shots']:.0e}")
            print(f"    d={d}: {' | '.join(results_line)}")


if __name__ == '__main__':
    main()
