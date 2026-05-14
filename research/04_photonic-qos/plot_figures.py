#!/usr/bin/env python3
"""
Paper 4 figures: Quantum Network Slicing & Photonic QOS
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
plt.rcParams.update({
    'font.size': 11, 'axes.labelsize': 13, 'axes.titlesize': 13,
    'legend.fontsize': 9.5, 'figure.dpi': 200, 'font.family': 'serif',
})


# ═══════════════════════════════════════════════════════════════
#  Fig 1: TDM Scalability — Hardware vs Time tradeoff
# ═══════════════════════════════════════════════════════════════
def fig1_scalability():
    data = json.load(open(os.path.join(OUT, 'e1_scalability.json')))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    colors = {'3': '#2196F3', '5': '#FF5722', '7': '#4CAF50'}

    for d in [3, 5, 7]:
        ns = []
        sc_qubits = []
        tdm_time = []
        for k, v in data.items():
            if v['d'] == d:
                ns.append(v['n_logical'])
                sc_qubits.append(v['sc_physical_qubits'])
                tdm_time.append(v['tdm_cycle_us'])

        c = colors[str(d)]
        ax1.loglog(ns, sc_qubits, 'o-', color=c, lw=2, ms=6, label=f'd={d} SC qubits')
        ax1.axhline(1, color='gray', ls='--', lw=1)
        ax1.annotate('TDM: 1 device (all d)', xy=(2, 1.5), fontsize=10, color='gray')

        ax2.loglog(ns, tdm_time, 's-', color=c, lw=2, ms=6, label=f'd={d}')

    ax1.set_xlabel('Logical qubits')
    ax1.set_ylabel('Physical devices required')
    ax1.set_title('(a) Hardware Scaling: SC vs TDM')
    ax1.legend()
    ax1.grid(True, alpha=0.3, which='both')

    ax2.set_xlabel('Logical qubits')
    ax2.set_ylabel('TDM cycle time (us)')
    ax2.set_title('(b) TDM Time Cost')
    ax2.legend()
    ax2.grid(True, alpha=0.3, which='both')

    fig.suptitle('Fig. 1: TDM Photonic Scalability — Constant Hardware, Linear Time',
                 fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig1_scalability.png'), bbox_inches='tight')
    print('  fig1_scalability.png')


# ═══════════════════════════════════════════════════════════════
#  Fig 2: Factory Overhead vs T-gate Density
# ═══════════════════════════════════════════════════════════════
def fig2_factory_overhead():
    data = json.load(open(os.path.join(OUT, 'e1_tgate_density.json')))

    fig, ax = plt.subplots(figsize=(8, 5))

    for d, color, marker in [(3, '#2196F3', 'o'), (5, '#FF5722', 's'), (7, '#4CAF50', 'D')]:
        densities = []
        overheads = []
        for k, v in data.items():
            if v['d'] == d and v['n_logical'] == 10:
                densities.append(v['t_density'] * 100)
                overheads.append(v['factory_overhead_frac'] * 100)

        ax.plot(densities, overheads, f'{marker}-', color=color, lw=2, ms=8,
                label=f'd={d}')

    ax.set_xlabel('T-gate density (%)')
    ax.set_ylabel('Factory overhead (%)')
    ax.set_title('Fig. 2: Magic State Factory Overhead vs T-gate Density (N=10)')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(50, 100)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig2_factory_overhead.png'), bbox_inches='tight')
    print('  fig2_factory_overhead.png')


# ═══════════════════════════════════════════════════════════════
#  Fig 3: Lyapunov V-parameter Tradeoff
# ═══════════════════════════════════════════════════════════════
def fig3_v_tradeoff():
    if not os.path.exists(os.path.join(OUT, 'e2_v_tradeoff.json')):
        print('  [SKIP] e2_v_tradeoff.json not found')
        return

    data = json.load(open(os.path.join(OUT, 'e2_v_tradeoff.json')))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    for d, color in [(5, '#FF5722'), (7, '#4CAF50')]:
        vs = []
        pls = []
        bufs = []
        facts = []
        for k, v in data.items():
            if v['d'] == d:
                vs.append(v['V'])
                pls.append(v['avg_p_L'])
                bufs.append(v['avg_buffer'])
                facts.append(v.get('avg_factories', 0))

        ax1.semilogx(vs, pls, 'o-', color=color, lw=2, ms=7, label=f'd={d}')
        ax2.semilogx(vs, facts, 's-', color=color, lw=2, ms=7, label=f'd={d}')

    ax1.set_xlabel('V parameter')
    ax1.set_ylabel('Average logical error rate $p_L$')
    ax1.set_title('(a) Error Rate vs V')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.set_xlabel('V parameter')
    ax2.set_ylabel('Average factory count')
    ax2.set_title('(b) Factory Allocation vs V')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    fig.suptitle('Fig. 3: Lyapunov Drift-Plus-Penalty — V Parameter Tradeoff',
                 fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig3_v_tradeoff.png'), bbox_inches='tight')
    print('  fig3_v_tradeoff.png')


# ═══════════════════════════════════════════════════════════════
#  Fig 4: Policy Comparison Bar Chart
# ═══════════════════════════════════════════════════════════════
def fig4_policy_comparison():
    if not os.path.exists(os.path.join(OUT, 'e2_policy_comparison.json')):
        print('  [SKIP] e2_policy_comparison.json not found')
        return

    data = json.load(open(os.path.join(OUT, 'e2_policy_comparison.json')))

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    policies_show = ['fixed_1', 'fixed_8', 'greedy', 'lyapunov_V10', 'lyapunov_cv', 'lyapunov_dv']
    policy_labels = ['Fixed\nF=1', 'Fixed\nF=8', 'Greedy', 'Lyapunov\nV=10', 'Lyapunov\nCV', 'Lyapunov\nDV']
    colors_pol = ['#9E9E9E', '#757575', '#FFC107', '#2196F3', '#4CAF50', '#F44336']

    for ax_idx, (drift_name, ax) in enumerate(zip(
            ['stable', 'slow_drift', 'fast_drift'], axes)):
        x = np.arange(len(policies_show))
        pls = []
        errs = []
        for pol in policies_show:
            key = f"d7_{drift_name}_{pol}"
            if key in data:
                pls.append(data[key]['avg_p_L'])
                errs.append(data[key].get('std_p_L', 0))
            else:
                pls.append(0)
                errs.append(0)

        bars = ax.bar(x, pls, yerr=errs, color=colors_pol, alpha=0.85,
                      edgecolor='black', lw=0.5, capsize=3, error_kw={'lw': 1.2})
        ax.set_xticks(x)
        ax.set_xticklabels(policy_labels, fontsize=9)
        ax.set_ylabel('$p_L$')
        ax.set_title(f'{drift_name}')
        ax.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))

        # Annotate best
        best_idx = np.argmin(pls)
        ax.annotate('best', xy=(best_idx, pls[best_idx]),
                     xytext=(best_idx, pls[best_idx] * 1.3),
                     ha='center', fontsize=9, fontweight='bold', color='green')

    fig.suptitle('Fig. 4: Scheduling Policy Comparison (d=7)', fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig4_policy_comparison.png'), bbox_inches='tight')
    print('  fig4_policy_comparison.png')


# ═══════════════════════════════════════════════════════════════
#  Fig 5: MPC vs Reactive Decoder Switching
# ═══════════════════════════════════════════════════════════════
def fig5_decoder_switching():
    if not os.path.exists(os.path.join(OUT, 'e3_decoder_switching.json')):
        print('  [SKIP] e3_decoder_switching.json not found')
        return

    data = json.load(open(os.path.join(OUT, 'e3_decoder_switching.json')))

    fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))

    strats = ['static', 'reactive_h2', 'mpc_h5', 'oracle']
    strat_labels = ['Static\nMWPM', 'Reactive\nCUSUM', 'MPC\nH=5', 'Oracle']
    colors_s = ['#9E9E9E', '#FFC107', '#2196F3', '#4CAF50']

    for ax_idx, (drift_name, ax) in enumerate(zip(
            ['slow', 'medium', 'step', 'oscillating'], axes)):
        x = np.arange(len(strats))
        pls = []
        for s in strats:
            key = f"d7_{drift_name}_{s}"
            if key in data:
                pls.append(data[key]['avg_p_L'])
            else:
                pls.append(0)

        bars = ax.bar(x, pls, color=colors_s, alpha=0.85, edgecolor='black', lw=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(strat_labels, fontsize=8)
        ax.set_ylabel('$p_L$')
        ax.set_title(drift_name)
        ax.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))

    fig.suptitle('Fig. 5: Decoder Switching Strategies Under Drift (d=7)',
                 fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig5_decoder_switching.png'), bbox_inches='tight')
    print('  fig5_decoder_switching.png')


# ═══════════════════════════════════════════════════════════════
#  Fig 6: CV vs DV Drift Tracking
# ═══════════════════════════════════════════════════════════════
def fig6_drift_tracking():
    data = json.load(open(os.path.join(OUT, 'e4_drift_tracking.json')))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    drifts = ['stable', 'slow', 'medium', 'fast']
    x = np.arange(len(drifts))
    width = 0.35

    for d_idx, (d, ax) in enumerate(zip([5, 7], [ax1, ax2])):
        cv_errs = []
        dv_errs = []
        for drift in drifts:
            key = f"d{d}_{drift}"
            if key in data:
                cv_errs.append(data[key]['cv_median_error'] * 100)
                dv_errs.append(data[key]['dv_median_error'] * 100)
            else:
                cv_errs.append(0)
                dv_errs.append(0)

        ax.bar(x - width/2, cv_errs, width, label='CV (GKP residuals)',
               color='#4CAF50', alpha=0.85)
        ax.bar(x + width/2, dv_errs, width, label='DV (100-cycle window)',
               color='#F44336', alpha=0.85)

        ax.set_xticks(x)
        ax.set_xticklabels(drifts)
        ax.set_ylabel('Median V_eff estimation error (%)')
        ax.set_title(f'd = {d}')
        ax.legend()
        ax.grid(True, axis='y', alpha=0.3)

    fig.suptitle('Fig. 6: Zero-Overhead Calibration — CV vs DV Drift Tracking',
                 fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig6_drift_tracking.png'), bbox_inches='tight')
    print('  fig6_drift_tracking.png')


def fig7_stim_drift_coupling():
    """Fig 7: Stim-verified wall-time drift coupling with Wilson CIs."""
    if not os.path.exists(os.path.join(OUT, 'e2_stim.json')):
        print('  [SKIP] e2_stim.json not found')
        return

    data = json.load(open(os.path.join(OUT, 'e2_stim.json')))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    factories = [0, 1, 3, 8, 12]

    for drift, color, marker, ls in [
        (0.2, '#2196F3', 'o', '-'),
        (0.5, '#F44336', 's', '--'),
    ]:
        for d, ax in [(5, ax1), (7, ax2)]:
            pls, los, his = [], [], []
            for f in factories:
                k = f'd{d}_drift{drift}_F{f}_rho0.0_mwpm'
                if k in data:
                    v = data[k]
                    pls.append(v['p_L'])
                    los.append(v['ci_lo'])
                    his.append(v['ci_hi'])
                else:
                    pls.append(0); los.append(0); his.append(0)

            pls, los, his = np.array(pls), np.array(los), np.array(his)
            yerr = [pls - los, his - pls]
            ax.errorbar(factories, pls, yerr=yerr, fmt=f'{marker}{ls}',
                       color=color, lw=2, ms=7, capsize=4, capthick=1.5,
                       label=f'drift={drift} SNU/s')

    for d, ax in [(5, ax1), (7, ax2)]:
        ax.set_xlabel('Number of factories F')
        ax.set_ylabel('Logical error rate $p_L$ (Stim)')
        ax.set_title(f'd = {d}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_yscale('log')

    fig.suptitle('Fig. 7: TDM Wall-Time Drift Coupling (Stim Monte Carlo, Wilson 95% CI)',
                 fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig7_stim_drift_coupling.png'), bbox_inches='tight')
    print('  fig7_stim_drift_coupling.png')


def fig8_stim_decoder_trajectory():
    """Fig 8: Decoder performance along drift trajectory (Stim)."""
    if not os.path.exists(os.path.join(OUT, 'e3_stim.json')):
        print('  [SKIP] e3_stim.json not found')
        return

    data = json.load(open(os.path.join(OUT, 'e3_stim.json')))

    fig, ax = plt.subplots(figsize=(9, 5.5))

    labels_order = ['stable_t0', 'med_t30', 'med_t60', 'med_t120', 'step_after']
    x_labels = ['stable\n$\\rho$=0.03', 'med t=30s\n$\\rho$=0.10',
                'med t=60s\n$\\rho$=0.15', 'med t=120s\n$\\rho$=0.20',
                'step after\n$\\rho$=0.18']

    d = 7
    x = np.arange(len(labels_order))
    width = 0.35

    for di, (decoder, color, label) in enumerate([
        ('mwpm', '#F44336', 'Vanilla MWPM'),
        ('residual_sub', '#4CAF50', 'Residual Subtraction'),
    ]):
        pls, los, his = [], [], []
        for lbl in labels_order:
            k = f'd{d}_{lbl}_{decoder}'
            if k in data:
                v = data[k]
                pls.append(max(v['p_L'], 1e-5))
                los.append(max(v['ci_lo'], 1e-5))
                his.append(v['ci_hi'])
            else:
                pls.append(1e-5); los.append(1e-5); his.append(1e-4)

        pls, los, his = np.array(pls), np.array(los), np.array(his)
        yerr = [pls - los, his - pls]
        ax.bar(x + di * width, pls, width, yerr=yerr, color=color, alpha=0.85,
               label=label, capsize=3, error_kw={'lw': 1.2}, edgecolor='black', lw=0.5)

    ax.set_xticks(x + width / 2)
    ax.set_xticklabels(x_labels, fontsize=9)
    ax.set_ylabel('Logical error rate $p_L$ (Stim)')
    ax.set_yscale('log')
    ax.set_ylim(1e-4, 0.5)
    ax.legend(fontsize=11)
    ax.grid(True, axis='y', alpha=0.3, which='both')

    # Annotate ratios
    for i, lbl in enumerate(labels_order):
        km = f'd{d}_{lbl}_mwpm'
        kr = f'd{d}_{lbl}_residual_sub'
        if km in data and kr in data:
            pm = data[km]['p_L']
            pr = data[kr]['p_L']
            if pr > 0:
                ratio = pm / pr
                ax.annotate(f'{ratio:.0f}x', xy=(i + width/2, max(pm, pr) * 1.3),
                           ha='center', fontsize=9, fontweight='bold', color='#1565C0')

    fig.suptitle('Fig. 8: Decoder Performance Along Drift Trajectory (d=7, Stim Monte Carlo)',
                 fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig8_stim_decoder_trajectory.png'), bbox_inches='tight')
    print('  fig8_stim_decoder_trajectory.png')


if __name__ == '__main__':
    print("Generating Paper 4 figures...")
    fig1_scalability()
    fig2_factory_overhead()
    fig3_v_tradeoff()
    fig4_policy_comparison()
    fig5_decoder_switching()
    fig6_drift_tracking()
    fig7_stim_drift_coupling()
    fig8_stim_decoder_trajectory()
    print("Done.")
