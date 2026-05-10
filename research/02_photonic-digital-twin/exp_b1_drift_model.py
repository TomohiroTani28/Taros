#!/usr/bin/env python3
"""
Exp-B1: Time-Varying Noise and Fault-Tolerance Lifetime
========================================================

Photonic Quantum Digital Twin — Experiment 1

Goal: Demonstrate that thermal drift at room temperature degrades
      fault-tolerant performance over time, and quantify the
      "fault-tolerance lifetime" under a static decoder.

Physics:
  - V_eff(t) = eta(t) * V_sqz(t) + (1-eta(t)) + V_nl(t)
  - Each component drifts as Ornstein-Uhlenbeck process
  - Three scenarios: slow thermal, fast PLL, sudden event

Key result: Number of QEC cycles before p_L crosses 10^-3 threshold.

Builds on Paper 1 (Exp-A2/A3b) by extending static noise to time-varying.

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


# ============================================================
# Physics: Taros CV Noise Model (from Paper 1)
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
# NEW: Ornstein-Uhlenbeck Drift Model
# ============================================================
class OUDriftModel:
    """
    Ornstein-Uhlenbeck process for parameter drift.

    dX = -theta * (X - mu) * dt + sigma_ou * dW

    Parameters:
      mu: long-term mean
      theta: mean-reversion rate (1/tau)
      sigma_ou: volatility
      dt: time step (in seconds)
    """

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

    def trajectory(self, n_steps):
        xs = np.zeros(n_steps)
        for i in range(n_steps):
            xs[i] = self.step()
        return xs


class PhotonicDriftSimulator:
    """
    Time-varying V_eff(t) for a room-temperature CV photonic system.

    Three drift sources:
      1. OPA squeezing: crystal temperature -> V_sqz drift (tau ~ 600s)
      2. Channel loss: fiber thermal expansion -> eta drift (tau ~ 1800s)
      3. Phase noise: PLL bandwidth fluctuation -> V_nl drift (tau ~ 60s)

    Parameters calibrated from Taros design docs.
    """

    # Drift parameters (calibrated from design docs)
    SCENARIOS = {
        'slow_thermal': {
            'description': 'Slow thermal drift (lab temperature 0.1K fluctuation)',
            # OPA crystal temp: 0.1K -> 0.05dB squeezing change
            'sqz_sigma_ou': 0.003,   # dB volatility
            'sqz_theta': 1/600,      # tau = 10 min
            # Fiber loss: 0.1K -> 0.002dB loss change
            'loss_sigma_ou': 0.001,  # dB volatility
            'loss_theta': 1/1800,    # tau = 30 min
            # Phase noise: PLL bandwidth drift
            'vnl_sigma_ou': 0.0005,  # SNU volatility
            'vnl_theta': 1/300,      # tau = 5 min
        },
        'fast_pll': {
            'description': 'Fast PLL fluctuation (vibration/acoustic coupling)',
            'sqz_sigma_ou': 0.001,
            'sqz_theta': 1/600,
            'loss_sigma_ou': 0.0005,
            'loss_theta': 1/1800,
            'vnl_sigma_ou': 0.002,   # Larger phase noise volatility
            'vnl_theta': 1/60,       # tau = 1 min (fast)
        },
        'sudden_event': {
            'description': 'Sudden event (PLL cycle slip / OPA mode hop)',
            'sqz_sigma_ou': 0.001,
            'sqz_theta': 1/600,
            'loss_sigma_ou': 0.0005,
            'loss_theta': 1/1800,
            'vnl_sigma_ou': 0.0005,
            'vnl_theta': 1/300,
            # Sudden event injected separately
            'event_time_frac': 0.4,   # At 40% of simulation
            'event_type': 'pll_slip',
            'event_magnitude': 0.05,  # +0.05 SNU to V_nl (large spike)
            'event_recovery_tau': 30, # 30s recovery
        },
    }

    def __init__(self, scenario, sigma_gen=13.0, L_dB_base=0.27,
                 V_nl_base=0.010, dt=0.01, rng=None):
        """
        Args:
            scenario: one of 'slow_thermal', 'fast_pll', 'sudden_event'
            sigma_gen: base OPA squeezing (dB)
            L_dB_base: base channel loss (dB)
            V_nl_base: base non-loss noise (SNU)
            dt: time step in seconds
        """
        self.scenario_name = scenario
        self.params = self.SCENARIOS[scenario]
        self.sigma_gen_base = sigma_gen
        self.L_dB_base = L_dB_base
        self.V_nl_base = V_nl_base
        self.dt = dt
        self.rng = rng or np.random.default_rng(42)

        # Initialize OU processes (perturbations around base values)
        p = self.params
        self.sqz_drift = OUDriftModel(
            mu=0.0, theta=p['sqz_theta'], sigma_ou=p['sqz_sigma_ou'],
            dt=dt, rng=self.rng
        )
        self.loss_drift = OUDriftModel(
            mu=0.0, theta=p['loss_theta'], sigma_ou=p['loss_sigma_ou'],
            dt=dt, rng=self.rng
        )
        self.vnl_drift = OUDriftModel(
            mu=0.0, theta=p['vnl_theta'], sigma_ou=p['vnl_sigma_ou'],
            dt=dt, rng=self.rng
        )

    def generate_trajectory(self, duration_s):
        """Generate V_eff(t) trajectory.

        Args:
            duration_s: total simulation time in seconds

        Returns:
            dict with time, V_eff, sigma_eff, p_phys arrays
        """
        n_steps = int(duration_s / self.dt)
        t = np.arange(n_steps) * self.dt

        sigma_gen = np.full(n_steps, self.sigma_gen_base)
        L_dB = np.full(n_steps, self.L_dB_base)
        V_nl = np.full(n_steps, self.V_nl_base)

        # Apply OU drift
        for i in range(n_steps):
            sigma_gen[i] += self.sqz_drift.step()
            L_dB[i] += self.loss_drift.step()
            V_nl[i] += self.vnl_drift.step()

        # Clamp to physical bounds
        sigma_gen = np.clip(sigma_gen, 8.0, 15.0)
        L_dB = np.clip(L_dB, 0.05, 2.0)
        V_nl = np.clip(V_nl, 0.001, 0.1)

        # Inject sudden event if applicable
        if 'event_time_frac' in self.params:
            t_event = int(self.params['event_time_frac'] * n_steps)
            tau_rec = self.params['event_recovery_tau'] / self.dt
            mag = self.params['event_magnitude']
            for i in range(t_event, n_steps):
                decay = mag * np.exp(-(i - t_event) / tau_rec)
                V_nl[i] += decay

        # Compute V_eff trajectory
        V_sqz = 10.0 ** (-sigma_gen / 10.0)
        eta = 10.0 ** (-L_dB / 10.0)
        V_eff = eta * V_sqz + (1.0 - eta) + V_nl
        sigma_eff = -10.0 * np.log10(V_eff)
        p_phys = 0.5 * erfc(SQRT_PI / (4.0 * np.sqrt(V_eff / 2.0)))

        return {
            'time': t,
            'sigma_gen': sigma_gen,
            'L_dB': L_dB,
            'V_nl': V_nl,
            'V_eff': V_eff,
            'sigma_eff': sigma_eff,
            'p_phys': p_phys,
        }


# ============================================================
# QEC simulation (from Paper 1, simplified for batch efficiency)
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


def run_qec_window(d, V_eff, n_shots, rng, edges, n_det, use_soft_info=True):
    """Run QEC for a batch of shots at given V_eff. Returns p_L estimate."""
    n_edges = len(edges)
    sigma = np.sqrt(V_eff)
    delta = sigma * rng.standard_normal((n_shots, n_edges))
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

    # Decode
    n_logical_errors = 0
    if use_soft_info:
        r_abs = np.abs(residual)
        log_lr = ((SQRT_PI - r_abs) ** 2 - r_abs ** 2) / (2.0 * V_eff)
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
        p_phys = compute_p_phys(V_eff)
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

    # Also return residual variance for estimator experiments
    residual_var = np.var(residual)
    return n_logical_errors / n_shots, residual_var


# ============================================================
# Exp-B1: Fault-Tolerance Lifetime Under Drift
# ============================================================
def run_exp_b1(rng):
    """
    Simulate QEC performance over time under drifting noise.

    For each scenario:
      1. Generate V_eff(t) trajectory (300s duration)
      2. Every QEC_WINDOW seconds, run n_shots of QEC
      3. Record p_L(t) trajectory
      4. Find fault-tolerance lifetime (first crossing of p_L > 10^-3)
    """
    print("=" * 70)
    print("  Exp-B1: Fault-Tolerance Lifetime Under Drift")
    print("=" * 70)

    d = 5  # Code distance (reasonable for computational cost)
    n_shots_per_window = 2000  # Shots per time window
    qec_window_s = 1.0  # 1 second per measurement window
    duration_s = 300.0  # 5 minutes total
    dt = 0.01  # 10ms time resolution for drift

    # Pre-extract graph (reuse across time steps)
    edges, n_det = extract_matching_graph(d, rounds=d)
    print(f"  Code: d={d}, {len(edges)} edges, {n_det} detectors")

    n_windows = int(duration_s / qec_window_s)
    n_drift_steps_per_window = int(qec_window_s / dt)

    results = {}

    for scenario_name in ['slow_thermal', 'fast_pll', 'sudden_event']:
        print(f"\n--- Scenario: {scenario_name} ---")
        desc = PhotonicDriftSimulator.SCENARIOS[scenario_name]['description']
        print(f"  {desc}")

        # Generate full drift trajectory
        sim = PhotonicDriftSimulator(
            scenario_name, sigma_gen=13.0, L_dB_base=0.27,
            V_nl_base=0.010, dt=dt, rng=np.random.default_rng(42)
        )
        traj = sim.generate_trajectory(duration_s)

        # Subsample to window resolution
        window_times = np.arange(n_windows) * qec_window_s
        window_V_eff = np.zeros(n_windows)
        window_sigma_eff = np.zeros(n_windows)
        window_p_phys = np.zeros(n_windows)
        window_p_L_static = np.zeros(n_windows)
        window_p_L_soft = np.zeros(n_windows)
        window_residual_var = np.zeros(n_windows)

        # Static decoder: uses V_eff at t=0
        V_eff_0 = traj['V_eff'][0]

        t0 = time.time()
        ft_lifetime_static = None
        ft_lifetime_soft = None

        for w in range(n_windows):
            # Use V_eff at the midpoint of this window
            idx_mid = min(int((w + 0.5) * n_drift_steps_per_window),
                          len(traj['V_eff']) - 1)
            V_eff_now = traj['V_eff'][idx_mid]
            window_V_eff[w] = V_eff_now
            window_sigma_eff[w] = traj['sigma_eff'][idx_mid]
            window_p_phys[w] = traj['p_phys'][idx_mid]

            # QEC with soft-info (adaptive: uses true V_eff for LLR)
            p_L_soft, res_var = run_qec_window(
                d, V_eff_now, n_shots_per_window, rng, edges, n_det,
                use_soft_info=True
            )
            window_p_L_soft[w] = p_L_soft
            window_residual_var[w] = res_var

            # Check fault-tolerance lifetime
            if ft_lifetime_soft is None and p_L_soft > 1e-3:
                ft_lifetime_soft = window_times[w]

            if w % 50 == 0 or w == n_windows - 1:
                elapsed = time.time() - t0
                print(f"  t={window_times[w]:.0f}s: σ_eff={window_sigma_eff[w]:.2f}dB, "
                      f"p_phys={window_p_phys[w]:.4e}, "
                      f"p_L(soft)={p_L_soft:.4e}  "
                      f"[{elapsed:.1f}s elapsed]")

        # Summary
        ft_soft_str = f"{ft_lifetime_soft:.0f}s" if ft_lifetime_soft else ">300s"
        print(f"\n  FT lifetime (soft-info): {ft_soft_str}")
        print(f"  σ_eff range: {window_sigma_eff.min():.2f} - {window_sigma_eff.max():.2f} dB")
        print(f"  V_eff range: {window_V_eff.min():.4f} - {window_V_eff.max():.4f} SNU")

        results[scenario_name] = {
            'description': desc,
            'time': window_times.tolist(),
            'V_eff': window_V_eff.tolist(),
            'sigma_eff': window_sigma_eff.tolist(),
            'p_phys': window_p_phys.tolist(),
            'p_L_soft': window_p_L_soft.tolist(),
            'residual_var': window_residual_var.tolist(),
            'ft_lifetime_soft': ft_lifetime_soft,
            'd': d,
            'n_shots_per_window': n_shots_per_window,
            'qec_window_s': qec_window_s,
            'V_eff_initial': float(V_eff_0),
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
        print("  matplotlib not available — skipping plots")
        return

    plt.rcParams.update({
        'font.size': 11, 'axes.grid': True, 'grid.alpha': 0.3,
        'figure.dpi': 150,
    })

    fig, axes = plt.subplots(3, 3, figsize=(18, 14))
    fig.suptitle('Exp-B1: Fault-Tolerance Lifetime Under Drift\n'
                 'Photonic Quantum Digital Twin — Room Temperature CV-QEC',
                 fontsize=14, fontweight='bold')

    scenarios = ['slow_thermal', 'fast_pll', 'sudden_event']
    titles = ['Slow Thermal Drift', 'Fast PLL Fluctuation', 'Sudden Event (PLL Slip)']
    colors = ['#e74c3c', '#3498db', '#f39c12']

    for col, (scenario, title, color) in enumerate(zip(scenarios, titles, colors)):
        data = results[scenario]
        t = np.array(data['time'])

        # Row 1: sigma_eff(t)
        ax = axes[0, col]
        ax.plot(t, data['sigma_eff'], color=color, lw=1.5)
        ax.axhline(9.3, color='gray', ls=':', alpha=0.5)
        ax.set_ylabel('$\\sigma_{eff}$ (dB)')
        ax.set_title(title)
        ax.text(0.02, 0.05, f'Initial: {data["sigma_eff"][0]:.2f} dB',
                transform=ax.transAxes, fontsize=8, color='gray')

        # Row 2: p_phys(t)
        ax = axes[1, col]
        ax.semilogy(t, data['p_phys'], color=color, lw=1.5)
        ax.set_ylabel('$p_{phys}$')

        # Row 3: p_L(t)
        ax = axes[2, col]
        p_L_soft = np.array(data['p_L_soft'])
        p_L_soft_plot = np.where(p_L_soft > 0, p_L_soft, 1e-5)
        ax.semilogy(t, p_L_soft_plot, color=color, lw=1.5, label='Soft-info MWPM')
        ax.axhline(1e-3, color='red', ls='--', alpha=0.6, label='$p_L = 10^{-3}$')
        ax.set_ylabel('$p_L$')
        ax.set_xlabel('Time (s)')
        ax.legend(fontsize=8)

        if data['ft_lifetime_soft'] is not None:
            ax.axvline(data['ft_lifetime_soft'], color='red', ls=':', alpha=0.3)
            ax.text(data['ft_lifetime_soft'], 1e-2,
                    f'FT fail: {data["ft_lifetime_soft"]:.0f}s',
                    fontsize=8, color='red', ha='left')

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_b1_drift_lifetime.png')
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
    print("  Exp-B1: Fault-Tolerance Lifetime Under Drift")
    print(f"  Stim {stim.__version__}, PyMatching {pymatching.__version__}")
    print()

    t_start = time.time()
    results = run_exp_b1(rng)

    # Save
    json_path = os.path.join(OUT_DIR, 'exp_b1_results.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved: {json_path}")

    # Plot
    plot_results(results)

    elapsed = time.time() - t_start
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY: Fault-Tolerance Lifetime Under Drift")
    print("=" * 70)
    for name, data in results.items():
        ft = data['ft_lifetime_soft']
        ft_str = f"{ft:.0f}s" if ft else ">300s (stable)"
        sig_range = f"{min(data['sigma_eff']):.2f}-{max(data['sigma_eff']):.2f}"
        print(f"  {name:20s}: FT lifetime = {ft_str}, "
              f"σ_eff = {sig_range} dB")


if __name__ == '__main__':
    main()
