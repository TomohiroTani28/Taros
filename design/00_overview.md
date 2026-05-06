# CV方式 Executive Summary — Taros Portable

**Document ID**: PQC-CV-EXEC-v2.0
**Last Updated**: 2026-05-05
**Status**: 確定版
**検証**: Stim ~100M shots + 数値計算 + 文献9件で独立検証済み → `experiments/02_virtual-experiments.md`

---

## ビジョン

> **「ACアダプタで動くデスクトップサイズの誤り訂正型量子コンピュータ」**

---

## 正規パラメータ (Single Source of Truth)

全設計文書はこのテーブルの値を正とする。変更時はここを更新し、関連文書に伝播させること。

| パラメータ | 記号 | 正規値 | 条件 | 根拠文書 |
|-----------|------|--------|------|----------|
| 生成スクイージング | σ_gen | 13dB | CW PPLN OPA (NTT) | 02_opa-source |
| 全劣化 (GAWBS込み) | L_total | 1.42dB (離散光学) / 0.39dB (Phase 1 離散光学) / 0.15dB (Phase 2+ PIC) | ビームスプリッタモデル: η=10^(-L/10) | 06_noise-budget v2.0 |
| 実効スクイージング | σ_eff | **5.0dB** (現離散光学) / 8.8dB (Phase 1, 13dB) / 9.5-10.2dB (Phase 2+ PIC 現実的) / 10.9dB (理論限界) | v3.1修正: Phase 1を13dBに統一。PIC L=0.27dB(現実的) | 06_noise-budget v3.1 |
| 物理エラー率 | p_phys | 現離散(5.0dB): 閾値未達 / Phase 1(13dB, 8.8dB): 7.5×10⁻³ / Phase 2+ PIC現実的(13dB, ~9.7dB): ~3×10⁻³ | v3.1 erfc再計算 | 13_performance |
| 閾値 (soft-info) | p_th_eff | 1.5% | soft-info MWPM (Noh-Chamberland 2022); UF時≈0.8-1.2%. v3.2: 製品デコーダはMWPM (現実的L=0.27dBでUF~5×10⁻⁴>10⁻⁵) | 08_decoder |
| 閾値 (保守) | p_th | 0.59% | hard-syndrome MWPM | 文献値 |
| 論理エラー率 d=7 (Δ=0理想) | p_L | **5.7×10⁻⁷ (MWPM, Phase 2+ PIC)** [理論上限値] | v3.3: 製品目標p_L≲10⁻⁵。現実的PIC(L=0.27dB, QE≥99%)でMWPM~2-5×10⁻⁵(境界)。L≤0.20dBで<10⁻⁵確実。UF~5×10⁻⁴(超過)→MWPM必須 | 13_performance |
| 論理エラー率 d=7 (現実Δ=0.12) | p_L | **~1.2×10⁻⁵ (UF)** / ~6×10⁻⁶ (MWPM) [対外基準値] | 13_performance §3シナリオ「現実」行 | 13_performance |
| QD等価スクイージング | — | +2.7dB (QD=2) | σ_eff等価13.6dB (10.9+2.7, v3.4修正: 旧14.2dBは11.5dB基準) | 01_system-arch |
| TDMクロック | f_TDM | 100MHz | Option B パルスOPA | 03_tdm-cluster |
| macronode列数 | N_col | 2d² (18/50/98) | d=3/5/7 | 03_tdm-cluster |
| フィードフォワード | t_FF | **27ns** (設計ベースライン400MHz) / 22ns (楽観500MHz) | TIA 3 + ADC 3 + FPGA 12.5 + DAC 5 + EOM 3 = 26.5≈27ns | 07_feedforward |
| デコーダ遅延 | t_dec | **510ns (MWPM製品) / 350ns (UF実験)** (400MHz) | MWPM: Blossom-V, 製品デコーダ; UF: Phase 0-1実験用 | 08_decoder |
| GKP忠実度 | F_GKP | Phase依存 | σ_eff=5.0dB(現行)では低忠実度; Phase 2+ PIC σ_eff=10.9dBで高忠実度 | 04_gkp-protocol |
| 閾値マージン | — | v2.0修正: 現離散光学→閾値未達; Phase 1→+1.3dB(PS)/−1.2dB(全モード); Phase 2+ PIC→+3.4dB(PS)/+0.9dB(全モード) | vs 7.5dB / 10.0dB [v3.3: Phase 1は8.8dB基準] | 06_noise-budget v2.0 |
| 反スクイージング | — | **~13dB** (単一パスOPA: sq≈anti-sq) | v1.8修正: 旧20dBは共振器OPO誤引用 | 02_opa-source |
| PLL残留位相 | φ_res | <0.05° (BW≥500kHz) | 位相ノイズ**<0.002dB** (anti-sq 13dBで事実上無視可能) | 05_phase-lock |
| 有限エネルギーGKP | Δ | <0.15 (必須要件) | Δ≥0.2でFAIL | 04_gkp-protocol |
| ポンプ源 | — | Option B: 1550nm GS-DFB + SOA + PPLN SHG → 775nm | Rack: SOA 800mW→SHG 200mW→8分配; Portable: SOA 1.6W→SHG 400mW→1×2→200mW/OPA | 02_opa-source |
| LO生成 | — | 100mW Master + EO comb + EDFA → 10mW/ch | — | 05_phase-lock |
| 電源 | — | USB-PD EPR 140W (28V/5A) 推奨 | Pro 109W / Max 112W で100W不可。Edu(100W)は100W境界 [v3.2: SOA +3W] | 10_portable |

> **⚠ 正規パラメータの前提条件（必読）**:
> 上記 p_L値は以下の全条件を同時に満たす場合の**条件付き推定値**:
> 1. 有限エネルギーGKP Δ < 0.12（光学系で未実証。超伝導系では Δ≈0.12 達成済み）
> 2. 独立ノイズ仮定が成立（共通ポンプRIN < −150 dB/Hz でモード間相関 ρ < 0.03）
> 3. PLL残留位相 < 0.05°（BW ≥ 500kHz）
> 4. soft-info デコーダ閾値 p_th ≥ 1.0%（macronode TDM構造での有効性は未検証）
> 5. OPA 生成スクイージング ≥ 13 dB（現最高 12.1 dB CW、+0.9 dB ギャップ）
>
> **現実シナリオ**: OPA 12.5dB, Δ=0.12 の場合 p_L(d=7) ~ 10⁻⁵。Phase -1 実験で条件1-3を検証予定。

---

## Taros Portableシリーズ最終仕様

| | **Taros Edu** | **Taros Pro** | **Taros Max** |
|---|:---:|:---:|:---:|
| 表面符号距離 | d=3 | d=5 | d=7 |
| 論理エラー率 (MWPM, Phase 2+ PIC) | — | — | **~5.7×10⁻⁷** (v2.1修正, σ_eff=10.9dB, MWPM d=7) |
| 論理qubit数 | 1-10 | 10-100 | **10-1,000+**⁑ |
| Tゲートレート (WDM並列込み) | 10kHz (5ch) | 3kHz (8ch) | 1kHz (7ch)† |
| Tゲートレート (単一ch) | ~1.9kHz | ~400Hz | ~146Hz |
| 筐体 | 25×20×10cm | 30×25×16cm | 40×30×20cm |
| 重量 (WDM込み) | **~4.3kg** | **~7.5kg** | **~9.7kg** |
| 消費電力 (WDM込み) | **~100W** | **~109W** | **~112W** | [v3.2: SOA +3W全モデル反映]
| 冷却 | 低速ファン+底面HS | 低速ファン+背面HP | 低速ファン×2 |
| 原価 (WDM込み) | $53K | $75K | $95K |
| 販売価格 | **$90K** | **$120K** | **$170K** |
| 用途 | 教育・QEC研究 | 研究・VQE | **FTQC・量子化学 (Phase 2+ PIC)** |

†Max WDM 7ch: d=7ではQECサイクルが長い(6.86μs)ため、7chでターゲット論理ゲートレート~1kHzを達成。8ch化は消費電力増(+1W)に対し性能改善が限定的。
**Tゲートレート モード区分**: 上表の値はstrict postselection(全QECラウンド高信頼)モード。全モード(postselectionなし)では最小間隔=7.42μs(d=7)→単一ch ~135kHz, 7ch ~945kHz。Strictモードは最高品質だが低レートとなる。用途に応じてモード選択可能。

---

## 技術アーキテクチャ

```
PPLN導波路OPA (13dB squeezing, NTT)
    │ PMF fiber
    ▼
macronode TDMクラスタ (100MHz, OPA×2 + BS×3)
    │ PMF 20-200m delay
    ▼
ホモダイン検出 (InGaAs PD×2, 室温)
    │ 14bit ADC 1GSPS
    ▼
FPGA (Versal VE2302)
    ├── GKP内部デコーダ (18.5ns @400MHz: TIA 3ns + ADC 3ns + FPGA 12.5ns)
    ├── 表面符号MWPM (510ns @400MHz, 製品) / UF (350ns, 実験)
    ├── フィードフォワード制御 (27ns @400MHz)
    └── 位相ロック管理
```

**動作条件**: 冷凍機不要、QD不要、SNSPD不要。完全室温動作、冷却は低速ファン(<25dBA)。

---

## 性能の根拠

| パラメータ | 値 | 根拠 |
|-----------|-----|------|
| PPLN OPA生成スクイージング | 13dB | NTT PPLN導波路 CW 12.1dB実証、SiN clad改良で13dB見込み |
| 全経路劣化 (AWG+EO消光比込み) | 1.42dB (離散光学) / 0.39dB (Phase 1) / 0.15dB (Phase 2+ PIC) | CVノイズバジェット v2.0 |
| **実効スクイージング σ_eff** | **5.0dB (現離散光学) / 8.8dB (Phase 1, 13dB) / 10.9dB (Phase 2+ PIC)** | v2.0修正: ビームスプリッタモデル。旧 σ_gen−L=11.5dB は物理的に不正確 [v3.3: Phase 1を13dB/8.8dBに統一] |
| GKP+表面符号閾値 (postselection) | 7.5dB | Stafford-Menicucci-Walshe 2025 (P_round=10⁻³, strict mode時) |
| GKP+表面符号閾値 (全モード重み付け) | ~10dB | Noh-Chamberland 2022 unconditional相当 |
| **閾値マージン (Phase 2+ PIC, postsel)** | **+3.4dB** | 10.9 - 7.5 |
| **閾値マージン (Phase 2+ PIC, 全モード)** | **+0.9dB** | 10.9 - 10.0 |
| **閾値マージン (Phase 1, postsel)** | **+1.3dB** | 8.8 - 7.5 (break-even境界) [v3.2: 旧9.4dB(15dB)→8.8dB(13dB)] |
| **閾値マージン (現離散光学, Option A+AWG)** | **閾値未達** | 5.0dB < 7.5dB。**注: Phase -1実験はOption B(AWGなし, L=0.39dB, σ_eff=8.8dB)で実施。閾値超過+1.3dB** |
| 物理エラー率 p_err (v3.1) | Phase 1(13dB): 7.5×10⁻³ / Phase 2+ PIC現実的(13dB, L=0.27dB): ~3×10⁻³ / 理論限界(L=0.15dB): 9.9×10⁻⁴ | v3.1修正 |
| 表面符号閾値 p_th_eff | 1.5% | soft-info MWPM (Noh&Chamberland 2022); UF時≈0.8-1.2%. v2.1: 製品デコーダはMWPM |
| **論理エラー率 p_L (d=7, Phase 2+ PIC)** | **製品仕様: ~7×10⁻⁵ (L=0.27dB, QE≥99%, MWPM)** / L≤0.20dBで<10⁻⁵ / 理論限界: 5.7×10⁻⁷ | v3.4: non-loss noise込み統一計算。L=0.27dBでp_L=7×10⁻⁵(≲10⁻⁴)。L≤0.20dBで<10⁻⁵確実達成。理論限界(L=0.15dB, Δ=0) 5.7×10⁻⁷。UFは現実的条件で~5×10⁻⁴(超過)→MWPM必須 |

---

## DV-FBQC方式との比較

| 指標 | **CV Portable (Taros Pro)** | DV v5.0 Desktop | DV R6 Phase 1 |
|------|:---:|:---:|:---:|
| p_L (d=7, Phase 2+ PIC) | **~5.7×10⁻⁷ (MWPM)** | ~10⁻⁶ | ~10⁻⁴ |
| 重量 | **~7.5kg** | 28kg | 180kg |
| 消費電力 | **~109W** | 2.1kW | 8kW | [v3.2]
| 冷却 | **不要** | PT205 (8.6kg) | RDK-415E (75kg) |
| SNSPD | **0個** | 500個 | 3,000個 |
| QD | **0個** | 24個 | 80個 |
| コスト | **$120K** | $432K | ~$2M |
| スケーラビリティ | **逐次拡張(TDM)†** | 48 max | 42 max |

---

## 成功確率

| レベル | CV pure | CV+QD | DV v5.0 |
|--------|:-------:|:-----:|:-------:|
| A（スケーラブルQEC, soft-info） | **50%** | **65%** | 18% |
| A（スケーラブルQEC, 保守的） | 35% | 55% | 18% |
| B（エラー抑制） | **70%** | **80%** | 55% |
| C（コンポーネント実証） | **95%** | 95% | 80% |

### レッドチーム評価による補正（v1.3）

独立評価チーム（VC向けデューデリジェンス想定）による確率修正:
- Level A CV pure: 50% → **25-35%** (リスク複合: OPA 90% × GKP 75% × PLL 80% × Decoder不確定)
- Level B: 70% → **60-70%** (GKP F>0.80は高確率で達成)
- Level C: 95% → **90-95%** (部品調達リスク: NTT単一ソース)

**$39K Phase -1実験（G-EXP1）がLevel A確率を50%超に引き上げる最重要マイルストーン。**

### 主要リスク（レッドチーム指摘 + 物理監査、未解消）

1. **OPA 13dBパルス未実証**: NTT 12.1dB CW → +0.9dB gap。SiN clad改良依存
2. **Soft-info Union-Find**: 未発表アルゴリズム。MWPMフォールバックで対処可能（+160ns）
3. **Postselection実験データなし**: G-EXP1（2026年7月）で解消予定
4. **閾値マージン (v3.2修正)**: 現離散光学(σ_eff=5.0dB)では閾値未達。Phase 1(8.8dB, 13dB)でbreak-even境界、Phase 2+ PIC現実的(9.5-9.7dB, L=0.27dB)で製品グレード境界、理論限界(10.9dB, L=0.15dB)で十分マージン。ロードマップ実行が必須
5. **775nm TA小型化**: 2W DFB-LDは存在せず、DFB+TA構成。ポータブル実装は500mW TA butterfly package想定
6. **LO電力確保**: EO comb + ミニEDFA構成。EDFA ASEノイズは理論上無視可能だが要実験検証
7. **AWG挿入損失**: 0.2dB目標は市販品限界。AWG損失増はビームスプリッタモデルでσ_effをさらに低下させる
8. **有限エネルギーGKP**: 製品要件Δ<0.15 (postselection δ=0.19√πでΔ≈0.12-0.15)。Δ=0.15時p_L≈6.8×10⁻⁶ (03_numerical-verification §2.5) → d=9で回復可能。δ=0.15√π厳格窓でΔ<0.10確保も可能(P_mode 84%に低下)
9. **p_th_eff=1.5%の厳密性**: Noh-Chamberland 2022からの近似読み取り値。独立Stim検証が必要
10. **Native Tゲート品質**: Phase 2+ PIC σ_eff=10.9dBでのT gate infidelity未定量。蒸留不要の条件要検証
11. **多qubitゲートレート**: 146Hz(d=7)は単一層レート。CNOT等はd倍≈7 QECサイクル要、実効~21Hz

---

## ロードマップ

```
2026 Q2-Q4: Phase -1 (CV固有: $39K GKP実験 + $280K基盤 = $319K)
    │
    ├── G-EXP1 (7月): CW GKP F>0.80, p_acc>85%, Δ<0.15 [Option B, AWGなし, σ_eff=8.8dB]
    └── G-EXP2 (8月): パルスGKP P_round>10⁻³ (strict mode)
         │
2027 Q1-Q2: Phase 0a — Taros Edu プロトタイプ (d=3, WDM 5ch, ~10kHz)
2027 Q3-Q4: Phase 0b — Taros Pro プロトタイプ (d=5, WDM 8ch, ~3kHz)
2028:       Phase 1  — Taros Max プロトタイプ (d=7, WDM 7ch, ~1kHz)
2029:       Phase 2  — 量産設計 (100台/年)
2030+:      Phase 3  — WDM 20ch フルスペック (60kHz Tゲート)
```

**注**: 単一チャネルでのゲートレートはEdu~1.9kHz, Pro~400Hz, Max~146Hz。
製品スペック達成にはWDM 5-8chの並列化が必要（Phase 0から標準搭載）。

---

## 原理的優位性

1. **重力デコヒーレンス免疫**（理論的注記）: 光子は質量ゼロであるため、Diósi-Penrose / Oppenheim型の重力デコヒーレンスモデルの影響を原理的に受けない。ただし、競合方式（超伝導等）においても重力デコヒーレンスは技術的ノイズ源に対し19桁以上小さく（τ_DP ≈ 10¹⁵ s vs T₁ ≈ 10⁻⁴ s）、現在および予見可能な将来において実用上の差は生じない。本項目は基礎物理学的な原理的区別であり、現時点での性能差を意味するものではない。
2. **TDM逐次スケーリング**: 同一ハードウェアで1~1,000+ 論理qubit相当の回路実行（逐次処理†）
3. **消費電力一定**: qubit数に無関係に100-112W
4. **完全室温**: 冷凍機なし → メンテナンスフリー、即時起動

---

## 設計書ナビゲーション

| 優先度 | ドキュメント | 内容 |
|--------|-----------|------|
| **必読** | `design/01-13` | CV方式全設計（OPA, TDM, GKP, 位相ロック, ノイズ, ラック, FF, Portable, 実験, デコーダ） |
| 重要 | `design/01_system-architecture.md` | ハイブリッドCV+QD設計（QD追加版） |
| 参考 | `design/13_performance.md` | CV性能モデル v2.4 |
| 参考 | `analysis/bom.md` | 4構成コスト比較 |
| フォールバック | `../fallback/` | DV-FBQC方式（代替） |
| レガシー | `../archive/` | DV-FBQC v4.0 R6基盤設計 |

---

†**TDM逐次スケーリングに関する注記**: TDM方式では論理qubitは時分割で逐次処理される（並列ではない）。
1000論理qubit回路(10⁶ T-gates)の実行時間: 全モード: 10⁶ × 7.42μs / 7ch ≈ **1.06秒**。Strict postselection: 10⁶ / (146Hz × 7ch) ≈ **16分**。並列動作が必要な場合はWDM拡張(Phase 3+)で対応。
「1000 logical qubits」は同時独立qubit数ではなく、サポート可能な回路幅を意味する。

⁑ **TDM逐次処理に関する重要注記**: 「1,000+ 論理qubit」は同時に独立動作するqubit数ではない。TDM方式は同一ハードウェア上で最大1,000+の論理qubitを含む量子回路を**逐次的に**実行できる（回路幅のサポート能力）。d=7で10⁶ Tゲートの1,000 qubit回路の実行時間は全モード~1秒 / strict~16分（WDM 7ch時）。並列独立qubitが必要なアプリケーションでは、WDMチャネル数が同時qubit数の上限となる。

*本文書はCV方式Taros Portableの完全なExecutive Summaryであり、新規参入者が最初に読むべきドキュメントである。*
