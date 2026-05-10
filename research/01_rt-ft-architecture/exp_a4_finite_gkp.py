#!/usr/bin/env python3
"""
Exp-A4: Finite-Energy GKP Impact Analysis
==========================================
Δ > 0 adds extra noise: V_eff → V_eff + Δ²/2
Sweep Δ = 0, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20
At all 3 TAROS operating points, d=3,5,7, MR+Soft
"""
import numpy as np
from scipy.special import erfc
import stim, pymatching, json, os, time

SQRT_PI = np.sqrt(np.pi)
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')

def compute_V_eff(sg, L, Vnl=0.010, Delta=0.0):
    V_sqz = 10**(-sg/10); eta = 10**(-L/10)
    return eta*V_sqz + (1-eta) + Vnl + Delta**2/2

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

def run_gkp_mr_soft(d, V, ns, rng, rounds=None):
    if rounds is None: rounds = d
    edges, nd = extract_graph(d, rounds)
    ne = len(edges)
    sig = np.sqrt(V)
    delta = sig * rng.standard_normal((ns, ne))
    nl = np.rint(delta/SQRT_PI).astype(np.int64)
    errors = (nl%2)!=0
    res = delta - nl*SQRT_PI
    r_abs = np.abs(res)
    llr = np.clip(((SQRT_PI-r_abs)**2 - r_abs**2)/(2*V), -30, 30)
    syn = np.zeros((ns, nd), dtype=np.uint8)
    obs = np.zeros(ns, dtype=np.uint8)
    for j,e in enumerate(edges):
        m = errors[:,j]; syn[m,e['n1']]^=1
        if e['n2'] is not None: syn[m,e['n2']]^=1
        if e['log']: obs[m]^=1
    bnd = nd
    H = np.zeros((nd+1,ne),dtype=np.uint8)
    F = np.zeros((1,ne),dtype=np.uint8)
    for j,e in enumerate(edges):
        H[e['n1'],j]=1
        if e['n2'] is not None: H[e['n2'],j]=1
        else: H[bnd,j]=1
        if e['log']: F[0,j]=1
    nerr = 0
    for i in range(ns):
        w = np.maximum(llr[i], 0.01)
        m = pymatching.Matching(H, weights=w, faults_matrix=F)
        m.set_boundary_nodes({bnd})
        if m.decode(syn[i])[0]!=obs[i]: nerr+=1
    return nerr, ns

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    print("="*70)
    print("  Exp-A4: Finite-Energy GKP (Δ > 0) Impact")
    print("="*70)

    deltas = [0.0, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
    phases = [
        ('Phase 1',        13.0, 0.39, 0.010),
        ('Phase 2+ Real',  13.0, 0.27, 0.010),
    ]

    all_results = []

    for name, sg, L, Vnl in phases:
        print(f"\n  {name}:")
        for Delta in deltas:
            V = compute_V_eff(sg, L, Vnl, Delta)
            p = compute_p_phys(V)
            s = -10*np.log10(V)
            print(f"    Δ={Delta:.2f}: σ_eff={s:.1f}dB p_phys={p:.4e}")

            for d in [3, 5]:
                ns = {3: 20000, 5: 8000}[d]
                t1 = time.time()
                nerr, _ = run_gkp_mr_soft(d, V, ns, rng, rounds=d)
                dt = time.time() - t1
                pL = nerr/ns
                pL_s = f"{pL:.2e}" if pL > 0 else f"<{1/ns:.0e}"
                print(f"      d={d}: p_L={pL_s} ({nerr}/{ns}) [{dt:.0f}s]")
                all_results.append({
                    'phase': name, 'Delta': Delta, 'd': d,
                    'sigma_eff': float(s), 'p_phys': float(p),
                    'V_eff': float(V), 'p_L': float(pL),
                    'n_errors': nerr, 'n_shots': ns,
                })

    # Save
    with open(os.path.join(OUT_DIR, 'exp_a4_results.json'), 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Saved results")

    # Plot
    try:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle('Exp-A4: Finite-Energy GKP Impact on Logical Error Rate\n'
                     'GKP Multi-Round + Soft-Info MWPM', fontsize=13, fontweight='bold')
        colors_d = {3: '#e74c3c', 5: '#2ecc71'}
        for ax_idx, phase in enumerate(['Phase 1', 'Phase 2+ Real']):
            ax = axes[ax_idx]
            for d in [3, 5]:
                subset = [r for r in all_results if r['phase']==phase and r['d']==d]
                ds_vals = [r['Delta'] for r in subset]
                pLs = [r['p_L'] if r['p_L']>0 else 0.5/r['n_shots'] for r in subset]
                ax.semilogy(ds_vals, pLs, '-o', color=colors_d[d], lw=2, ms=8, label=f'd={d}')
            ax.axhline(1e-3, color='gray', ls=':', alpha=0.4, label='p_L=10⁻³')
            ax.axvline(0.15, color='orange', ls='--', alpha=0.5, label='Δ=0.15 (req)')
            ax.axvline(0.12, color='green', ls='--', alpha=0.5, label='Δ=0.12 (target)')
            ax.set_xlabel('GKP Finite Energy Parameter Δ', fontsize=11)
            ax.set_ylabel('Logical Error Rate $p_L$', fontsize=11)
            ax.set_title(phase)
            ax.legend(fontsize=9)
        plt.tight_layout()
        path = os.path.join(OUT_DIR, 'fig_a4_finite_gkp.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Plot: {path}")
    except ImportError:
        pass

    elapsed = time.time() - t0
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Summary
    print("\n" + "="*70)
    print("  SUMMARY: Δ Impact")
    print("="*70)
    for phase in ['Phase 1', 'Phase 2+ Real']:
        print(f"\n  {phase}:")
        print(f"    {'Δ':>5} {'σ_eff':>7} {'p_phys':>10} {'d=3 p_L':>10} {'d=5 p_L':>10}")
        for Delta in deltas:
            r3 = [r for r in all_results if r['phase']==phase and r['Delta']==Delta and r['d']==3]
            r5 = [r for r in all_results if r['phase']==phase and r['Delta']==Delta and r['d']==5]
            if r3 and r5:
                p3 = f"{r3[0]['p_L']:.2e}" if r3[0]['p_L']>0 else f"<{1/r3[0]['n_shots']:.0e}"
                p5 = f"{r5[0]['p_L']:.2e}" if r5[0]['p_L']>0 else f"<{1/r5[0]['n_shots']:.0e}"
                print(f"    {Delta:5.2f} {r3[0]['sigma_eff']:6.1f}dB {r3[0]['p_phys']:10.4e} {p3:>10} {p5:>10}")

if __name__ == '__main__':
    main()
