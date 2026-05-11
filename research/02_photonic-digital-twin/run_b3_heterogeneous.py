#!/usr/bin/env python3
"""
B3 Revised: Adaptive Decoder under Heterogeneous V_eff Drift
=============================================================
Key fix: V_eff must vary ACROSS edges within a single shot to break
MWPM scale invariance. Uniform V_eff → all LLRs scale identically → no effect.

Physical motivation: In Taros TDM,
  1. WDM channels have different σ_gen (center 12.5dB, edge 11.5dB)
  2. V_eff drifts between rounds within a QEC cycle
  3. Per-channel loss drifts independently

Model: Assign each DEM edge to a "channel" (n_ch groups).
Each channel has V_eff_ch(t) = V_base(t) + δV_ch(t), where:
  - V_base(t): global OU drift (shared)
  - δV_ch(t): per-channel OU drift (independent, smaller amplitude)

Static decoder:  uses nominal V_ref for ALL edges → wrong relative weights
Adaptive decoder: estimates V_ch per channel from residuals → correct weights

seed=42, CPU only.
"""

import numpy as np
from scipy.special import erfc
import stim, pymatching
import json, os, time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
SEED = 42


def ou_process(n_steps, dt, tau, sigma, x0, rng):
    x = np.zeros(n_steps)
    x[0] = x0
    c = np.exp(-dt / tau)
    noise_std = sigma * np.sqrt(1 - c ** 2)
    for i in range(1, n_steps):
        x[i] = x[i - 1] * c + noise_std * rng.standard_normal()
    return x


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
    print("  B3 REVISED: Heterogeneous V_eff Adaptive Decoder")
    print("=" * 70)

    d = 5
    rounds = 5
    edges, nd, ne, h_mat, f_mat = build_surface_code(d, rounds)
    print(f"  d={d}, {ne} edges, {nd} detectors")

    # Assign edges to channels (n_ch groups, round-robin)
    n_ch = 5  # e.g., 5 WDM channels
    edge_channel = np.array([j % n_ch for j in range(ne)])

    # Channel V_eff offsets (WDM variation: center channels better)
    # Channel 0,1: edge channels (higher V_eff = worse squeezing)
    # Channel 2: center (nominal)
    # Channel 3,4: edge channels
    ch_offset_base = np.array([+0.015, +0.008, 0.0, +0.008, +0.015])

    v_nominal = 0.1417
    n_epochs = 300
    shots_per_epoch = 200

    scenarios = [
        ('Static channels (no drift)', 0.0, 0.0),
        ('Global drift only (τ=50)', 50.0, 0.0),
        ('Global + per-ch drift', 50.0, 0.005),
        ('Strong per-ch drift', 50.0, 0.010),
    ]

    results = {}

    for sc_name, tau_global, sigma_ch in scenarios:
        print(f"\n  Scenario: {sc_name}")

        # Global V_eff drift
        if tau_global > 0:
            v_global_drift = ou_process(n_epochs, 1.0, tau_global, 0.015, 0.0, rng)
        else:
            v_global_drift = np.zeros(n_epochs)

        # Per-channel drift
        ch_drifts = np.zeros((n_epochs, n_ch))
        if sigma_ch > 0:
            for ch in range(n_ch):
                ch_drifts[:, ch] = ou_process(n_epochs, 1.0, 20.0, sigma_ch, 0.0, rng)

        static_errs = []
        adaptive_errs = []
        v_true_global = []

        # Per-channel EMA estimators
        ema_ch = np.full(n_ch, v_nominal) + ch_offset_base

        for ep in range(n_epochs):
            v_base = v_nominal + v_global_drift[ep]

            # Per-channel V_eff for this epoch
            v_per_ch = np.clip(v_base + ch_offset_base + ch_drifts[ep], 0.05, 0.35)
            v_true_global.append(float(v_base))

            # Per-edge V_eff (each edge gets its channel's V_eff)
            v_per_edge = v_per_ch[edge_channel]  # shape (ne,)

            # Generate heterogeneous GKP noise
            sigma_per_edge = np.sqrt(v_per_edge)
            disp = sigma_per_edge[np.newaxis, :] * rng.standard_normal((shots_per_epoch, ne))
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

            # === Static decoder: nominal V_ref for ALL edges ===
            ra = np.abs(res)
            llr_static = np.clip(
                ((SQRT_PI - ra) ** 2 - ra ** 2) / (2 * v_nominal), -30, 30
            ).astype(np.float32)

            # === Adaptive decoder: per-channel V_eff from residuals ===
            # Estimate V_eff per channel from this epoch's residuals
            for ch in range(n_ch):
                ch_mask = edge_channel == ch
                ch_res = res[:, ch_mask]  # (shots, edges_in_channel)
                v_meas = float(np.mean(ch_res ** 2))
                ema_ch[ch] = 0.3 * v_meas + 0.7 * ema_ch[ch]

            # Per-edge estimated V_eff
            v_est_per_edge = ema_ch[edge_channel]  # shape (ne,)
            llr_adaptive = np.clip(
                ((SQRT_PI - ra) ** 2 - ra ** 2) / (2 * v_est_per_edge[np.newaxis, :]),
                -30, 30
            ).astype(np.float32)

            # Decode
            s_e = decode_batch(syn, obs, llr_static, h_mat, f_mat, nd)
            a_e = decode_batch(syn, obs, llr_adaptive, h_mat, f_mat, nd)

            static_errs.append(float(s_e.sum() / shots_per_epoch))
            adaptive_errs.append(float(a_e.sum() / shots_per_epoch))

            if ep % 100 == 0:
                print(f"    ep{ep:4d} V_base={v_base:.4f} "
                      f"static={static_errs[-1]:.3e} adaptive={adaptive_errs[-1]:.3e}")

        s_mean = float(np.mean(static_errs))
        a_mean = float(np.mean(adaptive_errs))
        imp = s_mean / a_mean if a_mean > 0 else float('inf')

        print(f"    Mean p_L: static={s_mean:.4e} adaptive={a_mean:.4e} → {imp:.2f}x improvement")

        results[sc_name] = {
            'tau_global': tau_global, 'sigma_ch': sigma_ch,
            'mean_static': s_mean, 'mean_adaptive': a_mean,
            'improvement': imp,
            'n_channels': n_ch,
            'ch_offset_base': ch_offset_base.tolist(),
            'static_pL': static_errs,
            'adaptive_pL': adaptive_errs,
        }
        save_json('b3_heterogeneous.json', results)

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"  DONE: {elapsed:.0f}s ({elapsed / 3600:.1f}h)")
    print(f"{'=' * 70}")

    print(f"\n  {'Scenario':>35} {'Static':>10} {'Adaptive':>10} {'Improve':>8}")
    print("  " + "-" * 68)
    for k, r in results.items():
        print(f"  {k:>35} {r['mean_static']:10.4e} {r['mean_adaptive']:10.4e} {r['improvement']:7.2f}x")


if __name__ == '__main__':
    main()
