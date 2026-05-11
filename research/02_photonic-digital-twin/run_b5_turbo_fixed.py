#!/usr/bin/env python3
"""
B5 Revised: Turbo Estimation + Decoding with Heterogeneous V_eff
=================================================================
Fixes:
  1. Use wrapped Gaussian MLE instead of mean(r²) for V_eff estimation
  2. Per-channel heterogeneous V_eff to break scale invariance
  3. Turbo: decode → exclude likely-error edges → re-estimate per-channel V_eff → re-decode

Physical scenario: Decoder calibrated for nominal V_eff, but actual hardware has
per-channel mismatch (WDM channel variation + drift).

seed=42, CPU only, ~30min.
"""

import numpy as np
from scipy.special import erfc
from scipy.optimize import minimize_scalar
import stim, pymatching
import json, os, time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
SEED = 42


def wrapped_gaussian_negloglik(residuals, v):
    ns = np.array([-1, 0, 1]) * SQRT_PI
    r = residuals[:, np.newaxis]
    exps = np.exp(-0.5 * (r - ns) ** 2 / v)
    return -np.sum(np.log(np.sum(exps, axis=-1) + 1e-300) - 0.5 * np.log(2 * np.pi * v))


def mle_veff(residuals):
    res = minimize_scalar(
        lambda v: wrapped_gaussian_negloglik(residuals, v),
        bounds=(0.02, 0.5), method='bounded')
    return float(res.x)


def build_surface_code(d, rounds):
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
    return edges, nd, ne, h_mat, f_mat


def decode_batch(syn, obs, weights, h_mat, f_mat, nd):
    ns = syn.shape[0]
    errs = np.zeros(ns, dtype=np.uint8)
    for i in range(ns):
        ww = np.maximum(weights[i], 0.01)
        m = pymatching.Matching(h_mat, weights=ww, faults_matrix=f_mat)
        m.set_boundary_nodes({nd})
        if m.decode(syn[i])[0] != obs[i]:
            errs[i] = 1
    return errs


def compute_llr_per_edge(res, v_per_edge):
    """LLR with per-edge V_eff. Shape: res (ns, ne), v_per_edge (ne,)."""
    ra = np.abs(res)
    v = v_per_edge[np.newaxis, :]  # broadcast (1, ne)
    return np.clip(((SQRT_PI - ra) ** 2 - ra ** 2) / (2 * v), -30, 30).astype(np.float32)


def save_json(name, data):
    path = os.path.join(OUT_DIR, name)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=lambda x: float(x) if isinstance(x, np.floating) else str(x))
    print(f"  [saved {name}]")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(SEED)
    t0 = time.time()

    print("=" * 70)
    print("  B5 REVISED: Turbo Estimation + Decoding (Heterogeneous V_eff)")
    print("=" * 70)

    d = 5
    rounds = 5
    edges, nd, ne, h_mat, f_mat = build_surface_code(d, rounds)
    print(f"  d={d}, {ne} edges")

    n_ch = 5
    edge_channel = np.array([j % n_ch for j in range(ne)])

    # Per-channel V_eff mismatch scenarios
    # Format: (name, true V_eff per channel, decoder-assumed V_eff)
    v_nominal = 0.1417
    scenarios = [
        ("No mismatch (control)",
         np.full(n_ch, v_nominal),
         v_nominal),
        ("Small WDM variation (±0.01)",
         np.array([0.152, 0.148, 0.142, 0.148, 0.152]),
         v_nominal),
        ("Large WDM variation (±0.02)",
         np.array([0.162, 0.152, 0.142, 0.152, 0.162]),
         v_nominal),
        ("Asymmetric drift (ch0 degraded)",
         np.array([0.180, 0.142, 0.142, 0.142, 0.142]),
         v_nominal),
        ("Two channels degraded",
         np.array([0.175, 0.142, 0.142, 0.142, 0.175]),
         v_nominal),
    ]

    n_shots = 10000
    n_turbo = 3

    results = []

    for sc_name, v_true_ch, v_dec in scenarios:
        print(f"\n  {sc_name}")
        print(f"    True V per ch: {[f'{v:.4f}' for v in v_true_ch]}")

        v_true_per_edge = v_true_ch[edge_channel]

        # Generate data with per-edge V_eff
        sigma_per_edge = np.sqrt(v_true_per_edge)
        disp = sigma_per_edge[np.newaxis, :] * rng.standard_normal((n_shots, ne))
        nl = np.rint(disp / SQRT_PI).astype(np.int64)
        err = (nl % 2) != 0
        res = (disp - nl * SQRT_PI).astype(np.float32)

        # Syndromes
        syn = np.zeros((n_shots, nd), dtype=np.uint8)
        obs = np.zeros(n_shots, dtype=np.uint8)
        for j, e in enumerate(edges):
            m = err[:, j]
            syn[m, e['n1']] ^= 1
            if e['n2'] is not None:
                syn[m, e['n2']] ^= 1
            if e['log']:
                obs[m] ^= 1

        iter_results = []

        # Iteration 0: static decoder (uniform nominal V_eff)
        llr = compute_llr_per_edge(res, np.full(ne, v_dec))
        e0 = decode_batch(syn, obs, llr, h_mat, f_mat, nd)
        pl0 = float(e0.sum() / n_shots)
        iter_results.append(pl0)
        print(f"    iter 0 (static):  p_L={pl0:.4e} ({e0.sum()}/{n_shots})")

        # Iteration 0.5: MLE per-channel (no turbo, just better estimation)
        v_est_ch = np.zeros(n_ch)
        for ch in range(n_ch):
            ch_mask = edge_channel == ch
            ch_res = res[:, ch_mask].flatten()
            v_est_ch[ch] = mle_veff(ch_res)

        v_est_per_edge = v_est_ch[edge_channel]
        llr_mle = compute_llr_per_edge(res, v_est_per_edge)
        e_mle = decode_batch(syn, obs, llr_mle, h_mat, f_mat, nd)
        pl_mle = float(e_mle.sum() / n_shots)
        iter_results.append(pl_mle)
        print(f"    iter 1 (MLE):     p_L={pl_mle:.4e} ({e_mle.sum()}/{n_shots}) "
              f"V_est={[f'{v:.4f}' for v in v_est_ch]}")

        # Turbo iterations: use decoder output to refine V_eff estimation
        prev_llr = llr_mle
        for it in range(2, 2 + n_turbo):
            # Use LLR confidence to weight residuals for V_eff estimation
            confidence = np.abs(prev_llr)  # High |LLR| = high confidence

            v_est_ch_turbo = np.zeros(n_ch)
            for ch in range(n_ch):
                ch_mask = edge_channel == ch
                ch_res = res[:, ch_mask]
                ch_conf = confidence[:, ch_mask]

                # Weight: high-confidence residuals are more reliable for V_eff estimation
                # Low-confidence residuals may be near decision boundary (less informative)
                weights = ch_conf / (ch_conf.mean() + 1e-10)
                weighted_r2 = np.average(ch_res.flatten() ** 2,
                                         weights=weights.flatten())
                # Blend with MLE for stability
                v_mle_ch = mle_veff(ch_res.flatten())
                v_est_ch_turbo[ch] = 0.5 * weighted_r2 + 0.5 * v_mle_ch

            v_est_turbo = v_est_ch_turbo[edge_channel]
            llr_turbo = compute_llr_per_edge(res, v_est_turbo)
            e_turbo = decode_batch(syn, obs, llr_turbo, h_mat, f_mat, nd)
            pl_turbo = float(e_turbo.sum() / n_shots)
            iter_results.append(pl_turbo)
            print(f"    iter {it} (turbo):  p_L={pl_turbo:.4e} ({e_turbo.sum()}/{n_shots})")
            prev_llr = llr_turbo

        improvement = pl0 / iter_results[-1] if iter_results[-1] > 0 else float('inf')
        mle_improvement = pl0 / pl_mle if pl_mle > 0 else float('inf')
        print(f"    → MLE improvement: {mle_improvement:.2f}x, "
              f"Final turbo: {improvement:.2f}x")

        results.append({
            'scenario': sc_name,
            'v_true_ch': v_true_ch.tolist(),
            'v_decoder': v_dec,
            'iter_pLs': iter_results,
            'mle_improvement': mle_improvement,
            'turbo_improvement': improvement,
            'n_shots': n_shots,
        })
        save_json('b5_turbo_heterogeneous.json', results)

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"  DONE: {elapsed:.0f}s ({elapsed / 60:.1f}min)")
    print(f"{'=' * 70}")

    print(f"\n  {'Scenario':>35} {'Static':>10} {'MLE':>10} {'MLE imp':>8} {'Turbo':>10} {'T imp':>8}")
    print("  " + "-" * 85)
    for r in results:
        print(f"  {r['scenario']:>35} {r['iter_pLs'][0]:10.4e} {r['iter_pLs'][1]:10.4e} "
              f"{r['mle_improvement']:7.2f}x {r['iter_pLs'][-1]:10.4e} {r['turbo_improvement']:7.2f}x")


if __name__ == '__main__':
    main()
