# Theme 1: 室温 Fault-Tolerant Photonic Architecture

## 研究目標

**室温動作のみで fault-tolerant photonic quantum computing が成立することを、シミュレーションと理論解析で証明する。**

---

## 証明すべき3命題

| # | 命題 | 現状 | 必要な追加証拠 |
|---|------|------|---------------|
| P1 | 室温でも logical qubit が成立する | σ_eff=9.3dB, p_L~3.3×10⁻⁴ (d=7, MWPM) 計算済み | GKP生成→QEC→論理演算の end-to-end シミュレーション |
| P2 | Scalable architecture が存在する | TDM macronode設計済み、WDM 5-8ch | スケーリング則の数値的検証 (d=3→5→7→9) |
| P3 | Cryogenic infrastructure 不要 | ホモダイン検出(室温InGaAs)、SNSPD/QD=0 | 室温ノイズ源の網羅的影響評価 |

---

## 4人チーム役割分担案

| 役割 | 担当領域 | 主要成果物 |
|------|---------|-----------|
| **A: アーキテクト** | 全体構成・スケーリング理論・論文構成 | アーキテクチャ証明フレームワーク |
| **B: QECシミュレータ** | Stim/PyMatching によるQECシミュレーション | 閾値・論理エラー率データ |
| **C: 光学モデラー** | OPA・TDM・損失伝搬の物理シミュレーション | ノイズモデル・損失解析 |
| **D: デコーダ研究者** | デコーダ性能・soft-info・QLDPC探索 | デコーダ比較データ |

---

## 議論アジェンダ

### 第1部: 現状の強みと既存成果の確認 (30min)

TAROSが既に持っている証拠:

1. **882万ショット QECシミュレーション** (RESEARCH_REPORT.md)
   - soft-info MWPM: d=3で7.6倍、d=5で26倍以上の改善
   - MWPMのスケール不変性・最適性の壁を発見（新規性あり）
   - BPは表面符号 girth-4 で劣化（壁3）

2. **設計パラメータの内部整合性** (Phase 6検証済み)
   - σ_eff = 9.3dB (L=0.27dB, Phase 2+ PIC)
   - p_L = 3.3×10⁻⁴ (d=7, MWPM) — 独立Stim検証で一致

3. **完全室温動作仕様** (00_overview.md)
   - 109W, 7.5kg, ホモダイン検出、冷凍機/SNSPD/QD不要

**議論ポイント**: これらは「証明」として十分か？ 何が不足しているか？

### 第2部: 証明の Gap Analysis (45min)

#### Gap 1: GKP状態生成の実現性

| 項目 | 現状 | 必要な証拠 |
|------|------|-----------|
| σ_gen ≥ 12.5dB | NTT CW 12.1dB実証、+0.9dBギャップ | 理論的到達可能性の議論 |
| Δ < 0.15 (有限エネルギーGKP) | 超伝導系でΔ≈0.12達成 | 光学系での生成プロトコルシミュレーション |
| p_acc > 85% | 設計値93% | postselection条件の感度分析 |

**議論**: OPA 13dBの+0.9dBギャップは致命的か？ 12.5dBで十分な理由を定量化できるか？

#### Gap 2: Macronode TDM の fault-tolerance

| 項目 | 現状 | 必要な証拠 |
|------|------|-----------|
| TDM構造でのQEC閾値 | Menicucci理論に基づく設計 | macronode構造を明示的にモデル化したStimシミュレーション |
| フィードフォワード遅延の影響 | 27ns (3モード遅延) 理論的に許容 | 遅延誤差の論理エラー率への感度 |
| WDMチャネル間独立性 | 共通ポンプRIN < -150dB/Hz で ρ < 0.03 | 相関ノイズ下でのQEC性能 |

**議論**: 標準的な表面符号シミュレーション (code capacity) と macronode TDM の差はどこまで大きいか？

#### Gap 3: デコーダの実用性

| 項目 | 現状 | 必要な証拠 |
|------|------|-----------|
| MWPM 510ns | Blossom-V, FPGA実装想定 | 実時間制約下での性能保証 |
| soft-info閾値 1.5% | Noh 2022からの読み取り | 独立検証（特にmacronode構造で） |
| UF p_th 0.8-1.2% | 文献値 | soft-info UF の具体的実装と閾値 |

**議論**: MWPM必須 vs UF で十分な条件の境界はどこか？

#### Gap 4: スケーリング

| 項目 | 現状 | 必要な証拠 |
|------|------|-----------|
| d=3→5→7 スケーリング | p_L指数減少の理論予測 | 数値的確認（特に realistic noise model で） |
| 1000論理qubit回路 | TDM逐次で~1秒(全モード) | 大規模回路のコンパイル・実行シミュレーション |
| Phase 2+ PIC統合 | L=0.27dB目標 | PIC損失モデルの精密化 |

### 第3部: 研究計画策定 (45min)

#### Simulation Track A: End-to-End QEC (担当: B+D)

```
目標: macronode TDM構造でのGKP表面符号 end-to-end シミュレーション

ツール: Stim + PyMatching (既存) + カスタムGKPノイズモデル
計算資源: CPU (API不要)

実験計画:
  Exp-A1: Macronode noise model構築
    - 4モードmacronode (input_A/B fixed X, output_A/B adaptive θ)
    - ビームスプリッタモデル V_eff = η×V_sqz + (1-η) + V_non_loss
    - フィードフォワード遅延ノイズの組み込み

  Exp-A2: 符号距離スケーリング (d=3,5,7,9)
    - σ_eff = 8.5, 9.3, 10.8 dB の3条件
    - soft-info MWPM vs hard-syndrome MWPM
    - 各条件 10⁶ ショット以上

  Exp-A3: 閾値の精密決定
    - p_th(soft-info MWPM, macronode TDM) の独立決定
    - phenomenological noise model への拡張
    - circuit-level noise model (Phase 2目標)

  Exp-A4: 相関ノイズ耐性
    - 共通ポンプRIN相関 (ρ=0.01, 0.03, 0.05, 0.10)
    - WDMクロストーク相関
    - p_L劣化の定量化
```

#### Simulation Track B: 損失伝搬解析 (担当: C)

```
目標: 室温光学系の損失が論理エラー率に与える影響の完全マッピング

ツール: Python (NumPy/SciPy), Strawberry Fields (オプション)
計算資源: CPU

実験計画:
  Exp-B1: 損失バジェット感度分析
    - 各コンポーネント損失の ±20% 変動に対する p_L 応答
    - 支配的損失源の特定と改善優先度

  Exp-B2: 室温ノイズ源の網羅的評価
    - 熱揺らぎ (ΔT = ±0.5K, ±1K, ±2K)
    - 位相ドリフト (PLL残留位相 0.01°-0.10°)
    - ADC量子化ノイズ (6bit, 8bit, 10bit)
    - ホモダインコモンモード除去比 (CMRR 30-50dB)

  Exp-B3: OPAスクイージング要求の精密化
    - σ_gen = 11, 12, 12.5, 13, 14 dB での p_L(d=3,5,7)
    - Go/No-Go境界の2次元マップ (σ_gen × L_total)
```

#### Simulation Track C: アーキテクチャ証明 (担当: A)

```
目標: 室温FT photonic QCの原理的成立性の理論的証明

実験計画:
  Exp-C1: Cryogenic不要の論証
    - CV方式が室温で動作する物理的根拠の体系化
    - ホモダイン vs SNSPD: 情報理論的等価性
    - 熱ノイズの影響: 1550nm光子エネルギー >> kT (室温で S/N十分)

  Exp-C2: スケーラビリティ証明
    - TDM macronode のリソースオーバーヘッド分析
    - 論理qubit数 vs 物理リソース (OPA数, 遅延線長, WDMチャネル数)
    - 既存方式 (superconducting, trapped ion, DV photonic) との比較表

  Exp-C3: Fault-tolerance閾値定理の適用可能性
    - Knill-Laflamme-Zurek閾値定理のCV macronode版
    - noise locality条件の検証
    - transversal gate set の構成可能性
```

#### Simulation Track D: 次世代デコーダ探索 (担当: D)

```
目標: MWPMの壁(RESEARCH_REPORT.md)を超えるデコーダの発見

ツール: Python, Stim, (オプション: TensorFlow/PyTorch)
計算資源: CPU (NN使用時はGPU推奨)

実験計画:
  Exp-D1: QLDPC + BP デコーダ
    - girth ≥ 6 の符号でBPがMWPMを超えるか検証
    - GKP連続値LLR初期化の効果測定
    - 表面符号との p_L 比較

  Exp-D2: 機械学習デコーダ (FiLM型)
    - GKP連続値を特徴量とするNN decoder
    - 訓練データ: Stimで生成 (10⁷ ショット)
    - 推論レイテンシ vs 精度のトレードオフ

  Exp-D3: RL sensor code (Acharya型拡張)
    - RLがMWPM重みを直接最適化
    - スケール不変性の迂回確認
    - GKP連続値のRL reward設計
```

---

## 議論で決めるべきこと

### 優先度決定

以下を4人で合議:

1. **最初に着手すべきTrackはどれか？**
   - 提案: Track A (Exp-A2) — 符号距離スケーリングの数値的確認が最も基礎的

2. **論文化のターゲット**
   - Option 1: arXiv preprint (速度重視) — 4-6週間
   - Option 2: PRL/PRX Quantum (インパクト重視) — 3-6ヶ月
   - Option 3: Conference paper (NeurIPS QML, QIP) — 締切依存

3. **計算リソースの配分**
   - CPU のみで開始 → Track D のNN decoder のみGPU必要
   - 初期は全員CPUで並列実行

4. **RESEARCH_REPORT.md の成果をどう組み込むか？**
   - MWPMの壁の発見は本研究の前提知識として位置づけ
   - 882万ショットのデータは再利用可能

### 成功基準

| レベル | 基準 | 達成時のインパクト |
|--------|------|-------------------|
| **必須** | macronode TDM構造で p_L < 10⁻³ (d=7) を数値的に確認 | TAROS設計の独立検証 |
| **目標** | 室温ノイズ込みで閾値マージン > 1dB を証明 | 投資家・学術コミュニティへの説得力 |
| **理想** | MWPMの壁を超えるデコーダで p_L < 10⁻⁴ | 競争優位性の確立 |

---

## 既存資産

```
利用可能なコード・データ:
  research/ploa_proof.py          — Stim+PyMatching QEC基盤 (即利用可)
  research/ploa_adaptive.py       — 適応ドリフト追跡
  research/ploa_bp.py             — BP decoder実装
  research/results/*.json         — 882万ショット生データ
  experiments/02_virtual/          — 仮想実験データ

利用可能な設計パラメータ:
  design/_parameters.md           — 全パラメータ SSOT
  design/06_noise-budget.md       — ノイズバジェット詳細
  design/08_decoder.md            — デコーダ設計
  design/13_performance.md        — 性能モデル v3.6
```

---

## 参考文献 (議論で参照すべきもの)

1. Noh & Chamberland (2022) — GKP analog info + MWPM
2. Stafford, Menicucci & Walshe (2025) — macronode TDM fault-tolerance threshold
3. Borah et al. (2025) — GKP + BP (QLDPC)
4. FiLM decoder (2026) — calibration-conditioned NN decoding
5. Walshe et al. (2020) — CV cluster state feedforward model
6. Bourassa et al. (2021) — Xanadu blueprint for FTQC
7. Larsen et al. (2021) — 2D cluster state generation (temporal)
8. Fukui et al. (2018) — GKP + surface code threshold

---

## Next Steps

1. 本ドキュメントを全員で読み、コメント追加
2. 役割分担の最終確定
3. 各Track の Exp-*1 を1週間以内に開始
4. 週次進捗共有 (30min)
