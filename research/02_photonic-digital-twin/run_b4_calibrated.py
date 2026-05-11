#!/usr/bin/env python3
"""
B4 Final: FAR-Calibrated CUSUM Detection
==========================================
Fix: Calibrate CUSUM threshold h to achieve identical false alarm rate
(FAR = 1%) for both CV and DV, THEN compare detection delay.

This is the fair comparison: at the same false positive rate,
how much faster does CV detect a real anomaly?

seed=42, CPU only, ~3min.
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


def cusum_one_sided(observations, mu0, sigma0, k, h):
    """One-sided CUSUM. Returns first index where S_t > h, or -1."""
    S = 0.0
    for t, x in enumerate(observations):
        z = (x - mu0) / sigma0
        S = max(0.0, S + z - k)
        if S > h:
            return t
    return -1


def calibrate_cusum_h(rng, n_modes, v_eff, n_cycles, k, target_far, n_cal=500):
    """Find h such that P(false alarm in n_cycles) ≈ target_far.

    Binary search on h.
    """
    h_lo, h_hi = 1.0, 30.0

    for _ in range(20):  # Binary search iterations
        h_mid = (h_lo + h_hi) / 2
        false_alarms = 0
        for _ in range(n_cal):
            obs = []
            for _ in range(n_cycles):
                res, err = generate_gkp(n_modes, v_eff, rng)
                obs.append(float(np.mean(res ** 2)))
            mu0 = np.mean(obs[:50])
            sig0 = np.std(obs[:50])
            if sig0 < 1e-8:
                sig0 = 1e-6
            det = cusum_one_sided(obs, mu0, sig0, k, h_mid)
            if det >= 0:
                false_alarms += 1
        far = false_alarms / n_cal
        if far > target_far:
            h_lo = h_mid  # h too low, increase
        else:
            h_hi = h_mid  # h too high or just right, decrease
    return (h_lo + h_hi) / 2


def calibrate_cusum_h_dv(rng, n_modes, v_eff, n_cycles, k, target_far, n_cal=500):
    """Same but for DV binary error rate."""
    h_lo, h_hi = 1.0, 30.0

    for _ in range(20):
        h_mid = (h_lo + h_hi) / 2
        false_alarms = 0
        for _ in range(n_cal):
            obs = []
            for _ in range(n_cycles):
                _, err = generate_gkp(n_modes, v_eff, rng)
                obs.append(float(np.mean(err)))
            mu0 = np.mean(obs[:50])
            sig0 = np.std(obs[:50])
            if sig0 < 1e-8:
                sig0 = 1e-6
            det = cusum_one_sided(obs, mu0, sig0, k, h_mid)
            if det >= 0:
                false_alarms += 1
        far = false_alarms / n_cal
        if far > target_far:
            h_lo = h_mid
        else:
            h_hi = h_mid
    return (h_lo + h_hi) / 2


def save_json(name, data):
    path = os.path.join(OUT_DIR, name)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=lambda x: float(x) if isinstance(x, np.floating) else str(x))
    print(f"  [saved {name}]")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()

    print("=" * 70)
    print("  B4 FINAL: FAR-Calibrated CUSUM Detection")
    print("=" * 70)

    rng = np.random.default_rng(SEED)
    modes = 686  # d=7
    v0 = 0.1417
    n_before = 300
    n_after = 500
    target_far = 0.01  # 1% false alarm rate in 300 in-control cycles
    k_cusum = 0.5  # Reference value (standard choice for ~1σ shifts)

    # Step 1: Calibrate thresholds
    print(f"\n  Calibrating CUSUM thresholds for FAR={target_far:.0%}...")
    h_cv = calibrate_cusum_h(np.random.default_rng(SEED + 1), modes, v0,
                              n_before, k_cusum, target_far, n_cal=300)
    h_dv = calibrate_cusum_h_dv(np.random.default_rng(SEED + 2), modes, v0,
                                 n_before, k_cusum, target_far, n_cal=300)
    print(f"  CV threshold h={h_cv:.2f}, DV threshold h={h_dv:.2f}")

    # Step 2: Detection experiments
    anomalies = [
        ('+0.2dB', 0.2),
        ('+0.3dB', 0.3),
        ('+0.5dB', 0.5),
        ('+1.0dB', 1.0),
    ]

    n_trials = 300
    results = {'h_cv': h_cv, 'h_dv': h_dv, 'target_far': target_far,
               'k_cusum': k_cusum, 'modes_per_cycle': modes, 'anomalies': {}}

    for anom_name, delta_db in anomalies:
        v_after = v0 * 10 ** (delta_db / 10)
        print(f"\n  {anom_name}: V {v0:.4f} → {v_after:.4f}")

        cv_delays = []
        dv_delays = []

        for trial in range(n_trials):
            # Generate time series
            cv_obs = []
            dv_obs = []
            for cyc in range(n_before + n_after):
                v = v0 if cyc < n_before else v_after
                res, err = generate_gkp(modes, v, rng)
                cv_obs.append(float(np.mean(res ** 2)))
                dv_obs.append(float(np.mean(err)))

            cv_arr = np.array(cv_obs)
            dv_arr = np.array(dv_obs)

            # In-control stats
            cv_mu = np.mean(cv_arr[:100])
            cv_sig = np.std(cv_arr[:100])
            dv_mu = np.mean(dv_arr[:100])
            dv_sig = np.std(dv_arr[:100])
            if cv_sig < 1e-8: cv_sig = 1e-6
            if dv_sig < 1e-8: dv_sig = 1e-6

            # Run CUSUM from changepoint onward (fair: start fresh at changepoint)
            cv_post = cv_arr[n_before:]
            dv_post = dv_arr[n_before:]

            cv_det = cusum_one_sided(cv_post, cv_mu, cv_sig, k_cusum, h_cv)
            dv_det = cusum_one_sided(dv_post, dv_mu, dv_sig, k_cusum, h_dv)

            cv_delays.append(cv_det if cv_det >= 0 else n_after)
            dv_delays.append(dv_det if dv_det >= 0 else n_after)

        cv_d = np.array(cv_delays)
        dv_d = np.array(dv_delays)

        cv_detected = cv_d < n_after
        dv_detected = dv_d < n_after

        cv_med = float(np.median(cv_d[cv_detected])) if cv_detected.any() else n_after
        dv_med = float(np.median(dv_d[dv_detected])) if dv_detected.any() else n_after
        cv_rate = float(np.mean(cv_detected))
        dv_rate = float(np.mean(dv_detected))

        adv = dv_med / cv_med if cv_med > 0 else float('inf')

        print(f"    CV: median={cv_med:.0f}cyc, rate={cv_rate:.0%}")
        print(f"    DV: median={dv_med:.0f}cyc, rate={dv_rate:.0%}")
        print(f"    Advantage: {adv:.1f}x")

        results['anomalies'][anom_name] = {
            'delta_dB': delta_db,
            'v_after': float(v_after),
            'cv_median_delay': cv_med,
            'dv_median_delay': dv_med,
            'cv_detect_rate': cv_rate,
            'dv_detect_rate': dv_rate,
            'advantage': adv,
            'cv_mean_delay': float(np.mean(cv_d[cv_detected])) if cv_detected.any() else n_after,
            'dv_mean_delay': float(np.mean(dv_d[dv_detected])) if dv_detected.any() else n_after,
            'n_trials': n_trials,
        }
        save_json('b4_calibrated_cusum.json', results)

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"  DONE: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"  h_cv={h_cv:.2f}, h_dv={h_dv:.2f} (calibrated for FAR={target_far:.0%})")
    print(f"{'=' * 70}")

    print(f"\n  {'Anomaly':>8} {'CV delay':>10} {'CV rate':>8} {'DV delay':>10} {'DV rate':>8} {'Advantage':>10}")
    print("  " + "-" * 60)
    for k, r in results['anomalies'].items():
        print(f"  {k:>8} {r['cv_median_delay']:9.0f}c {r['cv_detect_rate']:7.0%} "
              f"{r['dv_median_delay']:9.0f}c {r['dv_detect_rate']:7.0%} "
              f"{r['advantage']:9.1f}x")


if __name__ == '__main__':
    main()
