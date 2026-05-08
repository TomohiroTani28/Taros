# Phase 2 Technical Analysis Summaries — Beam Detailed Findings

**Date**: 2026-05-08
**Status**: 3 of 7 topics analyzed with deep technical detail
**Audience**: Team lead, Akira (HW), Cross (fallback), Delta (experiments)

---

## 論点 1: Decoder Strategy — UF vs MWPM Phased Implementation

### Problem Statement
- Current design mentions both UF (Phase 0-1) and MWPM (Phase 2+) but transition logic undefined
- "30倍性能ジャンプ" claim needs verification
- FPGA resource allocation strategy unclear (VE2302 vs VE2802 capacity)

### Beam's Detailed Analysis

**Root Cause of Performance Claim**:
The ~12倍 improvement (corrected from "30倍" mischaracterization) is NOT a single-algorithm jump, but compound effect:
1. **Decoder algorithm**: MWPM soft-info integration achieves p_L 3.3×10⁻⁴ vs UF 4×10⁻³ (theoretical limit)
2. **Optical margin**: Phase 2 PIC integration improves σ_eff from 9.3→10.8dB (+1.5dB margin recovery)
3. **QD support**: Optional Step B/C breeding further raises σ_eff to 12dB+

**Phased Implementation Timeline**:

| Phase | Decoder | FPGA | σ_eff | p_L Requirement | Cost Δ |
|-------|---------|------|-------|-----------------|--------|
| Phase 0 | UF | VE2302 | 8.5dB | <10⁻² | baseline |
| Phase 1a | UF | VE2302 | 9.3dB | <10⁻³ | $0 |
| Phase 1b | UF→MWPM evaluation | both | 9.3dB | <5×10⁻⁴ | $200K FPGA |
| Phase 2 | MWPM | VE2802 | 10.8dB | <3.3×10⁻⁴ | +$500K PIC |

**Phase 0→1 Decision Gate (T0b completion)**:
```
IF σ_gen ≥ 12.5dB AND p_th_UF ≥ 0.9%:
  → Phase 1a confirmed, UF continues

ELSE IF σ_gen ∈ [11.5, 12.5) AND soft-info achievable:
  → Phase 1b evaluation (dual FPGA, cost +$200K)

ELSE IF σ_gen < 11.5dB:
  → DV fallback contingency activated
```

**Soft-info Integration Detail**:
- UF Phase 1: 14-bit LUT soft-info path (separate from hard-decision 6-bit path)
- MWPM Phase 2: Cluster-growth algorithm with 16-bit edge weights (Noh-Chamberland 2022 model)
- Transition validation: Design both FPGA implementations in parallel during Phase 1a, reduce FPGA iteration risk

### Action Items (3)
1. **design/08_decoder.md §3**: Add "Phased Decoder Strategy" section detailing UF→MWPM transition criteria
2. **phase-minus1-execution.md Task T0b**: Expand to include "UF soft-info threshold validation" (Stim test: 100 samples × 50k syndrome each)
3. **design/13_performance.md**: Create p_L comparison table showing UF vs MWPM prediction curves (d=3, 5, 7)

### Questions for Akira
- **FPGA timing**: Phase 1b MWPM 510ns latency — does this require TDM re-timing or is 500MHz cycle margin sufficient?
- **Clock distribution**: Will parallel UF/MWPM implementation require dual clock domains or can CDC logic handle it?

### Questions for Delta
- **ibm_quantum**: Can we extract UF soft-info precision metrics from 02_virtual-experiments to validate simulation predictions?

---

## 論点 2: GKP Finite-Energy Parameter (Δ) Go/No-Go Criteria

### Problem Statement
- Product spec requires Δ < 0.15 (Menicucci 2014, Stafford-Menicucci 2025)
- No protocol defined for measuring Δ during Phase -1
- No action specified if Δ ≥ 0.15 (failure branch undefined)
- **Critical**: Δ is prerequisite for all downstream GKP quality metrics

### Beam's Detailed Analysis

**Δ Physics & Measurement**:
- **Definition**: Finite-energy lattice spacing deviation; characterizes how closely GKP approaches ideal
- **Critical threshold**: Δ < 0.12 for d=3 break-even (Menicucci strict bound); Δ < 0.15 for conditional operation
- **Measurement precision**: Wigner function tomography achieves ±0.02 accuracy; required for Go/No-Go

**Proposed Measurement Protocol**:
1. **Primary**: Wigner tomography (homodyne sweep + software reconstruction)
   - 360° phase scan × 50 quadrature points = 18,000 homodyne measurements
   - GPU-accelerated reconstruction (200ms per result)
   - Precision: ±0.02 (sufficient for Δ < 0.15 discrimination)

2. **Secondary**: Adaptive Bayesian tomography (100-300 shots per point, lower overhead)

3. **Fallback**: Homodyne variance analysis (rough estimate, ±0.05 precision)

**Phase -1 T0a-T0c Implementation Timeline**:

```
Week 1-2 (Initial measurement):
  - Wigner tomography × 3 independent measurements
  - Δ value determination (±0.02 tolerance)
  - GO/CONDITIONAL/NO-GO immediate classification

Week 3-8 (If CONDITIONAL, parallel optimization):
  - σ_gen optimization experiments (OPA tuning for +0.5-1dB improvement)
  - GKP protocol refinement (Step A→B transition conditions)
  - Δ trending (bi-weekly measurement, trend analysis)

Months 2-3 (T0b soft-info validation):
  - Monthly Δ measurement continues (monitor stability)
  - soft-info decoder p_th evaluation (decoder performance vs Δ correlation)

Month 3 (T0c Phase 0 gate):
  - Final Δ value + F_GKP + σ_gen integration
  - GO/CONDITIONAL/NO-GO final decision
```

**Decision Matrix**:

| Δ Value | F_GKP Range | Phase 0 Status | Phase 1 Impact | Fallback Path |
|---------|------------|----------------|----------------|---------------|
| ≤0.10 | >0.85 | GO ✓ | d=5/7 fully achievable | Not needed |
| 0.10-0.12 | 0.84-0.85 | GO ✓ | d=5 achievable, d=7 marginal | Not needed |
| 0.12-0.15 | 0.78-0.84 | CONDITIONAL ⚠ | d=5 requires QD, d=7 risky | QD Step B mandatory |
| ≥0.15 | <0.78 | NO-GO ❌ | d=3 only, unacceptable product | DV fallback → Phase 1b |

### Cost & Timeline Impact
- **Δ measurement apparatus**: ~$150K (specialized optical test equipment)
- **Outsourced analysis**: ~$50K (NTT/academic lab collaboration)
- **Total T0a cost addition**: $200K
- **Timeline impact**: +2 weeks if all measurements nominal; +6 weeks if CONDITIONAL with optimization

### Action Items (3)
1. **phase-minus1-execution.md Task T0a**: Add Δ measurement protocol with decision thresholds and response paths
2. **design/04_gkp-protocol.md**: New section "Finite-Energy Design" documenting Δ<0.15 basis, Wigner measurement procedure, Step A→B transition conditions
3. **design/13_performance.md**: Add Δ sensitivity analysis (table: Δ=0.10/0.12/0.15/0.20 → F_GKP → p_L predictions)

### Questions for Akira
- **σ_gen optimization**: What's the physical upper bound on OPA improvement? Can we reach σ_gen=13dB?
- **Cost sensitivity**: Is $200K measurement budget acceptable, or should we explore lower-cost alternatives?

### Questions for Cross
- **DV equivalent**: What parameter in DV-FBQC models corresponds to GKP's Δ? How would fallback handle NO-GO branch?

### Questions for Delta
- **ibm_quantum**: Can we estimate Δ from 02_virtual-experiments using Wigner reconstruction? What precision is achievable?

---

## 論点 3: WDM Channel Introduction & σ_eff Degradation Risk

### Problem Statement
- Phase 0-1 design assumes L = 0.39dB (fiber loss + PPLN + EOM + PD, **no WDM**)
- Phase 1+ roadmap mentions "5-8 WDM channels" for scalability
- **Critical gap**: WDM fiber-PIC coupler introduces +0.2dB loss when scaling to 8 channels
- **Consequence**: σ_eff drops 8.5dB → 8.2dB, making **d=5 IMPOSSIBLE**

### Beam's Detailed Analysis

**Loss Budget Breakdown** (Phase 0 baseline):

| Component | Loss | Variation | Notes |
|-----------|------|-----------|-------|
| PMF fiber | 0.07dB | fixed | 200m × 0.35dB/km (Corning/Fujikura spec) |
| PPLN waveguide | 0.08dB | fixed | NTT 2.5dB/cm × 32mm (actual: excellent) |
| EOM extinction | 0.05dB | fixed | LN phase modulation, L_wave control |
| AWG/filter | 0.10dB | conditional | Phase 0: none; Phase 1: added for WDM |
| Fiber-PIC coupler | 0.06dB (5ch) / **0.26dB (8ch)** | **+0.20dB risk** | **PRIMARY RISK** |
| PD quantum eff | -0.01dB | fixed | BS model offset (PD loss recovery term) |
| GAWBS | 0.04dB | fixed | Group velocity mismatch (minimal) |
| **Total** | **0.39dB (Phase 0)** | **0.59dB (Phase 1+)** | **+0.20dB WDM penalty** |

**Physical Root Cause of Coupler Loss Increase**:
1. WDM multiplexing at PIC facet (8 wavelengths × 100-200GHz spacing)
2. Multimode interference (MMI) effects in fiber taper-to-waveguide transition increase with channel count
3. Wavelength-dependent phase matching degrades center vs edge channels
4. Back-reflections increase due to impedance mismatch in multi-channel region

**σ_eff Impact Calculation** (BS model):
```
σ_eff = 10 log10 [ η × V_sqz + (1-η) + V_non-loss ]

Phase 0 (L=0.39dB):  σ_eff = 8.5dB
Phase 1+ WDM (L=0.59dB):  σ_eff = 8.2dB  ← d=5 becomes infeasible

d=5 feasibility: σ_eff must be > 8.3dB minimum
                 σ_eff = 8.2dB → FAILURE (not marginal)
```

**Proposed Strategy: Phase 1b Addition**

Currently, plan shows Phase 0 → Phase 1 → Phase 2. Add **Phase 1b (PIC Transition)** to decouple WDM/PIC challenges:

```
Phase 0 (Break-even, 12-18 months)
├─ L = 0.39dB (WDMless or 5ch optimized)
├─ σ_eff = 8.5dB
├─ d=3 achievable (p_L ~10⁻²)
└─ Validation: GKP generation, soft-info decoder UF

Phase 1a (Validation, 12-18 months)
├─ L = 0.39dB (same, FPGA soft-info optimization only)
├─ σ_eff = 8.5dB (same)
├─ d=3-5 achievable (UF decoder validation)
├─ 5ch WDM confirmed stable
└─ Decision gate: Is Phase 1b PIC transition feasible & justified?

Phase 1b (PIC Integration, 6-9 months) ← NEW PHASE
├─ L = 0.50dB (early-stage PIC coupler, loss reduced from 0.26→0.15dB)
├─ σ_eff = 8.8dB (recovery via PIC + soft-info optimization)
├─ d=5 stable achievable
├─ 5-6ch WDM capacity confirmed
└─ PIC design maturation in parallel

Phase 2 (Mass Production)
├─ L = 0.27dB (mature PIC coupler, fully optimized)
├─ σ_eff = 9.3-10.8dB (PIC + optional QD support)
├─ d=7 achievable (MWPM decoder commercial)
├─ 8ch WDM possible (if Phase 1b architecture permits)
└─ Commercial unit production
```

**WDM Channel Strategy (Revised)**:
- **Phase 0-1a**: **5 channels fixed** (100GHz spacing, optimal for OPA ~500GHz FWHM)
- **Phase 1b**: Maintain 5ch, design PIC coupler for future 8ch capability
- **Phase 2+**: 8ch becomes available post-PIC maturation (if needed for margin recovery)

**Why this matters**:
- Current plan: "5-8ch scaling" ambiguous → CMM-L2
- Revised plan: Phase-specific channel counts → CMM-L3
- Margin recovery: Don't depend on 8ch for Phase 1; use Phase 1b PIC evolution instead

### Cost & Timeline Impact
- **Phase 1b addition**: +6-9 months to overall timeline (but Phase 0-1a already planned for 24-36 months total)
- **PIC investment deferral**: $500K moves from Phase 0 → Phase 1b (cash flow benefit for Phase -1)
- **Risk reduction**: Separates optical scaling (WDM) from PIC complexity; reduces Phase 1 risk profile

### Action Items (3)
1. **phase-minus1-execution.md**: Add Phase 1b as new formal phase; add Task T-1 "5ch Fixed Decision + Phase 1b Timeline Agreement" (procurement of PIC coupler samples, $500K budget reserve confirmation)
2. **design/06_noise-budget.md §2.1**: Split fiber-PIC coupler row into phase-dependent values (Phase 0: 0.06dB / Phase 1b: 0.15dB / Phase 2: 0.06dB with mature PIC)
3. **design/09_rack-design.md + design/10_portable.md**: Add "WDM Channel Planning" section with phase-by-phase channel counts, spacing, coupler specifications

### Questions for Akira
- **Coupler optimization**: Which design changes reduce loss from 0.26→0.15dB? (MMI redesign? Taper geometry? Mode-field diameter matching?)
- **Phase 1b cost**: Is $500K sufficient for PIC coupler development + qualification?
- **Timeline**: Can Phase 1b start during Phase 1a (parallel) or must it wait for Phase 1a completion?

### Questions for Cross
- **DV fallback**: If Phase 1 WDM expansion causes d=5 failure, what's the cost of DV fallback at that point?

### Questions for Delta
- **Sensitivity analysis**: Can 02_virtual-experiments model coupler loss variations to predict sensitivity across channel counts?

---

## Summary Table: Status of All 7 Topics

| Topic | Owner | Status | Key Finding | Action Items | Timeline |
|-------|-------|--------|-------------|--------------|----------|
| **1. Decoder** | Beam | ✓ ANALYZED | UF→MWPM phased, T0b gate | 3 (design files) | 2-3 days |
| **2. Δ Go/No-Go** | Beam | ✓ ANALYZED | Wigner protocol, $200K cost | 3 (T0a-T0c protocol) | 2-3 days |
| **3. WDM σ_eff** | Beam | ✓ ANALYZED | **Phase 1b required** | 3 (timeline restructure) | 2-3 days |
| **4. fallback/03** | Akira/Cross | ⏳ | CV+QD as Phase 3 | Consensus call | 1 day |
| **5. v4.0→v5.0** | Cross/Akira | ✓ DONE | Completed 2026-05-08 | Analysis in fallback/04 | — |
| **6. Cost SSOT** | All | ✓ DONE | Master verified | — | — |
| **7. Supply chain** | Feasibility | ⏳ | Dual-source plan | Procurement plan | 2-3 days |

---

## Critical Path to Phase -1 Execution

**Immediate approvals needed**:
1. Phase 1b timeline addition (affects project roadmap)
2. $200K Δ measurement budget (Phase -1 cost increase)
3. $500K PIC investment deferral (Phase 0→1b cash timing change)

**If approved**:
- All 3 topics (1-3) have specific implementation actions ready
- Estimated 8-10 hours design document updates across team
- Target: PHASE2 documentation complete by 2026-05-10
- Phase -1 execution kickoff: 2026-05-12 pending final team-lead approval

---

**Document Location**: Original detailed analyses sent to team-lead via SendMessage
**Backup Archive**: /Users/tanitomohiro/.claude/projects/-Users-tanitomohiro-Downloads-Taros/memory/phase2-discussion-beam-analyses.md
