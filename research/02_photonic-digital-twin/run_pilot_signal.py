#!/usr/bin/env python3
"""
Paper 2: GKP Lattice as Quantum Pilot Signal
=============================================
The 14-bit advantage via telecom-inspired channel estimation

Core thesis: GKP grid structure is mathematically equivalent to pilot signals
in OFDM telecommunications. This enables 30 years of channel estimation theory
to be directly applied to quantum hardware state tracking.

Experiments:
  B1. Cramér-Rao bound: wrapped-Gaussian MLE vs binary Fisher information
  B2. Channel estimation: MMSE/Wiener vs DV Bayesian, convergence speed
  B3. Adaptive equalization decoder: residual normalization under drift
  B4. BOCPD anomaly detection: changepoint posterior from analog residuals
  B5. Iterative estimation + decoding (turbo principle)

All CPU-only. seed=42.
"""

import numpy as np
from scipy.special import erfc
from scipy.optimize import minimize_scalar
import json, os, time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
SEED = 42


# ═══════════════════════════════════════════════════════════════
#  Physics
# ═══════════════════════════════════════════════════════════════

def gkp_p_err(v_eff):
    sigma = np.sqrt(v_eff / 2)
    return 0.5 * erfc(SQRT_PI / (4 * sigma))


def wrapped_gaussian_loglik(r, v):
    """Log-likelihood of wrapped Gaussian: p(r|V) = sum_n N(r; n√π, V).
    For V < 0.3, 3 terms suffice."""
    ll = 0.0
    for n in [-1, 0, 1]:
        ll += np.exp(-0.5 * (r - n * SQRT_PI) ** 2 / v)
    return np.log(ll + 1e-300) - 0.5 * np.log(2 * np.pi * v)


def wrapped_gaussian_loglik_batch(residuals, v):
    """Vectorized log-likelihood for array of residuals."""
    r = residuals[:, np.newaxis] if residuals.ndim == 1 else residuals
    ns = np.array([-1, 0, 1]) * SQRT_PI
    exps = np.exp(-0.5 * (r - ns) ** 2 / v)
    return np.sum(np.log(np.sum(exps, axis=-1) + 1e-300) - 0.5 * np.log(2 * np.pi * v))


def mle_veff(residuals, v_init=0.14):
    """MLE of V_eff from wrapped Gaussian model."""
    res = minimize_scalar(
        lambda v: -wrapped_gaussian_loglik_batch(residuals, v),
        bounds=(0.01, 0.5), method='bounded')
    return res.x


def generate_gkp(n_modes, v_eff, rng):
    """Generate GKP displacements, residuals, errors."""
    sigma = np.sqrt(v_eff)
    disp = sigma * rng.standard_normal(n_modes)
    nearest = np.rint(disp / SQRT_PI)
    residuals = (disp - nearest * SQRT_PI).astype(np.float32)
    errors = (nearest.astype(np.int64) % 2) != 0
    return residuals, errors


def ou_process(n_steps, dt, tau, sigma, x0, rng):
    x = np.zeros(n_steps)
    x[0] = x0
    c = np.exp(-dt / tau)
    noise_std = sigma * np.sqrt(1 - c ** 2)
    for i in range(1, n_steps):
        x[i] = x[i - 1] * c + noise_std * rng.standard_normal()
    return x


def save_json(name, data):
    path = os.path.join(OUT_DIR, name)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=lambda x: float(x) if isinstance(x, np.floating) else str(x))
    print(f"  [saved {name}]")


# ═══════════════════════════════════════════════════════════════
#  B1: Cramér-Rao Bound — Wrapped Gaussian MLE
# ═══════════════════════════════════════════════════════════════

def fisher_cv_wrapped(v_eff, n_samples=200_000, rng=None):
    """Numerical Fisher information from wrapped Gaussian score function."""
    if rng is None:
        rng = np.random.default_rng(42)
    res, _ = generate_gkp(n_samples, v_eff, rng)
    # Score = d/dV log p(r|V), computed numerically
    dv = v_eff * 1e-5
    ll_plus = np.array([wrapped_gaussian_loglik(r, v_eff + dv) for r in res])
    ll_minus = np.array([wrapped_gaussian_loglik(r, v_eff - dv) for r in res])
    scores = (ll_plus - ll_minus) / (2 * dv)
    return float(np.mean(scores ** 2))


def fisher_dv(v_eff):
    """Fisher information from binary syndrome."""
    p = gkp_p_err(v_eff)
    if p < 1e-15 or p > 1 - 1e-15:
        return 0.0
    dv = v_eff * 1e-6
    dp = (gkp_p_err(v_eff + dv) - gkp_p_err(v_eff - dv)) / (2 * dv)
    return dp ** 2 / (p * (1 - p))


def run_b1():
    print("\n" + "=" * 70)
    print("  B1: Cramér-Rao Bound — Wrapped Gaussian Fisher Information")
    print("=" * 70)

    rng = np.random.default_rng(SEED)
    points = [
        ("Threshold (7.5dB)", 0.178),
        ("Phase 1 (8.5dB)", 0.1417),
        ("Phase 2+ Real (9.3dB)", 0.1175),
        ("Phase 2+ Limit (10.8dB)", 0.0832),
    ]

    results = []
    print(f"\n  {'Name':>25} {'V_eff':>7} {'I_CV':>10} {'I_DV':>10} {'Ratio':>8} {'CRB_CV':>10} {'CRB_DV':>10}")
    print("  " + "-" * 85)

    for name, v in points:
        i_cv = fisher_cv_wrapped(v, n_samples=200_000, rng=rng)
        i_dv = fisher_dv(v)
        ratio = i_cv / i_dv if i_dv > 0 else float('inf')
        # Cramér-Rao bound: Var(V_hat) >= 1/(N*I)
        # For N=686 modes (d=7, 1 cycle):
        N = 686
        crb_cv = 1.0 / (N * i_cv) if i_cv > 0 else float('inf')
        crb_dv = 1.0 / (N * i_dv) if i_dv > 0 else float('inf')
        rel_crb_cv = np.sqrt(crb_cv) / v  # Relative std
        rel_crb_dv = np.sqrt(crb_dv) / v

        print(f"  {name:>25} {v:7.4f} {i_cv:10.2f} {i_dv:10.4f} {ratio:7.0f}x "
              f"{rel_crb_cv:9.2%} {rel_crb_dv:9.2%}")

        results.append({
            'name': name, 'v_eff': v,
            'sigma_eff_dB': -10 * np.log10(v),
            'I_CV_wrapped': i_cv, 'I_DV': i_dv, 'ratio': ratio,
            'CRB_CV_1cycle_rel': rel_crb_cv,
            'CRB_DV_1cycle_rel': rel_crb_dv,
            'N_modes': N,
        })

    save_json('b1_cramer_rao.json', results)
    return results


# ═══════════════════════════════════════════════════════════════
#  B2: Channel Estimation — MLE + Wiener Filter
# ═══════════════════════════════════════════════════════════════

def run_b2():
    print("\n" + "=" * 70)
    print("  B2: Channel Estimation — CV MLE vs DV Bayesian")
    print("=" * 70)

    rng = np.random.default_rng(SEED + 10)
    v_true = 0.1417
    modes_per_cycle = 686  # d=7
    cycle_counts = [1, 2, 3, 5, 10, 20, 50, 100]
    n_trials = 200

    results_cv = []
    results_dv = []

    for n_cyc in cycle_counts:
        n_modes = modes_per_cycle * n_cyc
        cv_errs = []
        dv_errs = []

        for _ in range(n_trials):
            res, err = generate_gkp(n_modes, v_true, rng)

            # CV: wrapped Gaussian MLE
            v_cv = mle_veff(res, v_init=v_true)
            cv_errs.append(abs(v_cv - v_true) / v_true)

            # DV: binary count → MLE (invert erfc)
            p_hat = np.mean(err)
            if p_hat < 1e-10:
                v_dv = v_true * 0.5
            elif p_hat > 0.49:
                v_dv = 0.4
            else:
                from scipy.optimize import brentq
                try:
                    v_dv = brentq(lambda v: gkp_p_err(v) - p_hat, 0.01, 0.5)
                except ValueError:
                    v_dv = v_true
            dv_errs.append(abs(v_dv - v_true) / v_true)

        cv_med = np.median(cv_errs)
        dv_med = np.median(dv_errs)
        cv_iqr = np.percentile(cv_errs, 75) - np.percentile(cv_errs, 25)
        dv_iqr = np.percentile(dv_errs, 75) - np.percentile(dv_errs, 25)
        adv = dv_med / cv_med if cv_med > 1e-10 else float('inf')

        print(f"  {n_cyc:4d} cyc ({n_modes:7d} modes): "
              f"CV {cv_med:6.2%}±{cv_iqr:.2%}  DV {dv_med:6.2%}±{dv_iqr:.2%}  adv={adv:.1f}x")

        results_cv.append({'n_cycles': n_cyc, 'n_modes': n_modes,
                           'median_rel_err': float(cv_med), 'iqr': float(cv_iqr)})
        results_dv.append({'n_cycles': n_cyc, 'n_modes': n_modes,
                           'median_rel_err': float(dv_med), 'iqr': float(dv_iqr)})

    # Find cycles to 3% and 1%
    for target, label in [(0.03, '3%'), (0.01, '1%')]:
        cv_n = next((r['n_cycles'] for r in results_cv if r['median_rel_err'] <= target), '>100')
        dv_n = next((r['n_cycles'] for r in results_dv if r['median_rel_err'] <= target), '>100')
        print(f"  → Cycles to {label}: CV={cv_n}, DV={dv_n}")

    save_json('b2_channel_estimation.json', {'cv': results_cv, 'dv': results_dv,
              'v_true': v_true, 'modes_per_cycle': modes_per_cycle, 'n_trials': n_trials})
    return results_cv, results_dv


# ═══════════════════════════════════════════════════════════════
#  B3: Adaptive Equalization Decoder
# ═══════════════════════════════════════════════════════════════

def run_b3():
    """Residual normalization decoder under V_eff drift.

    Key insight: instead of rescaling LLR (scale-invariant → no effect),
    NORMALIZE residuals by estimated V_eff before computing LLR with
    a FIXED reference V_eff. This changes relative edge weights.

    r_normalized = r * sqrt(V_ref / V_est)
    LLR = f(r_normalized, V_ref)

    This is the quantum analog of adaptive equalization in telecom.
    """
    print("\n" + "=" * 70)
    print("  B3: Adaptive Equalization Decoder under Drift")
    print("=" * 70)

    import stim, pymatching

    rng = np.random.default_rng(SEED + 200)
    d = 5
    rounds = 5
    v_ref = 0.1417  # Nominal V_eff (Phase 1)

    # Build graph
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

    print(f"  d={d}, {ne} edges")

    # Drift scenarios
    n_epochs = 300
    shots_per_epoch = 200

    scenarios = [
        ('Slow OPA drift (τ=100, σ=0.015)', 100.0, 0.015),
        ('Medium PLL (τ=30, σ=0.020)', 30.0, 0.020),
        ('Fast fluctuation (τ=10, σ=0.025)', 10.0, 0.025),
    ]

    results = {}

    for sc_name, tau, sigma_ou in scenarios:
        print(f"\n  {sc_name}")

        v_drift = ou_process(n_epochs, 1.0, tau, sigma_ou, 0.0, rng)
        v_traj = np.clip(v_ref + v_drift, 0.06, 0.30)

        static_errs = []
        adaptive_errs = []
        equalized_errs = []
        v_ests = []

        ema_v = v_ref

        for ep in range(n_epochs):
            v_now = v_traj[ep]

            # Generate data at true V_eff
            sigma_now = np.sqrt(v_now)
            disp = sigma_now * rng.standard_normal((shots_per_epoch, ne))
            nl = np.rint(disp / SQRT_PI).astype(np.int64)
            err = (nl % 2) != 0
            res = (disp - nl * SQRT_PI).astype(np.float32)

            # Syndromes
            syn = np.zeros((shots_per_epoch, nd), dtype=np.uint8)
            obs = np.zeros(shots_per_epoch, dtype=np.uint8)
            for j, e in enumerate(edges):
                m = err[:, j]
                syn[m, e['n1']] ^= 1
                if e['n2'] is not None:
                    syn[m, e['n2']] ^= 1
                if e['log']:
                    obs[m] ^= 1

            # Estimate V_eff from residuals (EMA of MLE)
            v_meas = float(np.mean(res ** 2))
            ema_v = 0.3 * v_meas + 0.7 * ema_v
            v_ests.append(float(ema_v))

            # === Decoder 1: Static (uses nominal V_ref) ===
            ra = np.abs(res)
            llr_static = np.clip(((SQRT_PI - ra) ** 2 - ra ** 2) / (2 * v_ref), -30, 30)

            # === Decoder 2: Adaptive V_eff scaling (Paper 1 showed this = scale invariant) ===
            llr_adaptive = np.clip(((SQRT_PI - ra) ** 2 - ra ** 2) / (2 * ema_v), -30, 30)

            # === Decoder 3: Equalization (normalize residuals, then use fixed V_ref) ===
            # r_eq = r * sqrt(V_ref / V_est) — stretches/compresses residuals
            scale = np.sqrt(v_ref / max(ema_v, 0.01))
            res_eq = res * scale
            ra_eq = np.abs(res_eq)
            llr_equalized = np.clip(((SQRT_PI - ra_eq) ** 2 - ra_eq ** 2) / (2 * v_ref), -30, 30)

            # Decode all three
            s_e = _decode(syn, obs, llr_static.astype(np.float32), h_mat, f_mat, nd)
            a_e = _decode(syn, obs, llr_adaptive.astype(np.float32), h_mat, f_mat, nd)
            e_e = _decode(syn, obs, llr_equalized.astype(np.float32), h_mat, f_mat, nd)

            static_errs.append(float(s_e.sum() / shots_per_epoch))
            adaptive_errs.append(float(a_e.sum() / shots_per_epoch))
            equalized_errs.append(float(e_e.sum() / shots_per_epoch))

            if ep % 100 == 0:
                print(f"    ep{ep:4d} V={v_now:.4f} est={ema_v:.4f} "
                      f"static={static_errs[-1]:.3e} adapt={adaptive_errs[-1]:.3e} "
                      f"equal={equalized_errs[-1]:.3e}")

        # Smoothed p_L
        win = 30
        def smooth(a):
            return [float(np.mean(a[max(0, i - win):i + 1])) for i in range(len(a))]

        s_sm = smooth(static_errs)
        a_sm = smooth(adaptive_errs)
        e_sm = smooth(equalized_errs)

        # Mean p_L over full run
        s_mean = float(np.mean(static_errs))
        a_mean = float(np.mean(adaptive_errs))
        e_mean = float(np.mean(equalized_errs))

        print(f"    Mean p_L: static={s_mean:.4e} adaptive={a_mean:.4e} equalized={e_mean:.4e}")
        if s_mean > 0:
            print(f"    Equalized/Static = {s_mean/e_mean:.2f}x improvement" if e_mean > 0 else "")

        results[sc_name] = {
            'tau': tau, 'sigma_ou': sigma_ou,
            'v_trajectory': [float(x) for x in v_traj],
            'v_estimated': v_ests,
            'static_pL': static_errs,
            'adaptive_pL': adaptive_errs,
            'equalized_pL': equalized_errs,
            'mean_static': s_mean, 'mean_adaptive': a_mean, 'mean_equalized': e_mean,
        }
        save_json('b3_equalization_decoder.json', results)

    return results


def _decode(syn, obs, weights, h_mat, f_mat, nd):
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
#  B4: BOCPD Anomaly Detection
# ═══════════════════════════════════════════════════════════════

def bocpd_gaussian(data, mu0, kappa0, alpha0, beta0, hazard_rate=1/100):
    """Bayesian Online Changepoint Detection (Adams & MacKay 2007).

    Returns: run_length_probs (T x T matrix), changepoint_prob (T array).
    Simplified: track MAP run length and changepoint probability per step.
    """
    T = len(data)
    # Run length probabilities: R[t] = P(run_length=t | data)
    max_rl = min(T, 500)
    R = np.zeros((T + 1, max_rl + 1))
    R[0, 0] = 1.0

    # Sufficient statistics for each run length
    mu = np.full(max_rl + 1, mu0)
    kappa = np.full(max_rl + 1, kappa0)
    alpha = np.full(max_rl + 1, alpha0)
    beta = np.full(max_rl + 1, beta0)

    cp_prob = np.zeros(T)

    for t in range(T):
        x = data[t]

        # Predictive probability for each run length (Student-t)
        pred = np.zeros(max_rl + 1)
        for rl in range(min(t + 1, max_rl + 1)):
            scale = beta[rl] * (kappa[rl] + 1) / (alpha[rl] * kappa[rl])
            nu = 2 * alpha[rl]
            z = (x - mu[rl]) ** 2 / scale
            # Student-t log pdf (unnormalized for speed)
            pred[rl] = (1 + z / nu) ** (-(nu + 1) / 2) / np.sqrt(scale)

        # Growth probabilities
        growth = R[t, :max_rl + 1] * pred * (1 - hazard_rate)
        # Changepoint probability
        cp = np.sum(R[t, :max_rl + 1] * pred * hazard_rate)

        R[t + 1, 0] = cp
        R[t + 1, 1:max_rl + 1] = growth[:max_rl]

        # Normalize
        total = R[t + 1, :max_rl + 1].sum()
        if total > 0:
            R[t + 1, :max_rl + 1] /= total

        cp_prob[t] = float(R[t + 1, 0])

        # Update sufficient statistics
        new_mu = (kappa * mu + x) / (kappa + 1)
        new_kappa = kappa + 1
        new_alpha = alpha + 0.5
        new_beta = beta + kappa * (x - mu) ** 2 / (2 * (kappa + 1))
        # Shift for growth
        mu[1:] = new_mu[:-1]
        kappa[1:] = new_kappa[:-1]
        alpha[1:] = new_alpha[:-1]
        beta[1:] = new_beta[:-1]
        # Reset for changepoint
        mu[0] = mu0
        kappa[0] = kappa0
        alpha[0] = alpha0
        beta[0] = beta0

    return cp_prob


def run_b4():
    print("\n" + "=" * 70)
    print("  B4: BOCPD Anomaly Detection — Changepoint Posterior")
    print("=" * 70)

    rng = np.random.default_rng(SEED + 300)
    modes_per_cycle = 686
    n_before = 200
    n_after = 200
    n_trials = 50

    anomalies = [
        ('PLL cycle slip (+0.3dB)', 0.3),
        ('PLL cycle slip (+0.5dB)', 0.5),
        ('OPA mode hop (+1.0dB)', 1.0),
    ]

    results = {}

    for anom_name, delta_db in anomalies:
        print(f"\n  {anom_name}")
        v_before = 0.1417
        v_after = v_before * 10 ** (delta_db / 10)

        cv_detects = []
        dv_detects = []

        for trial in range(n_trials):
            cv_series = []
            dv_series = []

            for cyc in range(n_before + n_after):
                v = v_before if cyc < n_before else v_after
                res, err = generate_gkp(modes_per_cycle, v, rng)
                cv_series.append(float(np.mean(res ** 2)))
                dv_series.append(float(np.mean(err)))

            cv_arr = np.array(cv_series)
            dv_arr = np.array(dv_series)

            # BOCPD on CV residual variance
            cv_cp = bocpd_gaussian(cv_arr,
                                   mu0=np.mean(cv_arr[:50]),
                                   kappa0=1, alpha0=1,
                                   beta0=np.var(cv_arr[:50]) + 1e-6,
                                   hazard_rate=1 / 200)

            # BOCPD on DV error rate
            dv_cp = bocpd_gaussian(dv_arr,
                                   mu0=np.mean(dv_arr[:50]),
                                   kappa0=1, alpha0=1,
                                   beta0=np.var(dv_arr[:50]) + 1e-6,
                                   hazard_rate=1 / 200)

            # Detection: first cycle after changepoint where cp_prob > 0.5
            cv_det = n_after
            dv_det = n_after
            for i in range(n_before, n_before + n_after):
                if cv_det == n_after and cv_cp[i] > 0.5:
                    cv_det = i - n_before
                if dv_det == n_after and dv_cp[i] > 0.5:
                    dv_det = i - n_before

            cv_detects.append(cv_det)
            dv_detects.append(dv_det)

        cv_med = float(np.median(cv_detects))
        dv_med = float(np.median(dv_detects))
        cv_rate = float(np.mean(np.array(cv_detects) < n_after))
        dv_rate = float(np.mean(np.array(dv_detects) < n_after))

        adv = dv_med / cv_med if cv_med > 0 else float('inf')
        print(f"    CV: median {cv_med:.0f} cyc, rate {cv_rate:.0%}")
        print(f"    DV: median {dv_med:.0f} cyc, rate {dv_rate:.0%}")
        print(f"    CV advantage: {adv:.1f}x faster")

        results[anom_name] = {
            'delta_dB': delta_db,
            'v_before': v_before, 'v_after': v_after,
            'cv_median': cv_med, 'dv_median': dv_med,
            'cv_detect_rate': cv_rate, 'dv_detect_rate': dv_rate,
            'advantage': adv,
            'n_trials': n_trials,
        }
        save_json('b4_bocpd_detection.json', results)

    return results


# ═══════════════════════════════════════════════════════════════
#  B5: Iterative Estimation + Decoding (Turbo Principle)
# ═══════════════════════════════════════════════════════════════

def run_b5():
    """Turbo principle: decode → update V_eff estimate → re-decode.

    In telecom, turbo equalization iterates between channel estimation
    and decoding. Here we iterate between V_eff estimation and MWPM.

    After first MWPM pass, we know which edges likely have errors.
    Remove those residuals from V_eff estimation → better V_eff →
    normalize residuals → re-decode.
    """
    print("\n" + "=" * 70)
    print("  B5: Turbo Estimation + Decoding")
    print("=" * 70)

    import stim, pymatching

    rng = np.random.default_rng(SEED + 400)
    d = 5
    rounds = 5

    # Build graph (same as B3)
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

    # Test at multiple V_eff with mismatched decoder
    v_true_values = [0.12, 0.14, 0.16, 0.18, 0.20]
    v_decoder = 0.1417  # Decoder assumes nominal
    n_shots = 5000
    n_turbo_iters = 3

    results = []

    for v_true in v_true_values:
        print(f"\n  V_true={v_true:.3f} (decoder assumes {v_decoder:.4f})")

        sigma = np.sqrt(v_true)
        disp = sigma * rng.standard_normal((n_shots, ne))
        nl = np.rint(disp / SQRT_PI).astype(np.int64)
        err = (nl % 2) != 0
        res = (disp - nl * SQRT_PI).astype(np.float32)

        syn = np.zeros((n_shots, nd), dtype=np.uint8)
        obs = np.zeros(n_shots, dtype=np.uint8)
        for j, e in enumerate(edges):
            m = err[:, j]
            syn[m, e['n1']] ^= 1
            if e['n2'] is not None:
                syn[m, e['n2']] ^= 1
            if e['log']:
                obs[m] ^= 1

        iter_pLs = []

        # Iteration 0: standard decode with nominal V_eff
        ra = np.abs(res)
        llr = np.clip(((SQRT_PI - ra) ** 2 - ra ** 2) / (2 * v_decoder), -30, 30)
        e0 = _decode(syn, obs, llr.astype(np.float32), h_mat, f_mat, nd)
        pL0 = float(e0.sum() / n_shots)
        iter_pLs.append(pL0)
        print(f"    iter 0 (nominal): p_L={pL0:.4e} ({e0.sum()}/{n_shots})")

        # Turbo iterations
        v_est = v_decoder
        for it in range(1, n_turbo_iters + 1):
            # Estimate V_eff from residuals, excluding high-confidence errors
            ra_flat = np.abs(res).flatten()
            confidence = np.abs(llr).flatten()
            # Keep only high-confidence (likely correct) measurements for V_eff estimation
            threshold = np.percentile(confidence, 25)  # Bottom 25% confidence → exclude
            mask = confidence > threshold
            v_est = float(np.mean(ra_flat[mask] ** 2))
            v_est = np.clip(v_est, 0.05, 0.4)

            # Equalize: normalize residuals
            scale = np.sqrt(v_decoder / max(v_est, 0.01))
            res_eq = res * scale
            ra_eq = np.abs(res_eq)
            llr = np.clip(((SQRT_PI - ra_eq) ** 2 - ra_eq ** 2) / (2 * v_decoder), -30, 30)

            e_it = _decode(syn, obs, llr.astype(np.float32), h_mat, f_mat, nd)
            pL_it = float(e_it.sum() / n_shots)
            iter_pLs.append(pL_it)
            print(f"    iter {it} (V_est={v_est:.4f}): p_L={pL_it:.4e} ({e_it.sum()}/{n_shots})")

        results.append({
            'v_true': v_true, 'v_decoder': v_decoder,
            'mismatch_dB': 10 * np.log10(v_true / v_decoder),
            'iter_pLs': iter_pLs,
            'improvement': iter_pLs[0] / iter_pLs[-1] if iter_pLs[-1] > 0 else float('inf'),
        })

    save_json('b5_turbo_decoding.json', results)

    print(f"\n  Summary:")
    print(f"  {'V_true':>7} {'Mismatch':>9} {'iter0':>10} {'iter{n_turbo_iters}':>10} {'Improve':>8}")
    for r in results:
        print(f"  {r['v_true']:7.3f} {r['mismatch_dB']:+8.2f}dB "
              f"{r['iter_pLs'][0]:10.4e} {r['iter_pLs'][-1]:10.4e} {r['improvement']:7.2f}x")

    return results


# ═══════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()

    print("=" * 70)
    print("  PAPER 2: GKP LATTICE AS QUANTUM PILOT SIGNAL")
    print(f"  seed={SEED}")
    print("=" * 70)

    run_b1()   # ~2 min (Fisher info, 200K samples × 4 points)
    run_b2()   # ~10 min (MLE × 200 trials × 8 window sizes)
    run_b4()   # ~5 min (BOCPD × 50 trials × 3 anomalies)
    run_b3()   # ~2h (MWPM decode × 300 epochs × 200 shots × 3 scenarios)
    run_b5()   # ~1h (turbo: 5 V_eff × 5000 shots × 4 iterations)

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"  ALL DONE: {elapsed:.0f}s ({elapsed / 3600:.1f}h)")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
