#!/usr/bin/env python3
"""
Paper 2: The 14-bit Advantage
==============================
Unified experiment: B1 (Fisher information) + B2 (V_eff estimation) + B4 (anomaly detection)

Core claim: CV-QEC's analog GKP residuals provide orders-of-magnitude more
information about hardware state than DV-QEC's binary syndromes.

Experiments:
  B1. Fisher information ratio I_CV / I_DV  (analytical + numerical)
  B2. V_eff estimation: cycles to 3% accuracy (CV 14-bit vs DV 1-bit)
  B4. Anomaly detection: advance warning for cycle slip (CV kurtosis vs DV flip-rate)

All CPU-only. No GPU/MPS required. Parallel-safe with GNN experiment.
seed=42, ~3h total on Apple Silicon.
"""

import numpy as np
from scipy.special import erfc
from scipy.stats import kurtosis
from scipy.optimize import minimize_scalar
import json, os, time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
SEED = 42


# ═══════════════════════════════════════════════════════════════
#  Physics: GKP residuals and binary syndromes
# ═══════════════════════════════════════════════════════════════

def gkp_p_err(v_eff):
    """Physical error rate from V_eff."""
    sigma = np.sqrt(v_eff / 2)
    return 0.5 * erfc(SQRT_PI / (4 * sigma))


def gkp_residuals(n_modes, v_eff, rng):
    """Generate GKP residuals (analog, 14-bit equivalent).

    Displacement d ~ N(0, V_eff), residual r = d - round(d/√π)*√π
    Returns: residuals (float32), binary errors (bool)
    """
    sigma = np.sqrt(v_eff)
    disp = sigma * rng.standard_normal(n_modes)
    nearest = np.rint(disp / SQRT_PI)
    residuals = (disp - nearest * SQRT_PI).astype(np.float32)
    errors = (nearest.astype(np.int64) % 2) != 0
    return residuals, errors


def binary_syndromes(errors):
    """Convert errors to binary syndrome (DV-equivalent: 1-bit per measurement)."""
    return errors.astype(np.uint8)


# ═══════════════════════════════════════════════════════════════
#  B1: Fisher Information Analysis
# ═══════════════════════════════════════════════════════════════

def fisher_cv_analytical(v_eff):
    """Fisher information for V_eff from continuous GKP residual.

    For small V_eff (high squeezing), residual r ~ N(0, V_eff).
    I_CV = 1/(2*V_eff^2) per measurement (Gaussian variance estimation).
    """
    return 1.0 / (2.0 * v_eff ** 2)


def fisher_dv_analytical(v_eff):
    """Fisher information for V_eff from binary syndrome (0 or 1).

    p(error) = erfc(√π / (4σ)) / 2, σ = √(V_eff/2)
    I_DV = (dp/dV)^2 / (p*(1-p))
    """
    sigma = np.sqrt(v_eff / 2)
    p = 0.5 * erfc(SQRT_PI / (4 * sigma))
    if p < 1e-15 or p > 1 - 1e-15:
        return 0.0
    # dp/dV via chain rule: dp/dσ * dσ/dV
    # dp/dσ = (√π / (4σ²)) * (1/√π) * exp(-(√π/(4σ))²) = exp(-π/(16σ²)) / (4σ²√π) ...
    # Numerical derivative is safer
    dv = v_eff * 1e-6
    p_plus = gkp_p_err(v_eff + dv)
    p_minus = gkp_p_err(v_eff - dv)
    dp_dv = (p_plus - p_minus) / (2 * dv)
    return dp_dv ** 2 / (p * (1 - p))


def fisher_cv_numerical(v_eff, n_samples=1_000_000, rng=None):
    """Fisher information for V_eff from residuals (numerical, wrapped Gaussian)."""
    if rng is None:
        rng = np.random.default_rng(42)
    res, _ = gkp_residuals(n_samples, v_eff, rng)
    # Score function: d/dV log p(r|V) ≈ (r² - V) / (2V²) for Gaussian
    scores = (res ** 2 - v_eff) / (2 * v_eff ** 2)
    return float(np.mean(scores ** 2))


def run_b1():
    """B1: Fisher information ratio across Taros operating points."""
    print("\n" + "=" * 70)
    print("  B1: Fisher Information — The 14-bit Advantage")
    print("=" * 70)

    # Taros operating points
    points = [
        ("Phase 1 (8.5dB)", 0.1417),
        ("Phase 2+ Real (9.3dB)", 0.1175),
        ("Phase 2+ Limit (10.8dB)", 0.0832),
        ("Threshold (~7.5dB)", 0.178),
        ("Degraded (7.0dB)", 0.200),
    ]

    # Sweep V_eff
    v_sweep = np.logspace(np.log10(0.05), np.log10(0.30), 50)

    results = {'sweep': [], 'operating_points': []}
    rng = np.random.default_rng(SEED)

    for v in v_sweep:
        i_cv = fisher_cv_analytical(v)
        i_dv = fisher_dv_analytical(v)
        ratio = i_cv / i_dv if i_dv > 0 else float('inf')
        results['sweep'].append({
            'v_eff': float(v),
            'sigma_eff_dB': float(-10 * np.log10(v)),
            'I_CV': float(i_cv),
            'I_DV': float(i_dv),
            'ratio': float(ratio),
            'p_err': float(gkp_p_err(v)),
        })

    print(f"\n  {'σ_eff':>8} {'V_eff':>8} {'I_CV':>12} {'I_DV':>12} {'Ratio':>8} {'p_err':>10}")
    print("  " + "-" * 65)

    for name, v in points:
        i_cv_a = fisher_cv_analytical(v)
        i_cv_n = fisher_cv_numerical(v, rng=rng)
        i_dv = fisher_dv_analytical(v)
        ratio = i_cv_a / i_dv if i_dv > 0 else float('inf')
        sigma_db = -10 * np.log10(v)
        p = gkp_p_err(v)

        print(f"  {sigma_db:7.1f}dB {v:8.4f} {i_cv_a:12.1f} {i_dv:12.4f} "
              f"{ratio:7.0f}x {p:10.2e}  {name}")

        results['operating_points'].append({
            'name': name,
            'v_eff': float(v),
            'sigma_eff_dB': float(sigma_db),
            'I_CV_analytical': float(i_cv_a),
            'I_CV_numerical': float(i_cv_n),
            'I_DV': float(i_dv),
            'ratio': float(ratio),
            'p_err': float(p),
        })

    save_json('b1_fisher_information.json', results)
    return results


# ═══════════════════════════════════════════════════════════════
#  B2: V_eff Estimation — Cycles to Accuracy
# ═══════════════════════════════════════════════════════════════

def estimate_veff_cv(residuals):
    """ML estimator for V_eff from analog residuals: V_hat = mean(r²)."""
    return float(np.mean(residuals ** 2))


def estimate_veff_dv(syndromes, v_eff_prior=0.14):
    """Estimator for V_eff from binary syndromes: invert p_err = count/N."""
    n = len(syndromes)
    p_hat = np.sum(syndromes) / n
    if p_hat < 1e-10:
        return v_eff_prior * 0.5  # No errors: can only say V_eff is low
    if p_hat > 0.49:
        return 0.3  # Saturated
    # Invert p_err = erfc(√π/(4σ))/2 numerically
    from scipy.optimize import brentq
    try:
        v = brentq(lambda v: gkp_p_err(v) - p_hat, 0.01, 0.5)
        return float(v)
    except ValueError:
        return v_eff_prior


def run_b2():
    """B2: V_eff estimation accuracy — CV vs DV, various window sizes."""
    print("\n" + "=" * 70)
    print("  B2: V_eff Estimation — Cycles to 3% Accuracy")
    print("=" * 70)

    rng = np.random.default_rng(SEED)
    v_true = 0.1417  # Phase 1: 8.5dB

    # d=5: 50 data qubits, 5 rounds = 250 modes per QEC cycle
    # d=7: 98 modes × 7 rounds = 686 modes per QEC cycle
    configs = [
        ('d=5', 250),
        ('d=7', 686),
    ]

    cycle_counts = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    n_trials = 500  # Repeat for statistics

    results = {}

    for d_name, modes_per_cycle in configs:
        print(f"\n  {d_name} ({modes_per_cycle} modes/cycle)")
        results[d_name] = []

        for n_cycles in cycle_counts:
            n_modes = modes_per_cycle * n_cycles
            cv_errors = []
            dv_errors = []

            for trial in range(n_trials):
                res, err = gkp_residuals(n_modes, v_true, rng)

                # CV: estimate from residual variance
                v_cv = estimate_veff_cv(res)
                cv_errors.append(abs(v_cv - v_true) / v_true)

                # DV: estimate from binary error rate
                syn = binary_syndromes(err)
                v_dv = estimate_veff_dv(syn, v_eff_prior=v_true)
                dv_errors.append(abs(v_dv - v_true) / v_true)

            cv_median = float(np.median(cv_errors))
            dv_median = float(np.median(dv_errors))
            cv_90 = float(np.percentile(cv_errors, 90))
            dv_90 = float(np.percentile(dv_errors, 90))

            advantage = dv_median / cv_median if cv_median > 0 else float('inf')

            print(f"    {n_cycles:5d} cycles ({n_modes:7d} modes): "
                  f"CV {cv_median:6.2%} DV {dv_median:6.2%}  "
                  f"advantage={advantage:.0f}x")

            results[d_name].append({
                'n_cycles': n_cycles,
                'n_modes': n_modes,
                'cv_median_rel_err': cv_median,
                'dv_median_rel_err': dv_median,
                'cv_90pct': cv_90,
                'dv_90pct': dv_90,
                'advantage': advantage,
                'n_trials': n_trials,
            })

        save_json('b2_veff_estimation.json', results)

    # Find cycles to 3% accuracy
    print(f"\n  === Cycles to 3% median accuracy ===")
    for d_name in results:
        cv_3pct = None
        dv_3pct = None
        for r in results[d_name]:
            if cv_3pct is None and r['cv_median_rel_err'] <= 0.03:
                cv_3pct = r['n_cycles']
            if dv_3pct is None and r['dv_median_rel_err'] <= 0.03:
                dv_3pct = r['n_cycles']
        dv_str = str(dv_3pct) if dv_3pct else ">1000"
        cv_str = str(cv_3pct) if cv_3pct else ">1000"
        print(f"  {d_name}: CV={cv_str} cycles, DV={dv_str} cycles")

    return results


# ═══════════════════════════════════════════════════════════════
#  B4: Anomaly Detection — Advance Warning
# ═══════════════════════════════════════════════════════════════

def run_b4():
    """B4: Detect PLL cycle slip from residual statistics before p_L degrades."""
    print("\n" + "=" * 70)
    print("  B4: Anomaly Detection — Advance Warning Time")
    print("=" * 70)

    rng = np.random.default_rng(SEED + 100)
    modes_per_cycle = 686  # d=7
    n_cycles_before = 200  # Normal operation
    n_cycles_after = 200   # After anomaly
    n_trials = 100

    # Anomaly types
    anomalies = [
        ('PLL cycle slip (+0.5dB)', 0.1417, 0.1417 * 10**(0.5/10)),  # +0.5dB
        ('OPA mode hop (+1.0dB)', 0.1417, 0.1417 * 10**(1.0/10)),    # +1.0dB
        ('Gradual drift (0.3dB/100cyc)', 0.1417, None),              # Linear ramp
    ]

    results = {}

    for anomaly_name, v_before, v_after in anomalies:
        is_gradual = v_after is None
        print(f"\n  Anomaly: {anomaly_name}")

        cv_detections = []
        dv_detections = []

        for trial in range(n_trials):
            cv_stats = []  # Per-cycle residual variance
            dv_stats = []  # Per-cycle error rate

            for cyc in range(n_cycles_before + n_cycles_after):
                if cyc < n_cycles_before:
                    v = v_before
                elif is_gradual:
                    progress = (cyc - n_cycles_before) / n_cycles_after
                    v_target = v_before * 10 ** (0.3 / 10)  # +0.3dB final
                    v = v_before + (v_target - v_before) * progress
                else:
                    v = v_after

                res, err = gkp_residuals(modes_per_cycle, v, rng)
                cv_stats.append(float(np.mean(res ** 2)))
                dv_stats.append(float(np.mean(err)))

            cv_stats = np.array(cv_stats)
            dv_stats = np.array(dv_stats)

            # Baseline statistics (from first 100 cycles)
            cv_base_mean = np.mean(cv_stats[:100])
            cv_base_std = np.std(cv_stats[:100])
            dv_base_mean = np.mean(dv_stats[:100])
            dv_base_std = np.std(dv_stats[:100]) if np.std(dv_stats[:100]) > 0 else 1e-6

            # Detection: first cycle where z-score > 3
            cv_z = (cv_stats - cv_base_mean) / (cv_base_std if cv_base_std > 0 else 1e-6)
            dv_z = (dv_stats - dv_base_mean) / dv_base_std

            cv_detect = None
            dv_detect = None
            for i in range(n_cycles_before, len(cv_z)):
                if cv_detect is None and cv_z[i] > 3:
                    cv_detect = i - n_cycles_before  # Cycles after anomaly
                if dv_detect is None and dv_z[i] > 3:
                    dv_detect = i - n_cycles_before

            cv_detections.append(cv_detect if cv_detect is not None else n_cycles_after)
            dv_detections.append(dv_detect if dv_detect is not None else n_cycles_after)

        cv_arr = np.array(cv_detections)
        dv_arr = np.array(dv_detections)

        cv_med = float(np.median(cv_arr))
        dv_med = float(np.median(dv_arr))
        cv_detect_rate = float(np.mean(cv_arr < n_cycles_after))
        dv_detect_rate = float(np.mean(dv_arr < n_cycles_after))

        print(f"    CV: median {cv_med:.0f} cycles, detect rate {cv_detect_rate:.0%}")
        print(f"    DV: median {dv_med:.0f} cycles, detect rate {dv_detect_rate:.0%}")
        print(f"    Advantage: {dv_med/cv_med:.1f}x faster detection" if cv_med > 0 else "    CV instant")

        results[anomaly_name] = {
            'v_before': float(v_before),
            'v_after': float(v_after) if v_after else 'gradual',
            'cv_median_detect_cycles': cv_med,
            'dv_median_detect_cycles': dv_med,
            'cv_detect_rate': cv_detect_rate,
            'dv_detect_rate': dv_detect_rate,
            'advantage': float(dv_med / cv_med) if cv_med > 0 else float('inf'),
            'n_trials': n_trials,
            'modes_per_cycle': modes_per_cycle,
        }

        save_json('b4_anomaly_detection.json', results)

    return results


# ═══════════════════════════════════════════════════════════════
#  B3: Drift-Adaptive Decoder (Stim-based, the money shot)
# ═══════════════════════════════════════════════════════════════

def ou_process(n_steps, dt, tau, sigma, x0, rng):
    """Ornstein-Uhlenbeck process: dx = -x/tau * dt + sigma * dW."""
    x = np.zeros(n_steps)
    x[0] = x0
    noise_std = sigma * np.sqrt(2 * dt / tau)
    for i in range(1, n_steps):
        x[i] = x[i-1] * (1 - dt/tau) + noise_std * rng.standard_normal()
    return x


def run_b3():
    """B3: Drift-adaptive decoder — static vs adaptive vs oracle."""
    print("\n" + "=" * 70)
    print("  B3: Drift-Adaptive Decoder — Fault-Tolerance Lifetime")
    print("=" * 70)

    import stim, pymatching

    rng = np.random.default_rng(SEED + 200)
    d = 5
    rounds = 5
    v_nominal = 0.1417  # Phase 1: 8.5dB

    # Build surface code graph
    c = stim.Circuit.generated('surface_code:rotated_memory_z',
        rounds=rounds, distance=d,
        before_round_data_depolarization=0.01,
        before_measure_flip_probability=0.01)
    dem = c.detector_error_model(decompose_errors=True)
    edges = []
    for inst in dem.flattened():
        if inst.type != 'error':
            continue
        dets, has_log = [], False
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                dets.append(t.val)
            elif t.is_logical_observable_id():
                has_log = True
        if len(dets) == 1:
            edges.append({'n1': dets[0], 'n2': None, 'log': has_log})
        elif len(dets) == 2:
            edges.append({'n1': dets[0], 'n2': dets[1], 'log': has_log})
    nd = dem.num_detectors
    ne = len(edges)

    # Build matching matrices
    h_mat = np.zeros((nd + 1, ne), dtype=np.uint8)
    f_mat = np.zeros((1, ne), dtype=np.uint8)
    for j, e in enumerate(edges):
        h_mat[e['n1'], j] = 1
        if e['n2'] is not None:
            h_mat[e['n2'], j] = 1
        else:
            h_mat[nd, j] = 1
        if e['log']:
            f_mat[0, j] = 1

    print(f"  d={d}, {ne} edges, {nd} detectors")

    # Drift scenarios
    n_epochs = 500        # Number of time epochs
    shots_per_epoch = 100  # Shots per epoch for p_L estimation
    dt = 1.0              # Arbitrary time unit per epoch

    drift_scenarios = [
        ('Slow thermal (τ=100)', 100.0, 0.01),   # tau=100 epochs, small amplitude
        ('Medium PLL (τ=30)', 30.0, 0.015),       # tau=30 epochs
        ('Fast fluctuation (τ=10)', 10.0, 0.02),  # tau=10 epochs
    ]

    results = {}

    for scenario_name, tau, sigma_drift in drift_scenarios:
        print(f"\n  Scenario: {scenario_name}")

        # Generate V_eff trajectory
        v_drift = ou_process(n_epochs, dt, tau, sigma_drift, 0.0, rng)
        v_trajectory = v_nominal + v_drift
        v_trajectory = np.clip(v_trajectory, 0.05, 0.35)

        static_pL = []
        adaptive_pL = []
        oracle_pL = []
        v_estimated = []
        v_true_list = []

        ema_v = v_nominal  # EMA estimate of V_eff

        for epoch in range(n_epochs):
            v_true = v_trajectory[epoch]
            v_true_list.append(float(v_true))

            # Generate GKP data for this epoch
            err, res, llr_true = _gkp_batch(ne, shots_per_epoch, v_true, rng)
            syn, obs = _compute_syndromes(err, edges, nd)

            # Update V_eff estimate from residuals (EMA)
            v_measured = float(np.mean(res ** 2))
            alpha = 0.3  # EMA smoothing factor
            ema_v = alpha * v_measured + (1 - alpha) * ema_v
            v_estimated.append(float(ema_v))

            # LLR with different V_eff assumptions
            llr_static = _compute_llr(res, v_nominal)     # Static: uses nominal
            llr_adaptive = _compute_llr(res, ema_v)        # Adaptive: uses estimate
            # Oracle already has llr_true

            # Decode
            s_err = _decode_batch(syn, obs, llr_static, h_mat, f_mat, nd)
            a_err = _decode_batch(syn, obs, llr_adaptive, h_mat, f_mat, nd)
            o_err = _decode_batch(syn, obs, llr_true, h_mat, f_mat, nd)

            static_pL.append(float(s_err.sum() / shots_per_epoch))
            adaptive_pL.append(float(a_err.sum() / shots_per_epoch))
            oracle_pL.append(float(o_err.sum() / shots_per_epoch))

            if epoch % 100 == 0:
                print(f"    epoch {epoch:4d}: V_true={v_true:.4f} V_est={ema_v:.4f} "
                      f"static={static_pL[-1]:.3e} adaptive={adaptive_pL[-1]:.3e}")

        # Smooth p_L with window for readability
        win = 20
        def smooth(arr):
            return [float(np.mean(arr[max(0,i-win):i+1])) for i in range(len(arr))]

        static_smooth = smooth(static_pL)
        adaptive_smooth = smooth(adaptive_pL)
        oracle_smooth = smooth(oracle_pL)

        # Fault-tolerance lifetime: first epoch where smoothed p_L > 10^-3
        def ft_lifetime(arr_smooth):
            for i, v in enumerate(arr_smooth):
                if v > 1e-3:
                    return i
            return n_epochs

        lt_static = ft_lifetime(static_smooth)
        lt_adaptive = ft_lifetime(adaptive_smooth)
        lt_oracle = ft_lifetime(oracle_smooth)

        print(f"    FT lifetime: static={lt_static}, adaptive={lt_adaptive}, oracle={lt_oracle}")

        results[scenario_name] = {
            'tau': tau, 'sigma_drift': sigma_drift,
            'v_true': v_true_list,
            'v_estimated': v_estimated,
            'static_pL': static_pL,
            'adaptive_pL': adaptive_pL,
            'oracle_pL': oracle_pL,
            'ft_lifetime_static': lt_static,
            'ft_lifetime_adaptive': lt_adaptive,
            'ft_lifetime_oracle': lt_oracle,
            'n_epochs': n_epochs,
            'shots_per_epoch': shots_per_epoch,
        }

        save_json('b3_adaptive_decoder.json', results)

    return results


def _gkp_batch(ne, ns, v_eff, rng):
    """Generate GKP errors, residuals, LLR for a batch."""
    sigma = np.sqrt(v_eff)
    disp = sigma * rng.standard_normal((ns, ne))
    nl = np.rint(disp / SQRT_PI).astype(np.int64)
    err = (nl % 2) != 0
    res = (disp - nl * SQRT_PI).astype(np.float32)
    ra = np.abs(res)
    llr = np.clip(((SQRT_PI - ra)**2 - ra**2) / (2 * v_eff), -30, 30).astype(np.float32)
    return err, res, llr


def _compute_llr(res, v_eff):
    """Recompute LLR with given V_eff."""
    ra = np.abs(res)
    return np.clip(((SQRT_PI - ra)**2 - ra**2) / (2 * v_eff), -30, 30).astype(np.float32)


def _compute_syndromes(errors, edges, nd):
    ns = errors.shape[0]
    syn = np.zeros((ns, nd), dtype=np.uint8)
    obs = np.zeros(ns, dtype=np.uint8)
    for j, e in enumerate(edges):
        m = errors[:, j]
        syn[m, e['n1']] ^= 1
        if e['n2'] is not None:
            syn[m, e['n2']] ^= 1
        if e['log']:
            obs[m] ^= 1
    return syn, obs


def _decode_batch(syn, obs, weights, h_mat, f_mat, nd):
    import pymatching
    ns = syn.shape[0]
    errs = np.zeros(ns, dtype=np.uint8)
    for i in range(ns):
        ww = np.maximum(weights[i], 0.01)
        m = pymatching.Matching(h_mat, weights=ww, faults_matrix=f_mat)
        m.set_boundary_nodes({nd})
        if m.decode(syn[i])[0] != obs[i]:
            errs[i] = 1
    return errs


# ═══════════════════════════════════════════════════════════════
#  Utilities
# ═══════════════════════════════════════════════════════════════

def save_json(name, data):
    path = os.path.join(OUT_DIR, name)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  [saved {name}]")


# ═══════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()

    print("=" * 70)
    print("  PAPER 2: THE 14-BIT ADVANTAGE")
    print("  CV-QEC analog residuals vs DV-QEC binary syndromes")
    print(f"  seed={SEED}")
    print("=" * 70)

    # B1: Fast (analytical + 1M samples)
    run_b1()

    # B2: Medium (500 trials × 10 window sizes × 2 configs)
    run_b2()

    # B4: Medium (100 trials × 3 anomaly types × 400 cycles)
    run_b4()

    # B3: Heavy (500 epochs × 100 shots × MWPM decode)
    run_b3()

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"  ALL DONE: {elapsed:.0f}s ({elapsed/3600:.1f}h)")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
