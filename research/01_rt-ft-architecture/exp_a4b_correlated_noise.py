#!/usr/bin/env python3
"""
Exp-A4b: Correlated Noise Impact Analysis
==========================================

Correlated noise sources in TAROS CV architecture:
  1. Common pump RIN: amplitude noise shared across all OPA output modes
  2. WDM crosstalk: noise leakage between adjacent frequency channels
  3. TDM temporal correlation: phase drift between consecutive time slots

Model:
  δ_i = √(1-ρ) × ξ_i + √ρ × ξ_common
  where ξ_i ~ N(0, V_eff), ξ_common ~ N(0, V_eff)

  This preserves per-mode variance: Var(δ_i) = V_eff
  But introduces correlation: Cov(δ_i, δ_j) = ρ × V_eff

Design spec: ρ < 0.03 (RIN < -150 dB/Hz)

Sweep ρ = 0, 0.01, 0.03, 0.05, 0.10, 0.20
At Phase 1 and Phase 2+ Real, d=3,5, MR+Soft

seed=42
"""
import numpy as np
from scipy.special import erfc
import stim, pymatching, json, os, time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')

def compute_V_eff(sg, L, Vnl=0.010):
    V_sqz = 10**(-sg/10); eta = 10**(-L/10)
    return eta*V_sqz + (1-eta) + Vnl

def compute_p_phys(V):
    return float(erfc(SQRT_PI/(4*np.sqrt(V/2)))/2)

def extract_graph(d, rounds):
    c = stim.Circuit.generated('surface_code:rotated_memory_z',
        rounds=rounds, distance=d,
        before_round_data_depolarization=0.01,
        before_measure_flip_probability=0.01)
    dem = c.detector_error_model(decompose_errors=True)
    edges = []
    for inst in dem.flattened():
        if inst.type != 'error': continue
        dets, has_log = [], False
        for t in inst.targets_copy():
            if t.is_relative_detector_id(): dets.append(t.val)
            elif t.is_logical_observable_id(): has_log = True
        if len(dets)==1: edges.append({'n1':dets[0],'n2':None,'log':has_log})
        elif len(dets)==2: edges.append({'n1':dets[0],'n2':dets[1],'log':has_log})
    return edges, dem.num_detectors

def gkp_sample_correlated(n_edges, n_shots, V_eff, rho, rng):
    """
    Sample GKP displacement noise with inter-mode correlations.

    Model: δ_i = √(1-ρ) × ξ_i + √ρ × ξ_common
    - ξ_i: independent noise per edge
    - ξ_common: common noise shared across all edges in each shot
    - Preserves marginal variance V_eff per edge
    - Correlation between edges = ρ
    """
    sigma = np.sqrt(V_eff)

    if rho <= 0:
        # Independent noise (baseline)
        delta = sigma * rng.standard_normal((n_shots, n_edges))
    else:
        # Independent component
        indep = sigma * np.sqrt(1 - rho) * rng.standard_normal((n_shots, n_edges))
        # Common component (same for all edges in each shot)
        common = sigma * np.sqrt(rho) * rng.standard_normal((n_shots, 1))
        delta = indep + common  # broadcasts (n_shots, n_edges)

    # GKP decoding
    n_lattice = np.rint(delta / SQRT_PI).astype(np.int64)
    errors = (n_lattice % 2) != 0
    residual = delta - n_lattice * SQRT_PI
    r_abs = np.abs(residual)
    log_lr = np.clip(((SQRT_PI - r_abs)**2 - r_abs**2) / (2 * V_eff), -30, 30)

    return errors, log_lr

def run_correlated(d, V, ns, rng, rounds, rho, soft=True):
    edges, nd = extract_graph(d, rounds)
    ne = len(edges)

    errors, llr = gkp_sample_correlated(ne, ns, V, rho, rng)

    # Syndromes
    syn = np.zeros((ns, nd), dtype=np.uint8)
    obs = np.zeros(ns, dtype=np.uint8)
    for j, e in enumerate(edges):
        m = errors[:, j]; syn[m, e['n1']] ^= 1
        if e['n2'] is not None: syn[m, e['n2']] ^= 1
        if e['log']: obs[m] ^= 1

    # Matching matrix
    bnd = nd
    H = np.zeros((nd+1, ne), dtype=np.uint8)
    F = np.zeros((1, ne), dtype=np.uint8)
    for j, e in enumerate(edges):
        H[e['n1'], j] = 1
        if e['n2'] is not None: H[e['n2'], j] = 1
        else: H[bnd, j] = 1
        if e['log']: F[0, j] = 1

    nerr = 0
    if soft:
        for i in range(ns):
            w = np.maximum(llr[i], 0.01)
            m = pymatching.Matching(H, weights=w, faults_matrix=F)
            m.set_boundary_nodes({bnd})
            if m.decode(syn[i])[0] != obs[i]: nerr += 1
    else:
        p = compute_p_phys(V)
        uw = np.full(ne, max(-np.log(p/(1-p)), 0.01))
        m = pymatching.Matching(H, weights=uw, faults_matrix=F)
        m.set_boundary_nodes({bnd})
        for i in range(ns):
            if m.decode(syn[i])[0] != obs[i]: nerr += 1

    return {'d': d, 'rounds': rounds, 'rho': rho, 'pL': nerr/ns,
            'nerr': nerr, 'ns': ns, 'soft': soft}

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    print("=" * 70)
    print("  Exp-A4b: Correlated Noise (Common Pump RIN) Impact")
    print("=" * 70)

    rhos = [0.0, 0.01, 0.03, 0.05, 0.10, 0.20]
    phases = [
        ('Phase 1',       13.0, 0.39, 0.010),
        ('Phase 2+ Real', 13.0, 0.27, 0.010),
    ]

    all_results = []

    for name, sg, L, Vnl in phases:
        V = compute_V_eff(sg, L, Vnl)
        p = compute_p_phys(V)
        s = -10*np.log10(V)
        print(f"\n  {name}: σ_eff={s:.1f}dB, p_phys={p:.4e}")

        for rho in rhos:
            print(f"    ρ={rho:.2f}:")
            for d in [3, 5]:
                ns = {3: 20000, 5: 10000}[d]
                t1 = time.time()

                # MR + Soft (CV model)
                r_soft = run_correlated(d, V, ns, rng, rounds=d, rho=rho, soft=True)
                dt = time.time() - t1

                # MR + Hard (for comparison at ρ=0 and max ρ)
                r_hard = None
                if rho == 0 or rho == rhos[-1]:
                    r_hard = run_correlated(d, V, min(ns, 10000), rng,
                                           rounds=d, rho=rho, soft=False)

                pL_s = f"{r_soft['pL']:.2e}" if r_soft['pL'] > 0 else f"<{1/ns:.0e}"
                hard_str = ""
                if r_hard:
                    pL_h = f"{r_hard['pL']:.2e}" if r_hard['pL'] > 0 else f"<{1/r_hard['ns']:.0e}"
                    hard_str = f"  hard={pL_h}"

                print(f"      d={d}: soft={pL_s} ({r_soft['nerr']}/{ns}){hard_str} [{dt:.0f}s]")

                entry = {
                    'phase': name, 'rho': rho, 'd': d,
                    'sigma_eff': float(s), 'p_phys': float(p),
                    'soft': r_soft,
                }
                if r_hard:
                    entry['hard'] = r_hard
                all_results.append(entry)

    # Save
    with open(os.path.join(OUT_DIR, 'exp_a4b_results.json'), 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Saved results")

    # Plot
    try:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle('Exp-A4b: Correlated Noise Impact (Common Pump RIN)\n'
                     'GKP Multi-Round + Soft-Info MWPM',
                     fontsize=13, fontweight='bold')

        colors_d = {3: '#e74c3c', 5: '#2ecc71'}

        for ax_idx, phase in enumerate(['Phase 1', 'Phase 2+ Real']):
            ax = axes[ax_idx]
            for d in [3, 5]:
                subset = [r for r in all_results
                          if r['phase'] == phase and r['d'] == d]
                rs = [r['rho'] for r in subset]
                pLs = [r['soft']['pL'] if r['soft']['pL'] > 0
                       else 0.5/r['soft']['ns'] for r in subset]
                ax.semilogy(rs, pLs, '-o', color=colors_d[d],
                           lw=2, ms=8, label=f'd={d}')

            ax.axhline(1e-3, color='gray', ls=':', alpha=0.4, label='p_L=10⁻³')
            ax.axvline(0.03, color='orange', ls='--', alpha=0.5,
                      label='ρ=0.03 (design spec)')
            ax.set_xlabel('Correlation Coefficient ρ', fontsize=11)
            ax.set_ylabel('Logical Error Rate $p_L$', fontsize=11)
            ax.set_title(phase)
            ax.legend(fontsize=9)

        plt.tight_layout()
        path = os.path.join(OUT_DIR, 'fig_a4b_correlated.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Plot: {path}")
    except ImportError:
        pass

    elapsed = time.time() - t0
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY: Correlated Noise Impact")
    print("=" * 70)

    for phase in ['Phase 1', 'Phase 2+ Real']:
        print(f"\n  {phase}:")
        print(f"    {'ρ':>5}  {'d=3 p_L':>10}  {'d=5 p_L':>10}  {'d=3 ratio':>10}  {'d=5 ratio':>10}")

        # Get baseline (ρ=0)
        base3 = [r for r in all_results if r['phase']==phase and r['rho']==0 and r['d']==3]
        base5 = [r for r in all_results if r['phase']==phase and r['rho']==0 and r['d']==5]
        b3 = base3[0]['soft']['pL'] if base3 and base3[0]['soft']['pL'] > 0 else None
        b5 = base5[0]['soft']['pL'] if base5 and base5[0]['soft']['pL'] > 0 else None

        for rho in rhos:
            r3 = [r for r in all_results if r['phase']==phase and r['rho']==rho and r['d']==3]
            r5 = [r for r in all_results if r['phase']==phase and r['rho']==rho and r['d']==5]
            if r3 and r5:
                p3 = r3[0]['soft']['pL']
                p5 = r5[0]['soft']['pL']
                p3_s = f"{p3:.2e}" if p3 > 0 else f"<{1/r3[0]['soft']['ns']:.0e}"
                p5_s = f"{p5:.2e}" if p5 > 0 else f"<{1/r5[0]['soft']['ns']:.0e}"
                rat3 = f"{p3/b3:.1f}x" if (b3 and p3 > 0) else "-"
                rat5 = f"{p5/b5:.1f}x" if (b5 and p5 > 0) else "-"
                print(f"    {rho:5.2f}  {p3_s:>10}  {p5_s:>10}  {rat3:>10}  {rat5:>10}")

    # Critical assessment
    print("\n  Design spec: ρ < 0.03 (RIN < -150 dB/Hz)")
    for phase in ['Phase 1', 'Phase 2+ Real']:
        r_spec = [r for r in all_results
                  if r['phase']==phase and r['rho']==0.03 and r['d']==5]
        r_base = [r for r in all_results
                  if r['phase']==phase and r['rho']==0 and r['d']==5]
        if r_spec and r_base:
            p_s = r_spec[0]['soft']['pL']
            p_b = r_base[0]['soft']['pL']
            if p_s > 0 and p_b > 0:
                print(f"    {phase} d=5: ρ=0→{p_b:.2e}, ρ=0.03→{p_s:.2e}, "
                      f"degradation={p_s/p_b:.1f}x")
            elif p_s == 0 and p_b == 0:
                print(f"    {phase} d=5: both below detection — no significant impact")
            else:
                print(f"    {phase} d=5: ρ=0→{p_b}, ρ=0.03→{p_s}")

if __name__ == '__main__':
    main()
