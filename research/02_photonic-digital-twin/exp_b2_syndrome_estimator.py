#!/usr/bin/env python3
"""
Exp-B2: Syndrome-Based Hardware State Estimation
=================================================

Photonic Quantum Digital Twin — Experiment 2

Goal: Demonstrate that V_eff can be estimated in real-time from QEC
      syndrome statistics alone, without external sensors.

Key insight: GKP residuals r_i ~ N(0, V_eff), so their variance
            directly tracks V_eff. The QEC syndrome stream is itself
            a rich telemetry channel for hardware health monitoring.

Methods compared:
  1. Sliding-window ML estimator (V_hat = sample variance of residuals)
  2. Exponential moving average (EMA) of residual variance
  3. Bayesian Kalman filter with OU prior on V_eff drift

Metric: |V_eff_estimated - V_eff_true| / V_eff_true (relative error)

Builds on Exp-B1 drift trajectories.

seed=42
"""

import numpy as np
from scipy.special import erfc
import json
import os
import time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')


# ============================================================
# Physics (from Paper 1)
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
# Drift model (from Exp-B1)
# ============================================================
class OUDriftModel:
    def __init__(self, mu, theta, sigma_ou, dt, rng, x0=None):
        self.mu = mu
        self.theta = theta
        self.sigma_ou = sigma_ou
        self.dt = dt
        self.rng = rng
        self.x = x0 if x0 is not None else mu

    def step(self):
        dx = -self.theta * (self.x - self.mu) * self.dt
        dx += self.sigma_ou * np.sqrt(self.dt) * self.rng.standard_normal()
        self.x += dx
        return self.x


def generate_drift_trajectory(duration_s, dt, rng, scenario='slow_thermal'):
    """Generate V_eff(t) trajectory matching Exp-B1 scenarios."""
    from exp_b1_drift_model import PhotonicDriftSimulator
    sim = PhotonicDriftSimulator(scenario, dt=dt, rng=rng)
    return sim.generate_trajectory(duration_s)


# ============================================================
# GKP Residual Simulation (no QEC decoding needed for estimation)
# ============================================================
def simulate_gkp_residuals(V_eff, n_modes, rng):
    """
    Simulate GKP displacement noise and return residuals.

    In each QEC cycle, n_modes homodyne measurements produce residuals
    r_i = displacement mod sqrt(pi), folded to [-sqrt(pi)/2, sqrt(pi)/2).

    The variance of r_i tracks V_eff (for V_eff << pi).
    """
    sigma = np.sqrt(V_eff)
    displacements = sigma * rng.standard_normal(n_modes)
    n_lattice = np.rint(displacements / SQRT_PI).astype(np.int64)
    residuals = displacements - n_lattice * SQRT_PI
    return residuals


# ============================================================
# Estimators
# ============================================================
class SlidingWindowEstimator:
    """
    ML estimator: V_hat = sample variance of residuals in a window.

    For GKP residuals r ~ N(0, V_eff) (approximate for V_eff << pi):
      Var(r) = V_eff * (1 - 2*V_eff/pi + ...) ≈ V_eff

    Correction factor for modular folding (wrapped Gaussian):
      V_hat_corrected = V_hat / (1 - 2*V_hat/pi)
    """

    def __init__(self, window_size):
        self.window_size = window_size
        self.buffer = []

    def update(self, residuals):
        self.buffer.extend(residuals.tolist())
        if len(self.buffer) > self.window_size:
            self.buffer = self.buffer[-self.window_size:]

    def estimate(self):
        if len(self.buffer) < 10:
            return None
        var_raw = np.var(self.buffer)
        # Correction for modular folding
        if var_raw < np.pi / 3:
            return var_raw / (1.0 - 2.0 * var_raw / np.pi)
        return var_raw  # Fallback for large noise


class EMAEstimator:
    """Exponential moving average of residual variance."""

    def __init__(self, alpha=0.1):
        self.alpha = alpha
        self.V_hat = None

    def update(self, residuals):
        var_batch = np.var(residuals)
        if self.V_hat is None:
            self.V_hat = var_batch
        else:
            self.V_hat = self.alpha * var_batch + (1.0 - self.alpha) * self.V_hat

    def estimate(self):
        if self.V_hat is None:
            return None
        var_raw = self.V_hat
        if var_raw < np.pi / 3:
            return var_raw / (1.0 - 2.0 * var_raw / np.pi)
        return var_raw


class KalmanEstimator:
    """
    Kalman filter for V_eff estimation with OU prior on drift.

    State: x = V_eff
    Process: x_{k+1} = x_k + theta*(mu - x_k)*dt + process_noise
    Measurement: z_k = sample_variance(residuals) ≈ V_eff + measurement_noise
    """

    def __init__(self, V_eff_init, process_noise=1e-6, dt=1.0):
        self.x = V_eff_init  # State estimate
        self.P = 1e-4  # State covariance
        self.Q = process_noise  # Process noise
        self.dt = dt

    def update(self, residuals):
        n = len(residuals)
        # Measurement: sample variance
        z = np.var(residuals)
        # Measurement correction for folding
        if z < np.pi / 3:
            z = z / (1.0 - 2.0 * z / np.pi)

        # Measurement noise: Var(sample_variance) ≈ 2*V^2/n
        R = 2.0 * self.x ** 2 / max(n, 1)

        # Predict
        x_pred = self.x  # Simple random walk (OU mean-reversion handled by Q)
        P_pred = self.P + self.Q

        # Update
        K = P_pred / (P_pred + R)
        self.x = x_pred + K * (z - x_pred)
        self.P = (1.0 - K) * P_pred

        # Clamp
        self.x = max(self.x, 0.01)

    def estimate(self):
        return self.x


# ============================================================
# Exp-B2: Estimator Comparison
# ============================================================
def run_exp_b2(rng):
    """
    Compare three estimators on tracking V_eff(t) under drift.

    For each scenario:
      1. Generate V_eff(t) trajectory
      2. At each time step, simulate n_modes GKP residuals
      3. Feed to each estimator
      4. Record estimation error
    """
    print("=" * 70)
    print("  Exp-B2: Syndrome-Based Hardware State Estimation")
    print("=" * 70)

    duration_s = 300.0
    dt = 1.0  # 1 second per estimation step
    n_steps = int(duration_s / dt)

    # Number of GKP modes per QEC cycle at 100MHz TDM
    # d=5 surface code: ~50 modes/cycle, 100MHz -> ~10^6 modes/second
    # We use a realistic subset for estimation
    n_modes_per_step = 5000  # 5000 residuals per second (conservative)

    # Window sizes to compare
    window_sizes = [500, 1000, 5000, 10000]

    results = {}

    for scenario in ['slow_thermal', 'fast_pll', 'sudden_event']:
        print(f"\n--- Scenario: {scenario} ---")

        # Generate drift trajectory at fine resolution, then subsample
        drift_rng = np.random.default_rng(42)
        fine_dt = 0.01
        from exp_b1_drift_model import PhotonicDriftSimulator
        sim = PhotonicDriftSimulator(scenario, dt=fine_dt, rng=drift_rng)
        traj = sim.generate_trajectory(duration_s)

        # Subsample to estimation resolution
        step_indices = (np.arange(n_steps) * dt / fine_dt).astype(int)
        step_indices = np.clip(step_indices, 0, len(traj['V_eff']) - 1)
        V_eff_true = traj['V_eff'][step_indices]

        # Initialize estimators
        estimators = {
            f'SW_{ws}': SlidingWindowEstimator(ws) for ws in window_sizes
        }
        estimators['EMA_0.05'] = EMAEstimator(alpha=0.05)
        estimators['EMA_0.10'] = EMAEstimator(alpha=0.10)
        estimators['EMA_0.20'] = EMAEstimator(alpha=0.20)
        estimators['Kalman'] = KalmanEstimator(
            V_eff_init=V_eff_true[0], process_noise=1e-6
        )

        estimates = {name: np.zeros(n_steps) for name in estimators}
        est_rng = np.random.default_rng(123)  # Separate RNG for residuals

        t0 = time.time()
        for i in range(n_steps):
            # Simulate GKP residuals at current V_eff
            residuals = simulate_gkp_residuals(V_eff_true[i], n_modes_per_step, est_rng)

            # Update all estimators
            for name, est in estimators.items():
                est.update(residuals)
                v = est.estimate()
                estimates[name][i] = v if v is not None else V_eff_true[0]

            if i % 60 == 0:
                elapsed = time.time() - t0
                best_est = min(estimators.keys(),
                               key=lambda n: abs(estimates[n][i] - V_eff_true[i]))
                best_err = abs(estimates[best_est][i] - V_eff_true[i]) / V_eff_true[i]
                print(f"  t={i}s: V_eff_true={V_eff_true[i]:.5f}, "
                      f"best={best_est} (err={best_err:.3%})  [{elapsed:.1f}s]")

        # Compute metrics
        metrics = {}
        for name in estimators:
            rel_error = np.abs(estimates[name] - V_eff_true) / V_eff_true
            # Skip warmup period (first 10s for sliding window)
            warmup = max(10, window_sizes[0] // n_modes_per_step + 1) if 'SW' in name else 5
            rel_error_stable = rel_error[warmup:]

            metrics[name] = {
                'mean_rel_error': float(np.mean(rel_error_stable)),
                'max_rel_error': float(np.max(rel_error_stable)),
                'p95_rel_error': float(np.percentile(rel_error_stable, 95)),
                'std_rel_error': float(np.std(rel_error_stable)),
                'tracking_latency_s': float(warmup),
            }
            print(f"  {name:12s}: mean={metrics[name]['mean_rel_error']:.3%}, "
                  f"p95={metrics[name]['p95_rel_error']:.3%}, "
                  f"max={metrics[name]['max_rel_error']:.3%}")

        results[scenario] = {
            'time': np.arange(n_steps).tolist(),
            'V_eff_true': V_eff_true.tolist(),
            'estimates': {name: estimates[name].tolist() for name in estimators},
            'metrics': metrics,
            'n_modes_per_step': n_modes_per_step,
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
    fig.suptitle('Exp-B2: Syndrome-Based V_eff Estimation\n'
                 'QEC Syndromes as Hardware Telemetry (No External Sensors)',
                 fontsize=14, fontweight='bold')

    est_colors = {
        'SW_500': '#e74c3c',
        'SW_5000': '#3498db',
        'EMA_0.10': '#2ecc71',
        'Kalman': '#9b59b6',
    }

    for col, (scenario, title) in enumerate(zip(scenarios, titles)):
        data = results[scenario]
        t = np.array(data['time'])
        V_true = np.array(data['V_eff_true'])

        # Row 1: V_eff tracking
        ax = axes[0, col]
        ax.plot(t, V_true, 'k-', lw=2, alpha=0.7, label='True $V_{eff}$')
        for name, color in est_colors.items():
            if name in data['estimates']:
                V_est = np.array(data['estimates'][name])
                ax.plot(t, V_est, color=color, lw=1, alpha=0.7, label=name)
        ax.set_ylabel('$V_{eff}$ (SNU)')
        ax.set_title(title)
        ax.legend(fontsize=7, ncol=2)

        # Row 2: Relative error
        ax = axes[1, col]
        for name, color in est_colors.items():
            if name in data['estimates']:
                V_est = np.array(data['estimates'][name])
                rel_err = np.abs(V_est - V_true) / V_true * 100
                ax.plot(t, rel_err, color=color, lw=1, alpha=0.7, label=name)
        ax.axhline(3.0, color='red', ls='--', alpha=0.5, label='3% target')
        ax.set_ylabel('Relative Error (%)')
        ax.set_xlabel('Time (s)')
        ax.set_ylim(0, 15)
        ax.legend(fontsize=7, ncol=2)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_b2_estimation.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  Saved: {path}")

    # Summary bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle('Estimator Comparison: Mean Relative Error (%)',
                 fontsize=13, fontweight='bold')

    x = np.arange(len(scenarios))
    width = 0.15
    for i, (name, color) in enumerate(est_colors.items()):
        vals = []
        for scenario in scenarios:
            if name in results[scenario]['metrics']:
                vals.append(results[scenario]['metrics'][name]['mean_rel_error'] * 100)
            else:
                vals.append(0)
        ax.bar(x + i * width, vals, width, label=name, color=color, alpha=0.8)

    ax.set_xticks(x + 1.5 * width)
    ax.set_xticklabels([s.replace('_', ' ').title() for s in scenarios])
    ax.set_ylabel('Mean Relative Error (%)')
    ax.axhline(3.0, color='red', ls='--', alpha=0.5)
    ax.legend()
    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_b2_comparison.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)

    print("\n  Photonic Quantum Digital Twin — Theme 2")
    print("  Exp-B2: Syndrome-Based Hardware State Estimation")
    print()

    t_start = time.time()
    results = run_exp_b2(rng)

    # Save
    json_path = os.path.join(OUT_DIR, 'exp_b2_results.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved: {json_path}")

    # Plot
    plot_results(results)

    elapsed = time.time() - t_start
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY: Syndrome-Based Estimation Accuracy")
    print("=" * 70)
    for scenario in ['slow_thermal', 'fast_pll', 'sudden_event']:
        print(f"\n  {scenario}:")
        for name, m in results[scenario]['metrics'].items():
            print(f"    {name:12s}: mean={m['mean_rel_error']:.3%}, "
                  f"p95={m['p95_rel_error']:.3%}")


if __name__ == '__main__':
    main()
