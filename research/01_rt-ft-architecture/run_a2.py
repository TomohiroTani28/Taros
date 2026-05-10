#!/usr/bin/env python3
"""
Run Exp-A2 with practical shot counts (~15-25 min on Apple Silicon).
Reduced from full spec to ensure completion. Increase shots for publication.
"""
import numpy as np
import json
import os
import time
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp_a2_distance_scaling import (
    compute_V_eff, compute_sigma_eff, compute_p_phys,
    run_single, fit_scaling_law, OPERATING_POINTS, SQRT_PI, OUT_DIR
)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    t_start = time.time()

    print("=" * 70)
    print("  Exp-A2: Distance Scaling — Practical Run")
    print("=" * 70)

    distances = [3, 5, 7, 9]

    # Practical shot counts (balance stats vs time)
    SHOT_TABLE = {
        # (phase_idx, d) -> n_shots
        # Phase 1: high p_phys, errors appear quickly
        (0, 3): 100_000, (0, 5): 100_000, (0, 7): 100_000, (0, 9): 50_000,
        # Phase 2+ Real: medium p_phys
        (1, 3): 100_000, (1, 5): 200_000, (1, 7): 200_000, (1, 9): 100_000,
        # Phase 2+ Limit: low p_phys, need many shots
        (2, 3): 200_000, (2, 5): 500_000, (2, 7): 500_000, (2, 9): 200_000,
    }

    all_results = {}
    all_raw = []

    for phase_idx, (name, params) in enumerate(OPERATING_POINTS.items()):
        V_eff = compute_V_eff(params['sigma_gen'], params['L_dB'], params['V_nl'])
        sigma_eff = compute_sigma_eff(V_eff)
        p_phys = compute_p_phys(V_eff)

        print(f"\n{'='*50}")
        print(f"  {name}")
        print(f"  σ_eff={sigma_eff:.1f}dB  p_phys={p_phys:.4e}")
        print(f"{'='*50}")

        point_results = []
        for d in distances:
            n_shots = SHOT_TABLE[(phase_idx, d)]
            t0 = time.time()

            r_soft = run_single(d, V_eff, n_shots, rng, use_soft_info=True)
            dt = time.time() - t0

            # Also hard-decision at d=3 for ratio
            r_hard = None
            if d == 3:
                r_hard = run_single(d, V_eff, min(n_shots, 50_000), rng, use_soft_info=False)

            p_L_str = f"{r_soft['p_L']:.2e}" if r_soft['p_L'] > 0 else f"<{1/n_shots:.1e}"
            ratio_str = ""
            if r_hard and r_soft['p_L'] > 0:
                ratio_str = f"  hard/soft={r_hard['p_L']/r_soft['p_L']:.1f}x"

            status = ""
            if d == 7:
                if 0 < r_soft['p_L'] < 1e-3:
                    status = " ** PRODUCT SPEC"
                elif 0 < r_soft['p_L'] < 0.01:
                    status = " * break-even"

            print(f"  d={d}: p_L={p_L_str} ({r_soft['n_errors']:,}/{n_shots:,})"
                  f"{ratio_str}  [{dt:.1f}s]{status}")

            point_results.append({'soft': r_soft, 'hard': r_hard})
            all_raw.append({**r_soft, 'phase': name})

        all_results[name] = {
            'params': {
                'sigma_gen': params['sigma_gen'],
                'L_dB': params['L_dB'],
                'V_nl': params['V_nl'],
                'V_eff': float(V_eff),
                'sigma_eff_dB': float(sigma_eff),
                'p_phys': float(p_phys),
            },
            'distances': point_results,
        }

    # Scaling law fit
    fits = fit_scaling_law(all_results)

    # Threshold sweep (abbreviated)
    print("\n" + "=" * 70)
    print("  Threshold Sweep (abbreviated)")
    print("=" * 70)

    threshold_results = []
    for L_dB in [0.10, 0.15, 0.20, 0.27, 0.35, 0.50, 0.70, 1.00]:
        V = compute_V_eff(13.0, L_dB, 0.010)
        p = compute_p_phys(V)
        if p > 0.08:
            continue
        s = compute_sigma_eff(V)
        print(f"\n  L={L_dB:.2f}dB  σ_eff={s:.1f}dB  p_phys={p:.4e}")

        for d in [3, 5, 7]:
            ns = 50_000 if p > 0.005 else 100_000
            t0 = time.time()
            r = run_single(d, V, ns, rng, use_soft_info=True)
            dt = time.time() - t0
            p_L_str = f"{r['p_L']:.2e}" if r['p_L'] > 0 else f"<{1/ns:.1e}"
            print(f"    d={d}: p_L={p_L_str} ({r['n_errors']}/{ns})  [{dt:.1f}s]")
            threshold_results.append({**r, 'L_dB': L_dB, 'sigma_eff_dB': float(s)})

    # Save
    save_data = {
        'exp_a2': {k: v for k, v in all_results.items()},
        'threshold': threshold_results,
        'fits': fits,
        'metadata': {
            'seed': 42,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_shots': sum(r['n_shots'] for r in all_raw),
        },
    }
    json_path = os.path.join(OUT_DIR, 'exp_a2_results.json')
    with open(json_path, 'w') as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\n  Saved: {json_path}")

    # Design verification
    print("\n" + "=" * 70)
    print("  Design Document Verification")
    print("=" * 70)
    expected = {
        'Phase 1 (L=0.39dB)': {'p_L_d7': 4.4e-3},
        'Phase 2+ Real (L=0.27dB)': {'p_L_d7': 3.3e-4},
        'Phase 2+ Limit (L=0.15dB)': {'p_L_d7': 6.1e-7},
    }
    for name, data in all_results.items():
        for entry in data['distances']:
            r = entry['soft']
            if r['d'] == 7 and name in expected:
                e = expected[name]['p_L_d7']
                if r['p_L'] > 0:
                    ratio = r['p_L'] / e
                    match = "MATCH" if 0.1 < ratio < 10 else "CHECK"
                    print(f"  {name}: design={e:.2e}, sim={r['p_L']:.2e}, ratio={ratio:.2f} [{match}]")
                else:
                    print(f"  {name}: design={e:.2e}, sim=0 (need more shots)")

    # Plot
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        fig.suptitle('TAROS Theme 1: Room-Temperature FT Photonic Architecture\n'
                     'Exp-A2 — Code Distance Scaling (Soft-Info MWPM, seed=42)',
                     fontsize=14, fontweight='bold')

        for ax_idx, (name, data) in enumerate(all_results.items()):
            ax = axes[ax_idx]
            params = data['params']
            color = list(OPERATING_POINTS.values())[ax_idx]['color']

            ds, pLs, errs = [], [], []
            for entry in data['distances']:
                r = entry['soft']
                ds.append(r['d'])
                pLs.append(r['p_L'] if r['p_L'] > 0 else 0.5/r['n_shots'])
                errs.append(r['n_errors'])

            ax.semilogy(ds, pLs, '-o', color=color, lw=2.5, ms=9, zorder=3)

            # Fit line
            short = name.split('(')[0].strip()
            if name in fits:
                f = fits[name]
                dd = np.linspace(2.5, 9.5, 50)
                ax.semilogy(dd, f['A'] * f['p_ratio']**((dd+1)/2),
                            '--', color=color, alpha=0.4, lw=1.5,
                            label=f'Fit: A={f["A"]:.3f}, Λ={f["Lambda"]:.1f}')

            for i, (d, pL, ne) in enumerate(zip(ds, pLs, errs)):
                label = f'{ne}' if ne > 0 else '0'
                ax.annotate(label, (d, pL), textcoords='offset points',
                            xytext=(8, 0), fontsize=8, color='gray')

            ax.axhline(1e-3, color='gray', ls=':', alpha=0.4)
            ax.axhline(pLs[0]*0 + params['p_phys'], color='red', ls='--', alpha=0.2,
                       label=f'p_phys={params["p_phys"]:.2e}')

            ax.set_xlabel('Code Distance d', fontsize=11)
            ax.set_ylabel('Logical Error Rate $p_L$', fontsize=11)
            ax.set_title(f'{short}\nσ_eff={params["sigma_eff_dB"]:.1f}dB', fontsize=11)
            ax.set_xticks([3, 5, 7, 9])
            ax.legend(fontsize=8)
            ax.set_ylim(bottom=max(1e-8, min(pLs)*0.1))

        plt.tight_layout()
        path = os.path.join(OUT_DIR, 'fig_a2_distance_scaling.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n  Plot saved: {path}")

        # Threshold plot
        if threshold_results:
            fig, ax = plt.subplots(figsize=(9, 6))
            colors_d = {3: '#e74c3c', 5: '#f39c12', 7: '#2ecc71'}
            for d in [3, 5, 7]:
                subset = [r for r in threshold_results if r['d'] == d and r['p_L'] > 0]
                if subset:
                    pp = [r['p_phys'] for r in subset]
                    pL = [r['p_L'] for r in subset]
                    ax.loglog(pp, pL, '-o', color=colors_d[d], lw=2, ms=7, label=f'd={d}')

            pp_ref = np.logspace(-4, -1, 50)
            ax.loglog(pp_ref, pp_ref, 'k--', alpha=0.2, label='p_L = p_phys')
            ax.set_xlabel('Physical Error Rate $p_{phys}$')
            ax.set_ylabel('Logical Error Rate $p_L$')
            ax.set_title('Threshold Crossing (σ_gen=13dB, Soft-Info MWPM)')
            ax.legend()
            plt.tight_layout()
            path = os.path.join(OUT_DIR, 'fig_a2b_threshold.png')
            fig.savefig(path, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"  Plot saved: {path}")

    except ImportError:
        print("  matplotlib not available — skipping plots")

    elapsed = time.time() - t_start
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"  Total shots: {sum(r['n_shots'] for r in all_raw):,}")

    # Final summary
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)
    for name, data in all_results.items():
        params = data['params']
        print(f"\n  {name} (σ_eff={params['sigma_eff_dB']:.1f}dB, p_phys={params['p_phys']:.2e}):")
        for entry in data['distances']:
            r = entry['soft']
            pL = f"{r['p_L']:.2e}" if r['p_L'] > 0 else f"<{1/r['n_shots']:.1e}"
            print(f"    d={r['d']}: p_L = {pL}  ({r['n_errors']:,} errors / {r['n_shots']:,} shots)")


if __name__ == '__main__':
    main()
