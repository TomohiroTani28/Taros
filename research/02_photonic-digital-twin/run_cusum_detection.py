#!/usr/bin/env python3
"""
B4 revised: CUSUM + SPRT Anomaly Detection
============================================
Fix: BOCPD failed because it doesn't accumulate evidence.
CUSUM and SPRT accumulate log-likelihood ratios over cycles → detect small shifts.

Theory predicts:
  +0.5dB: CV ~7 cycles, DV ~109 cycles (16× advantage)
  +0.3dB: CV ~18 cycles, DV ~319 cycles (18× advantage)

This script validates these predictions numerically.
seed=42, CPU only, ~10min.
"""

import numpy as np
from scipy.special import erfc
import json, os, time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
SEED = 42


def generate_gkp(n_modes, v_eff, rng):
    sigma = np.sqrt(v_eff)
    disp = sigma * rng.standard_normal(n_modes)
    nearest = np.rint(disp / SQRT_PI)
    residuals = (disp - nearest * SQRT_PI).astype(np.float32)
    errors = (nearest.astype(np.int64) % 2) != 0
    return residuals, errors


def cusum_detect(observations, mu0, sigma0, delta, h=5.0):
    """One-sided CUSUM for upward shift detection.

    Accumulates: S_t = max(0, S_{t-1} + (x_t - mu0 - delta/2) / sigma0)
    Detects when S_t > h.

    Args:
        observations: time series
        mu0: in-control mean
        sigma0: in-control std
        delta: target shift size (in units of sigma0 if normalized)
        h: decision threshold (default 5.0 ≈ 5σ equivalent)

    Returns: detection index (or len(observations) if not detected)
    """
    S = 0.0
    k = delta / 2  # Reference value
    for t, x in enumerate(observations):
        z = (x - mu0) / sigma0
        S = max(0, S + z - k)
        if S > h:
            return t
    return len(observations)


def sprt_detect(observations, mu0, mu1, sigma):
    """Sequential Probability Ratio Test.

    H0: mean = mu0, H1: mean = mu1, both Gaussian with known sigma.
    Accumulates log-likelihood ratio.

    Returns: detection index, or len if not detected.
    """
    log_A = np.log(100)   # P(type II) = 0.01
    log_B = np.log(1/100) # P(type I) = 0.01
    cum_llr = 0.0
    for t, x in enumerate(observations):
        llr = ((x - mu0) ** 2 - (x - mu1) ** 2) / (2 * sigma ** 2)
        cum_llr += llr
        if cum_llr > log_A:
            return t  # Accept H1 (shift detected)
        if cum_llr < log_B:
            cum_llr = 0  # Reset (accept H0)
    return len(observations)


def save_json(name, data):
    path = os.path.join(OUT_DIR, name)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=lambda x: float(x) if isinstance(x, np.floating) else str(x))
    print(f"  [saved {name}]")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(SEED)
    t0 = time.time()

    print("=" * 70)
    print("  B4 REVISED: CUSUM + SPRT Anomaly Detection")
    print("  CV (14-bit residual variance) vs DV (binary error rate)")
    print("=" * 70)

    modes_per_cycle = 686  # d=7
    n_before = 200  # In-control cycles
    n_after = 300   # Post-anomaly cycles
    n_trials = 200

    anomalies = [
        ('+0.2dB', 0.2),
        ('+0.3dB', 0.3),
        ('+0.5dB', 0.5),
        ('+1.0dB', 1.0),
    ]

    v_nominal = 0.1417
    results = {}

    for anom_name, delta_db in anomalies:
        v_after = v_nominal * 10 ** (delta_db / 10)
        delta_v_pct = (v_after - v_nominal) / v_nominal * 100

        print(f"\n  Anomaly: {anom_name} (V: {v_nominal:.4f} → {v_after:.4f}, +{delta_v_pct:.1f}%)")

        cv_cusum = []
        cv_sprt = []
        dv_cusum = []
        dv_sprt = []

        for trial in range(n_trials):
            cv_obs = []  # Per-cycle residual variance
            dv_obs = []  # Per-cycle error rate

            for cyc in range(n_before + n_after):
                v = v_nominal if cyc < n_before else v_after
                res, err = generate_gkp(modes_per_cycle, v, rng)
                cv_obs.append(float(np.mean(res ** 2)))
                dv_obs.append(float(np.mean(err)))

            cv_arr = np.array(cv_obs)
            dv_arr = np.array(dv_obs)

            # In-control statistics (from first 100 cycles)
            cv_mu0 = np.mean(cv_arr[:100])
            cv_sig0 = np.std(cv_arr[:100])
            dv_mu0 = np.mean(dv_arr[:100])
            dv_sig0 = np.std(dv_arr[:100])
            if dv_sig0 < 1e-8:
                dv_sig0 = 1e-4  # Prevent division by zero

            # Expected shift (for CUSUM reference value and SPRT H1)
            cv_mu1 = v_after  # Expected V_eff after shift
            dv_mu1_raw = float(0.5 * erfc(SQRT_PI / (4 * np.sqrt(v_after / 2))))

            # CUSUM detection (from cycle n_before onward, but run from start)
            cv_delta_norm = (cv_mu1 - cv_mu0) / cv_sig0 if cv_sig0 > 0 else 0
            dv_delta_norm = (dv_mu1_raw - dv_mu0) / dv_sig0 if dv_sig0 > 0 else 0

            cv_det_c = cusum_detect(cv_arr, cv_mu0, cv_sig0,
                                     delta=max(cv_delta_norm, 0.1), h=4.0)
            dv_det_c = cusum_detect(dv_arr, dv_mu0, dv_sig0,
                                     delta=max(dv_delta_norm, 0.1), h=4.0)

            # SPRT detection
            cv_det_s = sprt_detect(cv_arr, cv_mu0, cv_mu1, cv_sig0)
            dv_det_s = sprt_detect(dv_arr, dv_mu0, dv_mu1_raw, max(dv_sig0, 1e-6))

            # Record delay from actual changepoint
            cv_cusum.append(max(0, cv_det_c - n_before))
            dv_cusum.append(max(0, dv_det_c - n_before))
            cv_sprt.append(max(0, cv_det_s - n_before))
            dv_sprt.append(max(0, dv_det_s - n_before))

        # Statistics
        def stats(arr, max_val=n_after):
            arr = np.array(arr)
            detected = arr < max_val
            return {
                'median_delay': float(np.median(arr[detected])) if detected.any() else float(max_val),
                'mean_delay': float(np.mean(arr[detected])) if detected.any() else float(max_val),
                'detect_rate': float(np.mean(detected)),
                'p10': float(np.percentile(arr, 10)),
                'p90': float(np.percentile(arr, 90)),
            }

        cv_c = stats(cv_cusum)
        dv_c = stats(dv_cusum)
        cv_s = stats(cv_sprt)
        dv_s = stats(dv_sprt)

        # Advantage
        cusum_adv = dv_c['median_delay'] / cv_c['median_delay'] if cv_c['median_delay'] > 0 else float('inf')
        sprt_adv = dv_s['median_delay'] / cv_s['median_delay'] if cv_s['median_delay'] > 0 else float('inf')

        print(f"    CUSUM: CV median={cv_c['median_delay']:.0f}cyc (rate={cv_c['detect_rate']:.0%}), "
              f"DV median={dv_c['median_delay']:.0f}cyc (rate={dv_c['detect_rate']:.0%}), "
              f"advantage={cusum_adv:.1f}x")
        print(f"    SPRT:  CV median={cv_s['median_delay']:.0f}cyc (rate={cv_s['detect_rate']:.0%}), "
              f"DV median={dv_s['median_delay']:.0f}cyc (rate={dv_s['detect_rate']:.0%}), "
              f"advantage={sprt_adv:.1f}x")

        # Theoretical prediction
        cv_snr_per_cycle = abs(v_after - v_nominal) / (cv_sig0 if cv_sig0 > 0 else 0.01)
        dv_snr_per_cycle = abs(dv_mu1_raw - dv_mu0) / (dv_sig0 if dv_sig0 > 0 else 0.01)
        cv_theory = (5 / cv_snr_per_cycle) ** 2 if cv_snr_per_cycle > 0 else 999
        dv_theory = (5 / dv_snr_per_cycle) ** 2 if dv_snr_per_cycle > 0 else 999
        print(f"    Theory (5σ): CV~{cv_theory:.0f}cyc, DV~{dv_theory:.0f}cyc")

        results[anom_name] = {
            'delta_dB': delta_db, 'v_before': v_nominal, 'v_after': float(v_after),
            'cusum_cv': cv_c, 'cusum_dv': dv_c, 'cusum_advantage': cusum_adv,
            'sprt_cv': cv_s, 'sprt_dv': dv_s, 'sprt_advantage': sprt_adv,
            'cv_snr_per_cycle': float(cv_snr_per_cycle),
            'dv_snr_per_cycle': float(dv_snr_per_cycle),
            'theory_cv_5sigma': float(cv_theory),
            'theory_dv_5sigma': float(dv_theory),
            'n_trials': n_trials,
        }
        save_json('b4_cusum_sprt.json', results)

    elapsed = time.time() - t0
    print(f"\n  Done: {elapsed:.0f}s")

    # Summary table
    print(f"\n  {'Anomaly':>8} {'CV CUSUM':>10} {'DV CUSUM':>10} {'Advantage':>10} "
          f"{'CV SPRT':>10} {'DV SPRT':>10} {'Advantage':>10}")
    print("  " + "-" * 70)
    for k, r in results.items():
        print(f"  {k:>8} {r['cusum_cv']['median_delay']:9.0f}c {r['cusum_dv']['median_delay']:9.0f}c "
              f"{r['cusum_advantage']:9.1f}x "
              f"{r['sprt_cv']['median_delay']:9.0f}c {r['sprt_dv']['median_delay']:9.0f}c "
              f"{r['sprt_advantage']:9.1f}x")


if __name__ == '__main__':
    main()
