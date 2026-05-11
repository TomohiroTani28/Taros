#!/usr/bin/env python3
"""
Decoder 2: V_eff-rescaling MWPM (scale invariance proof)
=========================================================
Estimates V_eff from residual variance per shot, recomputes LLR.
By MWPM scale invariance theorem, this should yield ~1.0× vs vanilla.

This is the classical "adaptive noise calibration" approach:
  1. Observe GKP residuals r_i for each edge i
  2. Estimate V_eff_hat = mean(r_i^2) across edges (MLE of variance)
  3. Recompute LLR with V_eff_hat instead of nominal V_eff
  4. Run MWPM with rescaled weights

Parameters match run_unified.py for direct comparison.
Output: results/unified_veff_rescaling.json
"""
import numpy as np
from scipy.special import erfc
import stim, pymatching
import os, json, time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
SEED = 42

V_EFF = 0.1417  # Phase 1: σ_eff = 8.5 dB
RHO_LIST = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15]

CONFIGS = {
    3: {'n_test': 30000, 'rounds': 3},
    5: {'n_test': 30000, 'rounds': 5},
    7: {'n_test': 10000, 'rounds': 7},
}


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


def gkp_correlated(ne, ns, v_eff, rho, rng):
    sig = np.sqrt(v_eff)
    if rho <= 0:
        disp = sig * rng.standard_normal((ns, ne))
    else:
        disp = sig * (np.sqrt(1 - rho) * rng.standard_normal((ns, ne)) +
                      np.sqrt(rho) * rng.standard_normal((ns, 1)))
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


def mwpm_decode_batch(syn, obs, weights, h_mat, f_mat, nd):
    ns = syn.shape[0]
    errs = np.zeros(ns, dtype=np.uint8)
    for i in range(ns):
        ww = np.maximum(weights[i], 0.01)
        m = pymatching.Matching(h_mat, weights=ww, faults_matrix=f_mat)
        m.set_boundary_nodes({nd})
        if m.decode(syn[i])[0] != obs[i]:
            errs[i] = 1
    return errs


def veff_rescaling_decode(syn, obs, res, h_mat, f_mat, nd):
    """
    Decoder 2: Estimate V_eff per shot from residual variance, recompute LLR.

    V_eff_hat[shot] = mean(res[shot,:]^2)  (MLE for Gaussian variance)
    LLR_rescaled = ((√π - |r|)² - |r|²) / (2 * V_eff_hat)

    By MWPM scale invariance: w_rescaled = (V_eff / V_eff_hat) * w_original
    Since V_eff_hat is constant across edges for a given shot,
    all weights scale by the same factor → matching result unchanged.
    """
    ns = syn.shape[0]
    # Estimate V_eff per shot
    v_hat = np.mean(res ** 2, axis=1, keepdims=True)  # (ns, 1)
    v_hat = np.maximum(v_hat, 1e-6)  # numerical safety

    ra = np.abs(res)
    llr_rescaled = np.clip(((SQRT_PI - ra)**2 - ra**2) / (2 * v_hat), -30, 30)

    return mwpm_decode_batch(syn, obs, llr_rescaled.astype(np.float32),
                             h_mat, f_mat, nd)


def save_json(name, data):
    path = os.path.join(OUT_DIR, name)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  [saved {name}]")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(SEED)
    t0 = time.time()

    print("=" * 70)
    print("  DECODER 2: V_eff-rescaling MWPM (scale invariance proof)")
    print("=" * 70)

    # IMPORTANT: consume RNG in same order as run_unified.py
    # run_unified does d=3 per-ρ (train+test per ρ), then d=3 mixed (train+eval),
    # then d=5, then d=7. We must match the RNG sequence for test data to align.
    #
    # However, matching exact RNG state is fragile. Instead, we use a SEPARATE
    # seed offset to generate independent test data. The vanilla MWPM baseline
    # is recomputed here for fair comparison on the same samples.

    rng_test = np.random.default_rng(SEED + 1000)  # Independent test data

    results = {}

    for d in [3, 5, 7]:
        cfg = CONFIGS[d]
        edges, nd = extract_graph(d, cfg['rounds'])
        ne = len(edges)
        h_mat, f_mat = build_matching_matrices(edges, nd)

        print(f"\n  d={d} ({ne} edges, n_test={cfg['n_test']})")

        for rho in RHO_LIST:
            key = f"d{d}_rho{rho:.2f}"
            print(f"\n    ρ={rho:.2f}")

            err_te, res_te, llr_te = gkp_correlated(
                ne, cfg['n_test'], V_EFF, rho, rng_test)
            syn_te, obs_te = compute_syndromes(err_te, edges, nd)

            # Vanilla MWPM (per-shot LLR with nominal V_eff)
            t1 = time.time()
            van_e = mwpm_decode_batch(syn_te, obs_te, llr_te, h_mat, f_mat, nd)
            dt_van = time.time() - t1
            van_pL = float(van_e.sum() / cfg['n_test'])
            print(f"      Vanilla:   {van_pL:.4e} ({van_e.sum()}/{cfg['n_test']}) "
                  f"[{dt_van:.0f}s]")

            # V_eff-rescaling MWPM
            t1 = time.time()
            vr_e = veff_rescaling_decode(syn_te, obs_te, res_te,
                                         h_mat, f_mat, nd)
            dt_vr = time.time() - t1
            vr_pL = float(vr_e.sum() / cfg['n_test'])
            improve = van_pL / vr_pL if vr_pL > 0 else float('inf')
            # Count identical decisions
            agree = int((van_e == vr_e).sum())
            print(f"      V-rescale: {vr_pL:.4e} ({vr_e.sum()}/{cfg['n_test']}) "
                  f"[{dt_vr:.0f}s] improve={improve:.3f}x "
                  f"agree={agree}/{cfg['n_test']} ({100*agree/cfg['n_test']:.1f}%)")

            results[key] = {
                'd': d, 'rho': rho,
                'vanilla_pL': van_pL,
                'veff_rescaling_pL': vr_pL,
                'improve_factor': improve,
                'vanilla_err': int(van_e.sum()),
                'veff_err': int(vr_e.sum()),
                'agree_count': agree,
                'agree_pct': 100 * agree / cfg['n_test'],
                'n_test': cfg['n_test'],
            }
            save_json('unified_veff_rescaling.json', results)

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"  DONE: {elapsed:.0f}s ({elapsed / 3600:.1f}h)")
    print(f"{'=' * 70}")

    # Summary
    print(f"\n  {'d':>3} {'ρ':>5} {'Vanilla':>10} {'V-rescale':>10} "
          f"{'Improve':>8} {'Agree%':>7}")
    print("  " + "-" * 50)
    for k in sorted(results.keys()):
        r = results[k]
        print(f"  {r['d']:3d} {r['rho']:5.2f} {r['vanilla_pL']:10.4e} "
              f"{r['veff_rescaling_pL']:10.4e} {r['improve_factor']:7.3f}x "
              f"{r['agree_pct']:6.1f}%")


if __name__ == '__main__':
    main()
