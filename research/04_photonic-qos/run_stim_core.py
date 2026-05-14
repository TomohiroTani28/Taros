#!/usr/bin/env python3
"""
Stim-based Monte Carlo p_L engine for Paper 4
==============================================
Reuses Paper 3's noise model + PyMatching decoder with V_eff(t) drift.
Provides actual QEC error counting instead of analytical formula.
"""
import numpy as np
from scipy.special import erfc
import stim, pymatching
import os, json, sys, time

SQRT_PI = np.sqrt(np.pi)
SEED = 42
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(OUT, exist_ok=True)


# ─── Graph extraction (from Paper 3) ───

def extract_graph(d, rounds):
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
    return edges, dem.num_detectors


def build_matching_matrices(edges, nd):
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
    return h_mat, f_mat


# ─── Noise model (from Paper 3) ───

def gkp_correlated(ne, ns, v_eff, rho, rng):
    """Generate GKP displacement noise with correlation."""
    sig = np.sqrt(v_eff)
    if rho <= 0:
        disp = sig * rng.standard_normal((ns, ne))
    else:
        rho_c = min(max(rho, 0), 0.99)
        disp = sig * (np.sqrt(1 - rho_c) * rng.standard_normal((ns, ne)) +
                      np.sqrt(rho_c) * rng.standard_normal((ns, 1)))
    nl = np.rint(disp / SQRT_PI).astype(np.int64)
    err = (nl % 2) != 0
    res = disp - nl * SQRT_PI
    ra = np.abs(res)
    llr = np.clip(((SQRT_PI - ra)**2 - ra**2) / (2 * v_eff), -30, 30)
    return err, res.astype(np.float32), llr.astype(np.float32)


def compute_syndromes(errors, edges, nd):
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


# ─── Decoding ───

def mwpm_soft_decode(syn, obs, llr, h_mat, f_mat, nd):
    """Per-shot soft-info MWPM (Paper 3 Decoder 1: Vanilla soft-info MWPM).
    Uses per-shot LLR weights w(r) = ((sqrt(pi)-|r|)^2 - |r|^2)/(2 V_eff).
    Equivalent to the baseline reported in Paper 3 Table I.
    """
    ns = syn.shape[0]
    errs = 0
    for i in range(ns):
        ww = np.maximum(llr[i], 0.01)
        m = pymatching.Matching(h_mat, weights=ww, faults_matrix=f_mat)
        m.set_boundary_nodes({nd})
        if m.decode(syn[i])[0] != obs[i]:
            errs += 1
    return errs


def residual_sub_decode(syn, obs, res, v_eff, h_mat, f_mat, nd):
    """Residual subtraction MWPM (Paper 3 Decoder 3)."""
    ns = syn.shape[0]
    common = np.mean(res, axis=1, keepdims=True)
    res_corr = res - common
    ra = np.abs(res_corr)
    llr_corr = np.clip(((SQRT_PI - ra)**2 - ra**2) / (2 * v_eff), -30, 30)
    errs = 0
    for i in range(ns):
        ww = np.maximum(llr_corr[i], 0.01)
        m = pymatching.Matching(h_mat, weights=ww, faults_matrix=f_mat)
        m.set_boundary_nodes({nd})
        if m.decode(syn[i])[0] != obs[i]:
            errs += 1
    return errs


# ─── Monte Carlo p_L measurement ───

def measure_p_L(d, v_eff, rho, n_shots, decoder='mwpm', rng=None):
    """Run Monte Carlo QEC and return error count + total shots.

    decoder: 'mwpm' | 'residual_sub'
    Returns: (n_errors, n_shots)
    """
    if rng is None:
        rng = np.random.default_rng(SEED)

    rounds = d
    edges, nd = extract_graph(d, rounds)
    ne = len(edges)
    h_mat, f_mat = build_matching_matrices(edges, nd)

    # Generate noise
    err, res, llr = gkp_correlated(ne, n_shots, v_eff, rho, rng)
    syn, obs = compute_syndromes(err, edges, nd)

    # Decode
    if decoder == 'mwpm':
        # Per-shot soft-info LLR weights (Paper 3 Decoder 1: Vanilla soft-info MWPM)
        n_err = mwpm_soft_decode(syn, obs, llr, h_mat, f_mat, nd)
    elif decoder == 'residual_sub':
        n_err = residual_sub_decode(syn, obs, res, v_eff, h_mat, f_mat, nd)
    else:
        raise ValueError(f"Unknown decoder: {decoder}")

    return n_err, n_shots


def wilson_ci(k, n, z=1.96):
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    half = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return max(0, center - half), min(1, center + half)


# ─── E2/E3 Stim-based experiments ───

def run_e2_stim():
    """E2: Factory allocation effect on p_L via Stim Monte Carlo.

    Key: different factory counts → different wall-time → different V_eff at end of cycle.
    We simulate this by computing V_eff(t) at end of 100 QEC cycles for each factory count,
    then measuring p_L at that V_eff.
    """
    print("=" * 60)
    print("E2-Stim: Factory allocation → wall-time → p_L (Monte Carlo)")
    print("=" * 60)

    results = {}
    V_EFF_BASE = 0.1417
    N_LOGICAL = 10
    N_SHOTS = 5000  # per condition

    for d in [5, 7]:
        rounds = d
        modes_per_qec = 2 * d**3
        slot_ns = 10

        for drift_rate in [0.0, 0.05, 0.2, 0.5]:
            for n_factories in [0, 1, 3, 8, 12]:
                # Compute wall-time after 100 QEC cycles
                total_modes = (N_LOGICAL + 15 * n_factories) * modes_per_qec
                cycle_time_sec = total_modes * slot_ns * 1e-9
                wall_time_100cyc = 100 * cycle_time_sec
                v_eff_end = V_EFF_BASE + drift_rate * wall_time_100cyc

                for rho in [0.0, 0.05, 0.10]:
                    for decoder in ['mwpm', 'residual_sub']:
                        rng = np.random.default_rng(SEED)
                        sys.stdout.write(
                            f"  d={d} drift={drift_rate} F={n_factories} "
                            f"rho={rho} {decoder}...")
                        sys.stdout.flush()

                        t0 = time.time()
                        n_err, n_tot = measure_p_L(
                            d, v_eff_end, rho, N_SHOTS, decoder, rng)
                        elapsed = time.time() - t0

                        p_L = n_err / n_tot
                        lo, hi = wilson_ci(n_err, n_tot) if n_err > 0 else (0, 3/n_tot)

                        key = (f"d{d}_drift{drift_rate}_F{n_factories}"
                               f"_rho{rho}_{decoder}")
                        results[key] = {
                            'd': d,
                            'drift_rate': drift_rate,
                            'n_factories': n_factories,
                            'rho': rho,
                            'decoder': decoder,
                            'v_eff_end': round(v_eff_end, 6),
                            'wall_time_100cyc_ms': round(wall_time_100cyc * 1000, 3),
                            'n_errors': n_err,
                            'n_shots': n_tot,
                            'p_L': round(p_L, 6),
                            'ci_lo': round(lo, 6),
                            'ci_hi': round(hi, 6),
                        }
                        print(f" p_L={p_L:.4f} [{lo:.4f},{hi:.4f}] "
                              f"V={v_eff_end:.4f} {elapsed:.1f}s")

                        # Save incrementally
                        with open(os.path.join(OUT, 'e2_stim.json'), 'w') as f:
                            json.dump(results, f, indent=2)

    return results


def run_e3_stim():
    """E3: Decoder switching effect via Stim Monte Carlo.

    Compare p_L of MWPM vs residual-subtraction at different (V_eff, rho) points
    along drift trajectories. This validates the analytical decoder performance model.
    """
    print("\n" + "=" * 60)
    print("E3-Stim: Decoder performance along drift trajectories")
    print("=" * 60)

    results = {}
    N_SHOTS = 5000

    # Sample points along drift trajectories
    # Each point: (v_eff, rho, label)
    trajectory_points = [
        # Stable
        (0.1417, 0.03, 'stable_t0'),
        # Medium drift: tau=60s, sampled at t=0,30,60,120s
        (0.1417, 0.03, 'med_t0'),
        (0.1417 * 1.15, 0.10, 'med_t30'),
        (0.1417 * 1.30, 0.15, 'med_t60'),
        (0.1417 * 1.40, 0.20, 'med_t120'),
        # Step change
        (0.1417, 0.03, 'step_before'),
        (0.1417 * 1.40, 0.18, 'step_after'),
        # High correlation
        (0.1417, 0.15, 'high_rho'),
        (0.1417, 0.20, 'extreme_rho'),
    ]

    for d in [5, 7]:
        for v_eff, rho, label in trajectory_points:
            for decoder in ['mwpm', 'residual_sub']:
                rng = np.random.default_rng(SEED)
                sys.stdout.write(f"  d={d} {label} {decoder}...")
                sys.stdout.flush()

                t0 = time.time()
                n_err, n_tot = measure_p_L(d, v_eff, rho, N_SHOTS, decoder, rng)
                elapsed = time.time() - t0

                p_L = n_err / n_tot
                lo, hi = wilson_ci(n_err, n_tot) if n_err > 0 else (0, 3/n_tot)

                key = f"d{d}_{label}_{decoder}"
                results[key] = {
                    'd': d,
                    'label': label,
                    'v_eff': round(v_eff, 6),
                    'rho': rho,
                    'decoder': decoder,
                    'n_errors': n_err,
                    'n_shots': n_tot,
                    'p_L': round(p_L, 6),
                    'ci_lo': round(lo, 6),
                    'ci_hi': round(hi, 6),
                }
                print(f" p_L={p_L:.4f} [{lo:.4f},{hi:.4f}] {elapsed:.1f}s")

                with open(os.path.join(OUT, 'e3_stim.json'), 'w') as f:
                    json.dump(results, f, indent=2)

    return results


def run_e4_stim():
    """E4: V_eff estimation from GKP residuals — Stim-verified.

    Generate QEC data at known V_eff, estimate V_eff from residuals,
    compare CV vs DV estimation quality.
    """
    print("\n" + "=" * 60)
    print("E4-Stim: CV vs DV V_eff estimation (Stim-verified)")
    print("=" * 60)

    results = {}
    N_SHOTS = 3000

    for d in [5, 7]:
        rounds = d
        edges, nd = extract_graph(d, rounds)
        ne = len(edges)

        for v_eff_true in [0.1417, 0.16, 0.20, 0.25]:
            rng = np.random.default_rng(SEED)

            # Generate data at true V_eff
            err, res, llr = gkp_correlated(ne, N_SHOTS, v_eff_true, 0.05, rng)
            syn, obs = compute_syndromes(err, edges, nd)

            # CV estimate: mean(r^2)
            cv_estimates = []
            for i in range(N_SHOTS):
                v_est = np.mean(res[i]**2)
                cv_estimates.append(v_est)

            cv_med_err = float(np.median(np.abs(
                np.array(cv_estimates) - v_eff_true)) / v_eff_true)

            # DV estimate: sliding window of binary syndrome counts
            dv_errors = []
            window = 100
            for i in range(window, N_SHOTS):
                # Count syndrome triggers in window
                syn_rate = np.mean(syn[i-window:i])
                # Rough DV estimate (binary only)
                if syn_rate > 0:
                    v_est_dv = v_eff_true * (syn_rate / np.mean(syn[:window]))
                else:
                    v_est_dv = 0.1417  # default
                dv_errors.append(abs(v_est_dv - v_eff_true) / v_eff_true)

            dv_med_err = float(np.median(dv_errors)) if dv_errors else 1.0

            key = f"d{d}_veff{v_eff_true:.4f}"
            results[key] = {
                'd': d,
                'v_eff_true': v_eff_true,
                'cv_median_error': round(cv_med_err, 4),
                'dv_median_error': round(dv_med_err, 4),
                'estimation_advantage': round(
                    dv_med_err / max(cv_med_err, 1e-6), 2),
                'n_shots': N_SHOTS,
            }
            print(f"  d={d} V_eff={v_eff_true:.4f}: "
                  f"CV {cv_med_err*100:.1f}% vs DV {dv_med_err*100:.1f}% "
                  f"({results[key]['estimation_advantage']}x)")

    with open(os.path.join(OUT, 'e4_stim.json'), 'w') as f:
        json.dump(results, f, indent=2)
    return results


if __name__ == "__main__":
    print("Paper 4: Stim-based Monte Carlo verification")
    print(f"stim {stim.__version__}, pymatching {pymatching.__version__}")
    print()

    run_e2_stim()
    run_e3_stim()
    run_e4_stim()

    print("\nAll Stim experiments complete.")
