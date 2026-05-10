#!/usr/bin/env python3
"""
Generate publication-quality figures and tables for R1 GNN paper.

Outputs:
  - fig_main_ler_vs_rho.png: LER vs ρ, 3 decoders × 2 distances (main figure)
  - fig_advantage_ratio.png: Advantage ratio (corrMWPM/GNN) vs ρ
  - tables printed to stdout: LER table with 95% CI, crossover ρ*, ρ→physical

Requires: r1_gnn_lite_results.json, r1_enhanced_results.json
"""
import numpy as np
import json, os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')


def wilson_ci(k, n, z=1.96):
    """Wilson score 95% CI for binomial proportion."""
    if n == 0:
        return 0, 0, 0
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    spread = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return p, max(center - spread, 0), min(center + spread, 1)


def load_data():
    """Load all result files."""
    with open(os.path.join(OUT_DIR, 'r1_gnn_lite_results.json')) as f:
        gnn = json.load(f)
    with open(os.path.join(OUT_DIR, 'r1_enhanced_results.json')) as f:
        enhanced = json.load(f)
    return gnn, enhanced


def build_table(gnn, enhanced):
    """Build unified LER table: 3 decoders × 2 distances × all ρ."""
    rhos = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15]
    rows = []
    for d in [3, 5]:
        n_te = 10000 if d == 3 else 5000
        for rho in rhos:
            gkey = f'd{d}_rho{rho:.2f}'
            ekey = f'd{d}_rho{rho:.2f}'

            # MWPM standard (from gnn results)
            mwpm_pl = gnn[gkey]['mwpm_pL'] if gkey in gnn else None
            mwpm_err = gnn[gkey]['mwpm_err'] if gkey in gnn else None

            # MWPM correlated (from enhanced results)
            corr_pl = enhanced[ekey]['mwpm_corr_pL'] if ekey in enhanced else None

            # GNN
            gnn_pl = gnn[gkey]['gnn_pL'] if gkey in gnn else None
            gnn_err = gnn[gkey]['gnn_err'] if gkey in gnn else None

            # 95% CI
            if mwpm_err is not None:
                _, mwpm_lo, mwpm_hi = wilson_ci(int(mwpm_err), n_te)
            else:
                mwpm_lo = mwpm_hi = None

            if gnn_err is not None:
                _, gnn_lo, gnn_hi = wilson_ci(int(gnn_err), n_te)
            else:
                gnn_lo = gnn_hi = None

            # corr MWPM CI: use enhanced n_test
            n_te_e = enhanced.get(ekey, {}).get('n_test', n_te)
            if corr_pl is not None:
                corr_err_est = int(round(corr_pl * n_te_e))
                _, corr_lo, corr_hi = wilson_ci(corr_err_est, n_te_e)
            else:
                corr_lo = corr_hi = None

            rows.append({
                'd': d, 'rho': rho,
                'mwpm': mwpm_pl, 'mwpm_ci': (mwpm_lo, mwpm_hi),
                'corr': corr_pl, 'corr_ci': (corr_lo, corr_hi),
                'gnn': gnn_pl, 'gnn_ci': (gnn_lo, gnn_hi),
            })
    return rows


def print_ler_table(rows):
    """Print LER table with 95% CI."""
    print("\n" + "=" * 95)
    print("  TABLE 1: Logical Error Rate (3 decoders × 2 distances × ρ)")
    print("=" * 95)
    print(f"  {'d':>2} {'ρ':>5} │ {'MWPM-std':>12} {'95%CI':>18} │"
          f" {'MWPM-corr':>12} {'95%CI':>18} │ {'GNN':>12} {'95%CI':>18}")
    print("  " + "─" * 92)

    for r in rows:
        def fmt(v, ci):
            if v is None:
                return f"{'—':>12} {'':>18}"
            lo, hi = ci
            if lo is not None:
                return f"{v:12.4e} [{lo:.4e},{hi:.4e}]"
            return f"{v:12.4e} {'':>18}"

        sep = "│" if r['rho'] != 0.15 else "│"
        print(f"  {r['d']:>2} {r['rho']:5.2f} │ {fmt(r['mwpm'], r['mwpm_ci'])} │"
              f" {fmt(r['corr'], r['corr_ci'])} │ {fmt(r['gnn'], r['gnn_ci'])}")
        if r['rho'] == 0.15:
            print("  " + "─" * 92)


def find_crossover(rows):
    """Find crossover ρ* where GNN beats correlated MWPM."""
    print("\n" + "=" * 60)
    print("  TABLE 2: Crossover ρ* (GNN > corr-MWPM)")
    print("=" * 60)

    for d in [3, 5]:
        d_rows = [r for r in rows if r['d'] == d]
        rho_star = None
        for i in range(len(d_rows)):
            if (d_rows[i]['gnn'] is not None and
                d_rows[i]['corr'] is not None and
                d_rows[i]['gnn'] < d_rows[i]['corr']):
                # Linear interpolation from previous point
                if i > 0 and d_rows[i-1]['gnn'] >= d_rows[i-1]['corr']:
                    r0, r1 = d_rows[i-1]['rho'], d_rows[i]['rho']
                    g0 = d_rows[i-1]['gnn'] - d_rows[i-1]['corr']
                    g1 = d_rows[i]['gnn'] - d_rows[i]['corr']
                    rho_star = r0 + (r1 - r0) * (-g0) / (g1 - g0)
                else:
                    rho_star = d_rows[i]['rho']
                break

        if rho_star is not None:
            print(f"  d={d}: ρ* ≈ {rho_star:.3f}")
            # Map to physical
            rin = -10 * np.log10(rho_star / (10**(-15) * 10**8 * 400))
            print(f"         ↔ RIN ≈ {-rin:.0f} dB/Hz (pump noise)")
            print(f"         ↔ WDM isolation ≈ {-10*np.log10(rho_star/2):.0f} dB")
        else:
            print(f"  d={d}: GNN does not surpass corr-MWPM in measured range")


def print_rho_physical():
    """Print ρ → physical noise mapping."""
    print("\n" + "=" * 70)
    print("  TABLE 3: ρ → Physical Noise Correspondence")
    print("=" * 70)
    print(f"  {'ρ':>6} │ {'Squeezing penalty':>18} │ {'Pump RIN':>14} │ {'WDM isolation':>14}")
    print("  " + "─" * 66)

    V0 = 0.1417  # V_eff at ρ=0, Phase 1
    for rho in [0.00, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]:
        # Effective variance increase from correlation
        # V_eff_corr ≈ V0 × (1 + ρ×(ne-1)) for large ne, but per-mode is V0
        # The relevant metric: additional noise in common mode
        # σ_eff penalty: Δσ = -10×log10(1 + ρ×V_anti/V0) ≈ small for small ρ
        if rho > 0:
            # Approximate squeezing penalty from correlation
            penalty_db = -10 * np.log10(1 / (1 + rho * 0.5))  # ~half the anti-squeezed
            rin = 10 * np.log10(rho / (10**8 * 400)) + 150  # relative to -150 reference
            rin_abs = -150 + rin
            wdm = -10 * np.log10(rho / 2) if rho > 0 else float('inf')
            print(f"  {rho:6.3f} │ {penalty_db:>15.2f} dB │ {rin_abs:>11.0f} dB/Hz │ {wdm:>11.1f} dB")
        else:
            print(f"  {rho:6.3f} │ {'0 (baseline)':>18} │ {'—':>14} │ {'—':>14}")


def plot_main(rows):
    """Main figure: LER vs ρ, 3 decoders × 2 distances."""
    fig, ax = plt.subplots(figsize=(10, 7))

    colors = {'d3': '#2196F3', 'd5': '#E91E63'}
    styles = {
        'mwpm': {'ls': '--', 'marker': 'o', 'label': 'MWPM soft-info'},
        'corr': {'ls': '-.', 'marker': 's', 'label': 'Corr-aware MWPM'},
        'gnn':  {'ls': '-',  'marker': 'D', 'label': 'GNN Lite (4K params)'},
    }

    for d in [3, 5]:
        d_rows = [r for r in rows if r['d'] == d]
        rhos = [r['rho'] for r in d_rows]
        c = colors[f'd{d}']

        for dec_key, style in styles.items():
            vals = [r[dec_key] for r in d_rows]
            ci_lo = [r[f'{dec_key}_ci'][0] for r in d_rows]
            ci_hi = [r[f'{dec_key}_ci'][1] for r in d_rows]

            valid = [(rho, v, lo, hi) for rho, v, lo, hi in
                     zip(rhos, vals, ci_lo, ci_hi) if v is not None and lo is not None]
            if not valid:
                continue

            r_v, v_v, lo_v, hi_v = zip(*valid)
            v_arr = np.array(v_v)
            lo_arr = np.array(lo_v)
            hi_arr = np.array(hi_v)

            err_lo = v_arr - lo_arr
            err_hi = hi_arr - v_arr

            alpha = 1.0 if dec_key == 'gnn' else 0.6
            lw = 2.5 if dec_key == 'gnn' else 1.5
            ax.errorbar(r_v, v_v, yerr=[err_lo, err_hi],
                        color=c, ls=style['ls'], marker=style['marker'],
                        markersize=7, linewidth=lw, alpha=alpha, capsize=3,
                        label=f"d={d} {style['label']}")

    # Crossover region
    ax.axvspan(0.06, 0.09, alpha=0.08, color='green', label='Crossover region')

    ax.set_yscale('log')
    ax.set_xlabel('Correlation strength ρ', fontsize=14)
    ax.set_ylabel('Logical error rate $p_L$', fontsize=14)
    ax.set_title('GNN decoder vs MWPM under correlated photonic noise\n'
                 '(Phase 1: σ_eff=8.5 dB, GKP surface code)', fontsize=13)
    ax.legend(fontsize=9, ncol=2, loc='upper left')
    ax.grid(True, alpha=0.3, which='both')
    ax.set_xlim(-0.01, 0.16)

    # Secondary x-axis: RIN
    ax2 = ax.twiny()
    rin_ticks = [0.003, 0.01, 0.03, 0.05, 0.08, 0.10, 0.15]
    ax2.set_xlim(ax.get_xlim())
    ax2.set_xticks(rin_ticks)
    rin_labels = []
    for rho in rin_ticks:
        if rho > 0:
            rin = 10 * np.log10(rho * 0.1417 / (10**8 * 400))
            rin_labels.append(f'{rin:.0f}')
        else:
            rin_labels.append('—')
    ax2.set_xticklabels(rin_labels, fontsize=8)
    ax2.set_xlabel('Approx. pump RIN (dB/Hz)', fontsize=10, labelpad=8)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_main_ler_vs_rho.png')
    plt.savefig(path, dpi=200, bbox_inches='tight')
    print(f"\n  Saved: {path}")
    plt.close()


def plot_advantage(rows):
    """Advantage ratio: LER(corrMWPM) / LER(GNN) vs ρ."""
    fig, ax = plt.subplots(figsize=(9, 5.5))

    colors = {'3': '#2196F3', '5': '#E91E63'}

    for d in [3, 5]:
        d_rows = [r for r in rows if r['d'] == d
                  and r['corr'] is not None and r['gnn'] is not None
                  and r['gnn'] > 0]
        if not d_rows:
            continue
        rhos = [r['rho'] for r in d_rows]
        ratios = [r['corr'] / r['gnn'] for r in d_rows]

        ax.plot(rhos, ratios, '-o', color=colors[str(d)],
                linewidth=2.5, markersize=9, label=f'd={d}')

    ax.axhline(y=1.0, color='black', ls='--', alpha=0.5, label='Parity (ratio=1)')
    ax.fill_between([0, 0.16], 1, 0, alpha=0.05, color='blue', label='MWPM advantage')
    ax.fill_between([0, 0.16], 1, 10, alpha=0.05, color='red', label='GNN advantage')

    ax.set_xlabel('Correlation strength ρ', fontsize=14)
    ax.set_ylabel('Advantage ratio: $p_L$(corr-MWPM) / $p_L$(GNN)', fontsize=13)
    ax.set_title('GNN decoder advantage over correlation-aware MWPM', fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-0.01, 0.16)
    ax.set_ylim(0, None)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_advantage_ratio.png')
    plt.savefig(path, dpi=200, bbox_inches='tight')
    print(f"  Saved: {path}")
    plt.close()


def main():
    gnn, enhanced = load_data()
    rows = build_table(gnn, enhanced)

    print_ler_table(rows)
    find_crossover(rows)
    print_rho_physical()
    plot_main(rows)
    plot_advantage(rows)

    print("\n  Done.")


if __name__ == '__main__':
    main()
