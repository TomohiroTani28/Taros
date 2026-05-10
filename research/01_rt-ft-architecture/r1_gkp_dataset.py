#!/usr/bin/env python3
"""
R1 Phase 1: GKP Surface Code Dataset Generator
================================================

Generates training/test data for the FiLM-GKP adaptive decoder.

Each sample contains:
  - GKP residuals: continuous-valued tensor (n_detectors,) per round
  - Syndrome bits: binary tensor (n_detectors,) per round
  - V_eff: the noise parameter (scalar, for FiLM conditioning)
  - Label: logical error (binary)

Data generation modes:
  - Static: fixed V_eff across all shots
  - Drift: V_eff(t) slowly changes over rounds
  - Spike: one channel jumps for a burst of rounds

Also establishes MWPM soft-info baseline for comparison.

seed=42
"""

import numpy as np
from scipy.special import erfc
import stim
import pymatching
import os
import time
import json

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
# Graph extraction
# ============================================================
def extract_graph(d, rounds):
    """Extract matching graph from Stim DEM."""
    c = stim.Circuit.generated(
        'surface_code:rotated_memory_z',
        rounds=rounds, distance=d,
        before_round_data_depolarization=0.01,
        before_measure_flip_probability=0.01,
    )
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


# ============================================================
# GKP noise sampling with time-varying V_eff
# ============================================================
def gkp_sample_static(n_edges, n_shots, V_eff, rng):
    """Static noise: same V_eff for all edges and shots."""
    sigma = np.sqrt(V_eff)
    delta = sigma * rng.standard_normal((n_shots, n_edges))
    return _gkp_decode(delta, V_eff)


def gkp_sample_drift(n_edges, n_shots, V_eff_base, drift_rate, rng):
    """
    Drift noise: V_eff increases linearly over shots.
    V_eff(shot) = V_eff_base + drift_rate * shot / n_shots
    """
    V_schedule = V_eff_base + drift_rate * np.arange(n_shots) / n_shots
    sigma_schedule = np.sqrt(V_schedule)  # (n_shots,)
    z = rng.standard_normal((n_shots, n_edges))
    delta = z * sigma_schedule[:, np.newaxis]
    # For LLR, use the TRUE V_eff per shot (oracle)
    # and also return the schedule for FiLM conditioning
    return _gkp_decode_varying(delta, V_schedule)


def gkp_sample_spike(n_edges, n_shots, V_eff_base, spike_edges,
                      spike_factor, spike_start, spike_end, rng):
    """
    Spike noise: subset of edges have elevated V_eff during [start, end).
    spike_edges: list of edge indices affected
    spike_factor: multiplicative increase in V_eff for affected edges
    """
    V_base = np.full((n_shots, n_edges), V_eff_base)
    for j in spike_edges:
        V_base[spike_start:spike_end, j] *= spike_factor
    sigma = np.sqrt(V_base)
    z = rng.standard_normal((n_shots, n_edges))
    delta = z * sigma
    return _gkp_decode_matrix(delta, V_base)


def _gkp_decode(delta, V_eff):
    """Decode GKP displacement noise. Returns errors, residuals, LLR."""
    n_lattice = np.rint(delta / SQRT_PI).astype(np.int64)
    errors = (n_lattice % 2) != 0
    residual = delta - n_lattice * SQRT_PI
    r_abs = np.abs(residual)
    llr = np.clip(((SQRT_PI - r_abs)**2 - r_abs**2) / (2.0 * V_eff), -30, 30)
    return errors, residual, llr


def _gkp_decode_varying(delta, V_schedule):
    """Decode with per-shot V_eff."""
    n_lattice = np.rint(delta / SQRT_PI).astype(np.int64)
    errors = (n_lattice % 2) != 0
    residual = delta - n_lattice * SQRT_PI
    r_abs = np.abs(residual)
    V = V_schedule[:, np.newaxis]  # (n_shots, 1)
    llr = np.clip(((SQRT_PI - r_abs)**2 - r_abs**2) / (2.0 * V), -30, 30)
    return errors, residual, llr, V_schedule


def _gkp_decode_matrix(delta, V_matrix):
    """Decode with per-shot-per-edge V_eff."""
    n_lattice = np.rint(delta / SQRT_PI).astype(np.int64)
    errors = (n_lattice % 2) != 0
    residual = delta - n_lattice * SQRT_PI
    r_abs = np.abs(residual)
    llr = np.clip(((SQRT_PI - r_abs)**2 - r_abs**2) / (2.0 * V_matrix), -30, 30)
    return errors, residual, llr, V_matrix


# ============================================================
# Syndrome computation
# ============================================================
def compute_syndromes(errors, edges, n_detectors):
    """Compute syndromes and observable flips."""
    n_shots = errors.shape[0]
    syndromes = np.zeros((n_shots, n_detectors), dtype=np.uint8)
    obs_flips = np.zeros(n_shots, dtype=np.uint8)
    for j, e in enumerate(edges):
        m = errors[:, j]
        syndromes[m, e['n1']] ^= 1
        if e['n2'] is not None:
            syndromes[m, e['n2']] ^= 1
        if e['log']:
            obs_flips[m] ^= 1
    return syndromes, obs_flips


# ============================================================
# MWPM soft-info baseline decoder
# ============================================================
def mwpm_decode_batch(syndromes, obs_flips, llr, edges, n_detectors):
    """Decode with per-shot soft-info MWPM. Returns logical errors."""
    n_shots = syndromes.shape[0]
    n_edges = len(edges)
    bnd = n_detectors
    H = np.zeros((n_detectors + 1, n_edges), dtype=np.uint8)
    F = np.zeros((1, n_edges), dtype=np.uint8)
    for j, e in enumerate(edges):
        H[e['n1'], j] = 1
        if e['n2'] is not None:
            H[e['n2'], j] = 1
        else:
            H[bnd, j] = 1
        if e['log']:
            F[0, j] = 1

    logical_errors = np.zeros(n_shots, dtype=np.uint8)
    for i in range(n_shots):
        w = np.maximum(llr[i], 0.01)
        m = pymatching.Matching(H, weights=w, faults_matrix=F)
        m.set_boundary_nodes({bnd})
        pred = m.decode(syndromes[i])
        if pred[0] != obs_flips[i]:
            logical_errors[i] = 1
    return logical_errors


# ============================================================
# Dataset generation
# ============================================================
def generate_dataset(d, rounds, V_eff, n_shots, rng, noise_mode='static',
                     drift_rate=0.0, spike_config=None):
    """
    Generate a complete dataset for decoder training/evaluation.

    Returns dict with:
      - residuals: (n_shots, n_edges) float32 — GKP residuals (continuous)
      - syndromes: (n_shots, n_detectors) uint8 — syndrome bits
      - llr: (n_shots, n_edges) float32 — log-likelihood ratios
      - labels: (n_shots,) uint8 — logical error (0/1)
      - V_eff_per_shot: (n_shots,) float32 — noise parameter per shot
      - mwpm_errors: (n_shots,) uint8 — MWPM baseline predictions
      - metadata: dict
    """
    edges, n_det = extract_graph(d, rounds)
    n_edges = len(edges)

    if noise_mode == 'static':
        errors, residuals, llr = gkp_sample_static(n_edges, n_shots, V_eff, rng)
        V_per_shot = np.full(n_shots, V_eff, dtype=np.float32)
    elif noise_mode == 'drift':
        errors, residuals, llr, V_schedule = gkp_sample_drift(
            n_edges, n_shots, V_eff, drift_rate, rng)
        V_per_shot = V_schedule.astype(np.float32)
    elif noise_mode == 'spike':
        sc = spike_config or {'edges': [0], 'factor': 2.0,
                              'start': n_shots//3, 'end': 2*n_shots//3}
        errors, residuals, llr, V_matrix = gkp_sample_spike(
            n_edges, n_shots, V_eff, sc['edges'], sc['factor'],
            sc['start'], sc['end'], rng)
        V_per_shot = V_matrix.mean(axis=1).astype(np.float32)
    else:
        raise ValueError(f"Unknown noise_mode: {noise_mode}")

    syndromes, obs_flips = compute_syndromes(errors, edges, n_det)

    # MWPM baseline (subsample for speed if large)
    n_mwpm = min(n_shots, 5000)
    mwpm_errors = np.zeros(n_shots, dtype=np.uint8)
    mwpm_errors[:n_mwpm] = mwpm_decode_batch(
        syndromes[:n_mwpm], obs_flips[:n_mwpm], llr[:n_mwpm], edges, n_det)

    return {
        'residuals': residuals.astype(np.float32),
        'syndromes': syndromes,
        'llr': llr.astype(np.float32),
        'labels': obs_flips,
        'V_eff_per_shot': V_per_shot,
        'mwpm_errors': mwpm_errors,
        'n_mwpm_evaluated': n_mwpm,
        'metadata': {
            'd': d, 'rounds': rounds, 'n_edges': n_edges,
            'n_detectors': n_det, 'V_eff_base': float(V_eff),
            'noise_mode': noise_mode, 'n_shots': n_shots,
        },
    }


# ============================================================
# Main: Generate datasets + establish baseline
# ============================================================
def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    print("=" * 70)
    print("  R1 Phase 1: GKP Dataset Generation + MWPM Baseline")
    print("=" * 70)

    # Configuration
    d = 3  # Start with d=3 for fast iteration
    rounds = 3

    V_phase1 = compute_V_eff(13.0, 0.39, 0.010)
    V_phase2r = compute_V_eff(13.0, 0.27, 0.010)

    configs = [
        # (name, V_eff, n_train, n_test, noise_mode, kwargs)
        ('static_phase1', V_phase1, 50000, 10000, 'static', {}),
        ('static_phase2r', V_phase2r, 50000, 10000, 'static', {}),
        ('drift_phase1', V_phase1, 50000, 10000, 'drift',
         {'drift_rate': 0.05}),  # V_eff increases by 0.05 over dataset
        ('spike_phase1', V_phase1, 50000, 10000, 'spike',
         {'spike_config': {'edges': [0, 1, 2], 'factor': 2.0,
                           'start': 16000, 'end': 33000}}),
    ]

    baselines = {}

    for name, V, n_train, n_test, mode, kwargs in configs:
        p = compute_p_phys(V)
        s = -10 * np.log10(V)
        print(f"\n  {name}: σ_eff={s:.1f}dB, p_phys={p:.4e}, mode={mode}")

        t1 = time.time()

        # Generate train set
        train = generate_dataset(d, rounds, V, n_train, rng,
                                noise_mode=mode, **kwargs)
        # Generate test set
        test = generate_dataset(d, rounds, V, n_test, rng,
                               noise_mode=mode, **kwargs)

        dt = time.time() - t1

        # Baseline: MWPM on test set
        n_eval = test['n_mwpm_evaluated']
        mwpm_errs = test['mwpm_errors'][:n_eval].sum()
        mwpm_pL = mwpm_errs / n_eval
        label_rate = test['labels'].mean()

        print(f"    Train: {n_train} shots, {train['metadata']['n_edges']} edges")
        print(f"    Test:  {n_test} shots")
        print(f"    MWPM baseline: p_L={mwpm_pL:.4e} ({mwpm_errs}/{n_eval})")
        print(f"    Label rate (raw error): {label_rate:.4f}")
        print(f"    [{dt:.1f}s]")

        baselines[name] = {
            'mwpm_pL': float(mwpm_pL),
            'mwpm_errors': int(mwpm_errs),
            'mwpm_evaluated': n_eval,
            'label_rate': float(label_rate),
            'sigma_eff': float(s),
            'p_phys': float(p),
        }

        # Save datasets as .npz for PyTorch loading
        for split, data in [('train', train), ('test', test)]:
            path = os.path.join(out_dir, f'r1_{name}_{split}.npz')
            np.savez_compressed(path,
                residuals=data['residuals'],
                syndromes=data['syndromes'],
                llr=data['llr'],
                labels=data['labels'],
                V_eff=data['V_eff_per_shot'],
            )

    # Save baselines
    with open(os.path.join(out_dir, 'r1_baselines.json'), 'w') as f:
        json.dump(baselines, f, indent=2)

    elapsed = time.time() - t0
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n" + "=" * 70)
    print("  MWPM SOFT-INFO BASELINES (d=3, 3 rounds)")
    print("=" * 70)
    for name, b in baselines.items():
        print(f"  {name:20s}: p_L={b['mwpm_pL']:.4e} "
              f"({b['mwpm_errors']}/{b['mwpm_evaluated']})")

    print(f"\n  Files saved to {out_dir}/r1_*.npz")
    print("  Ready for FiLM-GKP decoder training (Phase 2)")


if __name__ == '__main__':
    main()
