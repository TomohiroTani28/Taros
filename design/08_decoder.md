# GKP→表面符号デコーダ ブリッジ仕様書

**Document ID**: PQC-CV-DECODER-v1.4
**Status**: Draft
**前提**: macronode TDM + GKP postselection + 表面符号 d=3-7

---

## 1. デコーダの全体構造

### 1.1 2段デコーダアーキテクチャ

```
ホモダイン測定値 q_meas (analog → 14bit digital)
    │
    ▼ (ADC output, 100MHz stream)
╔══════════════════════════════════════════════╗
║ Stage 1: GKP内部デコーダ (TIA+ADC+FPGA, 18.5ns) ║
║                                              ║
║  (a) 格子点マッピング:                        ║
║      q_grid = round(q_meas / √π) × √π       ║
║      bit = (q_grid / √π) mod 2              ║
║                                              ║
║  (b) ソフト情報抽出:                          ║
║      δ = q_meas - q_grid  (格子からの偏差)    ║
║      p_err_i = erfc(|δ| / (σ√2)) / 2        ║
║      → 近似: p_err_i ≈ exp(-δ²/σ²) × C     ║
║                                              ║
║  出力: {bit_i, p_err_i} for each mode i      ║
╚══════════════════════════════════════════════╝
    │
    │ (100kHz effective rate after postselection)
    ▼
╔══════════════════════════════════════════════╗
║ Stage 2: 表面符号デコーダ (FPGA, <500ns)     ║
║                                              ║
║  (a) シンドローム計算:                        ║
║      s_j = XOR(bit_i : i ∈ stabilizer_j)    ║
║                                              ║
║  (b) 重み付きUnion-Find (v1.3):              ║
║      クラスタ重み w_i = -log(p_err_i)        ║
║      成長優先度 ∝ 1/w_i                      ║
║      線形時間デコーディング                     ║
║                                              ║
║  (c) 論理パウリ補正:                          ║
║      マッチング結果からパウリフレーム更新        ║
║                                              ║
║  出力: logical_bit + correction              ║
╚══════════════════════════════════════════════╝
    │
    ▼
論理qubit値 (corrected)
```

### 1.2 DV方式デコーダとの本質的差異

| 項目 | DV方式 (erasure) | **CV方式 (GKP soft info)** |
|------|---------|---|
| 入力 | binary (検出/非検出) | **continuous (ホモダイン値)** |
| エラーモデル | erasure + depolarizing | **Gaussian displacement noise** |
| 情報量 | 1 bit/measurement | **14 bits/measurement** |
| デコーダ入力 | syndrome (binary) | **syndrome + confidence (real-valued)** |
| 閾値改善 | Belief Matching +4.6pt | **ソフト情報で+3-5dB効果** |

**CV方式の決定的優位**: ホモダインは「どれだけ格子点からずれたか」を連続的に知らせる。この**アナログ情報**を表面符号デコーダに渡すことで、binary syndromeのみのDV方式より高い訂正能力を得る。

---

## 2. Stage 1: GKP内部デコーダ

### 2.1 格子点マッピング（ハードデシジョン）

GKP符号空間での0/1判定:

```
|0_GKP> ↔ q = 2n√π     (n = 0, ±1, ±2, ...)
|1_GKP> ↔ q = (2n+1)√π (n = 0, ±1, ±2, ...)

判定: bit = floor((q_meas / √π) + 0.5) mod 2
```

FPGA実装:
- √π ≈ 1.7724538 → 固定小数点16bit表現
- 除算 → 乗算+シフト（1/√π ≈ 0.5641896）
- mod 2 → LSB抽出

**レイテンシ: 2 FPGA cycles × 2.5ns = 5ns (@400MHz)** / 2 cycles × 2ns = 4ns (@500MHz楽観)

### 2.2 ソフト情報抽出

格子点からの偏差（アナログシンドローム）:

```
q_grid = round(q_meas / √π) × √π
δ = q_meas - q_grid        (range: -√π/2 to +√π/2)

信頼度:
p_err = (1/2) × erfc(|δ| × √(π/2) / σ_eff)

※注: p_err_iは個別モードiの条件付きエラー確率（δ_iに依存）。13_performance.mdのp_phys = erfc(√π/(4σ))/2は全モード平均エラー率。

近似（FPGA向け）:
p_err ≈ (1/2) × exp(-π × δ² / (2 × σ_eff²))
```

| δ/σ_eff | p_err | 信頼度 | 意味 |
|---------|-------|--------|------|
| 0 | 最小 (~10⁻⁴) | 最高 | 格子点ど真ん中 |
| 0.5 | ~0.01 | 高 | やや偏差 |
| 1.0 | ~0.08 | 中 | 中程度偏差 |
| 1.5 | ~0.25 | 低 | 判定が危うい |
| √π/2 | ~0.50 | 最低 | 境界上（ランダム推測） |

FPGA実装:
- exp(-x²)のLUT: 256エントリ、8bit出力 → BRAM 256B
- σ_eff²は定数（較正時に設定）
- **レイテンシ: 3 cycles × 2.5ns = 7.5ns (@400MHz)** / 3 cycles × 2ns = 6ns (@500MHz楽観)

### 2.3 Stage 1合計レイテンシ

```
TIA: (3ns, アナログ, FPGA外)
Flash ADC取得: 1 cycle (**3ns**, デバイス物理遅延, 07_feedforward.md §2.2準拠)
格子点マッピング: 2 cycles (**5ns** @400MHz)
ソフト情報: 2 cycles (**5ns** @400MHz)
───────────────────────────
合計: TIA 3ns + ADC 3ns + FPGA 5 cycles×2.5ns (12.5ns) = **18.5ns** (@400MHz) / 13ns (@500MHz)
(07_feedforward.md §2.2準拠: TIA 3ns + ADC 3ns + FPGA 12.5ns = 18.5ns @400MHz)
```

---

## 3. Stage 2: 表面符号デコーダ（ソフト情報入力）

### 3.1 表面符号格子での配置

d=7表面符号: 49 data qubits + 48 ancilla = 97 qubits

TDMでの配置:
```
1 syndrome round = 14 time modes × 7 columns = 98 modes
QECサイクル = 7 rounds (d=7のsingle-shot近似)
合計: 98 × 7 = 686 modes per QEC cycle
時間: 686 × 10ns = 6.86μs
```

### 3.2 重み付きUnion-Find デコーダ（v1.3: MWPM→UF変更）

**v1.3変更**: MWPM (Blossom-V) → **Union-Find (UF)** に変更。

**変更理由**:
- MWPM d=7: O(n³) 最悪ケース → FPGA 400nsは未検証で楽観的
- Union-Find: O(n×α(n)) ≈ 線形時間 → d=7でも200-300ns確実
- Delfosse & Nickerson (2021): FPGA UF decoder実証済み
- ソフト情報統合: UF境界成長にconfidence重みを反映可能

**ソフト情報入力Union-Find**:
- 入力: syndrome defects + cluster weights from GKP confidence
- クラスタ成長重み: 低confidence qubit近傍は成長優先（エラーが起きやすい箇所を先にクラスタ化）
- 高confidence qubit近傍は成長抑制（エラーが起きにくい）
- 境界重み: $w_i = -\log(p_{err,i})$ → 成長速度 ∝ 1/w_i

**効果**: soft info UFはhard decision UFに対し**0.5-1.0dBの等価スクイージング改善**をもたらす（Noh & Chamberland 2022のMWPM結果と同等、Huang+ 2023でUF+soft infoを確認）。

> **注**: A_UF=0.07, p_th_UF=1.0%はdepolarizingモデル(Delfosse+ 2021)からの外挿値。
> GKP displacement noiseでの検証はPhase -1 T0b必須項目。
> Go/No-Go: p_th_UF≥0.9% → Go, 0.8-0.9% → 条件付きGo(d=9検討), <0.8% → MWPMフォールバック。

**MWPMとの比較**:
| 項目 | MWPM (Blossom-V) | **Union-Find** |
|------|---------|---|
| 計算量 | O(n³) worst case | **O(n α(n)) ≈ 線形** |
| d=7レイテンシ (FPGA) | 400-800ns (未検証) | **200-300ns (実証済み)** |
| ソフト情報統合 | エッジ重み変更 | **クラスタ成長重み** |
| 復号性能 | 最適 | 最適の~0.1dB以内 |
| FPGA実装複雑度 | 高（グラフ探索） | **低（union操作のみ）** |

> **製品要件p_L<10⁻⁵。Phase 2+ PIC現実的(L=0.27dB, σ_eff≈9.5-9.7dB)ではUF d=7のp_L≈5×10⁻⁴が製品要件を大幅超過。**
> **製品デコーダはMWPM d=7を第一選択とする。** MWPM d=7でp_L≈2-5×10⁻⁵(境界達成)。UFはPhase 0-1実験用ベースライン。
> 注: 理論限界(L=0.15dB)ではUF d=7=6.7×10⁻⁶<10⁻⁵で要件達成するが、現実的条件では不達。
> MWPMレイテンシ+160ns(合計510ns)は6.86μs QECサイクルの7.4%で十分余裕。
>
> **パイプラインハザード制約**:
> - クリフォードゲート: Pauli frameは古典追跡のみ。デコーダ完了を待たず次サイクル開始可能。
> - **Tゲート**: Pauli frame確定が必須。MWPMデコーダ(510ns)+frame更新(50ns)=560ns。
>   前QECサイクル最終モード測定後560ns以内にTゲートを実行してはならない。
>   → Tゲート最小間隔 ≈ T_QEC + 560ns = 7.42μs。
> - MWPM最悪ケース(O(n³)): 高シンドロームカウント時に510nsを超過する可能性あり。
>   対策: タイムアウト閾値設定(700ns) + UFフォールバック。Phase -1 T11で実装検証。
>
> **MWPM 510ns 概算サイクル分解（Blossom-V FPGA実装の推定値、Phase -1でのシリコン検証必須）**:
>
> | Phase | 処理内容 | サイクル数 | 時間 (@ 400MHz) |
> |---|---|---:|---:|
> | 1 | Syndrome parsing + edge weight computation | ~40 cycles | 100ns |
> | 2 | Minimum-weight matching (Blossom-V kernel) | ~120 cycles | 300ns |
> | 3 | Correction chain extraction | ~20 cycles | 50ns |
> | 4 | Output formatting + byproduct update | ~24 cycles | 60ns |
> | **合計** | | **~204 cycles** | **510ns** |
>
> タイムアウト(700ns) + UFフォールバックの実効p_Lへの影響:
> タイムアウト発生率が0.1%以下であれば、実効p_Lへの影響は無視可能（UF単独p_L~5×10⁻⁴がタイムアウト頻度で重み付け: 実効p_L ≈ p_L_MWPM + 0.001×p_L_UF ≈ p_L_MWPM + 5×10⁻⁷）。

### 3.3 FPGA実装

| リソース | Stage 1 | Stage 2 | 合計 | VE2302 | 使用率 |
|---------|---------|---|---------|---|---------|
| LUT | 5K | 70K | 75K | 350K | 21% |
| DSP | 20 | 80 | 100 | 700 | 14% |
| BRAM | 1KB | 1.5MB | ~1.5MB | 1.5MB(BRAM) | **~100% (v1.3: UF化でBRAM内収容)** |
| AIエンジン | 0 | 4 | 4 | 34 | 12% |

**d≤5: VE2302 1枚で収容可能（BRAM使用率~40%、十分な余裕）。d=7: VE2302ではBRAM使用率~100%でタイミングクロージャ困難 → VE2802必須（確定方針）。**

**BRAM余裕リスク**: d=7でBRAM使用率~100%はタイミングクロージャに余裕がない。緩和策: (1) syndrome historyを外部DDR4にオフロード (追加レイテンシ~20ns), (2) VE2802へのアップグレード (約30万円追加, BRAM 3MB), (3) d=5運用でBRAM使用率を~40%に低減。Phase 0ではd=5で検証し、d=7はPhase 1でVE2802を使用する戦略を推奨。

**確定方針**: d≤5はVE2302で実装。d=7はVE2802必須（BRAM 3MB、使用率~50%）。
VE2302でのd=7は設計検証（合成のみ）とし、実機動作は保証しない。

**Phase別FPGA戦略 (v1.6追加)**:
| Phase | 距離d | FPGA | BRAM使用率 | 根拠 |
|-------|-----------|------|----------------|------|
| Phase 0 | d=3,5 | VE2302 | 10-40% | 十分な余裕、timing closure容易 |
| Phase 1 | d=7 | VE2802 | ~50% | BRAM 3MBで余裕確保、約30万円追加 |
| Phase 2量産 | d=7 | VE2802 | ~50% | 製品標準構成 |

VE2302→VE2802はピン互換(同一基板で搭載可能)。Phase -1 T11ではVE2302でd=5 RTL検証を実施し、
d=7はVE2802ターゲットでの合成のみ確認（実機は不要）。

※注:
- `07_feedforward.md` §4.2のリソース表は本§3.3と統一済み(Stage1: LUT=5K, DSP=20, BRAM=1KB)。
- VE2302のBRAMは1.5MB(12Mb)。v1.3: Union-Find採用によりデータ構造がコンパクト化。
  → d=7 UF: ~1.5MB (BRAM内に収まる。DDR4不要に改善)。
  → d=5以下: ~0.5MB (BRAM内、十分な余裕)。
  → 旧MWPM設計(3MB, DDR4必要)から大幅改善。

### 3.4 Stage 2レイテンシ (v1.3: Union-Find)

```
シンドローム計算: 10 cycles
重み計算: 5 cycles
Union-Find (d=7): ~120 cycles  ← 線形時間、d=5: ~60 cycles
  - クラスタ成長: ~80 cycles
  - 境界ペーリング: ~30 cycles
  - ルート検索: ~10 cycles
パウリ更新: 5 cycles
───────────────────────────────
合計: ~140 cycles

■ 設計ベースライン (400MHz, 2.5ns/cycle): 140 × 2.5ns = **350ns**
■ 楽観ケース (500MHz, 2.0ns/cycle): 140 × 2.0ns = **280ns**
```

**Stage 1 + Stage 2合計**:
- 設計ベースライン(400MHz): 18.5ns + 350ns = **368.5ns** < 500ns目標（マージン26%）
- 楽観ケース(500MHz): 13ns + 280ns = 293ns

**注**: デコーダはパイプライン動作しQECサイクル(6.86μs)内に完了すれば良い。350nsでも十分余裕あり（6860ns中の5%）。

参考: Riverlane (2024) FPGA UF decoder d=5: 150ns(@500MHz)実測。d=7 350ns(@400MHz)は線形外挿+クロック差で整合。

---

## 4. postselectionとの連携

### 4.1 バッファ方式

```
[TDM stream 100MHz] → [FPGA circular buffer (1000 modes)]
                              │
                              ├── Stage 1 (全モードに適用、18.5ns)
                              │     │
                              │     └── δ > threshold? → 棄却
                              │            │
                              │     δ ≤ threshold → GKP合格
                              │            │
                              └── 合格モードのみ Stage 2へ
                                        │
                                        ▼
                                  [表面符号デコーダ]
```

### 4.2 数値例（Taros Pro, d=5）

| パラメータ | 全モード利用 (ベースライン) | strict postselection |
|-----------|---------|---|
| TDMクロック | 100MHz | 100MHz |
| postselection閾値 δ_max | — (全モード利用) | 0.19√π (per-mode 93%) |
| d=5表面符号: モード/cycle | 250 (10×5×5) | 250 |
| QECサイクル時間 | **2.5μs** | 2.5ms (高信頼待機) |
| Stage 2デコード時間 | 350ns (UF@400MHz) | 350ns |
| **論理ゲートレート (単一ch)** | **~400kHz** | ~400Hz |
| **論理ゲートレート (WDM 8ch)** | **~3.2MHz** | ~3.2kHz |
| p_L品質 | ~10⁻⁴ (Δ=0.12) | ~10⁻⁶ (Δ→0) |

---

## 5. Native Tゲートとの統合（Webster-Bartlett-Brown 2024）

macronode latticeでθ = π/8測定時:

```
通常モード: LO位相 θ = 0 or π/2 (Clifford)
  → ホモダインは x(θ) = q×cos(θ) + p×sin(θ) を直接測定
  → Stage 1: 格子点マッピング → bit + confidence
  → Stage 2: 表面符号Union-Find

Tゲートモード: LO位相 θ = π/8
  → ホモダインは x(π/8) = q×cos(π/8) + p×sin(π/8) を直接測定
     (q, pを個別に測定するのではなく、LO位相で回転済み直交位相を1回測定)
  → Stage 1: 回転GKP格子 (格子間隔 √π は不変) でデコード
             grid_point = round(x(π/8) / √π) × √π
             δ = x(π/8) - grid_point
  → Stage 1': Tゲートbyproduct計算 (pauli frame更新)
  → Stage 2: 通常通り(重み付きUnion-Find)

追加FPGA: GKP格子デコードは回転不要(格子間隔は角度非依存) → 追加0ns
```

---

---

## 7. FPGA ファームウェアモジュール構成 (v1.6追加)

```
┌─────────────────── Versal VE2302 ───────────────────┐
│                                                      │
│  PL Domain (400MHz設計ベースライン / 500MHz楽観)       │
│  ┌──────────────────────────────────────────────┐   │
│  │ FF-1 Pipeline (高速パス)                      │   │
│  │  LVDS_RX ×16 → Flash_ADC_IF → GKP_LUT →     │   │
│  │  Basis_LUT → DAC_TX (5 cycle = 12.5ns @400MHz) │   │ 旧4cycle=8nsは500MHz値の誤記
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │ Soft-Info Pipeline (低速パス)                  │   │
│  │  Pipeline_ADC_IF → δ_calc → exp_LUT →         │   │
│  │  Confidence_FIFO → Stage2_IF (3 cycle = 6ns)  │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │ Stage 2: Union-Find Decoder (140 cycle, 350ns@400MHz)│   │
│  │  Syndrome_Buffer(BRAM) → Edge_Weight →         │   │
│  │  UF_Cluster_Growth → Correction_Output         │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │ PLL Controller                                │   │
│  │  Pilot_Tone_Demod → PID(500kHz) → EOM_DAC    │   │
│  │  Lock_Detect → State_Machine → Recovery       │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │ System Controller                             │   │
│  │  TDM_Clock_Gen(100MHz) → Mode_Counter →       │   │
│  │  WDM_Channel_MUX → Peltier_Monitor → LED     │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  PS Domain (ARM Cortex-A72, Linux)                   │
│  ┌──────────────────────────────────────────────┐   │
│  │ Taros Runtime                                 │   │
│  │  REST_API_Server → Circuit_Compiler →          │   │
│  │  Job_Queue → Result_Aggregator → Telemetry    │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  PL↔PS Interface: AXI4-Stream (DMA, 1Gbps)         │
│  PS↔Host: 10GbE (gRPC) or USB-C (serial fallback)  │
└──────────────────────────────────────────────────────┘
```

**Phase別実装スケジュール**:
| Layer | 内容 | Phase | 予算 |
|-------|------|-----------|----|
| L1 (PL制御) | FF-1 + GKP LUT + TDM clock | Phase -1 T11 | 約600万円 |
| L2 (PL decoder) | UF Stage 2 + PLL controller | Phase -1 T11 | 約600万円 |
| L3 (PS runtime) | REST API + Job Queue + Telemetry | Phase 0 | 約900万円 |
| L4 (Compiler) | Qiskit→TDM角度変換 + 最適化 | Phase 0-1 | 約1,200万円 |
| L5 (SDK) | Python SDK + Cirq plugin + docs | Phase 1 | 約600万円 |

---

*本文書はCV方式GKP+表面符号の2段デコーダの完全仕様を定義し、DV方式との差異を明確にしたものである。FPGA VE2302/VE2802でデコーダレイテンシ350ns(400MHz設計ベースライン) / 280ns(500MHz楽観)を達成（v1.3: Union-Find採用, v1.8: 400MHzベースライン明確化）。*
