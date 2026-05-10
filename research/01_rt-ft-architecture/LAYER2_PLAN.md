# 層2研究計画: 真にS+新規性のある研究方向

**日付**: 2026-05-09
**前提**: 層1（設計検証）完了。x.mdの批評により一般的主張の新規性は否定された。
**目標**: 先行研究が未踏の領域で、TAROS固有の学術的貢献を確立する。

---

## 新規性の源泉: RESEARCH_REPORT.mdで発見した空白

```
                  離散シンドローム          連続シンドローム(GKP)
静的ノイズ        AlphaQubit(2024)          Noh(2022) ← 確立済み
                  Mamba(2025)

時変ノイズ適応    FiLM(2026) 7.4×           ← 未開拓 ★★★
                  RL制御(2025) 3.5×

反復的推定+復号   Nayak(2026)               ← 未開拓 ★★★
```

さらに、RESEARCH_REPORT.mdで発見した3つの構造的壁:
1. MWPMのスケール不変性 → ノイズ再校正が原理的に無効
2. MWPMの厳密最適性 → 反復改善が不可能
3. 表面符号のgirth-4 → BPが劣化

**これらの壁を破るデコーダ × GKP連続値の組み合わせが、世界初の研究になる。**

---

## 研究候補の優先順位

| # | 研究方向 | 新規性 | 実現可能性 | TAROS直結 | 総合 |
|---|---------|--------|-----------|----------|------|
| **R1** | GKP連続値 × FiLM型適応デコーダ | **S+** | 高 (CPU/API) | 高 | **最優先** |
| **R2** | GKP連続値 × EM反復デコード | **S+** | 高 (CPU) | 高 | **次点** |
| R3 | QLDPC + GKP on macronode | S+ | 中 (理論+sim) | 中 | 3番手 |
| R4 | MWPMスケール不変性の一般理論 | S | 高 (理論) | 低 | 理論寄り |

---

## R1: GKP連続値 × FiLM型適応デコーダ（最優先）

### なぜ新規か

**FiLM decoder (Bausch+ 2026)**: calibration dataで条件付けしたNNが、ノイズ変動時に7.4×改善。
ただし**離散シンドローム**（0/1ビット）のみを入力とする。

**GKP homodyne**は14bitの連続値を出力する。この連続値をFiLM型デコーダの入力に使えば:
- 入力空間が離散(2^n)から連続(R^n)に拡大 → 情報量が桁違い
- 各モードの信頼度がリアルタイムで既知 → 適応が格段に容易
- MWPMのスケール不変性を破れる（NNは絶対値に感度がある）

**先行研究の空白**:
- FiLM (2026): 離散シンドロームのみ → GKP未対応
- Noh (2022): GKP soft-infoをMWPM重みに変換 → 適応性なし
- AlphaQubit (2024): リカレントTransformer → GKP未適用
- **GKP連続値 × 適応型NNデコーダ = 未踏 ★★★**

### 具体的研究計画

```
Phase 1: ベースライン構築 (1-2週間)
  - 層1のExp-A2c結果をベースライン（MWPM soft-info）として確立
  - GKP表面符号のシンドロームデータ生成パイプライン構築
  - 入力形式: (d²+d²-1) × rounds の連続値テンソル
  - ラベル: 論理エラーの有無 (binary)

Phase 2: FiLM-GKP デコーダ設計 (2-3週間)
  - アーキテクチャ:
    入力: GKP残差テンソル r ∈ R^{n_detectors × rounds}
    条件付け: ノイズパラメータ V_eff (FiLMレイヤーで注入)
    本体: 3-5層 ResNet + FiLM conditioning
    出力: P(logical_error) ∈ [0,1]
  - 訓練データ: Stim + カスタムGKPノイズで生成
    - 静的ノイズ: V_eff = 0.08-0.20 (σ_eff = 7-11dB)
    - 時変ノイズ: V_eff(t) にドリフト・スパイク注入
    - 10⁶-10⁷ ショット/条件
  - 損失関数: Binary cross-entropy

Phase 3: 静的ノイズでの性能検証 (1-2週間)
  - FiLM-GKP vs MWPM soft-info 比較
  - 距離スケーリング d=3,5,7
  - 期待結果: 静的ノイズでは MWPM soft-info と同等か微改善

Phase 4: 時変ノイズでの適応性検証 (2-3週間) ← 核心実験
  - ノイズドリフトシナリオ:
    (a) 緩やかドリフト: V_eff(t) = V_0 + 0.01t (10分スケール)
    (b) 急峻スパイク: 1チャネルが+0.8dB (80ラウンド)
    (c) 周期変動: OPAポンプRINによるV_eff振動
  - FiLM-GKP: calibration windowで条件付け → 適応
  - MWPM: 固定重み or 再校正（スケール不変性により無効）
  - 期待結果: FiLM-GKPがドリフト時に有意に改善

Phase 5: 論文化 (2-3週間)
  - タイトル案: "Adaptive decoding of GKP surface codes with
    continuous-variable syndrome information"
  - 核心結果: 時変ノイズ下でMWPMの壁を破る初のデコーダ
```

### 必要リソース

```
計算: CPU (Phase 1-3), GPU推奨 (Phase 2-4のNN訓練)
  - CPU-only fallback: 小規模NN (d=3,5) なら CPU で 1-2日/条件
  - GPU (RTX 4090): d=7 で 数時間/条件
ライブラリ: PyTorch/JAX, Stim, PyMatching (ベースライン)
人員: 2名 (B: シミュレータ + D: デコーダ研究者)
期間: 8-12週間
```

### 論文での主張（x.mdに耐える形）

> "We present the first decoder that exploits the continuous-variable
> syndrome output of GKP error correction for adaptive noise tracking.
> Unlike MWPM, which is provably insensitive to noise parameter
> recalibration due to scale invariance (our prior result), the FiLM-GKP
> decoder directly conditions on the analog residual distribution and
> adapts to time-varying noise. Under realistic drift scenarios, it
> outperforms soft-info MWPM by [X]×."

新規性の根拠:
- GKP連続値 × 適応型NNデコーダ = 世界初
- MWPMスケール不変性の壁を超える構成的解決策
- RESEARCH_REPORT.mdで同定した空白領域の開拓

---

## R2: GKP連続値 × EM反復デコード（次点）

### なぜ新規か

**Nayak+ (2026)**: 変分EMでノイズパラメータを推定しつつデコードを反復。
ただし**離散qubit (depolarizing noise)** のみ。GKPへの拡張は未実施。

**MWPMのターボ方式が失敗した理由** (RESEARCH_REPORT.md):
- MWPMは厳密最適 → 反復しても同じ解に戻る
- しかしBP/EMは近似的 → 反復改善の余地がある

**GKP連続値をEMの観測データとして使えば:**
- E-step: GKP残差 r_i から各エッジの事後エラー確率を計算
- M-step: 事後確率からノイズパラメータ V_eff を再推定
- BP decode: 更新されたV_effでBPを再実行
- GKP残差は離散シンドロームより**はるかに豊かな情報**を持つ → EMの収束が速い

### 具体的研究計画

```
Phase 1: GKP-EM基盤構築 (2週間)
  - Nayak+ 2026 の variational EM を GKP noise model に移植
  - E-step: p(error_j | r_j, V_eff) = GKP posterior from residual
  - M-step: V_eff_new = argmax Σ log p(r_j | V_eff)
  - 収束条件: |V_eff_new - V_eff_old| < ε

Phase 2: GKP-EM + BP デコーダ (2-3週間)
  - QLDPC符号 (girth ≥ 6) でBPが表面符号より有利
  - BPの初期メッセージをGKP残差のLLRで初期化
  - EM反復ごとにBPを再実行
  - 表面符号 (girth=4) でも試すが、QLDPC符号が主ターゲット

Phase 3: 性能評価 (2-3週間)
  - GKP-EM-BP vs MWPM soft-info vs 通常BP
  - 静的ノイズ + 時変ノイズ
  - 表面符号 + QLDPC (bivariate bicycle code)

Phase 4: 論文化 (2週間)
  - タイトル案: "Iterative decoding of GKP codes via expectation-
    maximization with continuous-variable syndrome data"
```

### 新規性の根拠

- Nayak 2026 を GKP に拡張 → 世界初
- RESEARCH_REPORT.mdの「ターボMWPMの失敗」から「ターボBP/EMの成功」へ
- GKP連続値がEMの収束を加速する理論的予測

---

## R3: QLDPC + GKP on Macronode TDM（3番手）

### なぜ新規か

RESEARCH_REPORT.md の壁3: 表面符号の girth-4 で BP が劣化。
**QLDPC符号 (girth ≥ 6) なら BP が MWPM を超える** (Borah+ 2025)。

しかし:
- Borah 2025 は一般的な GKP + QLDPC の閾値解析のみ
- macronode TDM アーキテクチャ上での QLDPC 実装は未検討
- TDM の時間多重構造と QLDPC の非局所性の整合性は未解決

### 研究計画

```
Phase 1: QLDPC on TDM の理論的検討
  - bivariate bicycle code のTDM上へのマッピング
  - 遅延線構成（長遅延の本数）の必要数検討
  - TDMクロックとQEC cycle の整合性

Phase 2: GKP + QLDPC + BP シミュレーション
  - Borah 2025 の手法を macronode パラメータで再実装
  - soft-info BP (GKP残差初期化) の閾値決定
  - 表面符号 soft-info MWPM との比較

Phase 3: TDM実装設計
  - 必要なハードウェア変更の評価
  - 遅延線追加コスト
  - Phase 2+ への組み込み可能性
```

### 新規性の根拠

- Macronode TDM上のQLDPC実装 = 世界初
- girth-4問題の構成的解決（表面符号→QLDPC移行）
- TAROS Phase 3+ の性能予測に直結

---

## 4人チーム アサインメント

| 役割 | R1 担当 | R2 担当 | 期間 |
|------|---------|---------|------|
| **A: アーキテクト** | 論文構成・理論的フレーミング | QLDPC-TDM理論 (R3) | 全期間 |
| **B: QECシミュレータ** | データ生成パイプライン | GKP-EM基盤 | 8-12週 |
| **C: 光学モデラー** | ノイズドリフトモデル | ハードウェア整合性検証 | 4-8週 |
| **D: デコーダ研究者** | FiLM-GKP NN設計・訓練 | BP-EM実装 | 8-12週 |

### タイムライン

```
Week 1-2:   R1 Phase 1 (ベースライン) + R2 Phase 1 (EM移植)     ← 並行
Week 3-5:   R1 Phase 2 (FiLM-GKP設計)                          ← D集中
Week 5-7:   R1 Phase 3 (静的ノイズ検証) + R2 Phase 2 (BP統合)   ← 並行
Week 7-10:  R1 Phase 4 (時変ノイズ) ← 核心実験                   ← 全員
Week 10-12: R1 Phase 5 (論文化)                                  ← A+D
Week 8-12:  R2 Phase 3-4 (性能評価・論文化)                      ← B+C
```

### 成功基準

| レベル | R1 基準 | R2 基準 |
|--------|---------|---------|
| **必須** | 時変ノイズ下でMWPM soft-infoを有意に上回る | GKP-EM-BPがGKP-MWPMと同等以上 |
| **目標** | 5× 以上の改善（FiLM離散の7.4×に匹敵） | QLDPC+BPで表面符号+MWPMを超える |
| **理想** | MWPMスケール不変性を破る初のデコーダとして確立 | EM反復×GKP連続値で収束加速を証明 |

---

## 論文ターゲット

| 研究 | ジャーナル | 理由 |
|------|-----------|------|
| **R1** | **PRX Quantum** or **PRL** | GKP×適応デコーダ = 未踏。主結果が明確 |
| **R2** | Physical Review A or QST | EM拡張は技術的貢献。R1よりインパクト低い可能性 |
| R1+R2統合 | Nature Physics (野心的) | 「GKP連続値がデコーダを根本的に変える」統一的主張 |

---

## リスクと対策

| リスク | 確率 | 影響 | 対策 |
|--------|------|------|------|
| FiLM-GKPが静的ノイズでMWPMに負ける | 中 | R1の前提崩壊 | NN容量増加、ResNet→Transformer |
| 時変ノイズでも改善しない | 低 | R1の核心失敗 | 条件付けメカニズム変更、RL方式に切替 |
| GKP-EMが収束しない | 中 | R2失敗 | 初期値をMWPMから取る、アニーリング |
| 先行研究に先を越される | 中 | 新規性喪失 | arXiv preprint早期投稿 |
| GPU不足 | 高 | R1遅延 | d=3,5でCPU訓練、Colab/Lambda Labs |
