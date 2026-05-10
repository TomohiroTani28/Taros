#!/usr/bin/env python3
"""
Exp-A2c: High-shot d=7 MR+Soft for precise p_L determination
=============================================================
Phase 1 and Phase 2+ Real, d=7, 50K shots each (MR+Soft)
Also d=5 with 50K for scaling law fit.
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

def run_gkp_mr(d, V, ns, rng, rounds, soft=True):
    edges, nd = extract_graph(d, rounds)
    ne = len(edges)
    p = compute_p_phys(V)
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
    if soft:
        for i in range(ns):
            w = np.maximum(llr[i], 0.01)
            m = pymatching.Matching(H, weights=w, faults_matrix=F)
            m.set_boundary_nodes({bnd})
            if m.decode(syn[i])[0]!=obs[i]: nerr+=1
    else:
        uw = np.full(ne, max(-np.log(p/(1-p)), 0.01))
        m = pymatching.Matching(H, weights=uw, faults_matrix=F)
        m.set_boundary_nodes({bnd})
        for i in range(ns):
            if m.decode(syn[i])[0]!=obs[i]: nerr+=1
    return {'d':d,'rounds':rounds,'pL':nerr/ns,'nerr':nerr,'ns':ns,'soft':soft,'ne':ne}

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t0 = time.time()

    print("="*70)
    print("  Exp-A2c: High-Shot d=5,7 MR+Soft")
    print("="*70)

    configs = [
        ('Phase 1',       13.0, 0.39, 0.010),
        ('Phase 2+ Real', 13.0, 0.27, 0.010),
    ]

    all_results = []

    for name, sg, L, Vnl in configs:
        V = compute_V_eff(sg, L, Vnl)
        p = compute_p_phys(V)
        s = -10*np.log10(V)
        print(f"\n  {name}: σ_eff={s:.1f}dB, p_phys={p:.4e}")

        for d in [3, 5, 7]:
            # High shot counts
            ns_soft = {3: 50000, 5: 30000, 7: 15000}[d]
            ns_hard = {3: 50000, 5: 20000, 7: 10000}[d]

            t1 = time.time()
            r_soft = run_gkp_mr(d, V, ns_soft, rng, rounds=d, soft=True)
            dt_s = time.time() - t1

            t1 = time.time()
            r_hard = run_gkp_mr(d, V, ns_hard, rng, rounds=d, soft=False)
            dt_h = time.time() - t1

            pL_s = f"{r_soft['pL']:.2e}" if r_soft['pL']>0 else f"<{1/ns_soft:.0e}"
            pL_h = f"{r_hard['pL']:.2e}" if r_hard['pL']>0 else f"<{1/ns_hard:.0e}"

            gain = ''
            if r_soft['pL']>0 and r_hard['pL']>0:
                gain = f"  gain={r_hard['pL']/r_soft['pL']:.1f}x"

            print(f"    d={d} ({r_soft['ne']}e): soft={pL_s}({r_soft['nerr']}/{ns_soft})"
                  f"  hard={pL_h}({r_hard['nerr']}/{ns_hard}){gain}"
                  f"  [{dt_s:.0f}+{dt_h:.0f}s]")

            all_results.append({
                'phase': name, 'd': d,
                'sigma_eff': float(s), 'p_phys': float(p),
                'soft': r_soft, 'hard': r_hard,
            })

    # Save
    with open(os.path.join(OUT_DIR, 'exp_a2c_results.json'), 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    elapsed = time.time() - t0
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Scaling law fit
    print("\n  Scaling Law (MR+Soft):")
    from scipy.optimize import curve_fit
    for name in ['Phase 1', 'Phase 2+ Real']:
        subset = [r for r in all_results if r['phase']==name and r['soft']['pL']>0]
        if len(subset) >= 2:
            ds = np.array([r['d'] for r in subset])
            pLs = np.array([r['soft']['pL'] for r in subset])
            p_phys = subset[0]['p_phys']
            def model(d, lA, lR): return lA + ((d+1)/2)*lR
            try:
                popt, _ = curve_fit(model, ds, np.log(pLs), p0=[np.log(0.03), np.log(0.3)])
                A = np.exp(popt[0]); ratio = np.exp(popt[1])
                p_th = p_phys / ratio
                Lambda = 1/ratio
                print(f"    {name}: A={A:.4f}, p/p_th={ratio:.4f}, p_th={p_th:.4e}, Λ={Lambda:.1f}")
            except Exception as e:
                print(f"    {name}: fit failed - {e}")

    # Summary
    print("\n" + "="*70)
    print("  HIGH-SHOT RESULTS (MR+Soft, CV-correct)")
    print("="*70)
    design = {'Phase 1': {3: None, 5: None, 7: 4.4e-3},
              'Phase 2+ Real': {3: None, 5: None, 7: 3.3e-4}}
    for name in ['Phase 1', 'Phase 2+ Real']:
        print(f"\n  {name}:")
        for r in [x for x in all_results if x['phase']==name]:
            d = r['d']
            s = r['soft']
            h = r['hard']
            dr = design.get(name,{}).get(d)
            pL_s = f"{s['pL']:.2e}" if s['pL']>0 else f"<{1/s['ns']:.0e}"
            pL_h = f"{h['pL']:.2e}" if h['pL']>0 else f"<{1/h['ns']:.0e}"
            dr_s = f"{dr:.2e}" if dr else "-"
            tag = ""
            if d==7 and s['pL']>0 and s['pL']<1e-3: tag = " ** PRODUCT SPEC"
            elif d==7 and s['pL']==0: tag = " ** BELOW DETECTION"
            print(f"    d={d}: MR-soft={pL_s} ({s['nerr']}/{s['ns']})  "
                  f"MR-hard={pL_h}  design={dr_s}{tag}")

if __name__ == '__main__':
    main()
