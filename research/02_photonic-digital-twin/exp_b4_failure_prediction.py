#!/usr/bin/env python3
"""
Exp-B4: Failure Prediction — Early Warning for Threshold Crossing
==================================================================

Photonic Quantum Digital Twin — Experiment 4

Goal: Predict when p_L will cross the 10^-3 threshold BEFORE it happens,
      giving operators advance warning for preemptive recalibration.

Methods:
  1. Linear extrapolation of V_eff(t) trend
  2. Kalman-predicted V_eff trajectory
  3. Lightweight LSTM on residual variance history

Metric: Advance warning time (in seconds) before p_L > 10^-3

seed=42
"""

import numpy as np
from scipy.special import erfc
import json
import os
import time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')


def compute_V_eff(sigma_gen_dB, L_dB, V_non_loss=0.010):
    V_sqz = 10.0 ** (-sigma_gen_dB / 10.0)
    eta = 10.0 ** (-L_dB / 10.0)
    return eta * V_sqz + (1.0 - eta) + V_non_loss


def compute_p_phys(V_eff):
    return float(erfc(SQRT_PI / (4.0 * np.sqrt(V_eff / 2.0))) / 2.0)


def p_L_from_V_eff(V_eff, d=5, A=0.03, p_th=0.025):
    """Approximate p_L from V_eff using scaling law."""
    p_phys = compute_p_phys(V_eff)
    if p_phys >= p_th:
        return 0.5
    ratio = p_phys / p_th
    return A * ratio ** ((d + 1) / 2)


def V_eff_threshold(d=5, A=0.03, p_th=0.025, p_L_target=1e-3):
    """Find V_eff at which p_L = p_L_target."""
    # Binary search
    lo, hi = 0.05, 0.5
    for _ in range(50):
        mid = (lo + hi) / 2
        if p_L_from_V_eff(mid, d, A, p_th) < p_L_target:
            lo = mid
        else:
            hi = mid
    return mid


# ============================================================
# Predictors
# ============================================================
class LinearExtrapolator:
    """Linear trend extrapolation of V_eff."""

    def __init__(self, lookback=30):
        self.lookback = lookback
        self.history = []

    def update(self, V_eff):
        self.history.append(V_eff)

    def predict_crossing_time(self, V_threshold, current_time, horizon=60):
        """Predict when V_eff will cross V_threshold.

        Returns predicted crossing time (seconds from now), or None.
        """
        if len(self.history) < self.lookback:
            return None

        recent = np.array(self.history[-self.lookback:])
        t_local = np.arange(len(recent))

        # Linear fit
        slope = np.polyfit(t_local, recent, 1)[0]
        if slope <= 0:
            return None  # Moving away from threshold

        current_V = self.history[-1]
        if current_V >= V_threshold:
            return 0  # Already past threshold

        dt = (V_threshold - current_V) / slope
        if dt > horizon:
            return None  # Too far out
        return dt


class KalmanPredictor:
    """Kalman filter with trend prediction."""

    def __init__(self, V_init, process_noise=1e-6):
        # State: [V_eff, dV/dt]
        self.x = np.array([V_init, 0.0])
        self.P = np.diag([1e-4, 1e-6])
        self.Q = np.diag([process_noise, process_noise * 0.1])
        self.dt = 1.0  # seconds

    def update(self, V_measured):
        # Prediction
        F = np.array([[1, self.dt], [0, 1]])
        x_pred = F @ self.x
        P_pred = F @ self.P @ F.T + self.Q

        # Measurement
        H = np.array([[1, 0]])
        R = np.array([[2e-6]])
        S = H @ P_pred @ H.T + R
        K = P_pred @ H.T / S[0, 0]
        self.x = x_pred + K.flatten() * (V_measured - (H @ x_pred)[0])
        self.P = (np.eye(2) - K @ H) @ P_pred

    def predict_crossing_time(self, V_threshold, current_time, horizon=60):
        current_V = self.x[0]
        trend = self.x[1]

        if current_V >= V_threshold:
            return 0
        if trend <= 0:
            return None

        dt = (V_threshold - current_V) / trend
        if dt > horizon:
            return None
        return dt


class WindowTrendPredictor:
    """Multiple-window trend analysis with confidence."""

    def __init__(self, windows=(10, 30, 60)):
        self.windows = windows
        self.history = []

    def update(self, V_eff):
        self.history.append(V_eff)

    def predict_crossing_time(self, V_threshold, current_time, horizon=60):
        if len(self.history) < max(self.windows):
            return None

        predictions = []
        for w in self.windows:
            if len(self.history) < w:
                continue
            recent = np.array(self.history[-w:])
            slope = np.polyfit(np.arange(w), recent, 1)[0]
            if slope > 0:
                dt = (V_threshold - self.history[-1]) / slope
                if 0 < dt < horizon:
                    predictions.append(dt)

        if not predictions:
            return None

        # Return median prediction (robust to outliers)
        return float(np.median(predictions))


# ============================================================
# Exp-B4: Failure Prediction Evaluation
# ============================================================
def run_exp_b4(rng):
    print("=" * 70)
    print("  Exp-B4: Failure Prediction")
    print("=" * 70)

    from exp_b1_drift_model import PhotonicDriftSimulator

    d = 5
    duration_s = 300.0
    dt_fine = 0.01
    dt_coarse = 1.0
    n_windows = int(duration_s / dt_coarse)

    V_th = V_eff_threshold(d=d)
    print(f"  V_eff threshold (p_L=10^-3, d={d}): {V_th:.5f} SNU")
    print(f"  Corresponding σ_eff: {-10*np.log10(V_th):.2f} dB")

    results = {}

    for scenario in ['slow_thermal', 'fast_pll', 'sudden_event']:
        print(f"\n--- Scenario: {scenario} ---")

        # Generate drift trajectory
        drift_rng = np.random.default_rng(42)
        sim = PhotonicDriftSimulator(scenario, dt=dt_fine, rng=drift_rng)
        traj = sim.generate_trajectory(duration_s)

        step_per_window = int(dt_coarse / dt_fine)
        V_true = np.zeros(n_windows)
        for w in range(n_windows):
            idx = min(int((w + 0.5) * step_per_window), len(traj['V_eff']) - 1)
            V_true[w] = traj['V_eff'][idx]

        # Add estimation noise (simulate syndrome-based estimation)
        est_noise_std = 0.001  # ~1% estimation noise on V_eff
        V_estimated = V_true + est_noise_std * rng.standard_normal(n_windows)
        V_estimated = np.clip(V_estimated, 0.05, 0.5)

        # Find actual crossing time
        actual_crossing = None
        for w in range(n_windows):
            if p_L_from_V_eff(V_true[w], d=d) > 1e-3:
                actual_crossing = w
                break

        print(f"  Actual threshold crossing: "
              f"{'t=' + str(actual_crossing) + 's' if actual_crossing else 'never'}")

        # Initialize predictors
        predictors = {
            'Linear_30': LinearExtrapolator(lookback=30),
            'Linear_60': LinearExtrapolator(lookback=60),
            'Kalman': KalmanPredictor(V_estimated[0]),
            'MultiWindow': WindowTrendPredictor(windows=(10, 30, 60)),
        }

        # Run predictions
        predictions = {name: [] for name in predictors}
        pred_times = {name: [] for name in predictors}
        warning_issued = {name: None for name in predictors}

        for w in range(n_windows):
            for name, pred in predictors.items():
                if name == 'Kalman':
                    pred.update(V_estimated[w])
                else:
                    pred.update(V_estimated[w])

                crossing_dt = pred.predict_crossing_time(V_th, w)
                predictions[name].append(crossing_dt)

                # Record first warning
                if crossing_dt is not None and crossing_dt > 0 and warning_issued[name] is None:
                    if actual_crossing is not None:
                        advance = actual_crossing - w
                        if advance > 0:
                            warning_issued[name] = {
                                'warning_time': w,
                                'predicted_crossing': w + crossing_dt,
                                'actual_crossing': actual_crossing,
                                'advance_warning': advance,
                                'prediction_error': abs((w + crossing_dt) - actual_crossing),
                            }

        # Evaluate
        print(f"\n  Predictor performance:")
        for name, info in warning_issued.items():
            if info:
                print(f"    {name:15s}: warning at t={info['warning_time']}s, "
                      f"advance={info['advance_warning']}s, "
                      f"pred_error={info['prediction_error']:.1f}s")
            else:
                print(f"    {name:15s}: no warning issued")

        # Compute ROC-like metrics (for scenarios where crossing occurs)
        tp, fp, fn = {}, {}, {}
        for name in predictors:
            tp[name] = 0
            fp[name] = 0
            fn[name] = 0
            for w in range(n_windows):
                pred_cross = predictions[name][w]
                will_cross = (actual_crossing is not None and
                              w < actual_crossing and
                              actual_crossing - w <= 60)
                if pred_cross is not None and pred_cross > 0:
                    if will_cross:
                        tp[name] += 1
                    else:
                        fp[name] += 1
                else:
                    if will_cross:
                        fn[name] += 1

        print(f"\n  Detection metrics (60s horizon):")
        for name in predictors:
            total = tp[name] + fn[name]
            recall = tp[name] / total if total > 0 else 0
            precision = tp[name] / (tp[name] + fp[name]) if (tp[name] + fp[name]) > 0 else 0
            print(f"    {name:15s}: precision={precision:.2%}, recall={recall:.2%}, "
                  f"TP={tp[name]}, FP={fp[name]}, FN={fn[name]}")

        results[scenario] = {
            'V_eff_true': V_true.tolist(),
            'V_eff_estimated': V_estimated.tolist(),
            'V_threshold': float(V_th),
            'actual_crossing': actual_crossing,
            'predictions': {name: [float(x) if x is not None else None
                                   for x in predictions[name]]
                            for name in predictors},
            'warnings': {name: info for name, info in warning_issued.items()},
            'metrics': {
                name: {'tp': tp[name], 'fp': fp[name], 'fn': fn[name]}
                for name in predictors
            },
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
    fig.suptitle('Exp-B4: Failure Prediction\nAdvance Warning for Threshold Crossing',
                 fontsize=14, fontweight='bold')

    if len(scenarios) == 1:
        axes = axes.reshape(-1, 1)

    for col, scenario in enumerate(scenarios):
        data = results[scenario]
        t = np.arange(len(data['V_eff_true']))
        V_true = np.array(data['V_eff_true'])

        ax = axes[0, col]
        ax.plot(t, V_true, 'k-', lw=1.5, label='True $V_{eff}$')
        ax.axhline(data['V_threshold'], color='red', ls='--', alpha=0.5,
                    label=f'Threshold ({data["V_threshold"]:.4f})')
        if data['actual_crossing']:
            ax.axvline(data['actual_crossing'], color='red', ls=':', alpha=0.3)
        ax.set_ylabel('$V_{eff}$ (SNU)')
        ax.set_title(scenario.replace('_', ' ').title())
        ax.legend(fontsize=8)

        ax = axes[1, col]
        colors = {'Linear_30': '#e74c3c', 'Kalman': '#3498db',
                  'MultiWindow': '#2ecc71', 'Linear_60': '#f39c12'}
        for name, preds in data['predictions'].items():
            valid = [(i, p) for i, p in enumerate(preds) if p is not None and p > 0]
            if valid:
                ts, ps = zip(*valid)
                ax.scatter(ts, ps, s=3, alpha=0.3, color=colors.get(name, 'gray'),
                           label=name)
        ax.set_ylabel('Predicted crossing (s from now)')
        ax.set_xlabel('Time (s)')
        ax.legend(fontsize=7)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_b4_prediction.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  Saved: {path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)

    print("\n  Photonic Quantum Digital Twin — Theme 2")
    print("  Exp-B4: Failure Prediction")
    print()

    t_start = time.time()
    results = run_exp_b4(rng)

    json_path = os.path.join(OUT_DIR, 'exp_b4_results.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved: {json_path}")

    plot_results(results)

    elapsed = time.time() - t_start
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")


if __name__ == '__main__':
    main()
