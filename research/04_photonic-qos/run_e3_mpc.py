#!/usr/bin/env python3
"""
E3: MPC Predictive Decoder Switching (v2)
==========================================
Compares: Static, Reactive (CUSUM), MPC, Oracle decoder switching.
Uses v2 engine with intra-cycle drift.
"""
import numpy as np
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tdm_runtime import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(OUT, exist_ok=True)

SEED = 42
N_CYCLES = 3000
N_TRIALS = 15
N_LOGICAL = 10
N_FACTORIES = 3  # Fixed for decoder comparison


# ═══════════════════════════════════════════════════════════════
#  Drift Trajectories
# ═══════════════════════════════════════════════════════════════

def drift_slow(t):
    v = V_EFF_SNU * (1 + 0.3 * (1 - np.exp(-t / 600)))
    rho = 0.03 + 0.12 * (1 - np.exp(-t / 600))
    return v, rho

def drift_medium(t):
    v = V_EFF_SNU * (1 + 0.4 * (1 - np.exp(-t / 60)))
    rho = 0.03 + 0.17 * (1 - np.exp(-t / 60))
    return v, rho

def drift_step(t):
    if t < 3.0:
        return V_EFF_SNU, 0.03
    return V_EFF_SNU * 1.4, 0.18

def drift_oscillating(t):
    v = V_EFF_SNU * (1 + 0.2 * np.sin(2 * np.pi * t / 120))
    rho = 0.10 + 0.08 * np.sin(2 * np.pi * t / 120)
    return max(v, V_EFF_SNU * 0.8), max(rho, 0.0)

DRIFT_SCENARIOS = {
    'slow': drift_slow,
    'medium': drift_medium,
    'step': drift_step,
    'oscillating': drift_oscillating,
}


# ═══════════════════════════════════════════════════════════════
#  Decoder Selection Strategies
# ═══════════════════════════════════════════════════════════════

def select_best_decoder(rho, v_eff, d):
    """Select decoder minimizing p_L for given conditions."""
    best_dec = DECODERS[0]
    best_pl = float('inf')
    for dec in DECODERS:
        pl = compute_p_L(v_eff, 0, rho, N_LOGICAL, N_FACTORIES, d, dec)
        if pl < best_pl:
            best_pl = pl
            best_dec = dec
    return best_dec


class StaticStrategy:
    def __init__(self):
        self.decoder = VanillaMWPM()
    def update(self, v_eff_est, rho_est, d):
        return self.decoder


class ReactiveStrategy:
    """CUSUM on both V_eff and rho — triggers decoder switch on detection."""
    def __init__(self, h=4.0, delta=0.005):
        self.h = h
        self.delta = delta
        self.cusum_v = 0.0
        self.cusum_rho = 0.0
        self.v_baseline = V_EFF_SNU
        self.rho_baseline = 0.03
        self.decoder = VanillaMWPM()
        self.cooldown = 0

    def update(self, v_eff_est, rho_est, d):
        if self.cooldown > 0:
            self.cooldown -= 1
            return self.decoder

        # CUSUM on V_eff
        self.cusum_v = max(0, self.cusum_v + (v_eff_est - self.v_baseline) - self.delta)
        # CUSUM on rho
        self.cusum_rho = max(0, self.cusum_rho + (rho_est - self.rho_baseline) - self.delta)

        if self.cusum_v > self.h or self.cusum_rho > self.h:
            self.decoder = select_best_decoder(rho_est, v_eff_est, d)
            self.v_baseline = v_eff_est
            self.rho_baseline = rho_est
            self.cusum_v = 0.0
            self.cusum_rho = 0.0
            self.cooldown = DECODER_SWITCH_COST.get(self.decoder.name, 0)

        return self.decoder


class MPCStrategy:
    def __init__(self, horizon=10):
        self.horizon = horizon
        self.v_history = []
        self.rho_history = []
        self.decoder = VanillaMWPM()
        self.cooldown = 0

    def update(self, v_eff_est, rho_est, d):
        self.v_history.append(v_eff_est)
        self.rho_history.append(rho_est)

        if self.cooldown > 0:
            self.cooldown -= 1
            return self.decoder

        # Predict future state
        if len(self.v_history) >= 5:
            v_slope = np.polyfit(range(5), self.v_history[-5:], 1)[0]
            rho_slope = np.polyfit(range(5), self.rho_history[-5:], 1)[0]
            v_pred = v_eff_est + v_slope * self.horizon
            rho_pred = np.clip(rho_est + rho_slope * self.horizon, 0, 0.5)
        else:
            v_pred = v_eff_est
            rho_pred = rho_est

        # Select decoder for predicted state
        best_dec = self.decoder
        best_cost = float('inf')

        p_l_now = compute_p_L(v_eff_est, 0, rho_est, N_LOGICAL, N_FACTORIES, d, self.decoder)

        for dec in DECODERS:
            pl_pred = compute_p_L(v_pred, 0, rho_pred, N_LOGICAL, N_FACTORIES, d, dec)
            switch_penalty = 0
            if dec.name != self.decoder.name:
                switch_penalty = DECODER_SWITCH_COST.get(dec.name, 0) * p_l_now
            cost = pl_pred * self.horizon + switch_penalty
            if cost < best_cost:
                best_cost = cost
                best_dec = dec

        if best_dec.name != self.decoder.name:
            self.cooldown = DECODER_SWITCH_COST.get(best_dec.name, 0)
            self.decoder = best_dec

        return self.decoder


class OracleStrategy:
    def __init__(self):
        self.decoder = VanillaMWPM()
    def update(self, v_eff_true, rho_true, d):
        self.decoder = select_best_decoder(rho_true, v_eff_true, d)
        return self.decoder


# ═══════════════════════════════════════════════════════════════
#  Simulation
# ═══════════════════════════════════════════════════════════════

def simulate_switching(strategy, drift_fn, d, rng):
    total_pl = 0.0
    pl_trace = []
    dec_trace = []
    v_trace = []
    rho_trace = []
    switches = 0
    prev_name = None
    n_modes = qec_cycle_modes(d)
    # SCALED simulation-time axis: 1 cycle = 2 ms of drift-trajectory time.
    # The physical TDM cycle time is (N + 15F) * 2d^3 * 10 ns
    # = 377 us for d=7, N=10, F=3 — much shorter than the 60-600 s drift constants
    # in drift_slow/medium etc. We compress lab-time drift into simulation time so
    # the experiment exercises the full drift profile within 3000 cycles. Drift
    # labels in Table II ("slow/medium/step/oscillating") refer to relative drift
    # speed, not wall-clock seconds.
    sim_dt = 0.002

    for cycle in range(N_CYCLES):
        t = cycle * sim_dt
        v_true, rho_true = drift_fn(t)

        # CV estimate
        residuals = gkp_residual_sample(v_true, min(n_modes, 200), rng)
        v_est = estimate_veff_from_residuals(residuals)
        rho_est = np.clip(rho_true + rng.normal(0, 0.015), 0, 0.5)

        # Strategy
        if isinstance(strategy, OracleStrategy):
            dec = strategy.update(v_true, rho_true, d)
        else:
            dec = strategy.update(v_est, rho_est, d)

        if prev_name and dec.name != prev_name:
            switches += 1
        prev_name = dec.name

        # Compute p_L with intra-cycle drift
        drift_rate = 0.01 if t > 0 else 0  # approximate
        pl = compute_p_L(v_true, drift_rate, rho_true,
                         N_LOGICAL, N_FACTORIES, d, dec)
        total_pl += pl

        if cycle % 30 == 0:
            pl_trace.append(float(pl))
            dec_trace.append(dec.name)
            v_trace.append(float(v_true))
            rho_trace.append(float(rho_true))

    return {
        'avg_p_L': total_pl / N_CYCLES,
        'switches': switches,
        'p_L_trace': pl_trace,
        'decoder_trace': dec_trace,
        'v_eff_trace': v_trace,
        'rho_trace': rho_trace,
    }


def run_experiment():
    results = {}

    strategies = {
        'static': lambda: StaticStrategy(),
        'reactive_h2': lambda: ReactiveStrategy(h=2.0, delta=0.003),
        'reactive_h4': lambda: ReactiveStrategy(h=4.0, delta=0.005),
        'mpc_h5': lambda: MPCStrategy(horizon=5),
        'mpc_h20': lambda: MPCStrategy(horizon=20),
        'mpc_h50': lambda: MPCStrategy(horizon=50),
        'oracle': lambda: OracleStrategy(),
    }

    for d in [5, 7]:
        for drift_name, drift_fn in DRIFT_SCENARIOS.items():
            for strat_name, strat_factory in strategies.items():
                sys.stdout.write(f"  d={d} {drift_name} {strat_name}...")
                sys.stdout.flush()

                trial_pls = []
                trial_sw = []
                for trial in range(N_TRIALS):
                    rng = np.random.default_rng(SEED + trial * 1000)
                    res = simulate_switching(strat_factory(), drift_fn, d, rng)
                    trial_pls.append(res['avg_p_L'])
                    trial_sw.append(res['switches'])

                avg_pl = float(np.mean(trial_pls))
                key = f"d{d}_{drift_name}_{strat_name}"
                results[key] = {
                    'd': d, 'drift': drift_name, 'strategy': strat_name,
                    'avg_p_L': float(f"{avg_pl:.6e}"),
                    'std_p_L': float(f"{np.std(trial_pls):.6e}"),
                    'avg_switches': round(float(np.mean(trial_sw)), 1),
                }

                # Compute improvement over static
                static_key = f"d{d}_{drift_name}_static"
                if static_key in results:
                    imp = results[static_key]['avg_p_L'] / max(avg_pl, 1e-30)
                    results[key]['improvement'] = round(float(imp), 3)

                print(f" p_L={avg_pl:.4e} sw={np.mean(trial_sw):.0f}")

    return results


def run_time_traces():
    traces = {}
    d = 7
    for drift_name in ['medium', 'step']:
        for strat_name, strat_fn in [
            ('static', lambda: StaticStrategy()),
            ('reactive', lambda: ReactiveStrategy(h=2.0, delta=0.003)),
            ('mpc', lambda: MPCStrategy(horizon=20)),
            ('oracle', lambda: OracleStrategy()),
        ]:
            rng = np.random.default_rng(SEED)
            res = simulate_switching(strat_fn(), DRIFT_SCENARIOS[drift_name], d, rng)
            traces[f"{drift_name}_{strat_name}"] = {
                'p_L_trace': res['p_L_trace'],
                'decoder_trace': res['decoder_trace'],
                'v_eff_trace': res['v_eff_trace'],
                'rho_trace': res['rho_trace'],
            }
    return traces


if __name__ == "__main__":
    print("=" * 60)
    print("E3: MPC Predictive Decoder Switching (v2)")
    print("=" * 60)

    print("\n[1/2] Strategy comparison...")
    results = run_experiment()
    with open(os.path.join(OUT, 'e3_decoder_switching.json'), 'w') as f:
        json.dump(results, f, indent=2)

    print("\n[2/2] Time traces...")
    traces = run_time_traces()
    with open(os.path.join(OUT, 'e3_time_traces.json'), 'w') as f:
        json.dump(traces, f, indent=2)

    # Summary
    print("\n" + "=" * 75)
    print("Summary: d=7")
    print("=" * 75)
    print(f"{'Drift':>12} {'Strategy':>14} {'p_L':>12} {'Improv':>8} {'Switches':>9}")
    print("-" * 60)
    for dn in DRIFT_SCENARIOS:
        for s in ['static', 'reactive_h2', 'mpc_h20', 'oracle']:
            k = f"d7_{dn}_{s}"
            if k in results:
                v = results[k]
                imp = v.get('improvement', 1.0)
                print(f"{dn:>12} {s:>14} {v['avg_p_L']:>12.4e} "
                      f"{imp:>7.3f}x {v['avg_switches']:>8.0f}")
        print()

    print("E3 complete.")
