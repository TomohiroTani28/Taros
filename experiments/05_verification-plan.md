# GKP・Soft-info・Decoder・TDM構造 検証実験計画

**Document ID**: PQC-CV-VERPLAN-v1.0
**Last Updated**: Phase -1 開始前
**Status**: Plan
**目的**: IBM Quantum実機では検証不可能な4項目の検証方法と費用を定義

---

## 0. なぜIBM Quantumでは検証できないか

| 項目 | IBM Quantum | 必要な物理系 |
|------|------------|------------|
| GKP符号 | 離散変数(qubit) | **連続変数**(光の振幅・位相) |
| Soft-info decoder | ハードシンドローム(0/1) | **アナログ値**(ホモダイン電圧) |
| TDM構造 | 並列配置qubit | **時分割多重**(遅延線ループ) |
| Macronode cluster | ゲート操作で生成 | **測定ベースQC**(エンタングルド光) |

IBM/超伝導量子コンピュータは「離散変数・回路モデル」であり、
Tarosの「連続変数・測定ベース・光」とは物理層が根本的に異なる。

---

## 1. 検証可能な4階層

```
┌─────────────────────────────────────────────────────────┐
│ Level 4: 全統合 (TDM + GKP + Surface + Decoder)         │ Phase 0
│    → 実際のTaros Edu プロトタイプ                         │ 約5,550万円 (Level 1-4累計)
├─────────────────────────────────────────────────────────┤
│ Level 3: TDM macronode クラスタ生成                       │ 光学実験
│    → OPA×2 + BS×3 + delay + homodyne                    │ 約1,200万円
├─────────────────────────────────────────────────────────┤
│ Level 2: GKP状態生成 + soft-info取得                     │ 光学実験
│    → OPA×2 + homodyne + postselection                   │ 約585万円 (G-EXP1)
├─────────────────────────────────────────────────────────┤
│ Level 1: Decoder / QEC シミュレーション                    │ 古典計算
│    → Stim + Python + GPU                                │ 約75万円〜300万円
└─────────────────────────────────────────────────────────┘
```

---

## 2. Level 1: Decoder検証（古典シミュレーション）

### 2.1 何を検証するか

- soft-info Union-Findの p_th_eff が本当に1.5%か
- macronode noise構造での表面符号threshold
- 有限エネルギーGKP (Δ>0) の影響定量化

### 2.2 方法

| 手法 | ツール | 計算規模 |
|------|--------|---------|
| Stim表面符号シミュレーション | Google Stim + PyMatching | 10⁶-10⁸ shots × d=3,5,7,9 |
| GKPノイズモデル追加 | カスタムPython (Gaussian displacement channel) | — |
| Soft-info decoder実装 | rustworkx Union-Find + weighted growth | — |
| GPU加速 | NVIDIA A100 (クラウドレンタル) | 100-500 GPU-hours |

### 2.3 費用

| 項目 | 費用 | 備考 |
|------|------|------|
| GPU計算 (AWS p4d.24xlarge, 500h) | 約240万円 | 約4,800円/h × 500h |
| 開発工数 (2名×2ヶ月) | 約600万円 | decoder実装+検証 |
| ソフトウェアライセンス | 0円 | Stim/PyMatching OSS |
| **Level 1 合計** | **約840万円** | **期間: 2ヶ月** |

### 2.4 期待成果

- p_th_eff (soft-info UF) の精密値 (±0.1%)
- 有限エネルギーΔに対するp_L感度曲線
- macronode noise correlation が threshold に与える影響

### 2.5 Go/No-Go判定基準

- **Go**: p_th_eff ≥ 1.0% かつ Δ=0.1で p_L(d=7) < 10⁻⁶
- **No-Go**: p_th_eff < 0.8% → soft-info効果不十分、MWPM必須

---

## 3. Level 2: GKP状態生成実験（光学テーブルトップ）

### 3.1 何を検証するか

- squeezed vacuum からの postselection による GKP 状態生成
- 実効 F_GKP と Δ の実測
- 成功確率 P_s の実測
- soft-info (アナログホモダイン値) の取得実証

### 3.2 方法

```
775nm LD (200mW) → PPLN OPA → squeezed vacuum (target 12-13dB)
                                    │
                                    ▼
                              [50:50 BS]
                              /         \
                       homodyne_q      homodyne_p
                       (amplitude)     (phase)
                              \         /
                               ▼     ▼
                         [ADC 14bit 1GSPS]
                               │
                               ▼
                    [PC: postselection + GKP Wigner解析]
```

### 3.3 費用

| 項目 | 費用 | 備考 |
|------|------|------|
| PPLN OPA ×2 (NTT共同研究) | 約90万円 | 単価約45万円 |
| 775nm pump LD (200mW DFB) | 約30万円 | 実験用(TA不要) |
| Balanced homodyne detector ×2 | 約120万円 | Thorlabs PDB480C相当 |
| ADC (14bit 1GSPS) ×2 | 約90万円 | Teledyne SP Devices |
| 光学部品 (BS, ミラー, PBS, λ/2) | 約75万円 | |
| PMF, コネクタ, マウント | 約45万円 | |
| Master laser (1550nm) | 約45万円 | |
| SHG module | 約45万円 | |
| 光学テーブル・マウント (既存流用想定) | 0〜約45万円 | |
| **Level 2 合計** | **約585万円** | **期間: 3ヶ月** |

> ※費用定義の統一: 装置BOM約630万円 (OPA×2正確計上) /
> 装置直接費約870万円 (予備・消耗品込み) /
> 完全コスト約2,970万円 (人件費2名×5ヶ月込み)。
> 本文書のLevel 2 約585万円は旧OPA×1構成の最小BOMに相当。

これは既存の `experiments/01_gkp-optical.md` (G-EXP1) と同一。

### 3.4 期待成果

- CW squeezing ≥12dB の確認
- postselection GKP F_GKP 実測 (目標 >0.80)
- per-mode高信頼率 実測 (目標 >90%, δ=0.19√π基準)
- アナログ soft-info 値の統計分布取得
- **有限エネルギー Δ の直接測定** (Wigner function tomography): 目標 Δ < 0.10
  - Δ測定方法: 状態トモグラフィ → Wigner関数再構成 → GKP格子のenvelope fitting
  - **Go/No-Go追加基準**: Δ < 0.12 で Go（p_L ~ 10⁻⁵達成可能）、Δ > 0.15 で No-Go

### 3.5 Go/No-Go判定基準

- **Go**: F_GKP > 0.80 (初期確認基準; 製品仕様は F>0.85),
  P_s > 5×10⁻⁴, squeezing > 12dB
- **No-Go**: squeezing < 10dB → OPA品質不足、NTT改良必要

---

## 4. Level 3: TDM macronode クラスタ生成

### 4.1 何を検証するか

- 2-OPA + BS + delay line による macronode lattice 生成
- TDM clock 100MHz での安定動作
- 位相ロック（PLL BW ≥ 500kHz）の実証
- cluster state nullifier 測定による entanglement 確認

### 4.2 方法

```
OPA#1 ──┐
         BS₁ ── short delay (2m) ── BS₂ ── homodyne_A
OPA#2 ──┘                              │
                                   long delay (37m = d=3用)
                                        │
                                       BS₃ ── homodyne_B
```

Level 2の装置を拡張（OPA×2、BS×3、遅延線、位相ロック追加）。

### 4.3 費用

| 項目 | 費用 | 備考 |
|------|------|------|
| Level 2装置（流用） | (約585万円) | G-EXP1から継続 |
| 追加BS ×3 (ファイバカプラ) | 約45万円 | |
| PMF 37m (short delay + long delay) | 約7.5万円 | |
| 775nm TA (500mW) | 約120万円 | 2-OPA同時ポンプ |
| PZT fiber stretcher ×2 | 約60万円 | 位相ロック用 |
| EO gate (LNOI EOM) | 約60万円 | |
| PLL制御基板 (PID + DAC) | 約75万円 | |
| 追加homodyne detector ×2 | 約120万円 | 計4ch |
| FPGA評価ボード (Versal VE2302) | 約75万円 | リアルタイムFF試験 |
| EO comb + RF driver (25GHz) | 約105万円 | WDM LO生成 |
| 追加ADC ×2 | 約90万円 | |
| 光学テーブル追加スペース | 約45万円 | |
| **Level 3 追加分** | **約803万円** | |
| **Level 2+3 累計** | **約1,388万円** | **期間: +3ヶ月 (累計6ヶ月)** |

### 4.4 期待成果

- 1D macronode cluster state 生成確認 (nullifier squeezing > 3dB)
- 100MHz TDM clock 安定動作 (>10⁶ modes連続)
- 位相ロック残留ノイズ < 0.1° RSS (PLL BW 500kHz)
- EO gate 動作確認 (消光比 >30dB, 設計要件。初期目標>25dBでGo判定可)

### 4.5 Go/No-Go判定基準

- **Go**: nullifier > 3dB, PLL < 0.1°, 連続10⁶ mode安定
- **No-Go**: nullifier < 1dB → cluster品質不足

---

## 5. Level 4: 全統合プロトタイプ (Taros Edu)

### 5.1 何を検証するか

- 完全なQECサイクル: GKP生成 → cluster → syndrome → decoder → feedforward
- 論理エラー率 p_L の直接測定
- break-even (p_L < p_phys) の実証

### 5.2 費用

Level 3装置 + decoder FPGA + feedforward制御を統合:

| 項目 | 費用 | 備考 |
|------|------|------|
| Level 3装置（流用） | (約1,388万円) | |
| FPGA本格実装 (VE2302 + カスタム基板) | 約225万円 | |
| DAC (16bit 12GSPS) + EO driver | 約150万円 | |
| AWG (8ch, 低損失) | 約45万円 | |
| 追加PD ×8 (WDM用) | 約60万円 | |
| 追加ADC ×8 | 約300万円 | |
| 制御ソフトウェア開発 (3名×4ヶ月) | 約1,800万円 | |
| 筐体・組立 | 約150万円 | |
| 較正・テスト期間の人件費 | 約600万円 | |
| **Level 4 追加分** | **約3,330万円** | |
| **Level 1-4 全累計** | **約5,550万円** | **期間: 12ヶ月** |

### 5.3 Go/No-Go判定基準

- **Level A (スケーラブルQEC)**: p_L(d=3) < p_phys (break-even)
- **Level B (動作実証)**: GKP + 表面符号の統合動作確認

---

## 6. 費用サマリー

```
                                                      累計コスト
Level 1: Stim simulation (decoder)     約840万円  ──┬── 約840万円    [2ヶ月]
                                                    │
Level 2: GKP光学実験 (G-EXP1)          約585万円  ──┘── 約1,425万円  [並列実行: 2ヶ月目から開始]
                                                │
                                                │ ※Level 1 & 2 は依存関係なし → 並列実行推奨
                                                │   並列時クリティカルパス: 6ヶ月 (Level 2律速)
                                                │
Level 3: TDM macronode                  約810万円  ──── 約2,235万円  [+3ヶ月 = 9ヶ月]
                                                │
Level 4: Full prototype (Taros Edu)   約3,330万円  ──── 約5,550万円  [+4ヶ月 = 13ヶ月]
```

> Level 1(Stim)とLevel 2(光学)に物理的依存関係はない。並列実行で2ヶ月短縮。
> **現実的タイムライン**: CW GKP実験6ヶ月 + パルスTDM追加4ヶ月 = Level 2-3合計10ヶ月。
> Level 1(2ヶ月)はLevel 2開始と同時に開始し、結果をLevel 3設計にフィードバック。

### 段階的Go/No-Go判定

| ゲート | 時期 | 判定基準 | 次ステップ |
|--------|------|---------|-----------|
| G1 | 開始後2ヶ月 | p_th_eff ≥ 1.0% (Stim) | Level 2開始 |
| G2 | 開始後5ヶ月 | F_GKP > 0.80 (光学) | Level 3開始 |
| G3 | 開始後8ヶ月 | Cluster nullifier > 3dB | Level 4開始 |
| G4 | 開始後12ヶ月 | p_L < p_phys (break-even) | 製品開発 |

---

## 7. 代替手段（安価な部分検証）

| 手法 | コスト | 検証範囲 | 限界 |
|------|--------|---------|------|
| **Stim + Python (Level 1のみ)** | 約75万〜300万円 (GPU rental) | Decoder, threshold | GKP実物なし |
| **Xanadu Strawberry Fields** | 0円 (OSS) | GKP simulation | ノイズモデル簡略 |
| **Amazon Braket (simulator)** | 約15万〜75万円 | 小規模QEC回路 | CV不可 |
| **Azure Quantum (IonQ/Quantinuum)** | 約150万〜750万円 | 高精度QEC (trapped ion) | 光方式ではない |

### 最小構成（最安）で何がわかるか

**約75万円 (GPU rental 150h)** で Level 1 の核心部分:
- Stim でsurface code d=3,5,7 を 10⁷ shots シミュレーション
- Gaussian displacement channel でGKPノイズモデル化
- p_th_eff の精密値取得

これだけで「設計が原理的に成立するか」の最重要判定が可能。

---

## 7.1 追加検証項目

| 区分 | 検証項目 | 方法・判定基準 | Phase / Level |
|------|---------|--------------|---------------|
| **追加** | macronode BS混合ノイズの実効値検証 | Stim sim: macronode構造でのp_phys実測値とσ²理論値の整合確認。BS混合による追加ノイズが閾値定義と整合することを独立検証。 | Phase -1 Level 1 |
| **追加** | EDFA ASEフィルタ有効性検証 | FP etalon挿入後のshot-noise clearance測定。ASE/shot ratio < 0.1を確認。 | Phase -1a Level 2 |
| **追加** | PD QE実測と損失バジェット検証 | 市販PD(QE~95%)での実効σ_eff測定。11.3dB±0.3dBの確認。 | Phase -1a Level 2 |

---

## 8. 結論

| 質問 | 回答 |
|------|------|
| GKP符号をどう実験する? | **光学テーブルトップ実験** (OPA + homodyne + postselection) |
| Soft-infoをどう検証する? | **Level 1**: Stimシミュレーション。**Level 2**: アナログhomodyne値の実測 |
| Decoderをどう検証する? | **Level 1**: GPU上のStimシミュレーション (10⁷-10⁸ shots) |
| TDM構造をどう検証する? | **Level 3**: 2-OPA + delay line + 100MHz clock光学実験 |
| 全部でいくら? | **約5,550万円 / 12ヶ月** (段階的Go/No-Go付き) |
| 最安で核心だけ? | **約75万円** (Stim GPU simulation、2週間) |
| Phase -1実験は? | **約1,425万円 / 5ヶ月** (Level 1+2、G-EXP1含む) |

---

*本文書はIBM Quantum実機では検証不可能なCV方式固有の4項目（GKP符号、soft-info decoder、
TDM構造、macronode cluster）の検証方法と費用を定義したものである。
最小約75万円(Stim GPU)から最大約5,550万円(全統合プロトタイプ)まで段階的に検証可能。*
