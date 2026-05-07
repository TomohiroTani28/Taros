# CV方式 Executive Summary — Taros Portable

**Document ID**: PQC-CV-EXEC-v2.0
**Status**: 確定版
**検証**: Stim ~100M shots + 数値計算 + 文献9件で独立検証済み → `experiments/02_virtual-experiments.md`

---

## ビジョン

> **「ACアダプタで動くデスクトップサイズの誤り訂正型光量子コンピュータ」**

---

## 正規パラメータ (Single Source of Truth)

全設計文書はこのテーブルの値を正とする。変更時はここを更新し、関連文書に伝播させること。

| パラメータ | 記号 | 正規値 | 条件 | 根拠文書 |
|-----------|------|--------|------|----------|
| 生成スクイージング | σ_gen | 13dB | CW PPLN OPA (NTT) | 02_opa-source |
| 全劣化 (GAWBS込み) | L_total | 1.42dB (離散光学) / 0.39dB (Phase 1 離散光学) / 0.15dB (Phase 2+ PIC) | ビームスプリッタモデル: η=10^(-L/10) | 06_noise-budget |
| 実効スクイージング | σ_eff | **5.0dB** (現離散光学) / 8.5dB (Phase 1, 13dB) / **≈9.3dB** (Phase 2+ PIC 現実的, L=0.27dB, non-loss込み) / 10.8dB (理論限界, L=0.15dB) | Phase 1を8.5dBに、Phase 2+ PIC現実的を9.3dBに修正。理論限界10.8dB。 | 06_noise-budget |
| 物理エラー率 | p_phys | 現離散(5.0dB): 閾値未達 / Phase 1(13dB, 8.5dB): 9.3×10⁻³ / Phase 2+ PIC現実的(13dB, L=0.27dB): ~4.9×10⁻³ | erfc再計算。Phase 1: σ=0.266→erfc(1.664)/2≈9.3×10⁻³ | 13_performance |
| 閾値 (soft-info) | p_th_eff | 1.5% | soft-info MWPM (Noh-Chamberland 2022); UF時≈0.8-1.2%. 製品デコーダはMWPM (現実的L=0.27dBでUF~4×10⁻³>10⁻³) | 08_decoder |
| 閾値 (保守) | p_th | 0.59% | hard-syndrome MWPM | 文献値 |
| 論理エラー率 d=7 (Δ=0理想) | p_L | **6.1×10⁻⁷ (MWPM, Phase 2+ PIC)** [理論上限値] | 製品目標p_L≲10⁻³(L=0.27dB)。現実的PIC(L=0.27dB, QE≥99%)でMWPM~3.3×10⁻⁴。L≤0.22dBで≲10⁻⁴。UF~4×10⁻³(超過)→MWPM必須 | 13_performance |
| 論理エラー率 d=7 (現実Δ=0.12) | p_L | **~3.3×10⁻⁴ (MWPM, L=0.27dB)** [対外基準値] | 13_performance §3.2 性能予測表「現実」行 | 13_performance |
| QD等価スクイージング | — | +2.7dB (QD=2) | σ_eff等価13.5dB (10.8+2.7, 旧14.2dBは11.5dB基準) | 01_system-arch |
| TDMクロック | f_TDM | 100MHz | Option B パルスOPA | 03_tdm-cluster |
| macronode列数 | N_col | 2d² (18/50/98) | d=3/5/7 | 03_tdm-cluster |
| フィードフォワード | t_FF | **27ns** (設計ベースライン400MHz) / 22ns (楽観500MHz) | TIA 3 + ADC 3 + FPGA 12.5 + DAC 5 + EOM 3 = 26.5≈27ns | 07_feedforward |
| デコーダ遅延 | t_dec | **510ns (MWPM製品) / 350ns (UF実験)** (400MHz) | MWPM: Blossom-V, 製品デコーダ; UF: Phase 0-1実験用 | 08_decoder |
| GKP忠実度 | F_GKP | Phase依存 | σ_eff=5.0dB(現行)では低忠実度; Phase 2+ PIC σ_eff=10.8dBで高忠実度 | 04_gkp-protocol |
| 閾値マージン | — | 現離散光学→閾値未達; Phase 1→+1.0dB(PS); **Phase 2+ PIC現実的(L=0.27dB)→+1.8dB(PS)**; Phase 2+ PIC理論限界→+3.3dB(PS)/+0.8dB(全モード) | vs 7.5dB(PS) / 10.0dB(全モード) | 06_noise-budget |
| 反スクイージング | — | **~13dB** (単一パスOPA: sq≈anti-sq) | 旧20dBは共振器OPO誤引用 | 02_opa-source |
| PLL残留位相 | φ_res | <0.05° (BW≥500kHz) | 位相ノイズ**<0.002dB** (anti-sq 13dBで事実上無視可能) | 05_phase-lock |
| 有限エネルギーGKP | Δ | <0.15 (必須要件) | Δ≥0.2でFAIL | 04_gkp-protocol |
| ポンプ源 | — | Option B: 1550nm GS-DFB + SOA/TA + PPLN SHG → 775nm パルス | Portable: SOA 1.6W→SHG 400mW→1×2→200mW/OPA; Rack: TA 6.4W→SHG 1.6W→1×8→200mW/OPA | 02_opa-source |
| LO生成 | — | 100mW Master + EO comb + EDFA → 10mW/ch | — | 05_phase-lock |
| 電源 | — | USB-PD EPR 140W (28V/5A) 推奨 | Pro 109W / Max 112W で100W不可。Edu(104W)は100W超 (OPA×2で100→104W) | 10_portable |

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
|---|---|---|---|
| 表面符号距離 | d=3 | d=5 | d=7 |
| 論理エラー率 (MWPM, Phase 2+ PIC現実的) | — | — | **~3.3×10⁻⁴** (σ_eff=9.3dB, L=0.27dB, MWPM d=7) |
| 論理qubit数 | 1-10 | 10-100 | **10-1,000+**⁑ |
| Tゲートレート (WDM並列込み, strict) | 10kHz (5ch) | 3kHz (8ch) | ~840Hz (7ch)† |
| Tゲートレート (単一ch, strict) | ~1.9kHz | ~400Hz | ~120Hz |
| 筐体 | 25×20×10cm | 30×25×16cm | 40×30×20cm |
| 重量 (WDM込み) | **~4.3kg** | **~7.5kg** | **~9.7kg** |
| 消費電力 (WDM込み) | **~104W** | **~109W** | **~112W** |
| 冷却 | 低速ファン+底面HS | 低速ファン+背面HP | 低速ファン×2 |
| 原価 (WDM込み) | 約840万円 | 約1,125万円 | 約1,425万円 |
| 販売価格 | **約1,350万円** | **約1,800万円** | **約2,550万円** |
| 用途 | 教育・QEC研究 | 研究・VQE | **FTQC・量子化学 (Phase 2+ PIC)** |

†Max WDM 7ch: d=7ではQECサイクルが長い(6.86μs)ため、7chでターゲット論理ゲートレート~840Hzを達成。8ch化は消費電力増(+1W)に対し性能改善が限定的。
**Tゲートレート モード区分**: 上表の値はstrict postselection(全QECラウンド高信頼)モード。P_round=0.93^98≈8×10⁻⁴, 146kHz×8×10⁻⁴≈117Hz→概算~120Hz。
全モード(postselectionなし)では最小間隔=7.42μs(d=7, デコーダ遅延560ns込み)→単一ch ~135kHz, 7ch ~945kHz。
Edu OPA×2必須(macronode要件)で100→104W。
Strictモードは最高品質だが低レートとなる。用途に応じてモード選択可能。

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
    │ Flash ADC 6bit 1.5GSPS + Pipeline 14bit 400MSPS (dual-path)
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
| 全経路劣化 (AWG+EO消光比込み) | 1.42dB (離散光学) / 0.39dB (Phase 1) / **0.27dB (Phase 2+ PIC現実的)** / 0.15dB (Phase 2+ PIC理論限界) | CVノイズバジェット |
| **実効スクイージング σ_eff** | **5.0dB (現離散光学) / 8.5dB (Phase 1, 13dB) / 10.8dB (Phase 2+ PIC理論限界)** | Phase 1を8.5dB、理論限界を10.8dBに統一。現実的(L=0.27dB)は9.3dB |
| GKP+表面符号閾値 (postselection) | 7.5dB | Stafford-Menicucci-Walshe 2025 (P_round=10⁻³, strict mode時) |
| GKP+表面符号閾値 (全モード重み付け) | ~10dB | Noh-Chamberland 2022 unconditional相当 |
| **閾値マージン (Phase 2+ PIC現実的, postsel)** | **+1.8dB** | 9.3 - 7.5 |
| **閾値マージン (Phase 2+ PIC理論限界, postsel)** | **+3.3dB** | 10.8 - 7.5 |
| **閾値マージン (Phase 2+ PIC理論限界, 全モード)** | **+0.8dB** | 10.8 - 10.0 |
| **閾値マージン (Phase 1, postsel)** | **+1.0dB** | 8.5 - 7.5 (break-even境界、8.8→8.5dB修正) |
| **閾値マージン (現離散光学, Option A+AWG)** | **閾値未達** | 5.0dB < 7.5dB。**注: Phase -1実験はOption B(AWGなし, L=0.39dB, σ_eff=8.5dB)で実施。閾値超過+1.0dB** |
| 物理エラー率 p_err | Phase 1(13dB): 9.3×10⁻³ / Phase 2+ PIC現実的(13dB, L=0.27dB): ~4.9×10⁻³ / 理論限界(L=0.15dB): ≈1.0×10⁻³ | erfc再計算+V_non-loss修正 |
| 表面符号閾値 p_th_eff | 1.5% | soft-info MWPM (Noh&Chamberland 2022); UF時≈0.8-1.2%. 製品デコーダはMWPM |
| **論理エラー率 p_L (d=7, Phase 2+ PIC)** | **製品仕様: ~3.3×10⁻⁴ (L=0.27dB, QE≥99%, MWPM)** / L≤0.22dBで≲10⁻⁴ / 理論限界: 6.1×10⁻⁷ | non-loss noise込み統一計算。L=0.27dBでp_L=3.3×10⁻⁴(≲10⁻³)。L≤0.22dBで≲10⁻⁴達成。理論限界(L=0.15dB, Δ=0) 6.1×10⁻⁷。UFは現実的条件で~4×10⁻³(超過)→MWPM必須 |

---

## DV-FBQC方式との比較

| 指標 | **CV Portable (Taros Pro)** | DV v5.0 Desktop | DV R6 Phase 1 |
|------|---|---|---|
| p_L (d=7, Phase 2+ PIC現実的) | **~3.3×10⁻⁴ (MWPM)** | ~10⁻⁶ | ~10⁻⁴ |
| 重量 | **~7.5kg** | 28kg | 180kg |
| 消費電力 | **~109W** | 2.1kW | 8kW |
| 冷却 | **不要** | PT205 (8.6kg) | RDK-415E (75kg) |
| SNSPD | **0個** | ~1,000個 | 3,000個 |
| QD | **0個** | 24個 | 80個 |
| コスト | **約1,800万円** | 約6,480万円 | ~約3億円 |
| スケーラビリティ | **逐次拡張(TDM)†** | 48 max | 42 max |

---

## 成功確率

| レベル | CV pure | CV+QD | DV v5.0 |
|--------|---------|-------|---------|
| A（スケーラブルQEC, soft-info） | **50%** | **65%** | 18% |
| A（スケーラブルQEC, 保守的） | 35% | 55% | 18% |
| B（エラー抑制） | **70%** | **80%** | 55% |
| C（コンポーネント実証） | **95%** | 95% | 80% |

### レッドチーム評価による補正

独立評価チーム（VC向けデューデリジェンス想定）による確率修正:
- Level A CV pure: 50% → **25-35%** (リスク複合: OPA 90% × GKP 75% × PLL 80% × Decoder不確定)
- Level B: 70% → **60-70%** (GKP F>0.80は高確率で達成)
- Level C: 95% → **90-95%** (部品調達リスク: NTT単一ソース)

**約560万円（装置BOM）Phase -1実験（G-EXP1、タスク費約4,760万円の一部。人件費込み完全コスト約2,900万円）がLevel A確率を50%超に引き上げる最重要マイルストーン。**

### 主要リスク（レッドチーム指摘 + 物理監査、未解消）

1. **OPA 13dBパルス未実証**: NTT 12.1dB CW → +0.9dB gap。SiN clad改良依存
2. **Soft-info Union-Find**: 未発表アルゴリズム。MWPMフォールバックで対処可能（+160ns）
3. **Postselection実験データなし**: G-EXP1（Phase -1 開始後約2ヶ月）で解消予定
4. **閾値マージン**: 現離散光学(σ_eff=5.0dB)では閾値未達。
   Phase 1(8.5dB, 13dB)でbreak-even境界、Phase 2+ PIC現実的(≈9.3dB, L=0.27dB)で製品グレード境界、
   理論限界(10.8dB, L=0.15dB)で十分マージン。ロードマップ実行が必須
5. **ポンプ光源 (Option B)**: Portable: 1550nm GS-DFB+SOA(1.6W peak)+SHG。Rack: GS-DFB+TA(6.4W peak)+SHG。TA小型化はRack版のみ課題
6. **LO電力確保**: EO comb + ミニEDFA構成。EDFA ASEノイズは理論上無視可能だが要実験検証
7. **AWG挿入損失**: 0.2dB目標は市販品限界。AWG損失増はビームスプリッタモデルでσ_effをさらに低下させる
8. **有限エネルギーGKP**: 製品要件Δ<0.15 (postselection δ=0.19√πでΔ≈0.12-0.15)。
   Δ=0.15時p_L≈6.8×10⁻⁶ (experiments/03_numerical-verification §2.5) → d=9で回復可能。
   δ=0.15√π厳格窓でΔ<0.10確保も可能(P_mode 84%に低下)
9. **p_th_eff=1.5%の厳密性**: Noh-Chamberland 2022からの近似読み取り値。独立Stim検証が必要
10. **Native Tゲート品質**: Phase 2+ PIC σ_eff=10.8dBでのT gate infidelity未定量。蒸留不要の条件要検証
11. **多qubitゲートレート**: 146Hz(d=7)は単一層レート。CNOT等はd倍≈7 QECサイクル要、実効~21Hz

---

## ロードマップ

```
Phase -1 (開始後0-12ヶ月): タスク費合計約1.7億円 (新規約9,190万円+既存約8,250万円)。人件費込み総額: 約4.6億円
    │  うちCV固有: GKP実験約560万円 + 基盤約4,200万円 = 約4,760万円
    │
    ├── G-EXP1 (開始後約2ヶ月): CW GKP F>0.80, p_acc>85%, Δ<0.15
    │       [Option B, AWGなし, σ_eff=8.5dB]
    └── G-EXP2 (開始後約3ヶ月): パルスGKP P_round>10⁻³ (strict mode)
         │
Phase 0a (開始後約9-12ヶ月): Taros Edu プロトタイプ (d=3, WDM 5ch, ~10kHz)
Phase 0b (開始後約15-18ヶ月): Taros Pro プロトタイプ (d=5, WDM 8ch, ~3kHz)
Phase 1  (開始後約2年): Taros Max プロトタイプ (d=7, WDM 7ch, ~1kHz)
Phase 2  (開始後約3年): 量産設計 (100台/年)
Phase 3  (開始後約4年以降): WDM 20ch フルスペック (60kHz Tゲート)
```

**注**: 単一チャネルでのゲートレート(strict)はEdu~1.9kHz, Pro~400Hz, Max~120Hz。
製品スペック達成にはWDM 5-8chの並列化が必要（Phase 0から標準搭載）。

---

## 原理的優位性

1. **重力デコヒーレンス免疫**（理論的注記）: 光子は質量ゼロであるため、
   Diósi-Penrose / Oppenheim型の重力デコヒーレンスモデルの影響を原理的に受けない。
   ただし、競合方式（超伝導等）においても重力デコヒーレンスは技術的ノイズ源に対し
   19桁以上小さく（τ_DP ≈ 10¹⁵ s vs T₁ ≈ 10⁻⁴ s）、現在および予見可能な将来において
   実用上の差は生じない。本項目は基礎物理学的な原理的区別であり、
   現時点での性能差を意味するものではない。
2. **TDM逐次スケーリング**: 同一ハードウェアで1~1,000+ 論理qubit相当の回路実行（逐次処理†）
3. **消費電力一定**: qubit数に無関係に100-112W
4. **完全室温**: 冷凍機なし → メンテナンスフリー、即時起動

---

## 設計書ナビゲーション

| 優先度 | ドキュメント | 内容 |
|--------|-----------|------|
| **必読** | `design/01-13` | CV方式全設計（OPA, TDM, GKP, 位相ロック, ノイズ, ラック, FF, Portable, 実験, デコーダ） |
| 重要 | `design/01_system-architecture.md` | ハイブリッドCV+QD設計（QD追加版） |
| 参考 | `design/13_performance.md` | CV性能モデル |
| 参考 | `analysis/bom.md` | 4構成コスト比較 |
| フォールバック | `../fallback/` | DV-FBQC方式（代替） |
| レガシー | `../archive/` | DV-FBQC v4.0 R6基盤設計 |

---

†**TDM逐次スケーリングに関する注記**: TDM方式では論理qubitは時分割で逐次処理される（並列ではない）。
1000論理qubit回路(10⁶ T-gates)の実行時間:
全モード: 10⁶ × 7.42μs / 7ch ≈ **1.06秒**。
Strict postselection: 10⁶ / (120Hz × 7ch) ≈ **20分**。
並列動作が必要な場合はWDM拡張(Phase 3+)で対応。
「1000 logical qubits」は同時独立qubit数ではなく、サポート可能な回路幅を意味する。

⁑ **TDM逐次処理に関する重要注記**: 「1,000+ 論理qubit」は同時に独立動作するqubit数ではない。
TDM方式は同一ハードウェア上で最大1,000+の論理qubitを含む量子回路を**逐次的に**実行できる（回路幅のサポート能力）。
d=7で10⁶ Tゲートの1,000 qubit回路の実行時間は全モード~1秒 / strict~20分（WDM 7ch時）。
並列独立qubitが必要なアプリケーションでは、WDMチャネル数が同時qubit数の上限となる。

*本文書はCV方式Taros Portableの完全なExecutive Summaryであり、新規参入者が最初に読むべきドキュメントである。*
