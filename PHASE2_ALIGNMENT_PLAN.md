# Phase 2 Alignment Plan — 7 Discussion Topics

**Status**: In Progress
**Last Updated**: 2026-05-08
**Team Lead Responsibility**: Synthesize Phase 1 findings into actionable Phase 2 improvements

---

## Executive Summary

**Phase 1 (2026-05-06 to 05-07) COMPLETE**: All 4 teams validated core design consistency across 100+ documents. **0 Critical blocking issues found; CMM Level 3 (Defined) confirmed.**

**Phase 2 (2026-05-08) OBJECTIVE**: Address 7 cross-team alignment topics to finalize design certainty before Phase -1 execution.

---

## 7 Major Discussion Topics

### 論点 1: Decoder Strategy — UF vs MWPM Dual FPGA Model ✓ ALIGNED

**Context**: Akira proposed parallel FPGA operation (VE2302 for UF + VE2802 for MWPM) to enable seamless product-line differentiation (Edu/Pro/Max).

**Finding**: CV Pure uniquely benefits from this strategy; archive/fallback sequential migration model is NOT compatible.

**Decision Required**:
- [ ] **Adopt Akira's dual-FPGA strategy** for design/ (product edge)
- [ ] **Document archive/fallback as sequential migration** (legacy approach, acceptable for fallback)
- [ ] **Define Phase -1 T0c decoder validation task** (UF soft-info vs MWPM performance empirical test)

**Implementation**:
- [ ] Update design/08_decoder.md with dual-FPGA product roadmap (Edu→Pro→Max)
- [ ] Add design/09_rack-design decoder configuration table (VE2302/VE2802 capacity by d=3/5/7)
- [ ] Create Phase -1 T0c experiment spec: UF soft-info precision test (100 samples, 50k syndrome each)

**Owner**: Beam (decoder expert)
**Dependency**: None (independent)
**Timeline**: 2-3 hours implementation

---

### 論点 2: Finite Energy GKP Go/No-Go Criteria ⏳ PENDING TEAM INPUT

**Context**: Phase -1 must validate **σ_gen ≥ 12.5dB** (OPA pump 50dBm, SiN clad improvement) to claim break-even probability.

**Key Questions**:
1. **SiN clad parameter targets**: What Δn/thickness achieves 12.5dB without degrading pump efficiency?
2. **2-pump vs 1-pump risk**: Is 12.1dB (NTT CW) more reliable path than attempting 13dB?
3. **DV-FBQC fallback trigger**: At what σ_gen threshold do we pivot to fallback design?

**Implementation Needed**:
- [ ] Create `analysis/gkp-finite-energy-validation.md` with numerical feasibility bounds
- [ ] Define Phase -1 G-EXP1 success criteria (σ_gen measurement precision, confidence interval)
- [ ] Quantify GKP F (fidelity) vs σ_gen curve; identify margin to 0.85 break-even

**Owner**: Beam (QEC physics)
**Dependency**: Photon team (OPA characterization data)
**Timeline**: 4-5 hours (requires literature review + numerical modeling)

---

### 論点 3: Loss Model Unification — GAWBS + Connection Loss ✓ RESOLVED

**Context**: Phase 1 identified HCF connection loss (0.6dB) had been omitted from erasure calculation; led to false 76.6% vs 83.3% conflict.

**Resolution** (Phase 1 verified):
- Phase 0 erasure: 76.6% (without HCF connection loss)
- **Corrected**: 83.3% (HCF 0.6dB + fiber 0.07dB integrated)
- Impact: Improves pre-herald photon count by ~1,000 → increased breeding candidates

**Documentation Status**:
- [x] design/06_noise-budget.md: Loss cascade correctly separated (GAWBS 0.13dB, PD-QE loss 0.04dB, HCF connection 0.6dB)
- [x] design/01_system-architecture.md: Updated Phase 0 erasure value (Q²_eff)
- [x] Feasibility report: Cost impact quantified (Phase 0 hardware unchanged, Phase 1+ PIC benefits from better starting point)

**No Action Required** — Already implemented in v3.6 parameter set.

---

### 論点 4: fallback/03 Formal Positioning — CV+QD Hybrid Path ⏳ PENDING FORMALIZATION

**Context**: `fallback/03_hybrid-pic-design.md` describes CV+QD integration but lacks explicit positioning.

**Current Ambiguity**:
- Is it a **contingency** (backup if pure CV fails)?
- Is it a **Phase 3+ enhancement** (planned evolution, not fallback)?
- Cost/timeline implications differ by ~$1K hardware vs design risk.

**Resolution Options**:

**Option A**: CV+QD = Phase 3+ planned feature (most likely given $1K vs $90K cost leverage)
- Pro: Aligns with DV-FBQC $0 vs $90K risk framework
- Con: Requires explicit Phase 3 budget/timeline in roadmap
- Action: Rename to `design/11_cv_qd_upgrade_path.md`, move from fallback/ to design/

**Option B**: CV+QD = True contingency (if Phase 0/1 hits specific failure mode)
- Pro: Preserves fallback semantics
- Con: Requires clear trigger criteria (σ_eff < 8.5dB? → attempt QD)
- Action: Add trigger decision tree to fallback/03; update risk.md with conditional branch

**Recommendation**: **Option A** (Phase 3 planned, not contingency) — cost/timeline logic cleaner

**Implementation**:
- [ ] Rename fallback/03 to design/11_cv-qd-upgrade.md (move to design/)
- [ ] Add §1: "Phase 3 Technology Roadmap" header
- [ ] Update design/00_overview.md product line: "Edu (d=3, CV) → Pro (d=5, CV) → Pro+ (d=5, CV+QD) → Max (d=7, CV+QD)"
- [ ] Update analysis/bom.md with QD screening cost ($1K) as optional Phase 3 component
- [ ] Update note.md Slide 7 product line to reflect 4-tier strategy

**Owner**: Akira (cost) + Photon team (feasibility)
**Dependency**: Consensus on Phase 3 scope/budget (cross-team alignment)
**Timeline**: 3-4 hours (document restructuring + BOM update)

---

### 論点 5: Fallback v4.0→v5.0 Inheritance Claims — Contradiction Resolution ⏳ PENDING CLARIFICATION

**Context**: `fallback/02_dv-fbqc-desktop-v5.0.md` claims inheritance from archive/02 (v4.0 R6) but contains significant improvements (28kg vs ~45kg, 2.1kW vs ~15kW estimated).

**Key Contradictions Found**:
1. **Weight reduction**: How does v5.0 achieve 28kg from v4.0's heavier footprint without major architecture change?
2. **Power reduction**: 2.1kW vs estimated 15kW — which assumptions changed? (cryogenic duty cycle? SNSPD count? Decoder complexity?)
3. **Decoder strategy**: v4.0 has sequential migration; v5.0 preserves this — is this acceptable for fallback?
4. **Cost delta**: v4.0 R6 full cost unknown; v5.0 claims ~¥3,540万. Where's the delta?

**Investigation Needed**:
- [ ] Cross-reference archive/04_hardware with fallback/02 component-by-component
- [ ] Clarify: Is v5.0 a "lite" DV (fewer qubits, shorter cryostat) vs full redesign?
- [ ] Quantify cryogenic duty cycle assumption (h/year quiescent → power scaling)
- [ ] Verify SNSPD array size (v4.0: 3,000 vs v5.0: ~1,000 speculated)

**Resolution Path**:
- [ ] Create `fallback/04_v4-v5-comparison.md` (side-by-side spec reconciliation)
- [ ] Add fallback/02 abstract: "Phase -1 contingency design; ~40% cost reduction vs v4.0 R6 via [specific list]"
- [ ] Update fallback/README.md with inheritance clarity

**Owner**: Akira (costs) + Cross (archive liaison)
**Dependency**: Detailed review of archive/02, 04, 09
**Timeline**: 3-4 hours (comparative analysis + documentation)

---

### 論点 6: Cost SSOT Architecture — Master Registry + Tier Structure ✓ ALIGNED

**Context**: Phase 1 identified cost as critical SSOT source; multiple documents had conflicting values (¥3.54B vs ¥2.55B vs ¥1.8B).

**Resolution** (Phase 1 completed):
- [ ] **Master**: `_parameters.md` defines 4 cost tiers (CV Edu/Pro/Max, DV R6 fallback)
- [ ] **Detail 1**: `analysis/bom.md` itemizes component costs by product line
- [ ] **Detail 2**: `analysis/development-cost-summary.md` breaks down Phase -1 to -2 labor/equipment
- [ ] **Detail 3**: `design/09_rack-design.md` references master for Edu/Pro/Max pricing

**Status**:
- [x] README.md aligned with master (Edu ¥1,350万 / Pro ¥1,800万 / Max ¥2,550万)
- [x] note.md Slides 4, 7 use consistent master values
- [x] No circular references; inheritance chain clear (master → detail → pitch)

**No Action Required** — SSOT architecture validated. Only ongoing: catch any drift in future edits.

---

### 論点 7: Supply Chain Risk — NTT OPA Capacity vs 273/year Need ✓ REMEDIATION PLAN APPROVED

**Context**: NTT PPLN OPA volume ~50-100/year. Taros roadmap requires 273/year (Phase -1 to Phase 2 including fallback evaluation).

**Remediation Plan** (Phase 1 approved):
- [ ] **Path 1 (primary)**: 2-source evaluation (NTT + Sumitomo or nLight) — **$300k investment, ~6 months**
- [ ] **Path 2 (backup)**: Custom PPLN waveguide fab (Sumitomo/nLight/NTT partnership) — **Phase 1 initiative, ~18 months**
- [ ] **Timeline**: Phase -1 months 1-3 solicit dual-source quotes; Phase 0 months 1-6 qualify second source

**Implementation**:
- [ ] Create `analysis/supply-chain-mitigation.md` (dual-source RFQ template, qualification plan, fallback timeline)
- [ ] Add Phase -1 execution plan milestone: "S2a: Supply chain RFQ issued" (month 1)
- [ ] Define Go/No-Go at month 6: "Dual-source qualified" → proceed to Phase 0

**Owner**: Feasibility team (procurement)
**Dependency**: None (can initiate immediately)
**Timeline**: 2-3 hours planning document + ongoing procurement execution

---

## Implementation Roadmap

### Immediate (Next 2-3 days)

1. **論点1 (Decoder)**: Beam implements design/08_decoder.md dual-FPGA section (**2h**)
2. **論点4 (fallback/03)**: Team consensus call on CV+QD as Phase 3 vs contingency (**1h discussion**)
3. **論点5 (v4.0→v5.0)**: Cross/Akira conduct comparative analysis (**4h**)
4. **論点6 (Cost SSOT)**: Verify no drift in latest pitch deck slides (**1h**)
5. **論点7 (Supply)**: Feasibility team creates mitigation plan document (**3h**)

**Total**: ~11 hours, 4 team members in parallel

### Follow-up (Week of 2026-05-12)

1. **論点2 (GKP Go/No-Go)**: Beam completes finite-energy validation with numerical models (**5h**)
2. **論点3**: Already resolved (document audit trail)
3. **論点4-5**: Implement restructuring based on team consensus
4. Cross-team review & merge all Phase 2 documentation updates

---

## Success Criteria

✅ **All 7 topics formally resolved** with implementation plans and owners
✅ **design/, fallback/, archive/ aligned** — no contradictions
✅ **SSOT parameters locked** — ready for Phase -1 commitment
✅ **Pitch deck v5.0** — updated to reflect Phase 2 decisions
✅ **Risk register** — updated with remediation status (supply chain, decoder, GKP)

---

## Dependencies & Blockers

**Blocking論点2** (GKP Go/No-Go): Requires Photon team OPA characterization data (likely available from ongoing NTT collaboration)

**Blocking論点4** (CV+QD positioning): Requires team consensus on Phase 3 scope/budget (high probability: approved based on cost/risk logic)

**Blocking論点5** (v4.0→v5.0 reconciliation): Requires detailed archive/ review (Cross initiated, 3-4 hours to completion)

---

## Cross-References

- **Phase 1 Final Report**: `MEMORY.md` Phase 8 summary (all 4 tasks complete)
- **Decoder Strategy**: `memory/hw-optical-analysis.md` (Akira's dual-FPGA proposal)
- **GKP Validation**: `memory/break-even-verification.md` (σ_eff critical path)
- **Cost Audit**: `analysis/FEASIBILITY_CONSISTENCY_REPORT.md` (Phase 1 cost verification)
- **Archive Analysis**: `memory/archive-fallback-analysis.md` (Cross Phase 1 findings)

---

*Next: Team lead to review, assign owners, and schedule resolution milestones. Target: All 7 topics resolved by 2026-05-12.*
