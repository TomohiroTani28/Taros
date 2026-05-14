#!/usr/bin/env python3
"""
TDM Photonic Quantum Runtime Simulator — Core Engine v2
========================================================
Key v2 improvement: intra-cycle drift accumulation.
In TDM, all logical qubits share one temporal pipeline.
More qubits/factories → longer cycle → more drift within one cycle → higher p_L.
This creates a real factory-allocation ↔ error-rate tradeoff.
"""
import numpy as np
from dataclasses import dataclass
from functools import lru_cache

# ═══════════════════════════════════════════════════════════════
#  TAROS Physical Parameters (from design/ documents)
# ═══════════════════════════════════════════════════════════════
TDM_CLOCK_HZ = 100e6
SLOT_NS = 10.0
SIGMA_EFF_DB = 8.5
# V_eff from Paper 3 full beamsplitter formula: eta*V_sqz + (1-eta) + V_nl
# = 0.914 * 0.0501 + 0.086 + 0.010 = 0.1417 SNU
V_EFF_SNU = 0.1417  # matches Papers 2/3 exactly

_SQPI = np.sqrt(np.pi)
_SQPI_HALF = _SQPI / 2


def qec_modes_per_round(d: int) -> int:
    return 2 * d * d

def qec_rounds(d: int) -> int:
    return d

def qec_cycle_modes(d: int) -> int:
    return qec_modes_per_round(d) * qec_rounds(d)

def qec_cycle_us(d: int) -> float:
    return qec_cycle_modes(d) * SLOT_NS / 1000

def factory_modes_per_distillation(d: int) -> int:
    return 15 * qec_cycle_modes(d)


# ═══════════════════════════════════════════════════════════════
#  Noise Model with Intra-Cycle Drift
# ═══════════════════════════════════════════════════════════════

@lru_cache(maxsize=8192)
def _erfc_cached(x: float) -> float:
    from scipy.special import erfc
    return float(erfc(x))

def p_phys_from_veff(v_eff: float) -> float:
    v_eff = round(v_eff, 6)
    arg = round(_SQPI / (2 * np.sqrt(2 * max(v_eff, 1e-6))), 6)
    return _erfc_cached(arg) / 2

def p_logical(p_phys: float, d: int) -> float:
    """p_L ~ 0.1 * (p_phys/p_th)^((d+1)/2), p_th=0.01 (soft-info)."""
    p_th = 0.01
    if p_phys >= p_th:
        return min(0.5, 0.1 * (p_phys / p_th)**((d + 1) / 2))
    return 0.1 * (p_phys / p_th)**((d + 1) / 2)


def tdm_cycle_time_sec(n_logical: int, n_factories: int, d: int) -> float:
    """Wall-clock time for one full TDM cycle.
    All logical qubits + factory qubits measured sequentially.
    """
    total_modes = (n_logical + n_factories * 15) * qec_cycle_modes(d)
    return total_modes * SLOT_NS * 1e-9


def effective_veff_with_intracycle_drift(v_eff_base: float, drift_rate: float,
                                         cycle_time_sec: float) -> float:
    """Average V_eff over a TDM cycle, accounting for drift accumulation.

    First qubit sees V_eff_base, last qubit sees V_eff_base + drift_rate * cycle_time.
    Average: V_eff_base + drift_rate * cycle_time / 2
    Worst-case (last qubit): V_eff_base + drift_rate * cycle_time

    We use the average for p_L estimation.
    """
    return v_eff_base + abs(drift_rate) * cycle_time_sec / 2


# ═══════════════════════════════════════════════════════════════
#  GKP Residual Estimator (from Paper 2)
# ═══════════════════════════════════════════════════════════════

def gkp_residual_sample(v_eff: float, n_modes: int, rng: np.random.Generator) -> np.ndarray:
    noise = rng.normal(0, np.sqrt(v_eff), n_modes)
    return ((noise + _SQPI_HALF) % _SQPI) - _SQPI_HALF

def estimate_veff_from_residuals(residuals: np.ndarray) -> float:
    return float(np.clip(np.mean(residuals**2), 1e-4, 1.0))


# ═══════════════════════════════════════════════════════════════
#  Decoder Models (from Paper 3)
# ═══════════════════════════════════════════════════════════════

@dataclass
class DecoderSpec:
    name: str
    def error_rate_factor(self, rho: float) -> float:
        raise NotImplementedError

class VanillaMWPM(DecoderSpec):
    def __init__(self):
        super().__init__(name="Vanilla MWPM")
    def error_rate_factor(self, rho: float) -> float:
        # Correlated noise degrades vanilla MWPM
        return 1.0 + 5.0 * rho**2  # e.g. rho=0.15 → 1.11x worse

class ResidualSubtraction(DecoderSpec):
    def __init__(self):
        super().__init__(name="Residual Subtraction")
    def error_rate_factor(self, rho: float) -> float:
        if rho < 0.01:
            return 1.15  # slightly worse at zero correlation
        return 1.0 / (1.0 + 300 * rho**2)

class GNNDecoder(DecoderSpec):
    def __init__(self):
        super().__init__(name="GNN Lite")
    def error_rate_factor(self, rho: float) -> float:
        if rho < 0.01:
            return 1.4
        return 1.0 / (1.0 + 200 * rho**1.8)

DECODER_SWITCH_COST = {
    "Vanilla MWPM": 0,
    "Residual Subtraction": 2,
    "GNN Lite": 8,
}
DECODERS = [VanillaMWPM(), ResidualSubtraction(), GNNDecoder()]


# ═══════════════════════════════════════════════════════════════
#  Unified Performance Model
# ═══════════════════════════════════════════════════════════════

def compute_p_L(v_eff_base: float, drift_rate: float, rho: float,
                n_logical: int, n_factories: int, d: int,
                decoder: DecoderSpec) -> float:
    """Compute logical error rate including intra-cycle drift effect.

    This is the KEY function: factory allocation affects p_L via cycle time.
    """
    ct = tdm_cycle_time_sec(n_logical, n_factories, d)
    v_eff_avg = effective_veff_with_intracycle_drift(v_eff_base, drift_rate, ct)
    p_phys = p_phys_from_veff(round(v_eff_avg, 6))
    p_L = p_logical(p_phys, d) * decoder.error_rate_factor(rho)
    return p_L


def compute_t_throughput(n_factories: int, d: int,
                         n_logical: int, v_eff: float) -> float:
    """T-gate throughput (magic states per second)."""
    ct = tdm_cycle_time_sec(n_logical, n_factories, d)
    if ct <= 0:
        return 0.0
    p_phys = p_phys_from_veff(round(v_eff, 6))
    success_prob = (1 - p_phys) ** (15 * d)
    # One distillation attempt per d QEC cycles per factory
    return n_factories * success_prob / (d * ct)
