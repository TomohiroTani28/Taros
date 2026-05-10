#!/usr/bin/env python3
"""
R1 GNN Enhanced: Correlated-aware MWPM baseline + ρ→physical noise mapping
============================================================================

Two additions to elevate the research:
  (a) Correlated MWPM baseline: adjusts edge weights using estimated ρ,
      giving MWPM the "best possible" classical baseline under correlation.
  (b) ρ → physical noise budget mapping: connects abstract correlation
      strength to concrete photonic noise sources (pump RIN, WDM crosstalk).

This runs as a post-analysis on existing r1_gnn_lite_results.json +
additional correlated MWPM runs for comparison.

seed=42
"""
import gc
import numpy as np
from scipy.special import erfc
import stim, pymatching
import json, os, time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')


# ============================================================
# (b) ρ → Physical Noise Budget Mapping
# ============================================================

def rho_physical_mapping():
    """
    Map correlation coefficient ρ to physical noise sources in TAROS.

    Returns dict with ρ values and their physical interpretations.

    Physical sources of inter-mode correlation:
    1. Pump RIN (Relative Intensity Noise):
       - OPA gain fluctuation δG/G ∝ pump power fluctuation δP/P
       - All modes from same OPA share pump → correlated gain noise
       - ρ_RIN ≈ (δG/G)² / V_eff ≈ RIN × BW × G² / V_eff
       - Design spec: RIN < -150 dB/Hz, BW = 100 MHz
       - → ρ_RIN ≈ 10^(-15) × 10^8 × (20)² / 0.14 ≈ 3×10⁻⁴

    2. WDM crosstalk:
       - Adjacent channel leakage through FP etalon filter
       - Isolation ~30 dB → power leakage 10⁻³
       - ρ_WDM ≈ 10⁻³ × (nearest-neighbor only)

    3. Thermal drift (slow):
       - Phase drift shared across fiber paths
       - ρ_thermal ≈ 0.01-0.05 on timescales > 1s
       - PLL BW ≥ 500 kHz suppresses to < 10⁻³ for QEC-relevant timescales

    4. TDM temporal correlation:
       - Consecutive time slots share OPA pump state
       - ρ_TDM ≈ ρ_RIN × autocorrelation at Δt = 10ns
       - For RIN corner freq ~1 MHz: ρ_TDM ≈ ρ_RIN × 0.99 ≈ ρ_RIN

    Combined: ρ_total ≈ √(ρ_RIN² + ρ_WDM² + ρ_thermal² + ρ_TDM²)
    """
    mapping = {
        0.00: {
            'label': 'Ideal (independent)',
            'physical': 'No correlations; theoretical baseline',
            'achievable': True,
        },
        0.001: {
            'label': 'Shot-noise limited',
            'physical': 'RIN < -160 dB/Hz, no WDM crosstalk',
            'achievable': True,  # With high-quality laser
        },
        0.003: {
            'label': 'Design spec (RIN-limited)',
            'physical': 'RIN = -150 dB/Hz, WDM isolation 30dB, PLL BW ≥ 500kHz',
            'achievable': True,  # TAROS Phase 1 target
        },
        0.01: {
            'label': 'Moderate (WDM-limited)',
            'physical': 'WDM isolation 20dB or RIN = -140 dB/Hz',
            'achievable': True,  # Achievable with care
        },
        0.03: {
            'label': 'Design spec boundary',
            'physical': 'ρ_RIN + ρ_WDM combined; upper bound of spec',
            'achievable': True,  # Edge of design spec
        },
        0.05: {
            'label': 'Degraded (thermal drift)',
            'physical': 'PLL BW < 100kHz or WDM isolation < 15dB',
            'achievable': True,  # Below spec but physically plausible
        },
        0.08: {
            'label': 'GNN crossover (d=3)',
            'physical': 'Multiple degraded subsystems; ~500Hz PLL BW or RIN=-130dB/Hz',
            'achievable': True,  # Stressed but recoverable
        },
        0.10: {
            'label': 'Significant correlation',
            'physical': 'Pump RIN=-125dB/Hz or shared thermal drift >0.5°',
            'achievable': True,  # Needs attention
        },
        0.15: {
            'label': 'High correlation',
            'physical': 'Multi-pump RIN or broadband thermal instability',
            'achievable': False,  # Outside normal operating range
        },
        0.20: {
            'label': 'FT boundary',
            'physical': 'System-level failure; FT collapse per Exp-A4b',
            'achievable': False,
        },
    }
    return mapping


def rin_to_rho(rin_dbhz, bw_hz=1e8, gain=20, v_eff=0.1417):
    """Convert pump RIN (dB/Hz) to correlation coefficient ρ.

    Args:
        rin_dbhz: RIN in dB/Hz (e.g., -150)
        bw_hz: measurement bandwidth (default 100 MHz = TDM clock)
        gain: OPA parametric gain (linear, ~13dB → 20)
        v_eff: effective noise variance (Phase 1)
    """
    rin_linear = 10**(rin_dbhz / 10)
    # Gain fluctuation variance: δG² = RIN × BW × G²
    delta_g_sq = rin_linear * bw_hz * gain**2
    # Correlation: shared gain noise / total noise
    rho = delta_g_sq / v_eff
    return min(rho, 1.0)


def wdm_isolation_to_rho(isolation_db, n_neighbors=2):
    """Convert WDM channel isolation to correlation coefficient.

    Args:
        isolation_db: channel isolation in dB (e.g., 30)
        n_neighbors: number of adjacent channels contributing
    """
    leakage = 10**(-isolation_db / 10)
    return leakage * n_neighbors


# ============================================================
# (a) Correlated-aware MWPM
# ============================================================

def gkp_correlated(ne, ns, V, rho, rng):
    """Sample GKP noise with inter-mode correlation."""
    sig = np.sqrt(V)
    if rho <= 0:
        d = sig * rng.standard_normal((ns, ne))
    else:
        d = sig * (np.sqrt(1-rho) * rng.standard_normal((ns, ne)) +
                   np.sqrt(rho) * rng.standard_normal((ns, 1)))
    nl = np.rint(d / SQRT_PI).astype(np.int64)
    err = (nl % 2) != 0
    res = d - nl * SQRT_PI
    ra = np.abs(res)
    llr = np.clip(((SQRT_PI - ra)**2 - ra**2) / (2*V), -30, 30)
    return err, res.astype(np.float32), llr.astype(np.float32)


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


def mwpm_decode(syn, obs, weights, edges, nd):
    """Standard MWPM with per-sample weights."""
    ns, ne = syn.shape[0], len(edges)
    H = np.zeros((nd+1, ne), dtype=np.uint8)
    Fm = np.zeros((1, ne), dtype=np.uint8)
    for j, e in enumerate(edges):
        H[e['n1'], j] = 1
        if e['n2'] is not None:
            H[e['n2'], j] = 1
        else:
            H[nd, j] = 1
        if e['log']:
            Fm[0, j] = 1
    errs = np.zeros(ns, dtype=np.uint8)
    for i in range(ns):
        ww = np.maximum(weights[i], 0.01)
        m = pymatching.Matching(H, weights=ww, faults_matrix=Fm)
        m.set_boundary_nodes({nd})
        if m.decode(syn[i])[0] != obs[i]:
            errs[i] = 1
    return errs


def correlated_mwpm_weights(llr, rho, V_eff):
    """
    Adjust MWPM weights to account for known correlation structure.

    Under correlated noise with known ρ, the optimal weight adjustment is:
    - Estimate common noise component from sample mean of residuals
    - Subtract estimated common component
    - Recompute LLR from corrected residuals

    This gives MWPM the "best possible" classical correction for ρ.
    """
    ns, ne = llr.shape

    if rho <= 0:
        return llr

    # The key insight: under the correlated model δ_i = √(1-ρ)ξ_i + √ρ ξ_c,
    # the MMSE estimate of ξ_c given all δ_i is:
    #   ξ_c_hat = (ρ / (1 - ρ + ne*ρ)) × Σ_i δ_i / √V_eff
    # However, we only have residuals r_i (after GKP lattice decoding),
    # not the raw displacements δ_i. So we estimate from residuals:
    #   ξ_c_hat ≈ mean(r_i) × √ρ × ne / (1 - ρ + ne*ρ)
    # This is a partial correction — the lattice decoding information loss
    # limits how well we can estimate ξ_c.

    # Correction factor for common mode
    alpha = np.sqrt(rho) * ne / (1 - rho + ne * rho)

    # We can't directly access residuals from LLR, but we can adjust
    # the weights by the expected correlation-induced variance reduction.
    # The effective per-edge variance after common-mode subtraction:
    #   V_corrected = V_eff × (1 - ρ²×ne/(1-ρ+ne×ρ))
    # This translates to a scale factor on LLR:
    v_ratio = 1 - rho**2 * ne / (1 - rho + ne * rho)
    corrected_llr = llr / v_ratio  # Sharper weights

    return corrected_llr


def correlated_mwpm_residual(res, llr, rho, V_eff):
    """
    Full residual-based correlated MWPM.

    Uses the actual GKP residuals to estimate and subtract the common
    noise component, then recomputes LLR from corrected residuals.
    This is the strongest classical baseline — it directly exploits
    knowledge of ρ in the decoding.
    """
    ns, ne = res.shape

    if rho <= 0:
        return llr

    # Estimate common component from residual mean per shot
    r_mean = res.mean(axis=1, keepdims=True)  # (ns, 1)

    # MMSE estimate of common noise
    # Under model: r_i ≈ √(1-ρ)ξ_i + √ρ ξ_c (mod √π lattice)
    # Best linear estimate: ξ_c_hat = √ρ × r_mean × ne / (1-ρ+ne×ρ)
    weight = np.sqrt(rho) * ne / (1 - rho + ne * rho)
    common_hat = weight * r_mean / ne  # per-mode contribution

    # Corrected residuals
    res_corrected = res - np.sqrt(rho) * common_hat
    ra = np.abs(res_corrected)

    # Effective variance after correction
    v_corr = V_eff * (1 - rho**2 * ne / (1 - rho + ne * rho))
    v_corr = max(v_corr, 1e-6)

    # Recompute LLR from corrected residuals
    llr_new = np.clip(((SQRT_PI - ra)**2 - ra**2) / (2 * v_corr), -30, 30)
    return llr_new.astype(np.float32)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    V = 0.1417  # Phase 1 (σ_eff=8.5dB)
    rho_list = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15]
    results = {}

    print("=" * 70)
    print("  R1 GNN Enhanced: Correlated MWPM baseline + ρ mapping")
    print("=" * 70)

    # --- (b) Print ρ → physical mapping ---
    print("\n" + "=" * 70)
    print("  (b) ρ → Physical Noise Budget Mapping")
    print("=" * 70)

    mapping = rho_physical_mapping()
    print(f"\n  {'ρ':>6}  {'Label':<30} {'Physical source'}")
    print("  " + "-" * 80)
    for rho_val in sorted(mapping.keys()):
        m = mapping[rho_val]
        print(f"  {rho_val:6.3f}  {m['label']:<30} {m['physical'][:50]}")

    # RIN examples
    print("\n  RIN → ρ conversion (BW=100MHz, G=20, V_eff=0.14):")
    for rin in [-160, -155, -150, -145, -140, -135, -130, -125]:
        rho_val = rin_to_rho(rin)
        print(f"    RIN={rin} dB/Hz → ρ = {rho_val:.4e}")

    # WDM examples
    print("\n  WDM isolation → ρ conversion (2 neighbors):")
    for iso in [40, 35, 30, 25, 20, 15]:
        rho_val = wdm_isolation_to_rho(iso)
        print(f"    Isolation={iso} dB → ρ = {rho_val:.4e}")

    # --- (a) Correlated MWPM baseline ---
    print("\n" + "=" * 70)
    print("  (a) Correlated-aware MWPM vs Standard MWPM vs GNN")
    print("=" * 70)

    for d in [3, 5]:
        rounds = d
        edges, nd = extract_graph(d, rounds)
        ne = len(edges)

        n_test = 10000 if d == 3 else 5000

        print(f"\n  d={d}, {ne} DEM edges")
        print(f"  {'ρ':>5} {'MWPM-std':>12} {'MWPM-corr':>12} {'Improve':>8} {'GNN(ref)':>12}")
        print("  " + "-" * 55)

        for rho in rho_list:
            err, res, llr = gkp_correlated(ne, n_test, V, rho, rng)
            syn, obs = compute_syndromes(err, edges, nd)

            # Standard MWPM (soft-info, ignores correlation)
            t1 = time.time()
            std_errs = mwpm_decode(syn, obs, llr, edges, nd)
            dt_std = time.time() - t1
            std_pl = std_errs.sum() / n_test

            # Correlated MWPM (residual-based common-mode subtraction)
            llr_corr = correlated_mwpm_residual(res, llr, rho, V)
            t1 = time.time()
            corr_errs = mwpm_decode(syn, obs, llr_corr, edges, nd)
            dt_corr = time.time() - t1
            corr_pl = corr_errs.sum() / n_test

            improve = std_pl / corr_pl if corr_pl > 0 else float('inf')

            # Load GNN result for reference
            gnn_ref = "—"
            try:
                with open(os.path.join(OUT_DIR, 'r1_gnn_lite_results.json')) as f:
                    gnn_data = json.load(f)
                key = f'd{d}_rho{rho:.2f}'
                if key in gnn_data:
                    gnn_ref = f"{gnn_data[key]['gnn_pL']:.4e}"
            except FileNotFoundError:
                pass

            print(f"  {rho:5.2f} {std_pl:12.4e} {corr_pl:12.4e} {improve:7.2f}× {gnn_ref:>12}")

            results[f'd{d}_rho{rho:.2f}'] = {
                'd': d, 'rho': rho,
                'mwpm_std_pL': float(std_pl),
                'mwpm_corr_pL': float(corr_pl),
                'improve_factor': float(improve),
                'n_test': n_test,
            }

    # Save results
    out_path = os.path.join(OUT_DIR, 'r1_enhanced_results.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to {out_path}")

    # Save physical mapping as JSON
    map_path = os.path.join(OUT_DIR, 'r1_rho_physical_mapping.json')
    with open(map_path, 'w') as f:
        json.dump({str(k): v for k, v in rho_physical_mapping().items()}, f, indent=2)
    print(f"  Physical mapping saved to {map_path}")

    elapsed = time.time() - t0
    print(f"\n  Total time: {elapsed:.0f}s ({elapsed/60:.1f}min)")


if __name__ == '__main__':
    main()
