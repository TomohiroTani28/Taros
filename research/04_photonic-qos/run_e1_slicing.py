#!/usr/bin/env python3
"""
E1: Quantum Network Slicing — TDM Resource Grid Analysis
=========================================================
Analogous to 5G OFDM resource block allocation.
Computes slot allocation overhead for d=3,5,7 with varying logical qubit counts
and T-gate densities. Compares CV (zero-overhead calibration) vs DV (dedicated slots).
"""
import numpy as np
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tdm_runtime import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(OUT, exist_ok=True)

def analyze_slot_budget():
    """Compute TDM slot budget for different configurations."""
    results = {}

    for d in [3, 5, 7]:
        modes_per_qec = qec_cycle_modes(d)
        cycle_us = qec_cycle_us(d)
        modes_per_round = qec_modes_per_round(d)
        n_rounds = qec_rounds(d)
        factory_modes = factory_modes_per_distillation(d)

        for n_logical in [1, 5, 10, 50, 100]:
            # Total modes per QEC cycle for all data qubits
            data_modes = n_logical * modes_per_qec

            # Magic state factory: 1 factory per ~10 data qubits
            n_factories = max(1, n_logical // 10)
            fact_modes = n_factories * factory_modes

            # Total TDM stream length per QEC cycle
            total_modes = data_modes + fact_modes

            # Time for one full QEC cycle
            total_us = total_modes * SLOT_NS / 1000

            # Slot fractions
            data_frac = data_modes / total_modes
            factory_frac = fact_modes / total_modes

            # CV: calibration from GKP residuals (zero overhead)
            cv_calib_frac = 0.0
            cv_compute_frac = data_frac
            cv_factory_frac = factory_frac

            # DV: need dedicated calibration slots (5% typical)
            dv_calib_frac = 0.05
            dv_compute_frac = data_frac * (1 - dv_calib_frac)
            dv_factory_frac = factory_frac * (1 - dv_calib_frac)

            # Logical gate rate
            # One logical Clifford gate per QEC cycle per qubit
            cv_gate_rate_hz = 1.0 / (total_us * 1e-6)
            dv_gate_rate_hz = cv_gate_rate_hz * (1 - dv_calib_frac)

            # T-gate rate (limited by factory throughput)
            # 15-to-1 distillation: 1 magic state per d QEC cycles per factory
            t_rate_per_factory = 1.0 / (d * total_us * 1e-6)
            cv_t_rate = n_factories * t_rate_per_factory
            dv_t_rate = cv_t_rate * (1 - dv_calib_frac)

            key = f"d{d}_n{n_logical}"
            results[key] = {
                "d": d,
                "n_logical": n_logical,
                "n_factories": n_factories,
                "modes_per_qec_cycle": modes_per_qec,
                "data_modes": data_modes,
                "factory_modes": fact_modes,
                "total_modes": total_modes,
                "cycle_time_us": round(total_us, 2),
                "cv_data_frac": round(cv_compute_frac, 4),
                "cv_factory_frac": round(cv_factory_frac, 4),
                "cv_calib_frac": 0.0,
                "dv_data_frac": round(dv_compute_frac, 4),
                "dv_factory_frac": round(dv_factory_frac, 4),
                "dv_calib_frac": dv_calib_frac,
                "cv_gate_rate_hz": round(cv_gate_rate_hz, 1),
                "dv_gate_rate_hz": round(dv_gate_rate_hz, 1),
                "cv_t_rate_hz": round(cv_t_rate, 2),
                "dv_t_rate_hz": round(dv_t_rate, 2),
                "cv_throughput_advantage": round(1 / (1 - dv_calib_frac), 4),
            }

    return results


def analyze_t_gate_density():
    """Analyze optimal factory ratio for different T-gate densities."""
    results = {}

    for d in [3, 5, 7]:
        modes_per_qec = qec_cycle_modes(d)

        for n_logical in [10, 50]:
            for t_density in [0.01, 0.05, 0.10, 0.20, 0.50]:
                # t_density = fraction of gates that are T-gates
                data_modes = n_logical * modes_per_qec

                # Required T-gate rate
                gate_rate_per_qubit = 1.0 / (data_modes * SLOT_NS * 1e-9)
                required_t_rate = t_density * gate_rate_per_qubit * n_logical

                # How many factories needed?
                t_per_factory = 1.0 / (d * data_modes * SLOT_NS * 1e-9)
                n_factories_needed = int(np.ceil(required_t_rate / t_per_factory))

                # Factory overhead
                fact_modes = n_factories_needed * factory_modes_per_distillation(d)
                total_modes = data_modes + fact_modes
                factory_overhead = fact_modes / total_modes

                # Effective throughput (T-gates/sec actually achievable)
                actual_t_rate = min(required_t_rate,
                                    n_factories_needed * t_per_factory)

                key = f"d{d}_n{n_logical}_td{t_density:.2f}"
                results[key] = {
                    "d": d,
                    "n_logical": n_logical,
                    "t_density": t_density,
                    "n_factories_needed": n_factories_needed,
                    "factory_overhead_frac": round(factory_overhead, 4),
                    "required_t_rate_hz": round(required_t_rate, 1),
                    "actual_t_rate_hz": round(actual_t_rate, 1),
                    "total_modes": total_modes,
                }

    return results


def analyze_scalability():
    """TDM scalability: hardware constant, time scales linearly."""
    results = {}

    for d in [3, 5, 7]:
        for n_logical in [1, 5, 10, 50, 100, 500, 1000]:
            modes_per_qec = qec_cycle_modes(d)
            n_factories = max(1, n_logical // 10)

            # TDM: single physical device, time increases
            tdm_total_modes = (n_logical + n_factories * 15) * modes_per_qec
            tdm_cycle_us = tdm_total_modes * SLOT_NS / 1000
            tdm_physical_devices = 1  # Always 1 TDM device

            # Superconducting comparison: need physical qubits
            # ~2d^2 physical qubits per logical qubit (data + ancilla)
            sc_physical_qubits = n_logical * 2 * d * d + n_factories * 15 * 2 * d * d
            sc_cycle_us = qec_cycle_us(d)  # Fixed per cycle (parallel)
            sc_physical_devices = sc_physical_qubits  # Each qubit is a device

            key = f"d{d}_n{n_logical}"
            results[key] = {
                "d": d,
                "n_logical": n_logical,
                "tdm_cycle_us": round(tdm_cycle_us, 2),
                "tdm_physical_devices": tdm_physical_devices,
                "tdm_total_modes": tdm_total_modes,
                "sc_physical_qubits": sc_physical_qubits,
                "sc_cycle_us": round(sc_cycle_us, 2),
                "hardware_ratio": sc_physical_qubits / tdm_physical_devices,
                "time_ratio": round(tdm_cycle_us / sc_cycle_us, 2),
            }

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("E1: Quantum Network Slicing — TDM Resource Analysis")
    print("=" * 60)

    print("\n[1/3] Slot budget analysis...")
    slot_results = analyze_slot_budget()
    with open(os.path.join(OUT, 'e1_slot_budget.json'), 'w') as f:
        json.dump(slot_results, f, indent=2)

    # Print summary table
    print(f"\n{'d':>3} {'N_log':>5} {'Cycle(us)':>10} {'CV_data%':>9} {'CV_fact%':>9} "
          f"{'DV_data%':>9} {'DV_calib%':>10} {'CV_adv':>7}")
    print("-" * 75)
    for k, v in slot_results.items():
        print(f"{v['d']:>3} {v['n_logical']:>5} {v['cycle_time_us']:>10.2f} "
              f"{v['cv_data_frac']*100:>8.1f}% {v['cv_factory_frac']*100:>8.1f}% "
              f"{v['dv_data_frac']*100:>8.1f}% {v['dv_calib_frac']*100:>9.1f}% "
              f"{v['cv_throughput_advantage']:>6.2f}x")

    print("\n[2/3] T-gate density optimization...")
    tgate_results = analyze_t_gate_density()
    with open(os.path.join(OUT, 'e1_tgate_density.json'), 'w') as f:
        json.dump(tgate_results, f, indent=2)

    print(f"\n{'d':>3} {'N_log':>5} {'T_dens':>7} {'Factories':>10} {'Overhead%':>10} "
          f"{'T_rate(Hz)':>11}")
    print("-" * 55)
    for k, v in tgate_results.items():
        print(f"{v['d']:>3} {v['n_logical']:>5} {v['t_density']:>6.0%} "
              f"{v['n_factories_needed']:>10} {v['factory_overhead_frac']*100:>9.1f}% "
              f"{v['actual_t_rate_hz']:>10.1f}")

    print("\n[3/3] Scalability analysis...")
    scale_results = analyze_scalability()
    with open(os.path.join(OUT, 'e1_scalability.json'), 'w') as f:
        json.dump(scale_results, f, indent=2)

    print(f"\n{'d':>3} {'N_log':>5} {'TDM_cycle(us)':>14} {'TDM_hw':>7} "
          f"{'SC_qubits':>10} {'HW_ratio':>9} {'Time_ratio':>11}")
    print("-" * 70)
    for k, v in scale_results.items():
        print(f"{v['d']:>3} {v['n_logical']:>5} {v['tdm_cycle_us']:>13.1f} "
              f"{v['tdm_physical_devices']:>7} {v['sc_physical_qubits']:>10} "
              f"{v['hardware_ratio']:>8.0f}x {v['time_ratio']:>10.1f}x")

    print("\nE1 complete. Results saved to results/e1_*.json")
