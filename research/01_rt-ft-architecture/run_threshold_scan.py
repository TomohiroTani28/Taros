#!/usr/bin/env python3
"""
Threshold scan: p_L vs d at multiple sigma_eff (MR+Soft)
=========================================================
Produces crossing plot for threshold determination.
6 operating points x d={3,5} x MR+Soft.
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

def run_mr_soft(d, V, ns, rng):
    edges, nd = extract_graph(d, d)
    ne = len(edges)
    sig = np.sqrt(V)
    delta = sig * rng.standard_normal((ns, ne))
    nl = np.rint(delta/SQRT_PI).astype(np.int64)
    errors = (nl%2)!=0
    res = delta - nl*SQRT_PI
    r_abs = np.abs(res)
    llr = np.clip(((SQRT_PI-r_abs)**2-r_abs**2)/(2*V), -30, 30)
    syn = np.zeros((ns,nd), dtype=np.uint8)
    obs = np.zeros(ns, dtype=np.uint8)
    for j,e in enumerate(edges):
        m=errors[:,j]; syn[m,e['n1']]^=1
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
    print("  Threshold Scan: MR+Soft, multiple sigma_eff")
    print("="*70)

    # 6 loss points spanning below/above threshold
    scan_points = [
        (0.15, 0.010),  # sigma_eff ~ 10.8 dB (well below threshold)
        (0.27, 0.010),  # sigma_eff ~ 9.3 dB
        (0.39, 0.010),  # sigma_eff ~ 8.5 dB (Phase 1)
        (0.50, 0.010),  # sigma_eff ~ 7.9 dB
        (0.70, 0.010),  # sigma_eff ~ 7.0 dB (near threshold)
        (1.00, 0.010),  # sigma_eff ~ 5.9 dB (above threshold)
    ]

    results = []
    for L, Vnl in scan_points:
        V = compute_V_eff(13.0, L, Vnl)
        p = compute_p_phys(V)
        s = -10*np.log10(V)
        print(f"\n  L={L:.2f}dB, sigma_eff={s:.1f}dB, p_phys={p:.4e}")

        for d in [3, 5]:
            # Adaptive shot count
            if p < 0.003:
                ns = 50000
            elif p < 0.01:
                ns = 30000
            else:
                ns = 20000

            t1 = time.time()
            nerr, _ = run_mr_soft(d, V, ns, rng)
            dt = time.time()-t1
            pL = nerr/ns
            pL_s = f"{pL:.3e}" if pL>0 else f"<{1/ns:.1e}"
            print(f"    d={d}: p_L={pL_s} ({nerr}/{ns}) [{dt:.0f}s]")

            results.append({
                'L_dB': L, 'sigma_eff_dB': float(s),
                'p_phys': float(p), 'V_eff': float(V),
                'd': d, 'p_L': float(pL),
                'n_errors': nerr, 'n_shots': ns,
            })

    # Save
    with open(os.path.join(OUT_DIR, 'threshold_scan.json'), 'w') as f:
        json.dump(results, f, indent=2)

    # Plot
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 6))
        colors = {3: '#e74c3c', 5: '#2ecc71'}
        for d in [3, 5]:
            sub = [r for r in results if r['d']==d and r['p_L']>0]
            if sub:
                seff = [r['sigma_eff_dB'] for r in sub]
                pL = [r['p_L'] for r in sub]
                ax.semilogy(seff, pL, '-o', color=colors[d], lw=2.5, ms=9,
                           label=f'd={d}', zorder=3)
                for s, p, r in zip(seff, pL, sub):
                    ax.annotate(f"{r['n_errors']}", (s, p),
                               textcoords='offset points', xytext=(8,0),
                               fontsize=8, color='gray')

        ax.axhline(1e-3, color='gray', ls=':', alpha=0.5, label='$10^{-3}$ threshold')
        ax.set_xlabel('Effective squeezing $\\sigma_{eff}$ (dB)', fontsize=12)
        ax.set_ylabel('Logical error rate $p_L$', fontsize=12)
        ax.set_title('Threshold Scan: MR+Soft (CV-motivated model)\n'
                     '$\\sigma_{gen}=13$ dB, $d$ rounds, soft-info MWPM',
                     fontsize=12, fontweight='bold')
        ax.legend(fontsize=11)
        ax.invert_xaxis()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, 'fig_threshold_scan.png'),
                    dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n  Plot saved: results/fig_threshold_scan.png")
    except ImportError:
        print("  matplotlib not available")

    elapsed = time.time()-t0
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

if __name__ == '__main__':
    main()
