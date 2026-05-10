#!/usr/bin/env python3
"""
R1 Publication Figures v2: With Mixed-ρ GNN results
=====================================================

3 outputs:
  - fig_thumbnail.png: Bar chart at ρ=0.20, d=3 (サムネ用)
  - fig_advantage_v2.png: Advantage ratio vs ρ, single + mixed lines
  - fig_ler_3decoder.png: LER vs ρ, 3 decoders × 2 distances
"""
import numpy as np
import json, os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')


def load_all():
    with open(os.path.join(OUT_DIR, 'r1_gnn_lite_results.json')) as f:
        lite = json.load(f)
    with open(os.path.join(OUT_DIR, 'r1_enhanced_results.json')) as f:
        enhanced = json.load(f)
    with open(os.path.join(OUT_DIR, 'r1_mixed_results.json')) as f:
        mixed = json.load(f)
    return lite, enhanced, mixed


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return 0, 0, 0
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    spread = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return p, max(center - spread, 0), min(center + spread, 1)


def fig_thumbnail(mixed):
    """Bar chart: 3 decoders at ρ=0.20, d=3."""
    fig, ax = plt.subplots(figsize=(7, 5.5))

    # d=3 ρ=0.20 data
    r = mixed['d3_eval0.20']
    corr_mwpm = r['mwpm_pL']  # 1.06e-2
    mixed_gnn = r['gnn_mixed_pL']  # 5.0e-3
    single_gnn = None  # N/A

    labels = ['Corr-aware\nMWPM', 'Single-ρ GNN\n(ρ=0.05 train)', 'Mixed-ρ GNN']
    values = [corr_mwpm, 0, mixed_gnn]  # 0 placeholder for N/A
    colors = ['#5C6BC0', '#BDBDBD', '#E53935']
    edge_colors = ['#3949AB', '#9E9E9E', '#C62828']

    bars = ax.bar(labels, values, color=colors, edgecolor=edge_colors,
                  linewidth=1.5, width=0.6, zorder=3)

    # N/A annotation for single-ρ
    ax.text(1, corr_mwpm * 0.15, 'N/A\n(out of training\ndistribution)',
            ha='center', va='bottom', fontsize=10, color='#616161',
            fontstyle='italic')

    # Value labels on bars
    ax.text(0, corr_mwpm * 1.15, f'{corr_mwpm:.2e}', ha='center',
            fontsize=11, fontweight='bold', color='#3949AB')
    ax.text(2, mixed_gnn * 1.15, f'{mixed_gnn:.2e}', ha='center',
            fontsize=11, fontweight='bold', color='#C62828')

    # 2.12× arrow
    ax.annotate('', xy=(2, mixed_gnn), xytext=(0, corr_mwpm),
                arrowprops=dict(arrowstyle='->', color='#2E7D32', lw=2.5))
    mid_y = np.sqrt(corr_mwpm * mixed_gnn)
    ax.text(1.5, mid_y, '2.12×', fontsize=14, fontweight='bold',
            color='#2E7D32', ha='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#E8F5E9',
                      edgecolor='#2E7D32', alpha=0.9))

    ax.set_yscale('log')
    ax.set_ylabel('Logical Error Rate $p_L$', fontsize=13)
    ax.set_title('Mixed-ρ GNN: 2.12× advantage over MWPM\nat OOD ρ=0.20 (d=3)',
                 fontsize=13, fontweight='bold')
    ax.set_ylim(1e-3, 3e-2)
    ax.grid(True, alpha=0.2, which='both', axis='y')
    ax.text(0.98, 0.02, 'ρ=0.20 is outside training distribution\n'
            'Training: ρ∈{0, 0.03, 0.05, 0.08, 0.10, 0.15}',
            transform=ax.transAxes, ha='right', va='bottom',
            fontsize=8.5, color='#757575',
            bbox=dict(boxstyle='round', facecolor='#FFF9C4', alpha=0.8))

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_thumbnail.png')
    plt.savefig(path, dpi=200, bbox_inches='tight')
    print(f"  Saved: {path}")
    plt.close()


def fig_advantage_v2(lite, enhanced, mixed):
    """Advantage ratio vs ρ: single-ρ + mixed-ρ lines, d=3 and d=5."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    for ax, d, title in [(ax1, 3, 'd=3'), (ax2, 5, 'd=5')]:
        rhos_all = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15]

        # Single-ρ GNN vs corr-MWPM
        single_rhos, single_ratios = [], []
        for rho in rhos_all:
            ekey = f'd{d}_rho{rho:.2f}'
            lkey = f'd{d}_rho{rho:.2f}'
            if ekey in enhanced and lkey in lite:
                corr = enhanced[ekey]['mwpm_corr_pL']
                gnn = lite[lkey]['gnn_pL']
                if gnn > 0:
                    single_rhos.append(rho)
                    single_ratios.append(corr / gnn)

        # Mixed-ρ GNN vs MWPM
        mixed_rhos_eval = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]
        mix_rhos, mix_ratios = [], []
        for rho in mixed_rhos_eval:
            mkey = f'd{d}_eval{rho:.2f}'
            if mkey in mixed:
                mwpm = mixed[mkey]['mwpm_pL']
                gnn_m = mixed[mkey]['gnn_mixed_pL']
                if gnn_m > 0:
                    mix_rhos.append(rho)
                    mix_ratios.append(mwpm / gnn_m)

        ax.plot(single_rhos, single_ratios, '-o', color='#E91E63',
                linewidth=2, markersize=8, label='Per-ρ trained GNN', zorder=4)
        ax.plot(mix_rhos, mix_ratios, '-D', color='#2196F3',
                linewidth=2.5, markersize=8, label='Mixed-ρ GNN', zorder=5)

        ax.axhline(y=1.0, color='black', ls='--', alpha=0.4, linewidth=1)
        ax.fill_between([-0.01, 0.22], 0, 1, alpha=0.04, color='blue')
        ax.fill_between([-0.01, 0.22], 1, 10, alpha=0.04, color='red')

        # OOD shading
        ax.axvspan(0.16, 0.22, alpha=0.08, color='orange',
                   label='OOD region (ρ>0.15)')

        ax.set_xlabel('Correlation strength ρ', fontsize=13)
        ax.set_ylabel('Advantage: $p_L$(MWPM) / $p_L$(GNN)', fontsize=12)
        ax.set_title(f'{title}: GNN advantage ratio', fontsize=13, fontweight='bold')
        ax.legend(fontsize=10, loc='upper left')
        ax.grid(True, alpha=0.2)
        ax.set_xlim(-0.01, 0.22)
        ax.set_ylim(0, None)

        # Annotate key points
        if d == 3 and len(mix_ratios) > 0:
            last_rho = mix_rhos[-1]
            last_ratio = mix_ratios[-1]
            ax.annotate(f'{last_ratio:.2f}×\n(OOD)',
                        xy=(last_rho, last_ratio),
                        xytext=(last_rho - 0.04, last_ratio + 0.5),
                        fontsize=10, fontweight='bold', color='#1565C0',
                        arrowprops=dict(arrowstyle='->', color='#1565C0'))
        if d == 5 and len(mix_ratios) > 0:
            # Annotate max
            max_idx = np.argmax(mix_ratios)
            ax.annotate(f'{mix_ratios[max_idx]:.1f}×',
                        xy=(mix_rhos[max_idx], mix_ratios[max_idx]),
                        xytext=(mix_rhos[max_idx] - 0.04, mix_ratios[max_idx] + 0.5),
                        fontsize=10, fontweight='bold', color='#1565C0',
                        arrowprops=dict(arrowstyle='->', color='#1565C0'))
            # Annotate OOD
            ax.annotate(f'{mix_ratios[-1]:.2f}×\n(OOD)',
                        xy=(mix_rhos[-1], mix_ratios[-1]),
                        xytext=(mix_rhos[-1] - 0.04, mix_ratios[-1] - 1.0),
                        fontsize=10, fontweight='bold', color='#1565C0',
                        arrowprops=dict(arrowstyle='->', color='#1565C0'))

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_advantage_v2.png')
    plt.savefig(path, dpi=200, bbox_inches='tight')
    print(f"  Saved: {path}")
    plt.close()


def fig_ler_3decoder(lite, enhanced, mixed):
    """LER vs ρ: 3 decoders, d=3 and d=5."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6.5))

    for ax, d, title in [(ax1, 3, 'd=3'), (ax2, 5, 'd=5')]:
        n_te = 10000 if d == 3 else 5000
        rhos_base = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15]

        # Corr-MWPM
        corr_rhos, corr_vals, corr_lo, corr_hi = [], [], [], []
        for rho in rhos_base:
            ekey = f'd{d}_rho{rho:.2f}'
            if ekey in enhanced:
                pl = enhanced[ekey]['mwpm_corr_pL']
                n_err = int(round(pl * enhanced[ekey]['n_test']))
                _, lo, hi = wilson_ci(n_err, enhanced[ekey]['n_test'])
                corr_rhos.append(rho)
                corr_vals.append(pl)
                corr_lo.append(pl - lo)
                corr_hi.append(hi - pl)

        # Single-ρ GNN
        sing_rhos, sing_vals, sing_lo, sing_hi = [], [], [], []
        for rho in rhos_base:
            lkey = f'd{d}_rho{rho:.2f}'
            if lkey in lite:
                pl = lite[lkey]['gnn_pL']
                n_err = lite[lkey]['gnn_err']
                _, lo, hi = wilson_ci(n_err, lite[lkey]['n_test'])
                sing_rhos.append(rho)
                sing_vals.append(pl)
                sing_lo.append(pl - lo)
                sing_hi.append(hi - pl)

        # Mixed-ρ GNN
        mix_rhos_eval = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]
        mix_rhos, mix_vals, mix_lo, mix_hi = [], [], [], []
        for rho in mix_rhos_eval:
            mkey = f'd{d}_eval{rho:.2f}'
            if mkey in mixed:
                pl = mixed[mkey]['gnn_mixed_pL']
                n_err = mixed[mkey]['gnn_err']
                _, lo, hi = wilson_ci(n_err, mixed[mkey]['n_test'])
                mix_rhos.append(rho)
                mix_vals.append(pl)
                mix_lo.append(pl - lo)
                mix_hi.append(hi - pl)

        # Plot
        ax.errorbar(corr_rhos, corr_vals, yerr=[corr_lo, corr_hi],
                    fmt='-s', color='#5C6BC0', linewidth=1.5, markersize=7,
                    capsize=3, alpha=0.7, label='Corr-aware MWPM')
        ax.errorbar(sing_rhos, sing_vals, yerr=[sing_lo, sing_hi],
                    fmt='--o', color='#E91E63', linewidth=1.5, markersize=7,
                    capsize=3, alpha=0.7, label='Per-ρ trained GNN')
        ax.errorbar(mix_rhos, mix_vals, yerr=[mix_lo, mix_hi],
                    fmt='-D', color='#2196F3', linewidth=2.5, markersize=8,
                    capsize=3, label='Mixed-ρ GNN', zorder=5)

        # OOD shading
        ax.axvspan(0.16, 0.22, alpha=0.08, color='orange', label='OOD')

        ax.set_yscale('log')
        ax.set_xlabel('Correlation strength ρ', fontsize=13)
        ax.set_ylabel('Logical error rate $p_L$', fontsize=13)
        ax.set_title(f'{title}: 3-decoder comparison (Phase 1, σ_eff=8.5 dB)',
                     fontsize=12, fontweight='bold')
        ax.legend(fontsize=9.5, loc='upper left' if d == 3 else 'best')
        ax.grid(True, alpha=0.2, which='both')
        ax.set_xlim(-0.01, 0.22)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, 'fig_ler_3decoder.png')
    plt.savefig(path, dpi=200, bbox_inches='tight')
    print(f"  Saved: {path}")
    plt.close()


def main():
    lite, enhanced, mixed = load_all()
    fig_thumbnail(mixed)
    fig_advantage_v2(lite, enhanced, mixed)
    fig_ler_3decoder(lite, enhanced, mixed)
    print("  All figures generated.")


if __name__ == '__main__':
    main()
