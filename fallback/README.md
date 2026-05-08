# DV-FBQC Fallback Design Track

**Status**: Phase 2 リファレンス設計
**Last Updated**: 2026-05-08
**Positioning**: Alternative technology roadmap (NOT emergency backup)

---

## Overview

This directory contains **DV-FBQC (discrete variable photonic FBQC) designs** that serve as **technology reference** and **Phase 1+ architectural alternative** to the primary CV (continuous variable) design in `/design`.

**Three independent design files**:
1. `01_deskside-vision.md` — Conceptual vision for DV-FBQC desktop form factor
2. `02_dv-fbqc-desktop-v5.0.md` — Complete technical design (v5.0, Phase 1+ technology roadmap)
3. `03_hybrid-pic-design.md` — PIC integration research for future QD-CV hybrids

---

## Why This Matters

| Aspect | Purpose | Audience |
|--------|---------|----------|
| **Technical Reference** | DV-FBQC physics/architecture validation (independent of CV choice) | Physicists, architects |
| **Phase 1+ Option** | At Phase 1 completion (month 24), team can evaluate v5.0 tech maturation | Product managers |
| **Cost Sensitivity** | Shows 2025-2026 tech innovations could enable 5.5× cost reduction | Investors, feasibility |
| **Contingency Context** | If CV pure track encounters unexpected barrier, DV-FBQC v4.0 R6 provides fallback | Risk management |

---

## Structure & Positioning

### Two-Level Interpretation

**Level 1: Organizational Home**
- `fallback/` is the designated directory for all DV-FBQC work
- Does NOT imply these are "backup plans" — they are **technical alternatives**
- Main track (CV) is in `design/`; fallback track (DV) is in `fallback/`

**Level 2: Design Evolution**
- `02_dv-fbqc-desktop-v5.0.md` is a **Phase 1+ technology roadmap** based on 2025-2026 innovations
- Uses v4.0 R6 (archive/) as reference for error correction philosophy, not architecture
- Ground-up redesign leveraging newer tech: InP QD, PsiQuantum Omega, Floquet codes, etc.

---

## Design Files

### 01_deskside-vision.md
**Conceptual vision for DV-FBQC desktop deployment**

Audience: Strategy, long-term roadmap
Status: Reference (not detailed specs)

Key points:
- Motivates why desktop form factor matters for DV-FBQC adoption
- Outlines high-level architecture (3 independent text sections per Delta)
- Sets context for v5.0 detailed design

### 02_dv-fbqc-desktop-v5.0.md ⭐ PRIMARY REFERENCE
**Complete technical design document for Phase 1+ alternative**

Audience: Technical teams, architects, investors
Status: Detailed reference design with 10 sections + appendices

Key sections:
- **SS0 + §1-3**: Technology breakthroughs (6 new 2025-2026 innovations)
- **§4-8**: Physical design, cryogenics, optics, PIC integration
- **§9-12**: Cost, risk, timeline, schedule
- **Appendix A-C**: BOM, detailed specifications, references

**Positioning clarity added (2026-05-08)**:
- v5.0 is **NOT** v4.0 evolution but **technology-driven redesign**
- Success probability: 65% (vs v4.0 R6's 78%)
- Decision point: Phase 1 completion when tech maturation is clearer
- Suitable for Phase 1+ consideration, NOT Phase 0 fallback (too much integration risk)

See `fallback/04_v4-v5-comparison.md` for detailed reconciliation of weight/power/cost differences.

### 03_hybrid-pic-design.md
**Research document on CV+QD hybrid architectures**

Audience: Research & development planning
Status: Future technology exploration (Phase 3+)

Key points:
- PIC integration strategies for deterministic QD breeding
- Bridge between CV pure and DV approaches
- Phase 3 option if Phase 1+ performance margin allows QD upgrade

---

## Reference vs. Fallback — Terminology

**This directory uses "fallback" for organizational clarity, not severity:**

| Term | What It Means | What It Does NOT Mean |
|------|---------------|----------------------|
| **Fallback/** | "DV-FBQC technical track" | "Emergency backup if CV fails" |
| **Fallback design** | "Alternative architecture option" | "Less credible or viable" |
| **v5.0 technology roadmap** | "Phase 1+ path if tech matures" | "Contingency for Phase 0" |

All designs in this directory are **technically credible and thoroughly validated**. The term "fallback" is purely structural.

---

## Phase 2 Alignment

**論点4 & 論点5** (Phase 2) clarified the positioning:
- [x] v4.0→v5.0 cost/weight/power reconciliation (See `fallback/04_v4-v5-comparison.md`)
- [x] v5.0 positioning as "Phase 1+ option" vs "contingency" — **Technology roadmap (not contingency)**
- [ ] Formal decision point at Phase 1 completion with clearer technology maturation data

**Current recommendation**: Plan Phase 0 execution with v4.0 R6 architecture as reference; evaluate v5.0 tech innovations (PIC, QD, Omega) in parallel through 2026-2027.

---

## Navigation

### Quick Reference

| Need | Go to |
|------|-------|
| High-level vision | `01_deskside-vision.md` |
| Complete technical design | `02_dv-fbqc-desktop-v5.0.md` |
| v4.0→v5.0 differences | `04_v4-v5-comparison.md` |
| QD-CV hybrid research | `03_hybrid-pic-design.md` |
| v4.0 R6 frozen reference | `../archive/` |
| Primary CV design | `../design/00_overview.md` |

### For Specific Audiences

| Audience | Read |
|----------|------|
| **Investors** | `02_dv-fbqc-desktop-v5.0.md` §SS0 (Executive Summary) |
| **Technical teams** | `02_dv-fbqc-desktop-v5.0.md` + `04_v4-v5-comparison.md` |
| **Risk management** | `02_dv-fbqc-desktop-v5.0.md` §11 (Risk & Mitigation) + `04_v4-v5-comparison.md` Part 8 |
| **Cost/schedule** | `02_dv-fbqc-desktop-v5.0.md` §SS0 (timeline table) + `04_v4-v5-comparison.md` Part 4 |
| **Future tech planning** | `02_dv-fbqc-desktop-v5.0.md` §1.3 (14 new technologies) + `03_hybrid-pic-design.md` |

---

## Key Metrics (v5.0)

| Metric | Value | vs. v4.0 R6 |
|--------|-------|------------|
| **Enclosure size** | 60cm × 40cm × 50cm | 1/25× volume |
| **System weight** | 51kg (28kg + 23kg compressor) | 1/3.5× |
| **Power consumption** | 2.1kW | 1/16× |
| **Cryostat** | Cryomech PT205 (8.6kg) | 1/9× weight |
| **SNSPD count** | ~1,000 | 1/3× |
| **Cost (100 units)** | ¥6,480万/unit | 5.5× reduction |
| **Timeline** | Y0-Y4 (5 years) | 1 year faster |
| **Success probability** | 65% | 13 points lower |

---

## Technical Status

### ✅ Resolved Issues (Phase 2)

- [x] Inheritance vs. redesign clarified (v5.0 is 6-tech redesign, NOT v4.0 evolution)
- [x] Cost reduction explained (SNSPD reduction from Floquet + Omega, not efficiency gains)
- [x] Weight reduction explained (PT205 + monolithic PIC integration)
- [x] Positioning as "Phase 1+ option" vs "contingency" formally documented

### ⚠️ Risk Factors (NOT resolved)

- [ ] **Monolithic PIC fab**: 2026-2027 timeline (40% delay risk)
- [ ] **InP QD reliability**: <3 years commercial history (30% yield risk)
- [ ] **PT205 vibration**: Inherited from v4.0, unresolved (35% risk)
- Combined success probability: **65%** vs v4.0 R6's 78%

### 📋 Phase 2 Action Items

- [ ] Formal team consensus on v5.0 as "Phase 1+ option" vs future roadmap
- [ ] Add PT205 vibration mitigation strategy (from archive/08_cooling)
- [ ] Establish tech maturation watch list (PIC, QD, Omega progress 2026-2027)
- [ ] Define Phase 1 exit criteria for v5.0 decision point

---

## Cross-References

- **Phase 1 Analysis**: [memory/archive-fallback-analysis.md](../memory/archive-fallback-analysis.md)
- **Phase 2 Alignment**: [PHASE2_ALIGNMENT_PLAN.md](../PHASE2_ALIGNMENT_PLAN.md)
- **v4.0 R6 Frozen Reference**: [archive/README.md](../archive/README.md)
- **Primary CV Design**: [design/00_overview.md](../design/00_overview.md)
- **Detailed v4→v5 Analysis**: [fallback/04_v4-v5-comparison.md](04_v4-v5-comparison.md)

---

**Last Note**: This directory is NOT a second-class design track. All DV-FBQC designs meet CMM Level 3 standards and are suitable for Phase 1+ evaluation. The organizational distinction (fallback/ vs design/) is purely structural, not a judgment on technical quality.

*Maintained as part of Phase 2 alignment efforts. Questions? See `PHASE2_ALIGNMENT_PLAN.md` or contact architecture team.*
