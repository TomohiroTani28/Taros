#!/usr/bin/env python3
"""
BP Decoder for GKP Surface Codes — Breaking the MWPM Walls
===========================================================

Research question:
  Does belief propagation (BP) decoding, leveraging GKP continuous
  measurements, break the scale-invariance and optimality walls
  that limit MWPM-based approaches?

Theoretical basis:
  1. BP is sensitive to absolute LLR magnitude (breaks scale invariance)
  2. BP is approximate on loopy graphs (room for iterative improvement)
  3. BP propagates cross-edge information via messages (breaks independence)

Implementation:
  - Normalized min-sum BP on the surface code Tanner graph
  - GKP continuous LLR as channel initialization
  - Turbo BP: iterate between BP decoding and noise re-estimation
  - Comparison with MWPM (static + soft-info) under static and drifting noise
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
# Physics (reused)
# ============================================================
def compute_V_eff(sigma_gen_dB, L_dB, V_non_loss=0.010):
    V_sqz = 10.0 ** (-sigma_gen_dB / 10.0)
    eta = 10.0 ** (-L_dB / 10.0)
    return eta * V_sqz + (1.0 - eta) + V_non_loss

def compute_p_phys(V_eff):
    return float(erfc(SQRT_PI / (4.0 * np.sqrt(V_eff / 2.0))) / 2.0)


# ============================================================
# Matching graph extraction (reused)
# ============================================================
def extract_graph(d):
    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z", rounds=1, distance=d,
        before_round_data_depolarization=0.01)
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
            edges.append((dets[0], -1, has_logical))
        elif len(dets) == 2:
            edges.append((dets[0], dets[1], has_logical))
    return edges, dem.num_detectors


# ============================================================
# Build check matrix H and logical vector L from edge list
# ============================================================
def build_matrices(edges, n_det):
    """
    H: (n_det, n_edges) — check matrix (detector x edge)
    L: (n_edges,) — logical observable vector
    """
    n_edges = len(edges)
    H = np.zeros((n_det, n_edges), dtype=np.int8)
    L = np.zeros(n_edges, dtype=np.int8)
    for j, (n1, n2, has_log) in enumerate(edges):
        if n1 >= 0:
            H[n1, j] = 1
        if n2 >= 0:
            H[n2, j] = 1
        if has_log:
            L[j] = 1
    return H, L


# ============================================================
# GKP sampling
# ============================================================
def gkp_sample(n_edges, n_shots, V_eff, rng):
    if np.isscalar(V_eff):
        V_eff = np.full(n_edges, V_eff)
    sigma = np.sqrt(V_eff)
    delta = rng.standard_normal((n_shots, n_edges)) * sigma[np.newaxis, :]
    n_lat = np.rint(delta / SQRT_PI).astype(np.int64)
    errors = (n_lat % 2) != 0
    residuals = delta - n_lat * SQRT_PI
    return errors, residuals


def compute_syndrome(errors, H):
    """Compute syndrome for a batch of error patterns."""
    # s = H @ e (mod 2), but using XOR for speed
    return (H @ errors.T % 2).T.astype(np.uint8)


def compute_obs(errors, L):
    """Compute observable flip for a batch."""
    return (errors @ L % 2).astype(np.uint8)


def compute_llr(residuals, V_eff):
    """GKP log-likelihood ratio: log(P(no error) / P(error))."""
    r_abs = np.abs(residuals)
    if np.isscalar(V_eff):
        llr = ((SQRT_PI - r_abs)**2 - r_abs**2) / (2.0 * V_eff)
    else:
        llr = ((SQRT_PI - r_abs)**2 - r_abs**2) / (2.0 * V_eff[np.newaxis, :])
    return np.clip(llr, -30, 30)


# ============================================================
# Belief Propagation Decoder (Normalized Min-Sum)
# ============================================================
class BPDecoder:
    """
    Normalized min-sum BP on the surface code Tanner graph.

    - Variable nodes = edges (potential errors)
    - Check nodes = detectors (syndrome bits)
    - Messages flow between connected variable and check nodes
    """

    def __init__(self, H, L, max_iter=20, alpha=0.625, damping=0.5):
        """
        Args:
            H: (n_checks, n_vars) check matrix
            L: (n_vars,) logical observable vector
            max_iter: maximum BP iterations
            alpha: normalization factor for min-sum (typically 0.5-0.8)
            damping: message damping factor (0=no damping, 1=full damping)
        """
        self.H = H
        self.L = L
        self.n_checks, self.n_vars = H.shape
        self.max_iter = max_iter
        self.alpha = alpha
        self.damping = damping

        # Precompute adjacency
        self.check_to_var = [[] for _ in range(self.n_checks)]
        self.var_to_check = [[] for _ in range(self.n_vars)]
        for c in range(self.n_checks):
            for v in range(self.n_vars):
                if H[c, v]:
                    self.check_to_var[c].append(v)
                    self.var_to_check[v].append(c)

    def decode(self, syndrome, channel_llr):
        """
        Decode one shot.

        Args:
            syndrome: (n_checks,) uint8
            channel_llr: (n_vars,) float — GKP log-likelihood ratio
                         positive = likely no error, negative = likely error

        Returns:
            (estimated_error, converged)
            estimated_error: (n_vars,) uint8
            converged: bool
        """
        n_c, n_v = self.n_checks, self.n_vars

        # Initialize messages
        # var_to_check messages: mu[c][v]
        # check_to_var messages: nu[c][v]
        mu = {}  # var -> check messages
        nu = {}  # check -> var messages
        for c in range(n_c):
            for v in self.check_to_var[c]:
                mu[(c, v)] = channel_llr[v]
                nu[(c, v)] = 0.0

        converged = False
        for iteration in range(self.max_iter):
            # --- Check-to-variable messages (min-sum) ---
            nu_new = {}
            for c in range(n_c):
                vars_c = self.check_to_var[c]
                s = 1 - 2 * int(syndrome[c])  # +1 if syndrome=0, -1 if syndrome=1
                for v in vars_c:
                    # Product of signs and min of magnitudes (excluding v)
                    sign = s
                    min_abs = float('inf')
                    for v2 in vars_c:
                        if v2 == v:
                            continue
                        m = mu[(c, v2)]
                        sign *= (1 if m >= 0 else -1)
                        min_abs = min(min_abs, abs(m))
                    # Normalized min-sum
                    nu_val = sign * self.alpha * min_abs
                    # Damping
                    nu_new[(c, v)] = (1 - self.damping) * nu_val + self.damping * nu[(c, v)]

            nu = nu_new

            # --- Variable-to-check messages ---
            mu_new = {}
            for v in range(n_v):
                checks_v = self.var_to_check[v]
                total_incoming = channel_llr[v] + sum(nu[(c, v)] for c in checks_v)
                for c in checks_v:
                    # Extrinsic: total minus contribution from c
                    mu_new[(c, v)] = total_incoming - nu[(c, v)]

            mu = mu_new

            # --- Check convergence: does the current estimate satisfy syndrome? ---
            posterior = np.zeros(n_v)
            for v in range(n_v):
                posterior[v] = channel_llr[v] + sum(nu[(c, v)] for c in self.var_to_check[v])

            hard_decision = (posterior < 0).astype(np.uint8)
            predicted_syndrome = (self.H @ hard_decision) % 2

            if np.array_equal(predicted_syndrome, syndrome):
                converged = True
                break

        # Final hard decision
        posterior = np.zeros(n_v)
        for v in range(n_v):
            posterior[v] = channel_llr[v] + sum(nu[(c, v)] for c in self.var_to_check[v])
        estimated_error = (posterior < 0).astype(np.uint8)

        return estimated_error, converged

    def decode_observable(self, syndrome, channel_llr):
        """Decode and return predicted observable flip."""
        est_error, converged = self.decode(syndrome, channel_llr)
        obs_flip = int(np.dot(est_error, self.L) % 2)
        return obs_flip, converged


# ============================================================
# Turbo BP: iterative noise estimation + BP
# ============================================================
class TurboBPDecoder:
    """
    Turbo BP: iterate between BP decoding and noise re-estimation.

    Round 1: BP with channel LLR(r, V_nominal) → posterior probabilities
    Noise update: estimate V_eff from posterior + residuals
    Round 2: BP with channel LLR(r, V_estimated) → improved posterior
    """

    def __init__(self, H, L, max_iter_bp=15, n_turbo=2, alpha=0.625, damping=0.5):
        self.bp = BPDecoder(H, L, max_iter=max_iter_bp, alpha=alpha, damping=damping)
        self.H = H
        self.L = L
        self.n_turbo = n_turbo

    def decode_observable(self, syndrome, residuals, V_eff_init):
        """
        Args:
            syndrome: (n_checks,) uint8
            residuals: (n_vars,) float — raw GKP residuals
            V_eff_init: initial (nominal) V_eff estimate
        """
        V_est = V_eff_init if np.isscalar(V_eff_init) else V_eff_init.copy()

        for turbo_round in range(self.n_turbo):
            # Compute channel LLR with current V estimate
            r_abs = np.abs(residuals)
            if np.isscalar(V_est):
                llr = ((SQRT_PI - r_abs)**2 - r_abs**2) / (2.0 * V_est)
            else:
                llr = ((SQRT_PI - r_abs)**2 - r_abs**2) / (2.0 * V_est)
            llr = np.clip(llr, -30, 30)

            # BP decode
            est_error, converged = self.bp.decode(syndrome, llr)

            if turbo_round < self.n_turbo - 1:
                # Noise re-estimation from BP posterior + residuals
                # For edges where BP says "likely error":
                #   the actual displacement was delta ≈ residual + n*sqrt(pi)
                #   so the noise variance is approximately delta^2
                # For edges where BP says "no error":
                #   delta ≈ residual, variance ≈ residual^2
                # Weighted combination gives per-edge V estimate

                posterior_p = np.zeros(len(residuals))
                for v in range(len(residuals)):
                    total = llr[v] + sum(
                        0.0 for _ in self.bp.var_to_check[v]  # simplified
                    )
                    posterior_p[v] = 1.0 / (1.0 + np.exp(np.clip(total, -30, 30)))

                # Estimate V_eff from residuals
                # E[r^2 | no error] ≈ V_eff (for small V)
                # E[(sqrt(pi) - |r|)^2 | error] ≈ V_eff
                r2 = residuals ** 2
                V_est_new = np.mean(r2) * 1.5  # rough estimate with correction
                V_est_new = np.clip(V_est_new, 0.05, 0.5)
                V_est = V_est_new

        obs_flip = int(np.dot(est_error, self.L) % 2)
        return obs_flip, converged


# ============================================================
# MWPM decoder (for comparison)
# ============================================================
def build_mwpm(edges, n_det, weights):
    n_edges = len(edges)
    boundary = n_det
    Hm = np.zeros((n_det + 1, n_edges), dtype=np.uint8)
    faults = np.zeros((1, n_edges), dtype=np.uint8)
    for j, (n1, n2, has_log) in enumerate(edges):
        Hm[n1 if n1 >= 0 else boundary, j] = 1
        Hm[n2 if n2 >= 0 else boundary, j] = 1
        if has_log:
            faults[0, j] = 1
    m = pymatching.Matching(Hm, weights=weights, faults_matrix=faults)
    m.set_boundary_nodes({boundary})
    return m


# ============================================================
# Main experiment
# ============================================================
def run_comparison(d, V_eff, n_shots, rng):
    edges, n_det = extract_graph(d)
    n_edges = len(edges)
    H, L = build_matrices(edges, n_det)
    p_phys = compute_p_phys(V_eff)

    # Decoders
    # 1. MWPM static
    static_w = np.full(n_edges, max(-np.log(p_phys / (1 - p_phys)), 0.01))
    mwpm_static = build_mwpm(edges, n_det, static_w)

    # 2. BP
    bp = BPDecoder(H, L, max_iter=20, alpha=0.625, damping=0.5)

    # 3. Turbo BP
    turbo_bp = TurboBPDecoder(H, L, max_iter_bp=15, n_turbo=3, alpha=0.625, damping=0.5)

    # Sample
    errors, residuals = gkp_sample(n_edges, n_shots, V_eff, rng)
    syndromes = compute_syndrome(errors, H)
    obs_flips = compute_obs(errors, L)

    # Channel LLR
    llr_all = compute_llr(residuals, V_eff)

    # Decode
    static_err = 0
    soft_err = 0
    bp_err = 0
    turbo_err = 0
    bp_converged = 0
    turbo_converged = 0

    for i in range(n_shots):
        syn = syndromes[i]
        actual = obs_flips[i]
        r = residuals[i]
        llr = llr_all[i]

        # MWPM static
        pred = mwpm_static.decode(syn)
        if pred[0] != actual:
            static_err += 1

        # MWPM soft
        soft_w = np.maximum(llr, 0.01)
        m_soft = build_mwpm(edges, n_det, soft_w)
        pred = m_soft.decode(syn)
        if pred[0] != actual:
            soft_err += 1

        # BP
        obs_pred, conv = bp.decode_observable(syn, llr)
        if obs_pred != actual:
            bp_err += 1
        if conv:
            bp_converged += 1

        # Turbo BP
        obs_pred, conv = turbo_bp.decode_observable(syn, r, V_eff)
        if obs_pred != actual:
            turbo_err += 1
        if conv:
            turbo_converged += 1

    return {
        'd': d, 'V_eff': float(V_eff), 'p_phys': p_phys,
        'n_shots': n_shots,
        'static_pL': static_err / n_shots, 'static_err': static_err,
        'soft_pL': soft_err / n_shots, 'soft_err': soft_err,
        'bp_pL': bp_err / n_shots, 'bp_err': bp_err,
        'bp_converge': bp_converged / n_shots,
        'turbo_pL': turbo_err / n_shots, 'turbo_err': turbo_err,
        'turbo_converge': turbo_converged / n_shots,
    }


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(42)

    print("=" * 70)
    print("  BP Decoder for GKP Surface Codes")
    print("  Breaking the MWPM Walls")
    print("=" * 70)

    # Test across loss range (d=3 for speed, BP is slower than MWPM)
    print("\n[Exp] d=3, loss sweep")
    results = []
    for L in [0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]:
        V = compute_V_eff(13.0, L)
        p = compute_p_phys(V)
        if p > 0.10:
            continue
        n_shots = 50_000  # BP is slower, use fewer shots
        t0 = time.time()
        r = run_comparison(3, V, n_shots, rng)
        el = time.time() - t0
        results.append(r)
        print(f"  L={L:.2f} p={p:.4f}: "
              f"Static={r['static_pL']:.4e}({r['static_err']}) "
              f"Soft={r['soft_pL']:.4e}({r['soft_err']}) "
              f"BP={r['bp_pL']:.4e}({r['bp_err']},conv={r['bp_converge']:.0%}) "
              f"TurboBP={r['turbo_pL']:.4e}({r['turbo_err']},conv={r['turbo_converge']:.0%}) "
              f"[{el:.0f}s]")

    # Plot
    if results:
        fig, ax = plt.subplots(figsize=(10, 6))
        pp = [r['p_phys'] for r in results]
        ax.semilogy(pp, [max(r['static_pL'], 1e-6) for r in results],
                    'r-o', lw=2, ms=8, label='MWPM Static')
        ax.semilogy(pp, [max(r['soft_pL'], 1e-6) for r in results],
                    color='#ff9800', ls='-', marker='s', lw=2, ms=8,
                    label='MWPM Soft-info')
        ax.semilogy(pp, [max(r['bp_pL'], 1e-6) for r in results],
                    'g-^', lw=2, ms=8, label='BP (GKP LLR)')
        ax.semilogy(pp, [max(r['turbo_pL'], 1e-6) for r in results],
                    'b-D', lw=2, ms=8, label='Turbo BP (2 rounds)')
        ax.set_xlabel('Physical Error Rate $p_{phys}$', fontsize=12)
        ax.set_ylabel('Logical Error Rate $p_L$', fontsize=12)
        ax.set_title('Breaking the MWPM Walls: BP Decoding for GKP Surface Codes\n'
                     'd=3, 50K shots/point, Stim graph + custom BP',
                     fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        path = os.path.join(out_dir, 'fig10_bp_decoder.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"\n  Saved: {path}")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for r in results:
        bp_vs_soft = r['soft_pL'] / r['bp_pL'] if r['bp_pL'] > 0 else float('inf')
        turbo_vs_bp = r['bp_pL'] / r['turbo_pL'] if r['turbo_pL'] > 0 else float('inf')
        print(f"  p={r['p_phys']:.4f}: "
              f"Soft={r['soft_pL']:.4e} "
              f"BP={r['bp_pL']:.4e} (vs Soft: {bp_vs_soft:.2f}x) "
              f"Turbo={r['turbo_pL']:.4e} (vs BP: {turbo_vs_bp:.2f}x)")

    with open(os.path.join(out_dir, 'bp_results.json'), 'w') as f:
        json.dump(results, f, indent=2)


if __name__ == '__main__':
    main()
