#!/usr/bin/env python3
"""
Paper 3 figures: threshold curves + 4-decoder comparison + distance scaling
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json, os
from scipy.stats import binom

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
plt.rcParams.update({
    'font.size': 11, 'axes.labelsize': 13, 'axes.titlesize': 13,
    'legend.fontsize': 9.5, 'figure.dpi': 200, 'font.family': 'serif',
})

def wilson_ci(k, n, z=1.96):
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    half = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return max(0, center - half), min(1, center + half)

def poisson_upper(k, n, conf=0.95):
    """Upper bound for p when k=0: use -ln(1-conf)/n."""
    if k == 0:
        return -np.log(1 - conf) / n
    return wilson_ci(k, n)[1]


# ═══════════════════════════════════════════════════════════════
#  Fig 1: Threshold curve — p_L vs ρ for 4 decoders (d=5)
# ═══════════════════════════════════════════════════════════════
def fig1_threshold_curve():
    pr = json.load(open(os.path.join(OUT, 'unified_per_rho.json')))
    cr = json.load(open(os.path.join(OUT, 'unified_corr_mwpm.json')))
    mx = json.load(open(os.path.join(OUT, 'unified_mixed_rho.json')))

    rho_list = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    for d, ax, n_test in [(5, ax1, 30000), (7, ax2, 10000)]:
        # Vanilla MWPM
        van_pL, van_lo, van_hi = [], [], []
        # Residual subtraction
        res_pL, res_lo, res_hi = [], [], []
        # Per-rho GNN
        gnn_pL, gnn_lo, gnn_hi = [], [], []
        # Mixed GNN
        mix_pL, mix_lo, mix_hi = [], [], []

        for rho in rho_list:
            pk = f'd{d}_rho{rho:.2f}'
            ek = f'd{d}_eval{rho:.2f}'

            # Vanilla
            if pk in pr:
                k = pr[pk]['mwpm_err']
                p = k / n_test
                lo, hi = wilson_ci(k, n_test) if k > 0 else (0, poisson_upper(0, n_test))
                van_pL.append(p); van_lo.append(lo); van_hi.append(hi)

            # Residual subtraction
            if pk in cr:
                k = cr[pk]['corr_err']
                p = k / n_test
                lo, hi = wilson_ci(k, n_test) if k > 0 else (0, poisson_upper(0, n_test))
                res_pL.append(p); res_lo.append(lo); res_hi.append(hi)

            # Per-rho GNN
            if pk in pr:
                k = pr[pk]['gnn_err']
                p = k / n_test
                lo, hi = wilson_ci(k, n_test) if k > 0 else (0, poisson_upper(0, n_test))
                gnn_pL.append(p); gnn_lo.append(lo); gnn_hi.append(hi)

            # Mixed GNN
            if ek in mx:
                k = mx[ek]['gnn_err']
                nt = mx[ek]['n_test']
                p = k / nt
                lo, hi = wilson_ci(k, nt) if k > 0 else (0, poisson_upper(0, nt))
                mix_pL.append(p); mix_lo.append(lo); mix_hi.append(hi)

        rhos = rho_list[:len(van_pL)]

        # Plot with error bars
        def plot_with_ci(ax, x, y, lo, hi, color, marker, label, ls='-'):
            y, lo, hi = np.array(y), np.array(lo), np.array(hi)
            # Replace 0 with small value for log scale
            y_plot = np.where(y > 0, y, hi * 0.5)
            ax.semilogy(x, y_plot, color=color, marker=marker, ls=ls, lw=2, ms=7,
                       label=label, zorder=4)
            for i in range(len(x)):
                if y[i] > 0:
                    ax.plot([x[i], x[i]], [lo[i], hi[i]], color=color, lw=1.5, alpha=0.5)
                else:
                    # Upper limit arrow for 0 errors
                    ax.annotate('', xy=(x[i], hi[i]),
                               xytext=(x[i], hi[i]*3),
                               arrowprops=dict(arrowstyle='->', color=color, lw=1.5))
                    ax.plot(x[i], hi[i], marker='v', color=color, ms=6, zorder=5)

        plot_with_ci(ax, rhos, van_pL, van_lo, van_hi, 'red', 's', 'Vanilla MWPM')
        plot_with_ci(ax, rhos, res_pL, res_lo, res_hi, 'orange', 'D',
                     'Residual subtraction', ls='--')
        plot_with_ci(ax, rhos, gnn_pL, gnn_lo, gnn_hi, 'blue', 'o', 'GNN per-ρ')
        if mix_pL:
            plot_with_ci(ax, rhos[:len(mix_pL)], mix_pL, mix_lo, mix_hi,
                         'green', '^', 'GNN mixed-ρ', ls='-.')

        ax.axhline(1e-3, color='gray', ls=':', lw=1.5, alpha=0.7)
        ax.annotate('$10^{-3}$ threshold', xy=(0.01, 1.2e-3), color='gray', fontsize=9)
        ax.set_xlabel('Correlation coefficient ρ')
        ax.set_ylabel('Logical error rate $p_L$')
        ax.set_title(f'd = {d} (n_test = {n_test:,})')
        ax.legend(loc='upper left')
        ax.set_ylim(1e-5, 2e-2)
        ax.grid(True, alpha=0.3, which='both')

    fig.suptitle('4-Decoder Comparison: $p_L$ vs Correlation ρ', fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_threshold_4decoder.png'), bbox_inches='tight')
    print('  fig_threshold_4decoder.png')


# ═══════════════════════════════════════════════════════════════
#  Fig 2: Distance scaling — advantage ratio vs d
# ═══════════════════════════════════════════════════════════════
def fig2_distance_scaling():
    pr = json.load(open(os.path.join(OUT, 'unified_per_rho.json')))

    fig, ax = plt.subplots(figsize=(7, 5))

    ds = [3, 5, 7]
    rho_targets = [0.08, 0.10, 0.15]
    colors = ['#2196F3', '#FF5722', '#4CAF50']
    markers = ['o', 's', 'D']

    for rho, color, marker in zip(rho_targets, colors, markers):
        ratios = []
        for d in ds:
            k = f'd{d}_rho{rho:.2f}'
            if k in pr:
                r = pr[k]
                if r['gnn_err'] > 0:
                    ratios.append(r['mwpm_err'] / r['gnn_err'])
                else:
                    # Lower bound: MWPM_err / 1 (conservative)
                    ratios.append(r['mwpm_err'] if r['mwpm_err'] > 0 else 1)
            else:
                ratios.append(np.nan)

        ax.plot(ds, ratios, color=color, marker=marker, lw=2.5, ms=9,
                label=f'ρ = {rho}')

        for i, (d, rat) in enumerate(zip(ds, ratios)):
            if rat > 50:
                ax.annotate(f'>{rat:.0f}×', xy=(d, rat),
                           xytext=(5, -10), textcoords='offset points',
                           fontsize=9, fontweight='bold', color=color)
            elif not np.isnan(rat):
                ax.annotate(f'{rat:.1f}×', xy=(d, rat),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=9, fontweight='bold', color=color)

    ax.set_xlabel('Code distance d')
    ax.set_ylabel('GNN / MWPM advantage ratio')
    ax.set_xticks(ds)
    ax.set_title('GNN Advantage Scales with Code Distance')
    ax.legend(fontsize=11)
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3, which='both')
    ax.set_ylim(0.5, 200)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_distance_scaling.png'), bbox_inches='tight')
    print('  fig_distance_scaling.png')


# ═══════════════════════════════════════════════════════════════
#  Fig 3: Mixed-ρ OOD — bar chart for d=3,5,7 at ρ=0.20
# ═══════════════════════════════════════════════════════════════
def fig3_ood_bar():
    mx = json.load(open(os.path.join(OUT, 'unified_mixed_rho.json')))

    fig, ax = plt.subplots(figsize=(8, 5))

    ds = [3, 5, 7]
    rhos = [0.10, 0.15, 0.20]
    x = np.arange(len(ds))
    width = 0.25

    for i, rho in enumerate(rhos):
        ratios = []
        for d in ds:
            k = f'd{d}_eval{rho:.2f}'
            if k in mx:
                r = mx[k]
                mwpm_err = r['mwpm_err']
                gnn_err = r['gnn_err']
                if gnn_err > 0:
                    ratios.append(mwpm_err / gnn_err)
                else:
                    ratios.append(mwpm_err if mwpm_err > 0 else 1)
            else:
                ratios.append(0)

        bars = ax.bar(x + i * width, ratios, width,
                      label=f'ρ = {rho}' + (' (OOD)' if rho == 0.20 else ''),
                      alpha=0.85)

        for j, (bar, rat) in enumerate(zip(bars, ratios)):
            if rat > 0:
                label = f'{rat:.0f}×' if rat < 100 else f'>{rat:.0f}×'
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                       label, ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_xticks(x + width)
    ax.set_xticklabels([f'd = {d}' for d in ds], fontsize=12)
    ax.set_ylabel('Mixed-ρ GNN / MWPM ratio')
    ax.set_title('Hardware-Adaptive GNN: Single Model, All Conditions\n(including OOD ρ = 0.20)')
    ax.legend(fontsize=11)
    ax.set_yscale('log')
    ax.grid(True, axis='y', alpha=0.3, which='both')

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_ood_mixed_rho.png'), bbox_inches='tight')
    print('  fig_ood_mixed_rho.png')


if __name__ == '__main__':
    print("Generating Paper 3 figures...")
    fig1_threshold_curve()
    fig2_distance_scaling()
    fig3_ood_bar()
    print("Done.")
