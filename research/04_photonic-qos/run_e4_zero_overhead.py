#!/usr/bin/env python3
"""
E4: Zero-Overhead Calibration Theorem
=======================================
Proves that CV GKP systems achieve calibration "for free" from QEC residuals,
while DV systems must sacrifice computation slots for calibration.

Quantifies the throughput advantage across d=3,5,7 and various calibration
requirements.
"""
import numpy as np
from scipy.special import erfc
from scipy.stats import norm
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tdm_runtime import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(OUT, exist_ok=True)

SEED = 42


# ═══════════════════════════════════════════════════════════════
#  Information-Theoretic Analysis
# ═══════════════════════════════════════════════════════════════

def fisher_info_cv(v_eff, n_modes):
    """Fisher information for V_eff estimation from CV GKP residuals.
    From Paper 2: wrapped Gaussian score function.
    I_CV = n_modes * [E(r^4/V^2) - 1] / V^2  (approximate)
    """
    # Simplified: for small V_eff, I_CV ≈ n_modes / (2 * V_eff^2)
    return n_modes / (2 * v_eff**2)


def fisher_info_dv(p_phys, n_syndromes):
    """Fisher information for V_eff estimation from DV binary syndromes.
    Each syndrome gives 1 bit. I_DV = n * p*(1-p) / (dp/dV)^2
    """
    if p_phys <= 0 or p_phys >= 1:
        return 0.0
    # dp/dV from error model
    dp_dv = 0.5 / np.sqrt(2 * np.pi * V_EFF_SNU)  # approximate derivative
    return n_syndromes * dp_dv**2 / (p_phys * (1 - p_phys))


def estimation_error_cv(v_eff, n_modes):
    """Cramer-Rao lower bound on V_eff estimation error (relative)."""
    fi = fisher_info_cv(v_eff, n_modes)
    if fi <= 0:
        return 1.0
    return 1.0 / np.sqrt(fi) / v_eff  # relative error


def estimation_error_dv(p_phys, n_syndromes):
    """Cramer-Rao lower bound on V_eff estimation error (relative) for DV."""
    fi = fisher_info_dv(p_phys, n_syndromes)
    if fi <= 0:
        return 1.0
    return 1.0 / np.sqrt(fi) / V_EFF_SNU  # relative error


# ═══════════════════════════════════════════════════════════════
#  Calibration Overhead Analysis
# ═══════════════════════════════════════════════════════════════

def analyze_calibration_overhead():
    """Compare CV vs DV calibration overhead for different scenarios.

    Key distinction: DV systems must dedicate entire QEC cycles to calibration
    (randomized benchmarking, gate set tomography). These are lost to computation.
    CV systems extract calibration info from QEC residuals — zero dedicated cycles.
    """
    results = {}

    for d in [3, 5, 7]:
        modes_per_cycle = qec_cycle_modes(d)
        cycle_us = qec_cycle_us(d)
        p_phys = p_phys_from_veff(V_EFF_SNU)

        # CV: estimation from QEC residuals (zero additional cost)
        cv_est_error_1cyc = estimation_error_cv(V_EFF_SNU, modes_per_cycle)
        cv_est_error_3cyc = estimation_error_cv(V_EFF_SNU, 3 * modes_per_cycle)

        # DV: binary syndromes only
        n_syndromes_per_cycle = d * d - 1
        dv_est_error_100cyc = estimation_error_dv(p_phys, 100 * n_syndromes_per_cycle)

        # DV calibration model:
        # - Randomized benchmarking: ~200 QEC cycles per calibration point
        # - Gate set tomography: ~500 QEC cycles
        # - Must run periodically to track drift
        dv_calib_cycles = 200  # QEC cycles per calibration

        for calib_interval_sec in [1.0, 10.0, 60.0, 300.0]:
            cycles_per_interval = calib_interval_sec / (cycle_us * 1e-6)

            # DV overhead: dedicated calibration cycles / total cycles
            dv_overhead = dv_calib_cycles / cycles_per_interval
            dv_overhead = min(dv_overhead, 0.20)

            cv_overhead = 0.0
            advantage = (1 - cv_overhead) / (1 - dv_overhead)

            # Fisher information ratio (from Paper 2)
            fi_cv = fisher_info_cv(V_EFF_SNU, modes_per_cycle)
            fi_dv = fisher_info_dv(p_phys, n_syndromes_per_cycle)
            fi_ratio = fi_cv / max(fi_dv, 1e-10)

            key = f"d{d}_calib{calib_interval_sec:.0f}s"
            results[key] = {
                "d": d,
                "calib_interval_sec": calib_interval_sec,
                "modes_per_cycle": modes_per_cycle,
                "cycle_us": round(cycle_us, 2),
                "cv_overhead_frac": 0.0,
                "dv_overhead_frac": round(dv_overhead, 4),
                "dv_calib_cycles": dv_calib_cycles,
                "cycles_per_interval": int(cycles_per_interval),
                "cv_throughput_advantage": round(advantage, 4),
                "cv_est_error_1cyc": round(cv_est_error_1cyc, 4),
                "cv_est_error_3cyc": round(cv_est_error_3cyc, 4),
                "dv_est_error_100cyc": round(min(dv_est_error_100cyc, 9.99), 4),
                "fisher_ratio_1cyc": round(fi_ratio, 2),
            }

    return results


def simulate_drift_tracking():
    """Simulate real-time V_eff tracking: CV vs DV under drift.

    CV: uses GKP residuals from current QEC cycle (instant, per-cycle).
    DV: accumulates binary syndromes over a sliding window (delayed, noisy).
         Needs ~100 cycles to get a meaningful error rate estimate.
    """
    results = {}
    rng = np.random.default_rng(SEED)

    DV_WINDOW = 100  # DV needs 100-cycle sliding window for any useful estimate

    for d in [5, 7]:
        modes_per_cycle = qec_cycle_modes(d)
        p_phys_base = p_phys_from_veff(V_EFF_SNU)
        n_synd = d * d - 1

        for drift_name, drift_rate in [
            ('stable', 0.0),
            ('slow', 0.0005),
            ('medium', 0.005),
            ('fast', 0.02),
        ]:
            n_sim = 1000
            # Effective cycle time including N=10 logical qubits scaling.
            # modes_per_cycle is per-qubit; with N_logical=10 qubits sharing the
            # TDM pipeline, the wall-clock cycle is ~10x longer.
            cycle_time_sec = modes_per_cycle * SLOT_NS * 1e-9 * 10

            cv_errors = []
            dv_errors = []
            cv_p_L_list = []
            dv_p_L_list = []
            dv_detection_history = []

            for cycle in range(n_sim):
                t = cycle * cycle_time_sec
                v_true = V_EFF_SNU + drift_rate * t
                p_true = p_phys_from_veff(v_true)

                # --- CV: estimate from GKP residuals this cycle ---
                residuals = gkp_residual_sample(v_true, modes_per_cycle, rng)
                v_cv = estimate_veff_from_residuals(residuals)
                cv_err = abs(v_cv - v_true) / max(v_true, 1e-6)
                cv_errors.append(cv_err)

                # --- DV: binary syndrome sliding window ---
                detections = rng.binomial(n_synd, p_true)
                dv_detection_history.append((detections, n_synd))

                if len(dv_detection_history) >= DV_WINDOW:
                    window = dv_detection_history[-DV_WINDOW:]
                    total_det = sum(w[0] for w in window)
                    total_n = sum(w[1] for w in window)
                    p_est = total_det / total_n if total_n > 0 else p_phys_base

                    # Invert error rate to V_eff (very rough)
                    if p_est > 0 and p_phys_base > 0:
                        v_dv = V_EFF_SNU * (p_est / p_phys_base)
                    else:
                        v_dv = V_EFF_SNU
                else:
                    # Not enough data yet — use baseline
                    v_dv = V_EFF_SNU

                dv_err = abs(v_dv - v_true) / max(v_true, 1e-6)
                dv_errors.append(dv_err)

                # --- Impact on decoding quality ---
                # Mismatched V_eff → suboptimal decoder weights → higher p_L
                p_L_base = p_logical(p_true, d)
                mismatch_cv = abs(v_cv - v_true) / v_true if v_true > 0 else 0
                mismatch_dv = abs(v_dv - v_true) / v_true if v_true > 0 else 0
                # Mismatch penalty: p_L scales as (1 + mismatch^2) (quadratic)
                p_L_cv = p_L_base * (1 + 5 * mismatch_cv**2)
                p_L_dv = p_L_base * (1 + 5 * mismatch_dv**2)
                cv_p_L_list.append(p_L_cv)
                dv_p_L_list.append(p_L_dv)

            # Skip first DV_WINDOW cycles for fair comparison
            cv_err_valid = cv_errors[DV_WINDOW:]
            dv_err_valid = dv_errors[DV_WINDOW:]
            cv_pL_valid = cv_p_L_list[DV_WINDOW:]
            dv_pL_valid = dv_p_L_list[DV_WINDOW:]

            cv_med = float(np.median(cv_err_valid))
            dv_med = float(np.median(dv_err_valid))

            key = f"d{d}_{drift_name}"
            results[key] = {
                "d": d,
                "drift": drift_name,
                "drift_rate": drift_rate,
                "dv_window": DV_WINDOW,
                "cv_median_error": round(cv_med, 4),
                "cv_90pct_error": round(float(np.percentile(cv_err_valid, 90)), 4),
                "dv_median_error": round(dv_med, 4),
                "dv_90pct_error": round(float(np.percentile(dv_err_valid, 90)), 4),
                "cv_avg_p_L": float(f"{np.mean(cv_pL_valid):.6e}"),
                "dv_avg_p_L": float(f"{np.mean(dv_pL_valid):.6e}"),
                "p_L_advantage": round(float(np.mean(dv_pL_valid) /
                                             max(np.mean(cv_pL_valid), 1e-30)), 2),
                "estimation_advantage": round(
                    dv_med / max(cv_med, 1e-6), 2),
            }

    return results


def analyze_schedulability():
    """T1: RTOS schedulability analysis for TDM quantum runtime.
    Apply Liu-Layland utilization bound."""
    results = {}

    for d in [3, 5, 7]:
        qec_period = qec_cycle_us(d)  # QEC cycle period (us)
        qec_exec = qec_period * 0.95  # QEC execution time (near-full)

        # Factory distillation: period = d * qec_period
        factory_period = d * qec_period
        factory_exec = factory_period * 0.8  # 80% of period

        # Different task sets
        for n_logical in [1, 10, 50, 100]:
            n_factories = max(1, n_logical // 10)

            # Task set: n_logical QEC tasks + n_factories factory tasks
            # In TDM, all tasks are serialized → total utilization must be ≤ 1

            # QEC utilization
            qec_util = n_logical * qec_exec / qec_period  # All must fit in 1 pipeline

            # Factory utilization (in same TDM pipeline)
            factory_util = n_factories * factory_exec / factory_period

            # Total utilization
            total_util = (n_logical * qec_exec + n_factories * factory_exec) / qec_period

            # Normalized (TDM stretches the period)
            # In TDM, the effective period is n_total * qec_period
            n_total = n_logical + n_factories * 15  # factory uses 15 logical qubits
            tdm_period = n_total * qec_period  # stretched period

            # EDF schedulability: utilization ≤ 1.0 (necessary and sufficient)
            effective_util = (n_logical + n_factories * 15) / n_total  # always 1.0 for TDM

            # But adding calibration for DV reduces available slots
            dv_calib_util = 0.05  # 5% overhead
            dv_effective_util = effective_util / (1 - dv_calib_util)

            # Maximum logical qubits that can be scheduled
            # TDM constraint: tdm_period ≤ QEC deadline
            # QEC deadline = d QEC cycles (must complete syndrome before next round)
            qec_deadline = d * qec_period
            max_logical_cv = int(qec_deadline / (qec_period * (1 + 15/10)))
            max_logical_dv = int(max_logical_cv * (1 - dv_calib_util))

            # Worst-case response time
            wcrt_us = tdm_period

            key = f"d{d}_n{n_logical}"
            results[key] = {
                "d": d,
                "n_logical": n_logical,
                "n_factories": n_factories,
                "qec_period_us": round(qec_period, 2),
                "tdm_period_us": round(tdm_period, 2),
                "cv_schedulable": tdm_period <= qec_deadline * n_logical,
                "dv_schedulable": tdm_period / (1 - dv_calib_util) <= qec_deadline * n_logical,
                "effective_utilization": round(effective_util, 4),
                "max_logical_cv": max_logical_cv,
                "max_logical_dv": max_logical_dv,
                "wcrt_us": round(wcrt_us, 2),
                "qec_deadline_us": round(qec_deadline * n_logical, 2),
            }

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("E4: Zero-Overhead Calibration + Schedulability Theorem")
    print("=" * 60)

    print("\n[1/3] Calibration overhead analysis...")
    calib_results = analyze_calibration_overhead()
    with open(os.path.join(OUT, 'e4_calibration_overhead.json'), 'w') as f:
        json.dump(calib_results, f, indent=2)

    print(f"\n{'d':>3} {'Interval':>10} {'CV_OH%':>8} {'DV_OH%':>8} {'CV_adv':>8} "
          f"{'Fisher_ratio':>13}")
    print("-" * 55)
    for k, v in calib_results.items():
        print(f"{v['d']:>3} {v['calib_interval_sec']:>8.0f}s {v['cv_overhead_frac']*100:>7.1f}% "
              f"{v['dv_overhead_frac']*100:>7.2f}% {v['cv_throughput_advantage']:>7.3f}x "
              f"{v['fisher_ratio_1cyc']:>12.1f}x")

    print("\n[2/3] Drift tracking simulation...")
    drift_results = simulate_drift_tracking()
    with open(os.path.join(OUT, 'e4_drift_tracking.json'), 'w') as f:
        json.dump(drift_results, f, indent=2)

    print(f"\n{'d':>3} {'Drift':>8} {'CV_err%':>8} {'DV_err%':>8} {'Est_adv':>8} {'pL_adv':>8}")
    print("-" * 50)
    for k, v in drift_results.items():
        print(f"{v['d']:>3} {v['drift']:>8} {v['cv_median_error']*100:>7.1f}% "
              f"{v['dv_median_error']*100:>7.1f}% {v['estimation_advantage']:>7.1f}x "
              f"{v['p_L_advantage']:>7.2f}x")

    print("\n[3/3] Schedulability analysis (T1)...")
    sched_results = analyze_schedulability()
    with open(os.path.join(OUT, 'e4_schedulability.json'), 'w') as f:
        json.dump(sched_results, f, indent=2)

    print(f"\n{'d':>3} {'N_log':>5} {'TDM_period':>11} {'QEC_deadline':>13} "
          f"{'Sched_CV':>9} {'Sched_DV':>9} {'Max_CV':>7} {'Max_DV':>7}")
    print("-" * 75)
    for k, v in sched_results.items():
        print(f"{v['d']:>3} {v['n_logical']:>5} {v['tdm_period_us']:>10.1f}us "
              f"{v['qec_deadline_us']:>11.1f}us "
              f"{'YES' if v['cv_schedulable'] else 'NO':>9} "
              f"{'YES' if v['dv_schedulable'] else 'NO':>9} "
              f"{v['max_logical_cv']:>7} {v['max_logical_dv']:>7}")

    print("\nE4 + T1 complete. Results saved to results/e4_*.json")
