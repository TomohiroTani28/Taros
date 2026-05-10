#!/usr/bin/env python3
"""
Adaptive PLOA — Multi-Round Surface Code with Drift Tracking
=============================================================

NOVEL CONTRIBUTION:
  Syndrome-based real-time noise estimation + recalibrated soft-info
  decoding for photonic GKP surface codes under environmental drift.

KEY DESIGN (fair comparison):
  - Physical noise: sampled with TRUE V_eff(t) (reality, unknown to decoder)
  - Static decoder: uses NOMINAL V_eff (fixed, never updated)
  - Soft-only decoder: uses GKP residuals with NOMINAL V_eff (miscalibrated during drift)
  - Adaptive PLOA: uses GKP residuals with ESTIMATED V_eff (recalibrated via syndrome stats)

  The adaptive advantage comes from using syndrome statistics to
  ESTIMATE the current V_eff, then RECALIBRATING the soft-info weights.
"""

import numpy as np
from scipy.special import erfc
import stim
import pymatching
import matplotlib.pyplot as plt
import json
import os
import time

SQRT_PI = np.sqrt(np.pi)


# ============================================================
# Physics
# ============================================================
def compute_V_eff(sigma_gen_dB, L_dB, V_non_loss=0.010):
    V_sqz = 10.0 ** (-sigma_gen_dB / 10.0)
    eta = 10.0 ** (-L_dB / 10.0)
    return eta * V_sqz + (1.0 - eta) + V_non_loss


def compute_p_phys(V_eff):
    return float(erfc(SQRT_PI / (4.0 * np.sqrt(V_eff / 2.0))) / 2.0)


# ============================================================
# Matching Graph from Stim
# ============================================================
def extract_matching_graph(d):
    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z", rounds=1, distance=d,
        before_round_data_depolarization=0.01,
    )
    dem = circuit.detector_error_model(decompose_errors=True)
    edges = []
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        dets, has_logical = [], False
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


def build_check_matrix(edges, n_det):
    H = np.zeros((n_det, len(edges)), dtype=np.float64)
    for j, e in enumerate(edges):
        H[e['node1'], j] = 1.0
        if e['node2'] is not None:
            H[e['node2'], j] = 1.0
    return H


def build_matching(edges, n_det, weights):
    n_edges = len(edges)
    boundary = n_det
    H = np.zeros((n_det + 1, n_edges), dtype=np.uint8)
    faults = np.zeros((1, n_edges), dtype=np.uint8)
    for j, e in enumerate(edges):
        H[e['node1'], j] = 1
        H[e['node2'] if e['node2'] is not None else boundary, j] = 1
        if e['has_logical']:
            faults[0, j] = 1
    m = pymatching.Matching(H, weights=weights, faults_matrix=faults)
    m.set_boundary_nodes({boundary})
    return m


# ============================================================
# GKP Noise — Separated Physical Sampling & Decoder Belief
# ============================================================
def gkp_sample_physical(n_edges, n_shots, V_eff_true, rng):
    """
    Sample GKP displacement noise with TRUE V_eff (physical reality).
    Returns: errors (bool), raw_residuals (float)
    """
    sigma = np.sqrt(V_eff_true)  # (n_edges,)
    delta = rng.standard_normal((n_shots, n_edges)) * sigma[np.newaxis, :]
    n_lattice = np.rint(delta / SQRT_PI).astype(np.int64)
    errors = (n_lattice % 2) != 0
    residuals = delta - n_lattice * SQRT_PI  # raw residuals
    return errors, residuals


def compute_log_lr(residuals, V_eff_believed):
    """
    Compute log-likelihood ratio using the DECODER'S BELIEVED V_eff.

    If V_eff_believed != V_eff_true, the weights are miscalibrated.
    This is the key: the adaptive decoder corrects this miscalibration.
    """
    r_abs = np.abs(residuals)
    log_lr = ((SQRT_PI - r_abs) ** 2 - r_abs ** 2) / (2.0 * V_eff_believed)
    return np.clip(log_lr, -30, 30)


def compute_syndromes_batch(errors, edges, n_det):
    n_shots, n_edges = errors.shape
    syndromes = np.zeros((n_shots, n_det), dtype=np.uint8)
    obs_flips = np.zeros(n_shots, dtype=np.uint8)
    for j, e in enumerate(edges):
        mask = errors[:, j]
        syndromes[mask, e['node1']] ^= 1
        if e['node2'] is not None:
            syndromes[mask, e['node2']] ^= 1
        if e['has_logical']:
            obs_flips[mask] ^= 1
    return syndromes, obs_flips


# ============================================================
# Drift Model
# ============================================================
class DriftModel:
    def __init__(self, n_edges, n_wdm=7, V_eff_base=0.1174,
                 ch_affected=3, delta_L_dB=0.30,
                 T_spike=80, T_end=160, R=240):
        self.n_edges = n_edges
        self.n_wdm = n_wdm
        self.V_eff_base = V_eff_base
        self.ch_affected = ch_affected
        self.T_spike = T_spike
        self.T_end = T_end
        self.R = R
        sigma_gen = 13.0
        V_sqz = 10 ** (-sigma_gen / 10)
        # Infer L_base from V_eff_base, then add delta
        # V_base = eta*V_sqz + (1-eta) + 0.01 → solve for eta
        eta_base = (V_eff_base - 1.0 - 0.01) / (V_sqz - 1.0)
        L_base_inferred = -10 * np.log10(max(eta_base, 0.01))
        L_spike = L_base_inferred + delta_L_dB
        eta_spike = 10 ** (-L_spike / 10)
        self.V_eff_spike = eta_spike * V_sqz + (1 - eta_spike) + 0.010
        self.ch_assignment = np.array([i % n_wdm for i in range(n_edges)])

    def get_V_eff(self, t):
        V = np.full(self.n_edges, self.V_eff_base)
        if self.T_spike <= t < self.T_end:
            V[self.ch_assignment == self.ch_affected] = self.V_eff_spike
        return V


# ============================================================
# Adaptive Noise Estimator (NOVEL ALGORITHM)
# ============================================================
class AdaptiveEstimator:
    """
    Estimate per-edge V_eff from syndrome statistics.

    Algorithm:
      1. Track per-detector flip rate over sliding window
      2. Estimate per-edge error probability: p = H^+ @ flip_rates
      3. Invert GKP formula to get V_eff: V_eff = f^{-1}(p)
      4. Use estimated V_eff for recalibrated soft-info computation
    """

    def __init__(self, edges, n_det, V_eff_nominal, window=15, alpha=0.5):
        self.H = build_check_matrix(edges, n_det)
        self.H_pinv = np.linalg.pinv(self.H)
        self.V_eff_nominal = V_eff_nominal
        self.p_nominal = compute_p_phys(V_eff_nominal)
        self.n_edges = len(edges)
        self.window = window
        self.alpha = alpha
        self.history = []

    def update(self, syndromes):
        flip_rate = np.mean(syndromes, axis=0)
        self.history.append(flip_rate)
        if len(self.history) > self.window * 3:
            self.history = self.history[-self.window * 3:]

    def estimate_V_eff(self):
        """Estimate per-edge V_eff from recent syndrome statistics."""
        if len(self.history) < 5:
            return np.full(self.n_edges, self.V_eff_nominal)

        W = min(len(self.history), self.window)
        recent_rates = np.mean(self.history[-W:], axis=0)

        # Estimate per-edge error probability
        p_est = self.H_pinv @ recent_rates
        p_est = np.clip(p_est, 1e-4, 0.20)

        # Blend with prior
        p_blended = self.alpha * p_est + (1 - self.alpha) * self.p_nominal

        # Invert GKP formula: p = erfc(√π / (4√(V/2))) / 2
        # → erfc^{-1}(2p) = √π / (4√(V/2))
        # → V/2 = (√π / (4 × erfc^{-1}(2p)))^2
        # → V = 2 × (√π / (4 × erfc^{-1}(2p)))^2
        from scipy.special import erfcinv
        p_safe = np.clip(p_blended, 1e-6, 0.499)
        inv_erfc = erfcinv(2 * p_safe)
        inv_erfc = np.maximum(inv_erfc, 0.1)  # prevent division by zero
        V_est = 2.0 * (SQRT_PI / (4.0 * inv_erfc)) ** 2
        V_est = np.clip(V_est, 0.05, 0.50)

        return V_est


# ============================================================
# Decode Functions
# ============================================================
def decode_batch(matching, syndromes, obs_flips):
    n_err = 0
    for i in range(len(syndromes)):
        pred = matching.decode(syndromes[i])
        if pred[0] != obs_flips[i]:
            n_err += 1
    return n_err


def decode_batch_soft(edges, n_det, syndromes, obs_flips, log_lr):
    n_err = 0
    for i in range(len(syndromes)):
        w = np.maximum(log_lr[i], 0.01)
        m = build_matching(edges, n_det, w)
        pred = m.decode(syndromes[i])
        if pred[0] != obs_flips[i]:
            n_err += 1
    return n_err


# ============================================================
# Main Experiment
# ============================================================
def run_experiment(d=3, n_shots=5000, seed=42,
                   L_base=0.27, delta_L=0.30,
                   T_spike=80, T_end=160, R=240):
    rng = np.random.default_rng(seed)
    edges, n_det = extract_matching_graph(d)
    n_edges = len(edges)

    V_base = compute_V_eff(13.0, L_base)
    drift = DriftModel(n_edges, n_wdm=7, V_eff_base=V_base,
                       ch_affected=3, delta_L_dB=delta_L,
                       T_spike=T_spike, T_end=T_end, R=R)
    R = drift.R
    V_nominal = drift.V_eff_base
    p_nominal = compute_p_phys(V_nominal)

    print(f"  d={d}, edges={n_edges}, R={R}, shots={n_shots}")
    print(f"  Base: V={V_nominal:.4f}, p={p_nominal:.4e}")
    print(f"  Spike: V={drift.V_eff_spike:.4f}, p={compute_p_phys(drift.V_eff_spike):.4e}")
    print(f"  Spike window: rounds {drift.T_spike}-{drift.T_end}")

    # Static decoder: fixed weights
    static_w = np.full(n_edges, max(-np.log(p_nominal / (1 - p_nominal)), 0.01))
    matching_static = build_matching(edges, n_det, static_w)

    # Adaptive estimator
    estimator = AdaptiveEstimator(edges, n_det, V_nominal, window=15, alpha=0.5)

    results = {'rounds': [], 'V_eff_true': [], 'V_eff_est': [],
               'static_pL': [], 'soft_pL': [], 'adaptive_pL': []}

    t0 = time.time()

    for t in range(R):
        V_true = drift.get_V_eff(t)  # TRUE physics (unknown to decoder)

        # 1. Physical sampling with TRUE V_eff
        errors, residuals = gkp_sample_physical(n_edges, n_shots, V_true, rng)
        syndromes, obs = compute_syndromes_batch(errors, edges, n_det)

        # 2. Static decode (uniform weights, no soft-info)
        n_err_static = decode_batch(matching_static, syndromes, obs)

        # 3. Soft-only decode (uses NOMINAL V_eff for log_lr — miscalibrated during spike)
        log_lr_nominal = compute_log_lr(residuals, V_nominal)
        n_err_soft = decode_batch_soft(edges, n_det, syndromes, obs, log_lr_nominal)

        # 4. Adaptive PLOA (uses ESTIMATED V_eff for log_lr — recalibrated)
        V_est = estimator.estimate_V_eff()  # estimated from syndrome history
        log_lr_adaptive = compute_log_lr(residuals, V_est[np.newaxis, :])
        n_err_adaptive = decode_batch_soft(edges, n_det, syndromes, obs, log_lr_adaptive)

        # Update estimator with this round's syndrome data
        estimator.update(syndromes)

        # Record
        results['rounds'].append(t)
        results['V_eff_true'].append(float(np.mean(V_true)))
        results['V_eff_est'].append(float(np.mean(V_est)))
        results['static_pL'].append(n_err_static / n_shots)
        results['soft_pL'].append(n_err_soft / n_shots)
        results['adaptive_pL'].append(n_err_adaptive / n_shots)

        if (t + 1) % 40 == 0:
            el = time.time() - t0
            print(f"    round {t+1}/{R}  "
                  f"S={results['static_pL'][-1]:.4f}  "
                  f"Soft={results['soft_pL'][-1]:.4f}  "
                  f"PLOA={results['adaptive_pL'][-1]:.4f}  "
                  f"V_est={np.mean(V_est):.4f}  [{el:.0f}s]")

    print(f"  Total: {time.time()-t0:.0f}s")
    return results, drift


# ============================================================
# Visualization
# ============================================================
def plot_results(results, drift, out_dir):
    plt.rcParams.update({'font.size': 11, 'axes.grid': True, 'grid.alpha': 0.3})
    rounds = results['rounds']

    def smooth(arr, w=10):
        return np.convolve(arr, np.ones(w)/w, mode='same')

    fig, axes = plt.subplots(3, 1, figsize=(14, 13), sharex=True)
    fig.suptitle(
        'Adaptive PLOA: Runtime Drift Tracking for GKP Surface Code\n'
        'Novel: Syndrome-based V_eff estimation + recalibrated soft-info decoding',
        fontsize=13, fontweight='bold')

    # Panel 1: Noise state tracking
    ax = axes[0]
    ax.plot(rounds, results['V_eff_true'], 'k-', lw=2, label='True $V_{eff}$ (unknown to decoder)')
    ax.plot(rounds, smooth(results['V_eff_est']), 'b-', lw=2, alpha=0.8,
            label='Estimated $V_{eff}$ (adaptive PLOA)')
    ax.axhline(drift.V_eff_base, color='gray', ls=':', alpha=0.5, label='Nominal $V_{eff}$')
    ax.axvspan(drift.T_spike, drift.T_end, color='red', alpha=0.08)
    ax.set_ylabel('$V_{eff}$ [SNU]')
    ax.set_title('Noise Tracking: True vs Estimated')
    ax.legend(loc='upper right')

    # Panel 2: Per-round p_L
    ax = axes[1]
    ax.plot(rounds, smooth(results['static_pL'], 15), 'r-', lw=2, alpha=0.8, label='Static (fixed weights)')
    ax.plot(rounds, smooth(results['soft_pL'], 15), color='#ff9800', lw=2, alpha=0.8,
            label='Soft-info (nominal $V_{eff}$)')
    ax.plot(rounds, smooth(results['adaptive_pL'], 15), 'b-', lw=2, alpha=0.8,
            label='Adaptive PLOA (estimated $V_{eff}$)')
    ax.axvspan(drift.T_spike, drift.T_end, color='red', alpha=0.08)
    ax.set_ylabel('$p_L$ (smoothed)')
    ax.set_title('Per-Round Logical Error Rate')
    ax.legend(loc='upper right')

    # Panel 3: Cumulative
    ax = axes[2]
    ax.plot(rounds, np.cumsum(results['static_pL']), 'r-', lw=2, label='Static')
    ax.plot(rounds, np.cumsum(results['soft_pL']), color='#ff9800', lw=2, label='Soft-info')
    ax.plot(rounds, np.cumsum(results['adaptive_pL']), 'b-', lw=2, label='Adaptive PLOA')
    ax.axvspan(drift.T_spike, drift.T_end, color='red', alpha=0.08)
    ax.set_xlabel('QEC Round')
    ax.set_ylabel('Cumulative $\\Sigma p_L$')
    ax.set_title('Cumulative Logical Errors')
    ax.legend(loc='upper left')

    plt.tight_layout()
    path = os.path.join(out_dir, 'fig7_adaptive_drift.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {path}")

    # Phase comparison bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    phases = [
        ('Before spike\n(0-79)', 0, drift.T_spike),
        ('During spike\n(80-159)', drift.T_spike, drift.T_end),
        ('After recovery\n(160-239)', drift.T_end, drift.R),
    ]
    x = np.arange(len(phases))
    w = 0.25
    for i, (name, t0, t1) in enumerate(phases):
        s = np.mean(results['static_pL'][t0:t1])
        sf = np.mean(results['soft_pL'][t0:t1])
        a = np.mean(results['adaptive_pL'][t0:t1])
        kw = {'label': None}
        if i == 0:
            ax.bar(x[i]-w, s, w, color='#d32f2f', label='Static')
            ax.bar(x[i], sf, w, color='#ff9800', label='Soft-info (nominal)')
            ax.bar(x[i]+w, a, w, color='#1565c0', label='Adaptive PLOA')
        else:
            ax.bar(x[i]-w, s, w, color='#d32f2f')
            ax.bar(x[i], sf, w, color='#ff9800')
            ax.bar(x[i]+w, a, w, color='#1565c0')
    ax.set_xticks(x)
    ax.set_xticklabels([p[0] for p in phases])
    ax.set_ylabel('Average $p_L$')
    ax.set_title('Phase-by-Phase: Static vs Soft-Info vs Adaptive PLOA', fontweight='bold')
    ax.legend()
    plt.tight_layout()
    path = os.path.join(out_dir, 'fig8_phase_comparison.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {path}")


# ============================================================
# Entry Point
# ============================================================
def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(out_dir, exist_ok=True)

    print("=" * 70)
    print("  Adaptive PLOA — Corrected Fair Comparison")
    print("  Key: decoder uses BELIEVED V_eff, not TRUE V_eff")
    print("=" * 70)

    results, drift = run_experiment(d=3, n_shots=8000, seed=42,
                                     L_base=0.60, delta_L=0.80,
                                     T_spike=80, T_end=160, R=240)
    plot_results(results, drift, out_dir)

    with open(os.path.join(out_dir, 'adaptive_results.json'), 'w') as f:
        json.dump(results, f, indent=2)

    T_s, T_e = drift.T_spike, drift.T_end
    print("\n" + "=" * 70)
    print("  RESULTS (fair comparison: decoder uses believed V_eff)")
    print("=" * 70)
    for phase, t0, t1 in [("Pre-spike", 0, T_s), ("DURING SPIKE", T_s, T_e),
                           ("Post-spike", T_e, drift.R), ("OVERALL", 0, drift.R)]:
        s = np.mean(results['static_pL'][t0:t1])
        sf = np.mean(results['soft_pL'][t0:t1])
        a = np.mean(results['adaptive_pL'][t0:t1])
        r_soft = sf/a if a > 0 else 0
        r_static = s/a if a > 0 else 0
        print(f"  {phase:15s}: Static={s:.4e}  Soft={sf:.4e}  PLOA={a:.4e}  "
              f"[PLOA vs Soft: {r_soft:.2f}x, vs Static: {r_static:.1f}x]")


if __name__ == '__main__':
    main()
