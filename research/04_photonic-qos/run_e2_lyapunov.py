#!/usr/bin/env python3
"""
E2: Lyapunov Drift-Plus-Penalty Optimal Scheduling (v2)
========================================================
Key v2 improvement: factory allocation affects p_L via intra-cycle drift.
More factories → longer TDM cycle → more drift accumulation → higher p_L.
This creates a genuine V-parameter tradeoff.
"""
import numpy as np
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tdm_runtime import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(OUT, exist_ok=True)

SEED = 42
N_CYCLES = 2000
N_TRIALS = 10
N_LOGICAL = 10

# ═══════════════════════════════════════════════════════════════
#  Scheduling Policies
# ═══════════════════════════════════════════════════════════════

# Factory allocation options (number of factories)
FACTORY_OPTIONS = [0, 1, 2, 3, 5, 8, 12]

def policy_fixed(state, params):
    """Fixed factory count."""
    return {'n_factories': params.get('n_factories', 3), 'decoder_idx': 0}

def policy_greedy(state, params):
    """Greedy: adjust factories based on buffer."""
    buf = state['magic_buffer']
    if buf > 10:
        return {'n_factories': 1, 'decoder_idx': 0}
    elif buf < 2:
        return {'n_factories': 8, 'decoder_idx': 0}
    else:
        return {'n_factories': 3, 'decoder_idx': 0}

def policy_lyapunov(state, params):
    """Lyapunov drift-plus-penalty scheduler.
    Minimize: V * p_L(action) + Q * (demand - production(action))
    where p_L depends on factory count via intra-cycle drift.
    """
    v_param = params.get('V', 10.0)
    q_buf = state['magic_buffer']
    v_eff = state['v_eff_est']
    rho = state['rho_est']
    drift_rate = state['drift_rate_est']
    t_demand = state['t_demand_norm']
    d = params['d']

    best_action = None
    best_cost = float('inf')

    for nf in FACTORY_OPTIONS:
        for di, dec in enumerate(DECODERS):
            # p_L depends on n_factories via cycle time
            p_l = compute_p_L(v_eff, drift_rate, rho,
                              N_LOGICAL, nf, d, dec)

            # T-gate production rate (normalized)
            t_prod = compute_t_throughput(nf, d, N_LOGICAL, v_eff)
            # Normalize to demand scale
            ct = tdm_cycle_time_sec(N_LOGICAL, nf, d)
            prod_norm = t_prod * ct if ct > 0 else 0

            # Drift-plus-penalty
            penalty = p_l
            drift = q_buf * (t_demand - prod_norm)
            cost = v_param * penalty + drift

            if cost < best_cost:
                best_cost = cost
                best_action = {'n_factories': nf, 'decoder_idx': di}

    return best_action

def policy_lyapunov_cv(state, params):
    """Lyapunov with CV zero-overhead calibration."""
    return policy_lyapunov(state, params)

def policy_lyapunov_dv(state, params):
    """Lyapunov for DV: noisy estimation + calibration overhead."""
    action = policy_lyapunov(state, params)
    action['calib_overhead'] = 0.05
    action['est_noise'] = 0.15
    return action


# ═══════════════════════════════════════════════════════════════
#  Simulation Engine v2
# ═══════════════════════════════════════════════════════════════

def simulate(policy_fn, params, drift_rate_snu_per_sec, rho_base, rng):
    d = params['d']
    v_param = params.get('V', 10.0)

    magic_buffer = 5.0
    current_decoder_idx = 0
    current_nf = 3  # track current factory count for cycle time
    switch_cooldown = 0
    total_p_l = 0.0
    total_t_completed = 0
    total_t_requested = 0
    total_stalls = 0
    buffer_trace = []
    p_l_trace = []
    factory_trace = []
    wall_time = 0.0  # accumulated wall clock time (seconds)

    v_eff_history = []

    for cycle in range(N_CYCLES):
        # Wall clock advances by actual cycle time (depends on factory count)
        ct = tdm_cycle_time_sec(N_LOGICAL, current_nf, d)
        wall_time += ct

        # True hardware state (drift accumulates with wall time)
        v_eff_true = V_EFF_SNU + drift_rate_snu_per_sec * wall_time
        rho_true = np.clip(rho_base + drift_rate_snu_per_sec * wall_time * 0.5, 0, 0.4)

        # CV estimate from GKP residuals
        n_modes = qec_cycle_modes(d)
        residuals = gkp_residual_sample(v_eff_true, min(n_modes, 200), rng)
        v_eff_est = estimate_veff_from_residuals(residuals)
        v_eff_history.append(v_eff_est)

        # Estimate drift rate from history
        if len(v_eff_history) >= 10:
            recent = v_eff_history[-10:]
            drift_rate_est = (recent[-1] - recent[0]) / (9 * 0.001)
        else:
            drift_rate_est = 0.0

        # T-gate demand
        t_demand = rng.poisson(0.5)
        total_t_requested += t_demand

        state = {
            'magic_buffer': magic_buffer,
            'v_eff_est': v_eff_est,
            'rho_est': rho_true + rng.normal(0, 0.01),
            'drift_rate_est': drift_rate_est,
            't_demand_norm': t_demand / max(N_LOGICAL, 1),
            'cycle': cycle,
        }

        # Get action
        action = policy_fn(state, params)
        nf = action['n_factories']
        di = action['decoder_idx']
        calib_oh = action.get('calib_overhead', 0.0)
        est_noise = action.get('est_noise', 0.0)

        # Apply DV estimation noise
        if est_noise > 0:
            v_eff_for_calc = v_eff_true * (1 + rng.normal(0, est_noise))
        else:
            v_eff_for_calc = v_eff_true

        # Effective factory count after calibration overhead.
        # Use round() to avoid silently truncating nf=1 to 0 when calib_oh = 0.05.
        nf_effective = max(0, round(nf * (1 - calib_oh)))
        current_nf = nf_effective  # update for next cycle's wall-time calculation

        # Compute actual p_L (with true V_eff and intra-cycle drift)
        dec = DECODERS[min(di, len(DECODERS)-1)]

        # Handle decoder switching
        if di != current_decoder_idx:
            if switch_cooldown <= 0:
                switch_cooldown = DECODER_SWITCH_COST.get(dec.name, 0)
                current_decoder_idx = di
            else:
                switch_cooldown -= 1
                dec = DECODERS[current_decoder_idx]

        p_l = compute_p_L(v_eff_true, drift_rate_snu_per_sec, rho_true,
                          N_LOGICAL, nf_effective, d, dec)
        total_p_l += p_l

        # Magic state production
        ct = tdm_cycle_time_sec(N_LOGICAL, nf_effective, d)
        t_rate = compute_t_throughput(nf_effective, d, N_LOGICAL, v_eff_true)
        new_magic = rng.poisson(max(t_rate * ct, 0.01))
        magic_buffer += new_magic

        # Consume magic states
        t_completed = min(t_demand, int(magic_buffer))
        magic_buffer -= t_completed
        total_t_completed += t_completed
        if t_demand > t_completed:
            total_stalls += t_demand - t_completed

        # Traces (subsample)
        if cycle % 20 == 0:
            buffer_trace.append(float(magic_buffer))
            p_l_trace.append(float(p_l))
            factory_trace.append(nf)

    return {
        'avg_p_L': total_p_l / N_CYCLES,
        'total_t_completed': total_t_completed,
        'total_t_requested': total_t_requested,
        't_utilization': total_t_completed / max(1, total_t_requested),
        'avg_buffer': float(np.mean(buffer_trace)),
        'max_buffer': float(np.max(buffer_trace)) if buffer_trace else 0,
        'total_stalls': total_stalls,
        'buffer_trace': buffer_trace,
        'p_l_trace': p_l_trace,
        'factory_trace': factory_trace,
    }


def run_policy_comparison():
    print("\n[1/2] Policy comparison...")
    results = {}

    policies = {
        'fixed_1': (policy_fixed, {'n_factories': 1}),
        'fixed_3': (policy_fixed, {'n_factories': 3}),
        'fixed_8': (policy_fixed, {'n_factories': 8}),
        'greedy': (policy_greedy, {}),
        'lyapunov_V1': (policy_lyapunov, {'V': 1.0}),
        'lyapunov_V10': (policy_lyapunov, {'V': 10.0}),
        'lyapunov_V100': (policy_lyapunov, {'V': 100.0}),
        'lyapunov_V1000': (policy_lyapunov, {'V': 1000.0}),
        'lyapunov_cv': (policy_lyapunov_cv, {'V': 50.0}),
        'lyapunov_dv': (policy_lyapunov_dv, {'V': 50.0}),
    }

    drift_scenarios = {
        'stable':     (0.0,   0.05),
        'slow_drift': (0.05,  0.05),   # ~+7% V_eff per second
        'fast_drift': (0.5,   0.05),   # ~+70% V_eff per second
        'high_rho':   (0.1,   0.15),
    }

    for d in [5, 7]:
        for drift_name, (drift_rate, rho_base) in drift_scenarios.items():
            for pol_name, (pol_fn, pol_extra) in policies.items():
                sys.stdout.write(f"  d={d} {drift_name} {pol_name}...")
                sys.stdout.flush()

                trial_pls = []
                trial_utils = []
                trial_bufs = []
                trial_stalls = []

                for trial in range(N_TRIALS):
                    trial_rng = np.random.default_rng(SEED + trial * 1000)
                    params = {**pol_extra, 'd': d}
                    res = simulate(pol_fn, params, drift_rate, rho_base, trial_rng)
                    trial_pls.append(res['avg_p_L'])
                    trial_utils.append(res['t_utilization'])
                    trial_bufs.append(res['avg_buffer'])
                    trial_stalls.append(res['total_stalls'])

                avg_pl = float(np.mean(trial_pls))
                key = f"d{d}_{drift_name}_{pol_name}"
                results[key] = {
                    'd': d, 'drift': drift_name, 'policy': pol_name,
                    'avg_p_L': float(f"{avg_pl:.6e}"),
                    'std_p_L': float(f"{np.std(trial_pls):.6e}"),
                    't_utilization': round(float(np.mean(trial_utils)), 4),
                    'avg_buffer': round(float(np.mean(trial_bufs)), 2),
                    'avg_stalls': round(float(np.mean(trial_stalls)), 1),
                }
                print(f" p_L={avg_pl:.4e} util={np.mean(trial_utils):.3f}")

    return results


def run_v_tradeoff():
    print("\n[2/2] V-parameter tradeoff curve...")
    results = {}

    drift_rate = 0.2  # moderate drift: +0.2 SNU/sec
    rho_base = 0.10

    for d in [5, 7]:
        for v_param in [0.1, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 5000]:
            trial_pls = []
            trial_bufs = []
            trial_stalls = []
            trial_factories = []

            for trial in range(N_TRIALS):
                trial_rng = np.random.default_rng(SEED + trial * 1000)
                params = {'V': v_param, 'd': d}
                res = simulate(policy_lyapunov, params, drift_rate, rho_base, trial_rng)
                trial_pls.append(res['avg_p_L'])
                trial_bufs.append(res['avg_buffer'])
                trial_stalls.append(res['total_stalls'])
                trial_factories.append(np.mean(res['factory_trace']))

            key = f"d{d}_V{v_param}"
            results[key] = {
                'd': d, 'V': v_param,
                'avg_p_L': float(f"{np.mean(trial_pls):.6e}"),
                'std_p_L': float(f"{np.std(trial_pls):.6e}"),
                'avg_buffer': round(float(np.mean(trial_bufs)), 2),
                'avg_stalls': round(float(np.mean(trial_stalls)), 1),
                'avg_factories': round(float(np.mean(trial_factories)), 2),
            }
            print(f"  d={d} V={v_param:>6}: p_L={np.mean(trial_pls):.4e} "
                  f"buf={np.mean(trial_bufs):.1f} fact={np.mean(trial_factories):.1f} "
                  f"stalls={np.mean(trial_stalls):.0f}")

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("E2: Lyapunov Drift-Plus-Penalty Scheduling (v2)")
    print("  Key: factory count affects p_L via intra-cycle drift")
    print("=" * 60)

    policy_results = run_policy_comparison()
    with open(os.path.join(OUT, 'e2_policy_comparison.json'), 'w') as f:
        json.dump(policy_results, f, indent=2)

    tradeoff_results = run_v_tradeoff()
    with open(os.path.join(OUT, 'e2_v_tradeoff.json'), 'w') as f:
        json.dump(tradeoff_results, f, indent=2)

    # Summary
    print("\n" + "=" * 70)
    print("Summary: d=7, fast_drift")
    print("=" * 70)
    for pol in ['fixed_1', 'fixed_3', 'fixed_8', 'greedy',
                'lyapunov_V10', 'lyapunov_V100', 'lyapunov_cv', 'lyapunov_dv']:
        key = f"d7_fast_drift_{pol}"
        if key in policy_results:
            v = policy_results[key]
            print(f"  {pol:>15s}: p_L={v['avg_p_L']:.4e}  "
                  f"util={v['t_utilization']:.3f}  stalls={v['avg_stalls']:.0f}")

    print("\nE2 complete.")
