#!/usr/bin/env python3
"""
Paper 2 publication figures — The 14-bit Advantage
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
plt.rcParams.update({
    'font.size': 11, 'axes.labelsize': 13, 'axes.titlesize': 13,
    'legend.fontsize': 10, 'figure.dpi': 200,
    'font.family': 'serif',
})

# ═══════════════════════════════════════════════════════════════
#  Fig 1: Fisher Information Ratio — the divergence
# ═══════════════════════════════════════════════════════════════
def fig1_fisher():
    b1_sweep = json.load(open(os.path.join(OUT, 'b1_fisher_information.json')))['sweep']
    b1_pts = json.load(open(os.path.join(OUT, 'b1_cramer_rao.json')))

    sigma_sweep = [r['sigma_eff_dB'] for r in b1_sweep]
    i_cv = [r['I_CV'] for r in b1_sweep]
    i_dv = [r['I_DV'] for r in b1_sweep]
    ratio = [r['ratio'] for r in b1_sweep]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    # Left: I_CV and I_DV
    ax1.semilogy(sigma_sweep, i_cv, 'b-', lw=2, label='$I_{CV}$ (14-bit analog)')
    ax1.semilogy(sigma_sweep, i_dv, 'r--', lw=2, label='$I_{DV}$ (1-bit binary)')
    for p in b1_pts:
        s = p['sigma_eff_dB']
        ax1.plot(s, p['I_CV_wrapped'], 'bo', ms=8, zorder=5)
        ax1.plot(s, p['I_DV'], 'rs', ms=8, zorder=5)
    ax1.set_xlabel('$\\sigma_{eff}$ (dB)')
    ax1.set_ylabel('Fisher Information $I(V_{eff})$')
    ax1.legend(loc='upper left')
    ax1.set_title('(a) Fisher Information per Measurement')
    ax1.axvspan(7.0, 7.5, alpha=0.1, color='red', label='Threshold region')
    # Phase labels
    ax1.annotate('Phase 1', xy=(8.5, 22), fontsize=9, color='gray')
    ax1.annotate('Phase 2+', xy=(9.3, 35), fontsize=9, color='gray')

    # Right: Ratio
    ax2.plot(sigma_sweep, ratio, 'k-', lw=2.5)
    for p in b1_pts:
        ax2.plot(p['sigma_eff_dB'], p['ratio'], 'ko', ms=9, zorder=5)
        ax2.annotate(f"{p['ratio']:.1f}×",
                     xy=(p['sigma_eff_dB'], p['ratio']),
                     xytext=(5, 8), textcoords='offset points', fontsize=9,
                     fontweight='bold')
    ax2.set_xlabel('$\\sigma_{eff}$ (dB)')
    ax2.set_ylabel('$I_{CV} / I_{DV}$')
    ax2.set_title('(b) 14-bit Advantage Ratio')
    ax2.axhline(1, color='gray', ls=':', alpha=0.5)
    ax2.fill_between(sigma_sweep, 1, ratio, alpha=0.15, color='blue')
    ax2.set_ylim(0, max(ratio) * 1.15)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig1_fisher_information.png'), bbox_inches='tight')
    print('  fig1_fisher_information.png')


# ═══════════════════════════════════════════════════════════════
#  Fig 2: Channel Estimation Convergence — THE money shot
# ═══════════════════════════════════════════════════════════════
def fig2_estimation():
    b2 = json.load(open(os.path.join(OUT, 'b2_channel_estimation.json')))

    fig, ax = plt.subplots(figsize=(7, 5))

    cyc_cv = [r['n_cycles'] for r in b2['cv']]
    err_cv = [r['median_rel_err'] * 100 for r in b2['cv']]
    err_dv = [r['median_rel_err'] * 100 for r in b2['dv']]

    ax.semilogx(cyc_cv, err_cv, 'b-o', lw=2.5, ms=7, label='CV (14-bit MLE)', zorder=5)
    ax.semilogx(cyc_cv, err_dv, 'r--s', lw=2.5, ms=7, label='DV (1-bit binary)', zorder=5)

    # 3% threshold line
    ax.axhline(3, color='green', ls='--', lw=1.5, alpha=0.7)
    ax.annotate('3% target', xy=(1.1, 3.5), color='green', fontsize=10)

    # Highlight the saturation
    ax.fill_between(cyc_cv, 25, 32, alpha=0.08, color='red')
    ax.annotate('DV saturation\n(information bottleneck)',
                xy=(30, 28), fontsize=9, color='red', ha='center',
                style='italic')

    # Highlight CV achievement
    ax.annotate('CV: 3 cycles → 2.6%',
                xy=(3, 2.61), xytext=(8, 8),
                arrowprops=dict(arrowstyle='->', color='blue', lw=1.5),
                fontsize=10, color='blue', fontweight='bold')

    ax.set_xlabel('QEC Cycles (d=7, 686 modes/cycle)')
    ax.set_ylabel('$V_{eff}$ Estimation Error (median %)')
    ax.set_title('Real-Time Hardware State Estimation:\nCV Analog vs DV Binary')
    ax.legend(loc='center right', fontsize=11)
    ax.set_ylim(0, 35)
    ax.set_xlim(0.8, 120)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig2_channel_estimation.png'), bbox_inches='tight')
    print('  fig2_channel_estimation.png')


# ═══════════════════════════════════════════════════════════════
#  Fig 3: CUSUM Anomaly Detection — bar chart
# ═══════════════════════════════════════════════════════════════
def fig3_cusum():
    b4 = json.load(open(os.path.join(OUT, 'b4_calibrated_cusum.json')))

    anomalies = list(b4['anomalies'].keys())
    cv_delays = [b4['anomalies'][k]['cv_median_delay'] for k in anomalies]
    dv_delays = [b4['anomalies'][k]['dv_median_delay'] for k in anomalies]
    dv_rates = [b4['anomalies'][k]['dv_detect_rate'] for k in anomalies]
    advantages = [b4['anomalies'][k]['advantage'] for k in anomalies]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    x = np.arange(len(anomalies))
    w = 0.35

    bars_cv = ax1.bar(x - w/2, cv_delays, w, label='CV (14-bit)', color='#2196F3', zorder=3)
    bars_dv = ax1.bar(x + w/2, dv_delays, w, label='DV (1-bit)', color='#F44336', zorder=3)

    # Add advantage labels
    for i, adv in enumerate(advantages):
        y_max = max(cv_delays[i], dv_delays[i])
        ax1.annotate(f'{adv:.1f}×', xy=(x[i], y_max + 3),
                     ha='center', fontsize=10, fontweight='bold', color='#333')

    ax1.set_xticks(x)
    ax1.set_xticklabels(anomalies)
    ax1.set_ylabel('Detection Delay (QEC cycles)')
    ax1.set_title('(a) Anomaly Detection Speed\n(FAR = 1%, CUSUM)')
    ax1.legend()
    ax1.grid(True, axis='y', alpha=0.3)

    # Right: Detection rate
    ax2.bar(x - w/2, [100]*len(anomalies), w, label='CV', color='#2196F3', alpha=0.8)
    ax2.bar(x + w/2, [r*100 for r in dv_rates], w, label='DV', color='#F44336', alpha=0.8)

    ax2.set_xticks(x)
    ax2.set_xticklabels(anomalies)
    ax2.set_ylabel('Detection Rate (%)')
    ax2.set_title('(b) Detection Reliability')
    ax2.set_ylim(85, 102)
    ax2.legend()
    ax2.grid(True, axis='y', alpha=0.3)

    # Highlight DV failure at small shift
    ax2.annotate('DV fails\nat +0.2dB',
                 xy=(0 + w/2, dv_rates[0]*100),
                 xytext=(0.8, 88),
                 arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
                 fontsize=10, color='red', fontweight='bold')

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig3_cusum_detection.png'), bbox_inches='tight')
    print('  fig3_cusum_detection.png')


# ═══════════════════════════════════════════════════════════════
#  Fig 4: Pilot Signal Analogy — conceptual diagram
# ═══════════════════════════════════════════════════════════════
def fig4_pilot_analogy():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6))

    # Top: Telecom OFDM pilot
    t = np.linspace(0, 4*np.pi, 200)
    signal = np.sin(t) * np.exp(-0.1*t)
    noise = 0.3 * np.random.RandomState(42).randn(200)
    received = signal + noise

    ax1.plot(t, signal, 'b-', lw=1.5, alpha=0.5, label='Known pilot')
    ax1.plot(t, received, 'k-', lw=0.8, alpha=0.6, label='Received')
    ax1.fill_between(t, signal, received, alpha=0.15, color='red', label='Channel noise')
    # Pilot positions
    pilot_idx = np.arange(0, 200, 25)
    ax1.plot(t[pilot_idx], signal[pilot_idx], 'b^', ms=10, zorder=5, label='Pilot symbols')
    ax1.set_title('Telecom: OFDM Pilot-Based Channel Estimation')
    ax1.set_xlabel('Subcarrier / Time')
    ax1.set_ylabel('Amplitude')
    ax1.legend(loc='upper right', fontsize=9)

    # Bottom: GKP lattice as pilot
    rng = np.random.RandomState(42)
    v_eff = 0.14
    n_modes = 40
    grid = np.arange(n_modes) * np.sqrt(np.pi)
    displacements = np.sqrt(v_eff) * rng.randn(n_modes)
    measurements = grid + displacements
    residuals = displacements  # simplified

    ax2.plot(np.arange(n_modes), grid, 'b-', lw=1, alpha=0.4)
    ax2.plot(np.arange(n_modes), grid, 'b^', ms=6, label='GKP lattice (known)', zorder=4)
    ax2.plot(np.arange(n_modes), measurements, 'ko', ms=4, alpha=0.6, label='Homodyne measurement')
    # Residual arrows
    for i in range(0, n_modes, 3):
        ax2.annotate('', xy=(i, measurements[i]), xytext=(i, grid[i]),
                     arrowprops=dict(arrowstyle='->', color='red', lw=0.8))
    ax2.plot([], [], 'r-', label='Residual r = $V_{eff}$ information (14-bit)')
    ax2.set_title('CV-QEC: GKP Lattice as Quantum Pilot Signal')
    ax2.set_xlabel('Mode index (TDM time slot)')
    ax2.set_ylabel('Quadrature $q$')
    ax2.legend(loc='upper left', fontsize=9)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig4_pilot_analogy.png'), bbox_inches='tight')
    print('  fig4_pilot_analogy.png')


# ═══════════════════════════════════════════════════════════════
#  Fig 5: Cramér-Rao bound — 1-cycle estimation precision
# ═══════════════════════════════════════════════════════════════
def fig5_crb_comparison():
    b1 = json.load(open(os.path.join(OUT, 'b1_cramer_rao.json')))

    names = [r['name'].split('(')[0].strip() for r in b1]
    crb_cv = [r['CRB_CV_1cycle_rel'] * 100 for r in b1]
    crb_dv = [r['CRB_DV_1cycle_rel'] * 100 for r in b1]

    fig, ax = plt.subplots(figsize=(7, 4.5))

    x = np.arange(len(names))
    w = 0.35

    ax.bar(x - w/2, crb_cv, w, label='CV (14-bit)', color='#2196F3')
    ax.bar(x + w/2, crb_dv, w, label='DV (1-bit)', color='#F44336')

    # Add ratio labels
    for i in range(len(names)):
        ratio = crb_dv[i] / crb_cv[i]
        ax.annotate(f'{ratio:.1f}× better',
                    xy=(x[i] - w/2, crb_cv[i] + 0.5),
                    fontsize=9, color='#2196F3', fontweight='bold', ha='center')

    ax.set_xticks(x)
    ax.set_xticklabels([r['name'] for r in b1], fontsize=9)
    ax.set_ylabel('Cramér-Rao Lower Bound\n(relative std, 1 QEC cycle, %)')
    ax.set_title('Fundamental Estimation Precision Limit\n(d=7, N=686 modes per cycle)')
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig5_crb_comparison.png'), bbox_inches='tight')
    print('  fig5_crb_comparison.png')


if __name__ == '__main__':
    print("Generating Paper 2 figures...")
    fig1_fisher()
    fig2_estimation()
    fig3_cusum()
    fig4_pilot_analogy()
    fig5_crb_comparison()
    print("Done.")
