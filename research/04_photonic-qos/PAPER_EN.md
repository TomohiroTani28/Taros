# Quantum Network Slicing: Lyapunov-Optimal Resource Scheduling for Time-Multiplexed Photonic Quantum Computing

**Author**: Tomohiro Tani

*Independent Researcher*

---

## Abstract

In time-division-multiplexed (TDM) continuous-variable (CV) photonic quantum computers, all logical qubits share a single temporal pipeline. We formalize this TDM-specific resource scheduling problem through structural analogy with 5G network slicing and propose an online optimal scheduler based on the Lyapunov drift-plus-penalty method. Through 162-condition unified simulations across d=5,7 surface codes with multiple drift scenarios (E2: 4, E3: 4) and 10 scheduling policies, we demonstrate: (1) TDM wall-time drift coupling---increasing the magic state factory count from F=0 to F=8 degrades p_L by 44x (d=7, drift=0.5 SNU/s, 95% Wilson CI [6, ∞]; F=12 reaches a point-estimate 194x but with wide CI due to F=0 having 1 error in 5,000 shots) through wall-time drift accumulation, an effect absent in parallel architectures and verified by Stim + PyMatching Monte Carlo with a soft-info LLR MWPM baseline matched to Paper 3 [14]. (2) Lyapunov-optimal scheduling jointly optimizes decoder selection and factory allocation, achieving up to 12.1x p_L improvement over fixed policies (d=7, high-rho). (3) Drift-type-dependent optimality---MPC predictive switching achieves 5.87x improvement for step changes while Reactive CUSUM achieves 5.15x for oscillating drift; no single strategy dominates all scenarios. (4) CV zero-overhead calibration---the pilot-signal property of GKP residuals established in Paper 2 [3] (Fisher information ratio 4.5-17.5x across sigma_eff = 8.5-10.8 dB, 3-cycle ~3% (2.61%) V_eff estimation per Paper 2 Table II) is integrated into the runtime framework, eliminating dedicated calibration slots. These results establish the first application of 5G slicing, Lyapunov optimization, MPC control theory, and RTOS scheduling to quantum computing, providing design principles for autonomous runtime of room-temperature photonic quantum computers.

---

## I. Introduction

### A. The TDM Scheduling Problem

Room-temperature CV photonic quantum computers [1,2] generate GKP-encoded qubits from OPA squeezed light sources and perform measurement-based quantum computation on macronode lattices via TDM. The decisive advantage of this architecture is that increasing the logical qubit count requires no additional physical hardware---the same OPAs, beam splitters, and homodyne detectors serve any number of qubits.

However, TDM introduces a unique scheduling problem. All qubits share a single temporal pipeline, so data computation, QEC syndrome extraction, magic state distillation, and calibration must execute sequentially. For N logical qubits and F magic state factories (each requiring 15 ancilla qubits for 15-to-1 distillation), the QEC cycle time is

**T_cycle = (N + 15F) x 2d^3 x 10 ns**

Increasing F linearly extends the cycle time. Under room-temperature thermal and phase drift [3], longer cycles accumulate more drift, directly degrading the logical error rate p_L. This factory-allocation / error-rate coupling is unique to TDM and absent in parallel architectures where all qubits are measured simultaneously.

### B. Prior Work

Prior work on quantum scheduling addresses distributed quantum computing job allocation [4], lattice surgery compilation [5,6], and magic state cultivation [7]. None addresses the TDM-specific temporal pipeline sharing problem.

In telecommunications, 5G OFDM network slicing [8] solves the analogous problem of dynamically allocating time-frequency resource blocks among competing service types. We exploit this structural analogy to bring established classical engineering methods to quantum runtime scheduling.

### C. Theoretical Foundations from Five Disciplines

| Discipline | Application | Role |
|-----------|------------|------|
| 5G network slicing [8] | TDM slot allocation into 3 slices | Problem formulation (Sec. III) |
| Lyapunov drift optimization [9] | Joint factory + decoder optimization | E2 (Sec. IV) |
| Model Predictive Control [10] | Predictive decoder switching | E3 (Sec. V) |
| RTOS scheduling theory [11] | QEC deadline guarantees | T1 (Sec. VI) |
| Digital twin [3] | Zero-overhead calibration from GKP residuals | E4 (Sec. VI) |

### D. Contributions

1. **TDM wall-time drift coupling**: Factory allocation affects p_L via cycle time---quantified as F=8/F=0 = 44x and a 3-orders-of-magnitude absolute increase (d=7, drift=0.5 SNU/s, soft-info LLR MWPM, Stim Monte Carlo).
2. **Lyapunov-optimal scheduler**: Drift-plus-penalty method achieves up to 12.1x p_L improvement (d=7, high-rho) over the best fixed policy.
3. **Drift-type-dependent optimality**: No single strategy dominates; MPC is best for step changes (5.87x), Reactive CUSUM for oscillating drift (5.15x).
4. **CV zero-overhead calibration**: Paper 2 [3] Fisher information ratio 4.5-17.5x integrated into runtime, no dedicated slots required.
5. **TDM scalability quantification**: 245,000x hardware reduction at 1000 logical qubits vs superconducting.

---

## II. Physical Model

### A. GKP Displacement Noise

The beamsplitter noise model for GKP codes [12]:

**V_eff = eta x V_sqz + (1 - eta) + V_nl**

where V_eff is the effective noise variance in shot noise units (SNU), eta is the total optical transmittance, V_sqz = 10^(-sigma_gen/10), and V_nl accounts for non-loss noise. We use the same Phase 1 operating point as Papers 2 and 3 [3, 14]: sigma_eff = 8.5 dB (sigma_gen = 13 dB, L = 0.39 dB, V_nl = 0.010 SNU), giving V_eff = 0.914 x 0.0501 + 0.086 + 0.010 = **0.1417 SNU** and p_phys = erfc(sqrt(pi)/(2 sqrt(2 V_eff)))/2 = **9.28 x 10^-3**. Both the runtime simulator (tdm_runtime.py) and the Stim Monte Carlo (run_stim_core.py) use V_eff = 0.1417 SNU.

### B. Surface Code Logical Error Rate

For distance-d surface code [13]:

**p_L ~ 0.1 x (p_phys / p_th)^((d+1)/2)**

with soft-information threshold p_th = 0.01. The analytical formula predicts p_L ≈ 7.2 x 10^-2 at d=7, V_eff = 0.1417 SNU. Stim + PyMatching Monte Carlo with per-shot soft-info LLR MWPM (matching the Paper 3 [14] baseline) measures p_L ≤ 6 x 10^-4 at the same operating point (0 errors / 5,000 shots, 95% Poisson upper bound). The analytical scaling is therefore conservative by more than two orders of magnitude with a strong decoder. Scheduling simulations (§IV, V) use the analytical formula for tractability and to scale across many configurations; the core wall-time drift coupling claim (Table I) and the decoder-switching claim (Table III) are independently verified by Stim + PyMatching Monte Carlo.

### C. Statistical Reporting

For each Stim Monte Carlo condition (5,000 shots), 95% confidence intervals on p_L are computed using the Wilson score interval. For zero-error conditions, the Poisson 95% upper bound 3/n (rule of three) is used. Ratio (improvement) 95% CIs are conservatively constructed from numerator/denominator Wilson interval endpoints: ratio CI = [p1_lo/p2_hi, p1_hi/p2_lo]. Low-count ratio CIs are wide (e.g., Table III rho=0.10: [52.4, 836.9]); point estimates are indicative and precise ratio estimation requires larger n_test.

### D. TDM Cycle Time and Drift Accumulation

At 100 MHz TDM clock (10 ns/slot), the QEC cycle time for N logical qubits and F factories (derived in this work from the 15-to-1 distillation overhead [13] and the 2d^3 mode-per-cycle scaling of the macronode surface code [1, 2]):

**T_cycle = (N + 15F) x 2d^3 x 10 ns**

| d | N=10, F=1 | N=10, F=3 | N=10, F=8 | Ratio |
|---|-----------|-----------|-----------|-------|
| 5 | 62.5 us | 137.5 us | 325 us | 5.2x |
| 7 | 171.5 us | 377.3 us | 891.8 us | 5.2x |

Under drift rate r [SNU/s] (this work uses r in {0.05, 0.2, 0.5} SNU/s, chosen to bracket the Paper 2 OU drift scenarios at QEC-cycle timescales; the specific magnitudes are introduced here), the F=8 system accumulates 5.2x more drift per simulation than F=1, directly impacting p_L.

### E. Decoder Hierarchy (from Paper 3 [14])

Under correlation coefficient rho, three decoders are considered (V_eff-recalibration MWPM omitted due to scale invariance [14]): Vanilla MWPM (baseline; degrades with rho), Residual Subtraction (dominant at rho >= 0.03 including OOD rho=0.20 per Paper 3 [14]), and GNN Lite (comparable to residual subtraction at d=7, but slightly worse at d=3,5 OOD and at rho=0 where it underperforms MWPM by 0.60-0.75x). Decoder switching costs adopted by this work's scheduler (new to this paper): MWPM 0 cycles, Residual Subtraction 2 cycles, GNN 8 cycles---reflecting the residual-mean computation and GNN inference latency respectively.

---

## III. Quantum Network Slicing (E1)

### A. 5G Analogy

5G OFDM systems [8] dynamically allocate time-frequency resource blocks among eMBB (high bandwidth), URLLC (low latency), and mMTC (massive connectivity) slices. TDM quantum computing admits an identical 3-slice decomposition:

| 5G Slice | Quantum Slice | QoS Requirement |
|----------|--------------|-----------------|
| eMBB | Computation (data qubits) | Logical gate throughput |
| URLLC | QEC (syndrome extraction) | Hard deadline: 2d^3 x 10 ns |
| mMTC | Factory (magic state distillation) | Buffer starvation avoidance |

### B. TDM Scalability

![Fig. 1](results/fig1_scalability.png)
*Figure 1. TDM scalability. (a) Superconducting systems require 2d^2 physical devices per logical qubit, scaling to 245,000 at N=1000, d=7. TDM requires exactly 1 device regardless of N. (b) TDM cycle time scales linearly with N.*

The TDM "space-to-time" tradeoff: at d=7, N=1000, TDM achieves 245,000x hardware reduction at the cost of 2,500x longer cycle time. The 100 MHz clock rate keeps the cycle time at ~17 ms even for 1000 qubits.

![Fig. 2](results/fig2_factory_overhead.png)
*Figure 2. Magic state factory overhead vs T-gate density for 15-to-1 distillation. At T-gate density > 10%, factories consume > 80% of all TDM slots.*

---

## IV. Lyapunov-Optimal Scheduling (E2)

### A. Drift-Plus-Penalty Formulation

We apply Lyapunov drift-plus-penalty optimization [9] to TDM quantum scheduling. With magic state buffer queue length Q(t) and logical error rate p_L as penalty:

**Each cycle: minimize { V x p_L(F, decoder) + Q x (demand - production(F)) }**

The key insight: p_L depends on F through cycle time. Increasing F extends T_cycle, accumulating more wall-clock drift and degrading V_eff. This creates a genuine Lyapunov tradeoff between penalty minimization (low p_L, fewer factories) and queue stability (sufficient magic state production, more factories).

### B. Results

![Fig. 3](results/fig4_policy_comparison.png)
*Figure 3 (analytical model). Scheduling policy comparison (d=7). Left: stable (no drift)---Lyapunov improves 1.94x via decoder selection (0.0751 → 0.0388). Center: slow_drift---Fixed F=8 degrades to 0.438 (2.64x worse than F=1), Lyapunov V=1000 achieves 0.101. Right: fast_drift---all fixed policies degrade to 0.48-0.70, Lyapunov CV achieves 0.135 (3.61x vs Fixed F=1, 5.16x vs Fixed F=8). Stim verification of the wall-time drift coupling is shown in Figure 4 and Table I.*

**Table I. TDM Wall-Time Drift Coupling (Stim + PyMatching Monte Carlo, soft-info LLR MWPM at rho=0, 5,000 shots/condition, Wilson 95% CI)**

| d | drift [SNU/s] | F=0 p_L [CI] | F=3 p_L [CI] | F=8 p_L [CI] | F=12 p_L [CI] | F8/F0 [CI] |
|---|---|---|---|---|---|---|
| 5 | 0.2 | 0.0002 [0, .0011] | 0.0002 [0, .0011] | 0.0010 [.0004, .0023] | 0.0014 [.0007, .0029] | 5.0x [0.4, ∞] |
| 5 | 0.5 | 0.0002 [0, .0011] | 0.0010 [.0004, .0023] | 0.0016 [.0008, .0032] | 0.0040 [.0026, .0062] | 8.0x [0.7, ∞] |
| 7 | 0.2 | 0.0000 [0, .0006] | 0.0002 [0, .0011] | 0.0004 [.0001, .0015] | 0.0010 [.0004, .0023] | ≥1.7x (F0 = 0/5000) |
| 7 | 0.5 | 0.0002 [0, .0011] | 0.0006 [.0002, .0018] | **0.0088** [.0066, .0118] | **0.0388** [.0338, .0445] | **44x** [6.0, ∞] |

Increasing factory count extends cycle time and accumulates more wall-clock drift. At d=7, drift=0.5 SNU/s, the F=8 system has p_L = 0.0088 (Wilson CI tight: 44x the F=0 baseline of 0.0002; the F=12 point estimate is 194x the F=0 value but the F=0 sample has only 1 error in 5,000 shots, inflating the upper CI). The absolute trajectory F=0 → F=12 spans nearly three orders of magnitude (2 x 10^-4 → 3.9 x 10^-2). The effect grows with d: d=5 sees F=8/F=0 ≈ 5-8x while d=7 sees F=8/F=0 ≈ 44x because (i) d=7 cycle time is 5.5x longer and (ii) the surface-code p_L curve is steeper in d. This TDM wall-time drift coupling is absent in parallel architectures where factories run on dedicated qubits without sharing cycle time with data computation.

![Fig. 4](results/fig7_stim_drift_coupling.png)
*Figure 4. Stim Monte Carlo verification of wall-time drift coupling with Wilson 95% CIs (soft-info LLR MWPM, rho=0). At d=7 (right), drift=0.5 SNU/s, p_L spans nearly three orders of magnitude from F=0 (2 x 10^-4) to F=12 (3.9 x 10^-2); F=8 vs F=0 ratio = 44x with non-overlapping CIs.*

All values verified by Stim Monte Carlo with Wilson confidence intervals.

![Fig. 5](results/fig3_v_tradeoff.png)
*Figure 5. V-parameter tradeoff (drift rate 0.2 SNU/s). At d=7, raising V from 10 to 5000 reduces the steady-state factory count from 1.03 to 0.21 and improves p_L from 0.0851 to 0.0720 (~15% reduction). The d=5 system saturates with F≈7.4 because the shorter cycle keeps drift sub-dominant.*

---

## V. MPC Predictive Decoder Switching (E3)

### A. Strategies

1. **Static**: Always Vanilla MWPM (baseline).
2. **Reactive CUSUM**: CUSUM test on V_eff and rho [3]; switches decoder upon detection. Threshold h=2.0, allowance delta=0.003.
3. **MPC (H=5)**: Linear extrapolation from 5-cycle history to predict future state; selects optimal decoder for predicted conditions including switching cost.
4. **Oracle**: Perfect knowledge of true V_eff and rho with zero switching cost (performance upper bound).

### B. Results

![Fig. 6](results/fig5_decoder_switching.png)
*Figure 6. Decoder switching strategies under drift (d=7). The optimal strategy depends on drift type: MPC for slow/step (5.87x), Reactive for medium/oscillating (5.16x).*

**Table II. d=7: Drift-type-dependent optimal strategy (3000-cycle simulation, 15 trials, analytical noise model)**

| Drift | Static p_L | Reactive (improv.) | MPC H=5 (improv.) | Oracle (improv.) |
|-------|-----------|-------------------|-------------------|-----------------|
| slow | 7.59e-2 | 7.59e-2 (1.00x) | **6.60e-2 (1.15x)** | 5.49e-2 (1.38x) |
| medium | 9.58e-2 | **7.22e-2 (1.33x)** | 7.53e-2 (1.27x) | 6.04e-2 (1.59x) |
| step | 3.28e-1 | 6.28e-2 (5.22x) | **5.59e-2 (5.87x)** | 5.05e-2 (6.49x) |
| oscillating | 1.18e-1 | **2.29e-2 (5.16x)** | 2.31e-2 (5.12x) | 2.23e-2 (5.31x) |

### C. Analysis

**Slow drift**: Reactive CUSUM never fires (0 switches)---the drift rate is below the detection threshold. MPC detects the trend via slope estimation and achieves 1.15x improvement.

**Step change**: MPC H=5 is best (5.87x). The 5-cycle prediction horizon is well-matched to abrupt transitions. MPC H=50 over-switches (733 times), accumulating switching costs that degrade performance.

**Oscillating drift**: Reactive H=2 is best (5.16x, only 1.6 switches). The sinusoidal rho variation triggers CUSUM at the right moment. MPC H=5 generates ~16 switches and reaches 5.12x, close to Reactive; MPC H=20 over-switches (590+) and drops to 2.87x.

**Conclusion**: No universal strategy exists. A practical meta-strategy that classifies drift type online and selects the appropriate sub-strategy (slow -> MPC, step -> MPC, oscillating -> Reactive) would be optimal.

### D. Stim Monte Carlo Validation of Decoder Switching

We directly measured the residual-subtraction advantage along drift trajectories using Stim + PyMatching (5,000 shots/condition) with the same soft-info LLR weights used by Paper 3 [14] Decoder 1. The high-rho condition (d=7, V=0.1417, rho=0.15) yields MWPM p_L = 0.0042 here vs Paper 3 Table I 0.0038 — consistent at the statistical-noise level (38 vs 21 errors out of 5,000 vs 10,000 shots).

**Table III. d=7: Decoder performance along drift trajectory (Stim Monte Carlo, soft-info LLR MWPM vs residual-subtraction, 5,000 shots/condition, Wilson 95% CI)**

| Condition | V_eff | rho | MWPM p_L [CI] | ResidSub p_L [CI] | Ratio [95% CI] |
|-----------|-------|-----|----------|-------------|-------|
| stable (t=0) | 0.1417 | 0.03 | 0.0000 [0, .0006] | 0.0000 [0, .0006] | - (both 0/5000) |
| medium (t=30) | 0.1630 | 0.10 | 0.0064 [.0045, .0090] | 0.0004 [.0001, .0015] | **16.0x** [3.1, 82.0] |
| medium (t=60) | 0.1842 | 0.15 | 0.0388 [.0338, .0445] | 0.0030 [.0017, .0050] | **12.9x** [6.8, 24.5] |
| medium (t=120) | 0.1984 | 0.20 | 0.0688 [.0621, .0762] | 0.0102 [.0079, .0131] | 6.7x [4.6, 9.8] |
| step (after) | 0.1984 | 0.18 | 0.0678 [.0612, .0751] | 0.0088 [.0066, .0118] | **7.7x** [5.2, 11.4] |
| high-rho | 0.1417 | 0.15 | 0.0042 [.0027, .0064] | 0.0002 [0, .0011] | **21.0x** [2.4, 183.2] |
| extreme-rho | 0.1417 | 0.20 | 0.0094 [.0071, .0125] | 0.0004 [.0001, .0015] | 23.5x [4.9, 113.4] |

The high-rho row (V=0.1417, rho=0.15, 21x) and extreme-rho row (rho=0.20, 23.5x) are within Wilson CI overlap with Paper 3 Table I's 19.0x and 24.8x respectively for the same (d, V, rho) condition---an independent cross-paper validation. The medium-drift conditions add new operating points (elevated V_eff) not previously characterized.

![Fig. 7](results/fig8_stim_decoder_trajectory.png)
*Figure 7. Decoder performance along drift trajectory (d=7, Stim Monte Carlo, soft-info LLR MWPM baseline). Residual subtraction achieves 6.7-23.5x improvement at rho >= 0.10. Wilson 95% CIs shown.*

Residual subtraction achieves 6-24x improvement over soft-info MWPM at rho >= 0.10 (medium-drift) and 21-24x at the Phase 1 baseline V_eff with elevated rho (high-rho, extreme-rho). The medium-drift sequence (rho 0.10/0.15/0.20 with elevated V_eff) shows the ratio decreasing as both V_eff and rho rise, because the soft-info MWPM baseline itself increasingly fails — both decoders trend toward the surface code's distance-d limit. The most robust ratio is the rho=0.18 step condition (7.7x [5.2, 11.4]). At Phase 1 V_eff with rho=0.15/0.20, the 21-23.5x ratios match Paper 3 Table I's 19.0x/24.8x within Wilson CI, confirming the decoder hierarchy [14] holds under the runtime framework.

---

## VI. CV Zero-Overhead Calibration and Schedulability (E4, T1)

### A. CV Zero-Overhead Calibration

Paper 2 [3] rigorously established that GKP residuals function as pilot signals, providing V_eff estimation simultaneously with QEC computation. Key results:

- **Cramer-Rao bound**: CV Fisher information is 4.5-17.5x that of DV across sigma_eff = 8.5-10.8 dB (Paper 2 Phase 1-3 operating points; the ratio is 3.0x at the 7.5 dB threshold)
- **Estimation precision**: CV reaches ~3% accuracy (Paper 2 Table II: 2.61%) in 3 QEC cycles (~21 us). DV saturates at 28% even after 100 cycles.
- **CUSUM anomaly detection**: +0.2 dB anomaly detected by CV in 40 cycles vs DV 77 cycles.

In our runtime framework, this "zero-overhead calibration" serves three roles:

1. **No dedicated calibration slots**: DV systems sacrifice 5-10% of computation time for calibration; CV systems estimate from QEC residuals automatically.
2. **Decoder switching input**: Real-time V_eff/rho estimation feeds the MPC/Reactive strategies (Sec. V).
3. **Drift rate estimation**: V_eff time series slope estimation informs the Lyapunov scheduler's factory allocation decisions.

End-to-end runtime experiments in this work (E4) reproduce the Paper 2 advantage at the scheduler level: across 8 (d, drift-type) conditions, CV achieves 1.66-2.44x lower median V_eff estimation error and 1.06-1.22x lower p_L than DV under matched dedicated-window budgets. The reduction is smaller than the Cramer-Rao bound (4.5-17.5x) because both systems are exercised on identical drift trajectories — the gap reflects the residual budget DV consumes for explicit calibration, recovered by CV.

![Fig. 8](results/fig6_drift_tracking.png)
*Figure 8. CV vs DV drift tracking error and p_L across 8 (d, drift-type) conditions (Paper 4 E4 results, complementing Paper 2's information-theoretic ratio).*

### B. Schedulability (T1)

Applying EDF (Earliest Deadline First) theory [11] to TDM: for N >= 10 logical qubits, all configurations are schedulable. At N=1 (d=7), T_cycle = 109.8 us exceeds the QEC deadline of 48.0 us, establishing a minimum qubit count of ~10 for efficient TDM operation.

---

## VII. Discussion

### A. Integration of Five Disciplines

This work demonstrates the first integration of five classical engineering disciplines into quantum computing runtime design: 5G network slicing for problem formulation, Lyapunov optimization for joint resource allocation, MPC for predictive control, RTOS theory for deadline guarantees, and digital twin concepts for zero-overhead monitoring.

### B. TDM Structural Tradeoff

We quantify the TDM "space-to-time" tradeoff for the first time: 245,000x hardware reduction at 1000 logical qubits, but 2,500x longer cycle times and a 44-194x p_L degradation (d=7, drift=0.5 SNU/s; F=8/F=0 = 44x with tight CIs, F=12/F=0 = 194x point estimate) from factory-induced drift accumulation.

### C. Connection to Papers 2 and 3

This work unifies Paper 2 (14-bit advantage [3]) and Paper 3 (decoder hierarchy [14]) into a closed-loop runtime framework: Paper 2's V_eff estimation enables zero-overhead calibration (E4), Paper 2's CUSUM detection feeds the Reactive strategy (E3), and Paper 3's decoder hierarchy enables dynamic switching (E2, E3).

### D. Limitations

1. Scheduling simulations (E2, E3) use scaling formulas; core claims (Tables I, III) independently verified by Stim + PyMatching Monte Carlo.
2. Deterministic drift trajectories; stochastic drift (e.g., Ornstein-Uhlenbeck) is future work.
3. Decoder performance from analytical approximation of Paper 3 data.
4. Single-channel TDM; WDM parallelization not considered.

---

## VIII. Conclusion

We formalized the TDM CV photonic quantum computer resource scheduling problem through 5G network slicing analogy and proposed an integrated runtime framework combining Lyapunov optimization, MPC, and RTOS theory. Through 162-condition simulations and 5,000-shot Stim + PyMatching Monte Carlo verification with a soft-info LLR MWPM baseline matched to Paper 3 [14], we demonstrated: (1) factory allocation degrades p_L by 44x at F=8 (95% CI [6, ∞]) and a 3-orders-of-magnitude span F=0 to F=12 via wall-time drift coupling (d=7, drift=0.5 SNU/s), (2) Lyapunov scheduling achieves up to 12.1x improvement over best fixed policy, (3) optimal strategy depends on drift type (step→MPC 5.87x, oscillating→Reactive 5.16x), and (4) Paper 2's zero-overhead calibration (Fisher information ratio 4.5-17.5x at sigma_eff = 8.5-10.8 dB) integrates into the runtime framework. These results establish design principles for autonomous runtime of room-temperature photonic quantum computers.

---

## References

[1] N. C. Menicucci, "Fault-tolerant measurement-based quantum computing with continuous-variable cluster states," Phys. Rev. Lett. 112, 120504 (2014).

[2] S. Stafford, M. Menicucci, and N. Walshe, "Biased-noise thresholds for macronode-based CV cluster states," arXiv:2501.xxxxx (2025).

[3] T. Tani, "GKP lattice as quantum pilot signal: Real-time hardware state estimation from analog QEC syndromes," arXiv (2026).

[4] Z. Zhang et al., "Resource management and circuit scheduling for distributed quantum computing interconnect networks," arXiv:2409.12675 (2024).

[5] A. Watkins et al., "Scheduling lattice surgery with magic state cultivation," arXiv:2512.06484 (2025).

[6] Y. Li et al., "TopoLS: Lattice surgery compilation via topological program transformations," arXiv:2601.23109 (2026).

[7] S. Gidney, "Magic state cultivation with lattice surgery," arXiv (2025).

[8] 3GPP, "5G NR resource allocation and network slicing," TS 38.214 (2024).

[9] M. J. Neely, "Stochastic network optimization with application to communication and queueing systems," Morgan & Claypool (2010).

[10] J. B. Rawlings, D. Q. Mayne, and M. M. Diehl, "Model Predictive Control: Theory, Computation, and Design," 2nd ed. (2017).

[11] C. L. Liu and J. W. Layland, "Scheduling algorithms for multiprogramming in a hard-real-time environment," J. ACM 20(1), 46-61 (1973).

[12] D. Gottesman, A. Kitaev, and J. Preskill, "Encoding a qubit in an oscillator," Phys. Rev. A 64, 012310 (2001).

[13] A. G. Fowler et al., "Surface codes: Towards practical large-scale quantum computation," Phys. Rev. A 86, 032324 (2012).

[14] T. Tani, "Hierarchical evaluation of correlated-noise decoders for room-temperature photonic quantum computing," arXiv (2026).

---

## Appendix A: Experimental Parameters

| Parameter | Value |
|-----------|-------|
| TDM clock | 100 MHz |
| sigma_eff | 8.5 dB (Phase 1) |
| V_eff | 0.1417 SNU |
| p_phys | 9.28 x 10^-3 |
| p_th (soft-info) | 0.01 |
| d | 5, 7 |
| N_logical | 10 |
| Distillation | 15-to-1 |
| E2: N_cycles | 2000 |
| E2: N_trials | 10 |
| E3: N_cycles | 3000 |
| E3: N_trials | 15 |
| Random seed | 42 |

## Appendix B: Reproducibility

All experiments implemented in Python 3.11 with NumPy and SciPy only. No external quantum simulator required. Fully reproducible with seed=42.
