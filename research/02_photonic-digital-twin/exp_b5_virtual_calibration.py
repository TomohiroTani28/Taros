#!/usr/bin/env python3
"""
Exp-B5: Virtual Calibration — Optimal Recalibration Scheduling
================================================================

Photonic Quantum Digital Twin — Experiment 5

Goal: Use the digital twin to optimize when to recalibrate the system,
      minimizing both total logical errors and calibration downtime.

Three strategies compared:
  1. Periodic: Recalibrate every T_cal seconds (fixed interval)
  2. Threshold: Recalibrate when estimated p_L exceeds threshold
  3. Twin-predicted: Recalibrate based on twin's failure prediction

Metric:
  - Total logical error count over simulation
  - Number of recalibrations
  - Effective duty cycle (fraction of time doing computation)

seed=42
"""

import numpy as np
from scipy.special import erfc
import json
import os
import time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')


def compute_p_phys(V_eff):
    return float(erfc(SQRT_PI / (4.0 * np.sqrt(V_eff / 2.0))) / 2.0)


def p_L_from_V_eff(V_eff, d=5, A=0.03, p_th=0.025):
    p_phys = compute_p_phys(V_eff)
    if p_phys >= p_th:
        return 0.5
    return A * (p_phys / p_th) ** ((d + 1) / 2)


# ============================================================
# Calibration Strategies
# ============================================================
class PeriodicCalibration:
    """Recalibrate every T_cal seconds."""

    def __init__(self, T_cal):
        self.T_cal = T_cal
        self.last_cal = 0

    def should_recalibrate(self, t, V_est, p_L_est):
        if t - self.last_cal >= self.T_cal:
            self.last_cal = t
            return True
        return False


class ThresholdCalibration:
    """Recalibrate when estimated p_L exceeds a threshold."""

    def __init__(self, p_L_trigger=5e-4, cooldown=10):
        self.p_L_trigger = p_L_trigger
        self.cooldown = cooldown
        self.last_cal = -cooldown

    def should_recalibrate(self, t, V_est, p_L_est):
        if t - self.last_cal < self.cooldown:
            return False
        if p_L_est > self.p_L_trigger:
            self.last_cal = t
            return True
        return False


class TwinPredictedCalibration:
    """Recalibrate based on digital twin's failure prediction."""

    def __init__(self, warning_horizon=30, cooldown=10):
        self.warning_horizon = warning_horizon
        self.cooldown = cooldown
        self.last_cal = -cooldown
        self.history = []
        self.lookback = 30

    def should_recalibrate(self, t, V_est, p_L_est):
        self.history.append(V_est)
        if t - self.last_cal < self.cooldown:
            return False

        # Predict V_eff trend
        if len(self.history) < self.lookback:
            return False

        recent = np.array(self.history[-self.lookback:])
        slope = np.polyfit(np.arange(self.lookback), recent, 1)[0]

        if slope <= 0:
            return False

        # Find V_threshold for p_L = 10^-3
        V_th = 0.155  # Pre-computed approximate threshold for d=5
        current_V = self.history[-1]
        if current_V >= V_th:
            self.last_cal = t
            return True

        dt_to_threshold = (V_th - current_V) / slope
        if dt_to_threshold < self.warning_horizon:
            self.last_cal = t
            return True

        return False


# ============================================================
# Exp-B5: Virtual Calibration Optimization
# ============================================================
def run_exp_b5(rng):
    print("=" * 70)
    print("  Exp-B5: Virtual Calibration — Optimal Recalibration Scheduling")
    print("=" * 70)

    from exp_b1_drift_model import PhotonicDriftSimulator

    d = 5
    duration_s = 600.0  # 10 minutes
    dt_fine = 0.01
    dt_coarse = 1.0
    n_windows = int(duration_s / dt_coarse)
    cal_downtime = 5.0  # 5 seconds per recalibration

    results = {}

    for scenario in ['slow_thermal', 'fast_pll', 'sudden_event']:
        print(f"\n--- Scenario: {scenario} ---")

        # Generate longer drift trajectory
        drift_rng = np.random.default_rng(42)
        sim = PhotonicDriftSimulator(scenario, dt=dt_fine, rng=drift_rng)
        traj = sim.generate_trajectory(duration_s)

        step_per_window = int(dt_coarse / dt_fine)
        V_true = np.zeros(n_windows)
        for w in range(n_windows):
            idx = min(int((w + 0.5) * step_per_window), len(traj['V_eff']) - 1)
            V_true[w] = traj['V_eff'][idx]

        # Initial calibration point
        V_cal = V_true[0]

        # Add estimation noise
        V_estimated = V_true + 0.001 * rng.standard_normal(n_windows)
        V_estimated = np.clip(V_estimated, 0.05, 0.5)

        # Define strategies
        strategies = {
            'No_cal': None,  # No recalibration
            'Periodic_30s': PeriodicCalibration(30),
            'Periodic_60s': PeriodicCalibration(60),
            'Periodic_120s': PeriodicCalibration(120),
            'Threshold': ThresholdCalibration(p_L_trigger=5e-4, cooldown=10),
            'Twin': TwinPredictedCalibration(warning_horizon=30, cooldown=10),
        }

        scenario_results = {}

        for strat_name, strategy in strategies.items():
            # Reset calibration state
            if strategy:
                strategy.last_cal = 0 if hasattr(strategy, 'last_cal') else -10
                if hasattr(strategy, 'history'):
                    strategy.history = []

            V_decoder = V_true[0]  # Decoder calibrated to initial V_eff
            total_errors = 0
            n_calibrations = 0
            downtime = 0
            p_L_trajectory = np.zeros(n_windows)
            cal_times = []

            for w in range(n_windows):
                # Check if in calibration downtime
                if cal_times and w - cal_times[-1] < cal_downtime:
                    p_L_trajectory[w] = 0  # Not computing during calibration
                    continue

                # Compute p_L with decoder mismatch
                V_now = V_true[w]
                # Mismatch effect: decoder uses V_decoder for LLR, but true noise is V_now
                # Approximate mismatch penalty
                mismatch = abs(V_now - V_decoder) / V_decoder
                p_L_base = p_L_from_V_eff(V_now, d=d)
                # Mismatch increases p_L (empirical: ~2x per 10% mismatch)
                mismatch_penalty = 1.0 + 5.0 * mismatch ** 2
                p_L_effective = min(p_L_base * mismatch_penalty, 0.5)
                p_L_trajectory[w] = p_L_effective
                total_errors += p_L_effective  # Accumulate expected errors

                # Check if should recalibrate
                p_L_est = p_L_from_V_eff(V_estimated[w], d=d)
                if strategy and strategy.should_recalibrate(w, V_estimated[w], p_L_est):
                    V_decoder = V_now  # Reset decoder to current state
                    n_calibrations += 1
                    cal_times.append(w)
                    downtime += cal_downtime

            duty_cycle = (duration_s - downtime) / duration_s

            print(f"  {strat_name:15s}: errors={total_errors:.2f}, "
                  f"cals={n_calibrations}, "
                  f"duty={duty_cycle:.2%}")

            scenario_results[strat_name] = {
                'total_errors': float(total_errors),
                'n_calibrations': n_calibrations,
                'downtime_s': float(downtime),
                'duty_cycle': float(duty_cycle),
                'p_L_trajectory': p_L_trajectory.tolist(),
                'cal_times': cal_times,
            }

        results[scenario] = {
            'V_eff_true': V_true.tolist(),
            'strategies': scenario_results,
            'd': d,
            'duration_s': duration_s,
            'cal_downtime_s': cal_downtime,
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

    plt.rcParams.update({'font.size': 11, 'axes.grid': True, 'grid.alpha': 0.3})

    scenarios = list(results.keys())
    fig, axes = plt.subplots(2, len(scenarios), figsize=(6*len(scenarios), 10))
    fig.suptitle('Exp-B5: Virtual Calibration — Recalibration Strategy Comparison\n'
                 'Photonic Quantum Digital Twin',
                 fontsize=14, fontweight='bold')

    if len(scenarios) == 1:
        axes = axes.reshape(-1, 1)

    strat_colors = {
        'No_cal': '#e74c3c',
        'Periodic_30s': '#f39c12',
        'Periodic_60s': '#e67e22',
        'Periodic_120s': '#d35400',
        'Threshold': '#3498db',
        'Twin': '#2ecc71',
    }

    for col, scenario in enumerate(scenarios):
        data = results[scenario]
        t = np.arange(len(data['V_eff_true']))

        # Row 1: p_L trajectories
        ax = axes[0, col]
        for strat_name, sdata in data['strategies'].items():
            p_L = np.array(sdata['p_L_trajectory'])
            # Smooth
            kernel = 10
            if len(p_L) > kernel:
                p_smooth = np.convolve(p_L, np.ones(kernel)/kernel, mode='valid')
                t_smooth = t[:len(p_smooth)]
                p_smooth = np.maximum(p_smooth, 1e-6)
                ax.semilogy(t_smooth, p_smooth, lw=1.2, alpha=0.7,
                            color=strat_colors.get(strat_name, 'gray'),
                            label=strat_name)

        ax.axhline(1e-3, color='red', ls='--', alpha=0.5, label='$10^{-3}$')
        ax.set_ylabel('$p_L$ (smoothed)')
        ax.set_title(scenario.replace('_', ' ').title())
        ax.legend(fontsize=6, ncol=2)

        # Row 2: Summary bar chart
        ax = axes[1, col]
        names = list(data['strategies'].keys())
        errors = [data['strategies'][n]['total_errors'] for n in names]
        colors = [strat_colors.get(n, 'gray') for n in names]

        bars = ax.bar(range(len(names)), errors, color=colors, alpha=0.8)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels([n.replace('_', '\n') for n in names],
                           fontsize=7, rotation=45, ha='right')
        ax.set_ylabel('Total Expected Errors')

        # Annotate with cal count
        for i, (bar, name) in enumerate(zip(bars, names)):
            n_cal = data['strategies'][name]['n_calibrations']
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{n_cal}cal', ha='center', va='bottom', fontsize=7)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_b5_calibration.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  Saved: {path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)

    print("\n  Photonic Quantum Digital Twin — Theme 2")
    print("  Exp-B5: Virtual Calibration Optimization")
    print()

    t_start = time.time()
    results = run_exp_b5(rng)

    json_path = os.path.join(OUT_DIR, 'exp_b5_results.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved: {json_path}")

    plot_results(results)

    elapsed = time.time() - t_start
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY: Virtual Calibration Results")
    print("=" * 70)
    for scenario, data in results.items():
        print(f"\n  {scenario}:")
        print(f"    {'Strategy':15s} {'Errors':>10} {'Cals':>6} {'Duty':>8}")
        print(f"    {'-'*41}")
        for name, sdata in data['strategies'].items():
            print(f"    {name:15s} {sdata['total_errors']:>10.2f} "
                  f"{sdata['n_calibrations']:>6} "
                  f"{sdata['duty_cycle']:>7.1%}")


if __name__ == '__main__':
    main()
