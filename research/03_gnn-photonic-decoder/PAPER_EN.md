# Hierarchical Evaluation of Correlated-Noise Decoders for Room-Temperature Photonic Quantum Computing: From Scale-Invariance Verification to Residual-Subtraction and GNN Decoders

**Author**: Tomohiro Tani

*Independent Researcher*

---

## Abstract

Room-temperature continuous-variable (CV) photonic quantum computers face inter-mode correlated displacement noise originating from a shared pump laser. We systematically evaluate four decoder strategies against correlated noise and establish a decoder hierarchy. (1) V_eff-recalibration MWPM is numerically verified to be identical to vanilla MWPM across 170,000 shots (100% decision agreement), a consequence of MWPM scale invariance. (2) Residual-subtraction MWPM circumvents scale invariance by estimating and removing the common mode from residual averages, achieving up to 41.8x improvement at d=5 (95% CI: [14.0, 125]) and 19.0x at d=7. This technique applies telecom common-mode rejection [9] to quantum error correction. (3) A GNN decoder (4,033 parameters; approximately 2,500x smaller than AlphaQubit [10]) learns correlation structure via graph convolution, achieving up to 33.4x at d=5 (95% CI: [12.3, 90.9]). (4) A single mixed-rho trained GNN maintains 20.8x advantage at out-of-distribution rho=0.20 for d=7. At rho=0 (no correlation), GNN underperforms MWPM (0.60x at d=3, 0.75x at d=5), and residual subtraction also degrades (0.84x at d=3)---correlated decoders assume the presence of correlation and degrade under independent noise. Unified-parameter experiments across d=3,5,7 (approximately 920,000 total shots, seed=42, fully reproducible) establish the decoder hierarchy.

---

## I. Introduction

### A. The Correlated Noise Problem

In room-temperature CV photonic quantum computers, two PPLN OPAs share a common pump laser, causing pump relative intensity noise (RIN) to introduce correlated displacement noise across modes [6,8]. MWPM decoders [3] assume independent noise, so this correlation directly degrades fault tolerance.

Prior work [1] identified the correct noise model for CV systems (phenomenological, soft-info MWPM), but decoder optimization under correlated noise remained unaddressed. While neural decoders [5,10,11,13] and code design advances [12] have shown promising results for DV systems, no systematic evaluation exists for correlated noise in CV photonic systems.

### B. Four Questions

1. Does recalibrating MWPM weights based on correlation improve performance?
2. Does directly removing the common mode from residuals improve performance?
3. Can an ML decoder learn the correlation structure?
4. Can a single model adapt to unknown correlation levels?

### C. Contributions

We systematically compare four decoders with unified parameters (d=3,5,7, seed=42) and demonstrate:

1. **No-go result: Principled impossibility of V_eff adaptation**: V_eff-recalibration MWPM produces identical decisions to vanilla across 170,000 shots. MWPM adaptation to uniform noise scaling is fundamentally ineffective, filling a blind spot in the literature.
2. **Residual-subtraction MWPM**: Applying telecom common-mode rejection [9] to CV-QEC. Up to 41.8x improvement at d=5.
3. **GNN distance scaling**: Advantage monotonically increases from d=3 to d=5 to d=7.
4. **Hardware-adaptive GNN**: A single mixed-rho model maintains 20.8x advantage at OOD rho=0.20 for d=7.

---

## II. Physical Model

### A. GKP Displacement Noise

The effective noise variance of GKP codes [4] under the beamsplitter model:

**V_eff = eta * V_sqz + (1 - eta) + V_nl**

where V_eff is the effective noise variance in shot noise units (SNU; vacuum noise = 1 SNU), eta is the total optical transmittance, V_sqz = 10^(-sigma_gen/10) is the squeezed state variance, and V_nl accounts for non-loss noise sources such as electronic noise. sigma_eff = -10 log_10(V_eff) [dB] is called the effective squeezing level; smaller V_eff means higher-quality GKP qubits.

This study uses the Phase 1 operating point: sigma_eff = 8.5 dB (sigma_gen = 13 dB, L = 0.39 dB, V_nl = 0.010 SNU included), V_eff = 0.1417 SNU, p_phys = 9.28 x 10^{-3} (see Appendix B).

### B. Correlated Noise Model

Common pump RIN introduces correlation between displacement errors of different modes. Under correlation coefficient rho, the displacement of mode pair (i, j) is

**(delta_i, delta_j) ~ N(0, V_eff x [[1, rho], [rho, 1]])**

Implementation: delta_i = sqrt(V_eff) x (sqrt(1-rho) * z_i + sqrt(rho) * z_common), where z_i, z_common ~ N(0,1) are independent standard normal variates.

The correspondence between rho and hardware parameters is shown below. These are order-of-magnitude guides arising from the combined effects of common pump RIN, WDM channel isolation, OPA gain bandwidth, and detection bandwidth. Since the detailed derivation depends on system design, this study sweeps rho as an independent model parameter.

| rho | Physical condition | Typical RIN and isolation level |
|------|-----------|-------------------------------|
| 0.003 | Design specification | RIN -150 dB/Hz, WDM isolation 30 dB |
| 0.03 | Specification upper bound | RIN -130 dB/Hz, WDM isolation 18 dB |
| 0.08 | Degraded condition (approx rho*) | RIN -127 dB/Hz, WDM isolation 14 dB |
| 0.10 | Significant correlation | RIN -125 dB/Hz |
| 0.20 | FT boundary (OOD evaluation) | System-level failure |

---

## III. Methods

### A. Simulation Framework

Rotated surface code detector error model (DEM) generation via Stim 1.15.0 [2], MWPM decoding via PyMatching 2.3.1 [3]. GKP displacement noise and correlated noise were implemented as custom models, generating GKP residuals and syndromes on the DEM edge structure. All experiments are reproducible with seed=42. Code is available at https://github.com/TomohiroTani28/Taros/tree/main/research/03_gnn-photonic-decoder.

### B. Unified Parameters

| d | DEM edges (total / used) | Detectors | n_train | n_test | rounds | epochs |
|---|------------------------|---------|---------|--------|--------|--------|
| 3 | 76 / 66 | 24 | 5,000 | 30,000 | 3 | 40 |
| 5 | 418 / 334 | 120 | 5,000 | 30,000 | 5 | 40 |
| 7 | 1,224 / 954 | 336 | 3,000 | 10,000 | 7 | 40 |

Total DEM error entries from Stim / edges actually used by extract_graph() (1-detector and 2-detector errors only). All simulations in this study use the latter (66/334/954).

rho in {0.00, 0.03, 0.05, 0.08, 0.10, 0.15}. OOD evaluation: rho = 0.20.

### C. Four Decoders

1. **Vanilla soft-info MWPM**: Computes LLR weights w(r) = ((sqrt(pi)-|r|)^2 - |r|^2)/(2V_eff) from GKP residuals. Baseline.
2. **V_eff-recalibration MWPM**: Estimates V_eff per shot from second moment of residuals (V_hat = mean(r^2)) and recomputes LLR.
3. **Residual-subtraction MWPM**: Subtracts the residual mean r_bar = mean(r_j) as a common-mode estimate (r'_j = r_j - r_bar), then recomputes LLR with the original V_eff. This is the CV-QEC version of telecom common-mode rejection [9].
4. **GNN Lite**: 3-layer Graph Convolutional Network [14] (GCNConv, hidden dimension 32, LayerNorm, 4,033 total parameters; approximately 2,500x smaller than Google AlphaQubit [10]). Input features: GKP residual r, |r|, LLR w(r) (3 dimensions). Output: modified edge weights passed to MWPM (Softplus activation ensures positivity).

### D. GNN Training Details

- **Loss function**: Binary cross-entropy. Edge-wise error probability p = sigma(-w + 2) computed from GNN output weights w, minimizing BCE loss against true edge errors.
- **Optimizer**: AdamW (lr=2x10^{-3}, weight_decay=10^{-4}) + CosineAnnealingLR
- **Per-rho training**: Separate GNN trained for each rho value (6 models per d)
- **Mixed-rho training**: Single GNN trained on uniform mixture of rho in {0, 0.03, 0.05, 0.08, 0.10, 0.15}, evaluated on all rho + OOD
- **Device**: Apple Silicon MPS (PyTorch 2.5.1, torch_geometric)

### E. Statistical Reporting

95% confidence intervals for p_L of each decoder were computed using the Wilson score interval. Ratio (improvement) 95% confidence intervals were conservatively constructed from Wilson interval endpoints (ratio CI = [p1_lo/p2_hi, p1_hi/p2_lo]). For conditions with zero errors, the 95% Poisson upper bound 3/n_test (rule of three) was used, and improvement lower bounds are reported as ">=Xx". Ratio CIs for low counts (k <= 5) are wide (e.g., 4/30,000 vs 167/30,000 yields CI = [14.0, 125]); point estimates serve as references, and precise ratio estimation requires larger n_test.

---

## IV. Results

### A. Numerical Verification of Scale Invariance (Decoder 2)

V_eff-recalibration MWPM was compared with vanilla MWPM across d=3,5,7 x 6 rho = 18 conditions, totaling 170,000 shots.

**All 18 conditions, all 170,000 shots produced identical decisions (agree = 100%).**

This is a consequence of scale invariance (see Appendix A). Since LLR w(r, V) is proportional to 1/V, a change in V scales all edge weights by the same scalar, leaving the MWPM minimum-weight matching invariant. Regardless of V_eff estimation accuracy, MWPM adaptation to uniform V_eff changes is impossible.

### B. Residual-Subtraction MWPM (Decoder 3)

![Figure 1: 4-decoder comparison threshold curve](results/fig_threshold_4decoder.png)
*Figure 1. p_L vs correlation coefficient rho for four decoders. d=5 (left) and d=7 (right). 95% confidence intervals shown. Points with zero errors display 95% upper bounds as downward arrows. Residual subtraction (orange) and GNN (blue) diverge from vanilla MWPM (red) as rho increases.*

As the CV-QEC version of common-mode rejection [9], we applied estimation and removal via residual averaging. Since each edge's residual is non-uniformly modified, this circumvents scale invariance (see Appendix A).

**Table I.** Residual-subtraction MWPM vs vanilla MWPM. 95% Wilson confidence intervals.

| rho | d=3 van/res (err/30K) | Improvement [95% CI] | d=5 van/res (err/30K) | Improvement [95% CI] |
|------|------|------|------|------|
| 0.00 | 81 / 96 | **0.84x** [0.63, 1.13] | 9 / 9 | 1.00x [0.33, 3.00] |
| 0.03 | 89 / 73 | 1.22x [0.89, 1.67] | 22 / 5 | **4.40x** [1.2, 15.6] |
| 0.05 | 110 / 70 | 1.57x [1.16, 2.13] | 24 / 7 | **3.43x** [1.1, 10.5] |
| 0.08 | 128 / 55 | **2.33x** [1.69, 3.20] | 36 / 7 | **5.14x** [1.8, 14.7] |
| 0.10 | 135 / 38 | **3.55x** [2.47, 5.12] | 64 / 3 | **21.3x** [5.7, 80.1] |
| 0.15 | 224 / 35 | **6.40x** [4.47, 9.16] | 167 / 4 | **41.8x** [14.0, 125] |

d=7 (n_test=10,000): Residual-subtraction errors = 0 for rho=0.03-0.10 (p_L <= 3.0x10^{-4}, 95% Poisson upper bound). At rho=0.15: vanilla 38 -> residual-subtraction 2 (19.0x, 95% CI: [3.8, 95.0]).

Three findings:

**(i) Degrades at rho=0.** 0.84x at d=3, rho=0.00 (95% CI includes 1.0, so statistical significance is limited, but direction is consistent). With no correlation, the residual mean is pure noise, and subtraction adds noise to residuals. **Residual subtraction assumes the presence of correlation and should not be used at rho=0.**

**(ii) Improvement increases with d.** d=3: 6.4x, d=5: 41.8x (at rho=0.15). As actual DEM edge count increases (d=3: 66, d=5: 334, d=7: 954), common-mode estimation accuracy improves (standard error proportional to 1/sqrt(N_edges)).

**(iii) Assumes common-mode model.** If the actual correlation structure is non-common-mode (spatially inhomogeneous, time-varying, etc.), estimation accuracy degrades and performance may suffer.

### C. Per-rho Trained GNN (Decoder 4)

**Table II.** Per-rho GNN vs vanilla MWPM. 95% CI. Notation: vanilla err / GNN err.

| rho | d=3 (err/30K) | Improvement [95% CI] | d=5 (err/30K) | Improvement [95% CI] |
|------|------|------|------|------|
| 0.00 | 81 / 136 | 0.60x [0.45, 0.79] | 9 / 12 | 0.75x [0.28, 2.03] |
| 0.03 | 89 / 139 | 0.64x [0.49, 0.84] | 22 / 15 | 1.47x [0.74, 2.90] |
| 0.05 | 110 / 118 | 0.93x [0.72, 1.21] | 24 / 12 | 2.00x [0.97, 4.10] |
| 0.08 | 128 / 114 | 1.12x [0.87, 1.45] | 36 / 10 | **3.60x** [1.77, 7.32] |
| 0.10 | 135 / 62 | **2.18x** [1.60, 2.96] | 64 / 4 | **16.0x** [5.84, 43.8] |
| 0.15 | 224 / 50 | **4.48x** [3.27, 6.13] | 167 / 5 | **33.4x** [12.3, 90.9] |

d=7 (n_test=10,000): rho=0.10 yields 19 / 1 (19.0x, 95% CI: [2.1, 168]). At rho=0.03-0.08 and rho=0.15, GNN errors = 0 (p_L <= 3.0x10^{-4}, 95% Poisson upper bound).

![Figure 2: Distance scaling](results/fig_distance_scaling.png)
*Figure 2. GNN/MWPM advantage ratio vs code distance. Monotonic increase confirmed across three rho values.*

**Distance scaling**: At rho=0.10, d=3: 2.18x, d=5: 16.0x, d=7: 19.0x. GNN advantage monotonically increases with code distance.

**Underperformance at rho=0**: 0.60x at d=3, 0.75x at d=5. Under independent noise, MWPM is (locally) near-optimal, so GNN's graph convolution "correlation learning" acts as noise. **GNN is not universal; vanilla MWPM is the optimal choice when correlation is absent.**

### D. Direct Comparison: GNN vs Residual Subtraction

**Table III.** Three-decoder comparison at d=5 (n_test=30,000). The engineering principle "at equal performance, the simpler method wins" determines "Recommended."

| rho | Vanilla (err) | Resid-sub (err) | GNN (err) | **Recommended** | Reason |
|------|------|------|------|------|------|
| 0.00 | 9 | 9 | 12 | **Vanilla** | Resid-sub=tie, GNN underperforms |
| 0.03 | 22 | **5** | 15 | **Resid-sub** | 4.40x vs 1.47x. Zero additional HW cost |
| 0.05 | 24 | **7** | 12 | **Resid-sub** | 3.43x vs 2.00x. Software change only |
| 0.08 | 36 | **7** | 10 | **Resid-sub** | 5.14x vs 3.60x |
| 0.10 | 64 | **3** | 4 | **Resid-sub** | 21.3x vs 16.0x |
| 0.15 | 167 | **4** | 5 | **Resid-sub** | 41.8x vs 33.4x |

**At d=5, residual subtraction outperforms GNN at all rho>0 for common-mode correlation.** The averaging over 334 edges (actual count) provides highly accurate common-mode estimation, at zero implementation cost (software change only, FPGA overhead: one adder + one divider). Following the engineering principle "the simpler method wins at equal performance," we recommend Decoder 3 for common-mode correlation.

However, Decoder 3 has two fundamental constraints: 1. **Degrades at rho=0** --- underperforms vanilla when correlation is absent. Combination with a rho estimator (e.g., CUSUM) is needed when rho is unknown. 2. **Common-mode model dependence** --- cannot handle spatially inhomogeneous correlation (per-WDM-channel rho, macronode 4-mode structural correlation).

GNN (Decoder 4) becomes advantageous when these constraints apply.

### E. Mixed-rho GNN: Hardware-Adaptive Decoding

![Figure 3: OOD generalization](results/fig_ood_mixed_rho.png)
*Figure 3. Mixed-rho GNN (single model) improvement ratio. Including OOD rho=0.20.*

A single GNN model trained on rho mixture was evaluated across all rho + OOD rho=0.20.

**Table IV.** Mixed-rho GNN (single model, no retraining). Notation: MWPM err / MixGNN err.

| rho | d=3 (err/30K) | Ratio | d=5 (err/30K) | Ratio | d=7 (err/10K) | Ratio |
|------|------|------|------|------|------|------|
| 0.00 | 91 / 135 | 0.67x | 6 / 23 | 0.26x | 2 / 1 | 2.0x |
| 0.03 | 103 / 111 | 0.93x | 15 / 13 | 1.15x | 0 / 0 | --- |
| 0.08 | 141 / 101 | **1.40x** | 35 / 8 | **4.38x** | 9 / 0 | **>=3.0x** |
| 0.10 | 139 / 86 | **1.62x** | 62 / 7 | **8.86x** | 23 / 0 | **>=7.7x** |
| 0.15 | 242 / 103 | **2.35x** | 159 / 13 | **12.2x** | 45 / 1 | **45.0x** [5.9, 341] |
| **0.20 (OOD)** | 337 / 109 | **3.09x** | 248 / 25 | **9.92x** | 83 / 4 | **20.8x** [6.5, 66.1] |

(d=7 GNN zero-error conditions: lower bounds computed from 95% Poisson upper bound 3/n_test, reported as ">=Xx")

**Comparison with residual subtraction at OOD rho=0.20** (supplementary experiment):

| d | Vanilla (err) | Resid-sub OOD | Mixed-rho GNN OOD | Resid-sub improvement | GNN improvement |
|---|------|------|------|------|------|
| 3 | 310/30K | **38** | 109 | **8.2x** | 3.1x |
| 5 | 276/30K | **12** | 25 | **23.0x** | 9.9x |
| 7 | 99/10K | **4** | 4 | **24.8x** | 20.8x |

**Residual subtraction outperforms GNN even at OOD rho=0.20 (d=3: 8.2x vs 3.1x, d=5: 23.0x vs 9.9x). At d=7, they are comparable (24.8x vs 20.8x).** For common-mode correlation, the principle of residual-subtraction (common-mode estimation via residual averaging) remains physically valid even at out-of-distribution rho, independent of ML training.

However, this result is limited to cases where the correlation structure follows the common-mode model. In operational environments where the correlation structure changes (e.g., spatially inhomogeneous correlation from WDM channel degradation), Mixed-rho GNN may become advantageous.

**Mixed-rho GNN behavior at rho=0**: Degrades to 0.26x at d=5 (6 -> 23 errors), worse than per-rho GNN's 0.75x. Mixed training underrepresents the low-rho regime. **When rho=0 operation is expected, vanilla MWPM is optimal; Mixed-rho GNN should only be applied when rho>0 is confirmed.**

---

## V. Discussion

### A. Decoder Hierarchy

The decoder hierarchy established in this study:

```
Decoder 1: Vanilla MWPM          --- Baseline. Optimal at rho=0
    | Scale invariance (verified at agree=100%)
Decoder 2: V_eff-recalibration   --- Identical to vanilla. Cannot improve
    | Non-uniform residual modification circumvents scale invariance
Decoder 3: Residual-subtraction  --- Strongest at rho>0, common-mode. Zero implementation cost
    | Model-free learning independent of correlation structure
Decoder 4: GNN Lite              --- Hardware-adaptive optimal for unknown/varying rho
```

At each stage, the "physical condition requiring a more complex decoder" is explicit. In implementation, one should select the simplest sufficient option.

### B. Literature Context of Residual Subtraction

Common-mode rejection via residual subtraction is based on the same principle as interference cancellation techniques in telecommunications [9], specifically common phase error (CPE) estimation in MIMO receivers [15]. In OFDM systems, the common phase error is estimated from the average phase rotation across all subcarriers and then removed. Our residual subtraction applies this to GKP residuals, and the property that estimation accuracy improves with more DEM edges (like more subcarriers) is shared.

### C. Physical Reason for Distance Scaling

Across the three data points d=3,5,7, improvement from all decoders monotonically increases with code distance.

- **Residual subtraction**: Actual DEM edge count increases from 66 to 334 to 954. The standard error of the common-mode estimator r_bar = (1/N) sum(r_j) decreases proportionally to sigma/sqrt(N). At d=7, averaging over 954 edges provides highly accurate common-mode estimation.
- **GNN**: The 3-layer GCN has a 3-hop receptive field. As d increases, the matching graph expands and the range of exploitable long-range correlation structure grows. Additionally, the number of "correlated edge pairs" per training sample increases as O(N^2), improving learning efficiency.

### D. Scale Invariance Theorem

For LLR w(r, V) = ((sqrt(pi)-|r|)^2 - |r|^2) / (2V), changing V to V' multiplies all edges by the same scalar V/V'. MWPM computes arg min_M sum w_j, which is invariant under positive scalar multiplication (Appendix A).

Residual subtraction breaks this invariance: the operation r_j -> r_j - r_bar modifies each edge's r non-uniformly, so |(r_j - r_bar)| != c * |r_j|, and relative LLR relationships change.

### E. Limitations

1. **d=7 statistics**: With n_test=10,000, GNN errors=0 is frequent. Only 95% Poisson upper bounds (p_L <= 3.0x10^{-4}) can be reported. Precise ratio estimation requires n_test >= 100,000.
2. **Macronode intrinsic correlation**: rho in this study is introduced as a model parameter. Intrinsic correlation arising from the macronode beamsplitter network's 4-mode structure [6] is not modeled.
3. **GNN inference latency**: ~6ms/shot (d=3, Apple MPS) is 10^6 times slower than real-time QEC (~10ns/cycle). Real-time decoding via FPGA/ASIC implementation [16,17] is essential for practical use. AlphaQubit [10] is TPU-dependent and faces similar challenges.
4. **Degradation at rho=0**: Both GNN and residual subtraction underperform vanilla MWPM under independent noise. Practical deployment requires a decoder-switching mechanism based on rho estimation.

---

## VI. Conclusion

We established a four-stage decoder hierarchy for correlated noise in room-temperature CV photonic QEC.

1. **No-go result: V_eff recalibration is fundamentally ineffective.** Verified across 170,000 shots. MWPM scale invariance means uniform V_eff adaptation does not change decoding results. This result negates the intuitive expectation that "knowing noise parameters precisely improves the decoder," and shows that circumventing scale invariance (via residual subtraction or ML) is necessary to improve MWPM under correlated noise.

2. **Residual-subtraction MWPM is strongest for common-mode correlation.** Up to 41.8x at d=5 (95% CI: [14.0, 125]), 19.0x at d=7. Zero implementation cost. However, it degrades at rho=0 (0.84x at d=3) and assumes a common-mode model.

3. **GNN scales with distance.** 33.4x at d=5 (95% CI: [12.3, 90.9]). 4,033 parameters (2,500x smaller than AlphaQubit) learn correlation structure model-free. At rho=0, it underperforms vanilla (d=3: 0.60x, d=5: 0.75x)---we honestly report the limits of correlated decoders.

4. **Residual subtraction outperforms GNN even at OOD.** At OOD rho=0.20, d=5: residual-subtraction 23.0x vs GNN 9.9x, d=7: 24.8x vs 20.8x. For common-mode correlation, the residual-subtraction principle remains physically valid even outside the training distribution, independent of ML learning. The true value of GNN lies in its ability to adapt model-free when the correlation structure is non-common-mode.

Residual subtraction and GNN are complementary. For common-mode correlation (rho>0), residual subtraction is strongest including at OOD. When the correlation structure is unknown or non-common-mode, GNN is advantageous. The optimal practical strategy is automatic decoder switching via rho estimation (e.g., CUSUM)---vanilla at rho=0, residual subtraction at rho>0 with common-mode, GNN when structure is unknown.

---

## References

[1] K. Noh and C. Chamberland, "Low-overhead fault-tolerant quantum error correction with the surface-GKP code," Phys. Rev. X **12**, 011058 (2022).

[2] C. Gidney, "Stim: A fast stabilizer circuit simulator," Quantum **5**, 497 (2021).

[3] O. Higgott and C. Gidney, "Sparse Blossom: correcting a million errors per core second with minimum-weight matching," arXiv:2303.15933 (2023).

[4] D. Gottesman, A. Kitaev, and J. Preskill, "Encoding a qubit in an oscillator," Phys. Rev. A **64**, 012310 (2001).

[5] R. W. J. Overwater, M. Babaie, and F. Sebastiano, "Neural-network decoders for quantum error correction using surface codes," IEEE Trans. Quantum Eng. **3**, 3101319 (2022).

[6] N. C. Menicucci, "Fault-tolerant measurement-based quantum computing with continuous-variable cluster states," Phys. Rev. Lett. **112**, 120504 (2014).

[7] B. Brock et al., "Fault tolerant decoding of QLDPC-GKP codes with circuit level soft information," arXiv:2505.06385 (2025).

[8] B. W. Walshe et al., "Robust fault tolerance for continuous-variable cluster states with excess antisqueezing," Phys. Rev. A **100**, 010301(R) (2019).

[9] D. Tse and P. Viswanath, *Fundamentals of Wireless Communications*, Cambridge University Press (2005).

[10] J. Bausch et al., "Learning high-accuracy error decoding for quantum processors," Nature **635**, 834 (2024). [AlphaQubit]

[11] V. Sivak et al., "Real-time quantum error correction beyond break-even," Nature **616**, 50 (2023).

[12] M. A. Tremblay et al., "Constant-overhead quantum error correction with thin planar connectivity," Phys. Rev. Lett. **129**, 050504 (2022).

[13] N. Shutty and C. Chamberland, "Efficient near-optimal decoding of the surface code through ensembling," arXiv:2401.12434 (2024).

[14] T. N. Kipf and M. Welling, "Semi-supervised classification with graph convolutional networks," arXiv:1609.02907 (2017).

[15] S. Wu and Y. Bar-Ness, "OFDM systems in the presence of phase noise: consequences and solutions," IEEE Trans. Comms. **52**, 1988 (2004).

[16] L. Skoric et al., "Parallel window decoding enables scalable fault tolerant quantum computation," Nat. Comms. **14**, 7040 (2023).

[17] S. Liyanage et al., "Scalable quantum error correction for surface codes using FPGA," arXiv:2301.08419 (2023).

---

## Appendix A: Proof of Scale Invariance

The LLR weight of soft-info MWPM is

w_j(r_j, V) = ((sqrt(pi) - |r_j|)^2 - |r_j|^2) / (2V)

For a change V -> V':

w_j(r_j, V') = (V/V') * w_j(r_j, V)

The same scalar V/V' multiplies all edges j, therefore

arg min_{M} sum_{j in M} w_j(V') = arg min_{M} (V/V') sum_{j in M} w_j(V) = arg min_{M} sum_{j in M} w_j(V)

Since V/V' > 0, the optimal matching is invariant. QED

Residual subtraction breaks this identity. The transformation r_j -> r'_j = r_j - r_bar causes |r'_j| to vary non-uniformly depending on r_bar, so w_j(r'_j, V) != c * w_j(r_j, V), and relative edge weights change.

## Appendix B: Derivation of p_phys

For GKP displacement noise standard deviation sigma = sqrt(V_eff/2), the displacement error (nearest lattice point misidentification) probability is

p_phys = (1/2) erfc(sqrt(pi) / (4 sigma))

For sigma_eff = 8.5 dB:

- Beamsplitter model calculation after full loss path (design document 06_noise-budget.md)
- eta = 0.914, V_sqz = 0.0501, V_nl = 0.010 SNU
- V_eff = 0.914 x 0.0501 + 0.086 + 0.010 = 0.142 approx 0.1417 SNU
- sigma = sqrt(0.1417/2) = 0.2662
- p_phys = erfc(sqrt(pi)/(4 x 0.2662))/2 = 9.28 x 10^{-3}

All simulations in this study use V_eff = 0.1417.

## Appendix C: Experimental Parameters and Reproducibility

| Experiment | d values | n_train | n_test | rho conditions | Total shots |
|------|-----|---------|--------|-------|----------|
| V_eff recalibration | 3,5,7 | --- | 30K/30K/10K | 6 | 170K |
| Residual subtraction | 3,5,7 | --- | 30K/30K/10K | 6 | 170K |
| Per-rho GNN | 3,5,7 | 5K/5K/3K | 30K/30K/10K | 6 | ~270K |
| Mixed-rho GNN | 3,5,7 | 5K/5K/3K | 30K/30K/10K | 7(+OOD) | ~310K |
| **Total** | | | | | **~920K** |

Environment: Apple Silicon (MPS), PyTorch 2.5.1, torch_geometric, Stim 1.15.0, PyMatching 2.3.1. Total runtime approximately 15 hours. All results are reproducible with seed=42.

**On DEM edge counts**: Total DEM error entries from Stim (d=3: 76, d=5: 418, d=7: 1,224) differ from actual edge counts used by extract_graph(), which extracts only 1-detector and 2-detector errors (d=3: 66, d=5: 334, d=7: 954). The difference consists of 0-detector (boundary only) and 3+-detector error entries. All simulations use the actual edge counts (66/334/954), and all error counts are generated from a single run_unified.py script (seed=42), ensuring internal consistency.
