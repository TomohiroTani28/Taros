# フィードフォワード制御レイテンシバジェット

**Document ID**: PQC-CV-FF-v1.4
**Status**: Draft
**前提**: macronode TDM 100MHzクロック、GKP+表面符号

---

## 1. フィードフォワードの必要性

CV測定型量子計算では、各モードの測定結果に基づいて後続モードの測定基底（LO位相角θ）を適応的に決定する。このフィードフォワード制御のレイテンシが計算の忠実度を決定する。

### 1.1 2種類のフィードフォワード

| 種類 | 目的 | タイミング要件 | 許容レイテンシ |
|------|------|-------------|--------------|
| **FF-1: 基底選択** | GKPデコーダ結果に基づくLO角度θの設定 | 次のTDMモードの測定前 | < T_clk = **10ns** |
| **FF-2: Byproduct補正** | パウリフレーム追跡に基づく論理補正 | QECサイクル内 | < T_QEC = **~7μs** (d=7) |

---

## 2. FF-1: 基底選択フィードフォワード

### 2.1 レイテンシチェーン（Flash ADC + Pipeline ADC 並列構成）

**設計変更**: パイプラインADC (ADS5474) の実レイテンシは14段パイプライン = 35ns。
これでは26ns FF-1は不可能。**Flash ADC (6bit) を高速パスに使用**し、
Pipeline ADC (14bit) は並列でsoft info計算に使用する2パス構成に変更。

```
                        T=0     T₁      T₂      T₃      T₄      T₅
                         │       │       │       │       │       │
ホモダイン出力 (analog) ──┬►│       │       │       │       │       │
                         │ │       │       │       │       │       │
                         │ ▼       │       │       │       │       │
  高速パス (hard decision):  │       │       │       │       │       │
                    [TIA]──►[Flash ADC 6bit]──►[FPGA]──►[DAC]──►[EOM]──►[LO]
                     3ns       3ns          12.5ns   5ns    3ns    <1ns
                         │       │       │       │       │       │
                         └───────┴───────┴───────┴───────┴───────┘
                          設計ベースライン(400MHz): 26.5ns ≈ 27ns (3モード遅延)
                          楽観ケース(500MHz):       22ns (2-3モード遅延)
                         │
  低速パス (soft info):   │
                    [TIA]──►[Pipeline ADC 14bit]──►[FPGA soft info]──► Stage 2
                     3ns        35ns                  6ns
                              (パイプライン: スループット100MHz維持)
```

### 2.2 各段の詳細

**高速パス（FF-1用: hard decision + 基底選択）:**

| 段階 | デバイス | レイテンシ | 根拠 |
|------|---------|----------|------|
| (1) TIA | Maxim MAX3665 | 3ns | 帯域500MHz |
| (2) Flash ADC | **TI ADC06D1500 (6bit 1.5GSPS 低レイテンシADC (folding/interpolating型))** | **3ns** | データシートclock-to-data latency 4.5 cycles @1.5GHz ≈ 3ns（LVDS board propagation ~1ns含む）。消費電力1.2W。注: パイプライン型とは異なり深いパイプライン遅延なし。Phase -1でADC trigger→FPGA I/O valid実測要 |
| (3) FPGA処理 | Versal VE2302 | **12.5ns** (設計ベースライン, 400MHz 5cycle) / 8ns (楽観, 500MHz 4cycle) | 下記内訳参照 |
| (4) DAC | **MAX5898 (14bit 400MSPS, パラレルIF)** | **5ns** | パラレルバスIF、JESD不使用 AD9117(250MSPS上限)→MAX5898に変更。group delay 2cycle@400MHz=5ns |
| (5) EOドライバ + EOM応答 | iXblue MPZ-LN-10 + LNOI MZM | 3ns | 帯域12GHz, EO効果~fs応答 |
| **合計(設計ベースライン 400MHz)** | | **26.5ns ≈ 27ns** | **3モード遅延 (100MHz時)** |
| **合計(楽観ケース 500MHz)** | | **22ns** | **2-3モード遅延 (100MHz時)** |

**注**: S&H回路(AD783, 2ns acquire)はPLL誤差信号サンプリング用(05_phase-lock.md §5.6)であり、FF-1高速パスには含まれない。FF-1はTIA→Flash ADC→FPGA→DAC→EOMの直結パスで動作し、S&Hを経由しない。

**低速パス（soft info用: confidence値計算）:**

| 段階 | デバイス | レイテンシ | 根拠 |
|------|---------|----------|------|
| Pipeline ADC | TI ADS5474 (14bit 400MSPS) | 35ns (パイプライン) | スループット400MSPS維持 |
| FPGA soft info | Versal VE2302 | 6ns | δ²計算 + exp LUT |
| **合計** | | 41ns | **Stage 2バッファに蓄積（時間制約なし）** |

**FPGA I/O帯域検証**:
WDM 8ch × ADC 2本/ch × 14bit × 100MHz = 22.4Gbps入力データレート。
VE2302 PL I/O容量: GTY ×34 (各12.5Gbps) + HDIO ×88。合計425Gbps帯域。
22.4Gbps / 425Gbps = **5.3%使用率** → I/O帯域は十分。
実装: Flash ADC ×16はLVDS (500Mbps/ch) × 16 = 8Gbps。Pipeline ADC ×16はJESD204B不使用、
パラレルIF (14bit × 100MHz = 1.4Gbps/ch × 16 = 22.4Gbps)。HDIO 88pinで十分収容。

**6bit Flash ADCでhard decisionが可能な理由**:
- GKP格子点判定は `round(q/√π) mod 2` — 閾値比較のみ
- √π間隔 ≈ 1.77に対し、6bit (64レベル) で分解能0.06十分
- δの符号判定（格子点の左右どちら）も6bitで可能
- soft info (confidence) のみ14bit精度が必要 → 低速パスで処理

### 2.3 FPGA処理の内訳 — 高速パス

```
■ 設計ベースライン: 400MHz (Versal PL domain, 2.5ns/cycle)

高速パス (Flash ADC 6bit入力, LUT化でtiming closure保証):
  Cycle 1 (2.5ns): Flash ADCデータ取得 (LVDS→PL register)
  Cycle 2 (2.5ns): 6bit→6bit LUT (64エントリROM: q→grid判定+bit値) ← DSP不使用
  Cycle 3 (2.5ns): 基底角度テーブルルックアップ + byproduct加算 (LUT)
  Cycle 4 (2.5ns): DAC書込み (パラレルIF)
  Cycle 5 (2.5ns): 出力レジスタ確定
  合計: 5 cycles × 2.5ns = 12.5ns
  ※乗算(q×1/√π)をLUT化: 6bit入力64点→事前計算ROM。timing closure容易

  FF-1合計(設計ベースライン 400MHz): TIA 3ns + ADC 3ns + FPGA 12.5ns + DAC 5ns + EOM 3ns = **26.5ns ≈ 27ns → 3モード遅延**

■ 楽観ケース: 500MHz (Versal PL domain, 2ns/cycle)

  Cycle 1-4: 各2ns、合計4 cycles × 2ns = 8ns
  FF-1合計(楽観ケース 500MHz): TIA 3ns + ADC 3ns + FPGA 8ns + DAC 5ns + EOM 3ns = **22ns → 2-3モード遅延** (旧21nsは内訳計算と不一致だったため22nsに修正)
  ※ADCは500MHzケースでも3ns維持（デバイス物理遅延は変わらない）。旧値2nsはデバイス仕様外。

  **500MHz timing closure検証計画**:
  - Versal PL LUT6伝搬遅延: typ 0.8ns, worst 1.5ns (@slow corner, 0.85V, 100°C)
  - 2段LUT (Cycle 2+3): worst 3.0ns > 2ns/cycle → **worst corner違反リスクあり**
  - 対策: (a) Phase -1 T11でVivado合成+P&R実施、setup slack確認
  - (b) worst corner不合格時: 400MHz設計ベースラインで続行
  - **Phase -1 Go基準**: 500MHz setup slack ≥ 0.3ns (typ corner)。未達時400MHzで設計続行。

低速パス (Pipeline ADC 14bit入力, 非クリティカル):
  Cycle 1-3 (6ns): δ計算 + exp(-δ²/2σ²) LUT → confidence値
  → Stage 2 バッファへ出力 (QECサイクル単位で蓄積)
```

**変更点**: soft info計算を高速パスから分離。hard decisionのみ設計ベースライン(400MHz)5 cycle / 楽観ケース(500MHz)4 cycleで完了。

### 2.4 レイテンシ vs TDMクロック (Flash ADC構成, 設計ベースライン400MHz)

| TDMクロック | T_clk | FF-1レイテンシ(設計ベースライン) | 遅延モード数 | 判定 |
|-----------|-------|-------------|-----------|------|
| 10MHz | 100ns | 27ns | 0.27 → **0** | 即時適用可能 |
| 50MHz | 20ns | 27ns | 1.35 → **1** | 1モード先を変調 |
| **100MHz** | **10ns** | **27ns** | **2.7 → 3** | **3モード先を変調(mode k+3に適用)** |
| 500MHz | 2ns | 27ns | 13.5 → **14** | 14モード先（要設計変更） |

**100MHzクロック時: 設計ベースライン(400MHz) 3モード遅延。楽観ケース(500MHz) 2-3モード遅延。**

**モードスロット内割り当て**: 10ns TDMスロット = パルスOPA照射 3ns (t=0-3ns) + ホモダイン測定窓 7ns (t=3-10ns)。
Flash ADC (1.5GSPS) は7ns窓内に10-11サンプル取得。TIA整定時間(0.7ns)後の有効測定窓は~6ns。

**タイミング注記**: ADCサンプル完了がモードスロット末尾(t≈9ns)の場合、
設計ベースライン27ns処理後t=36nsとなりmode k+2開始(t=20ns)に間に合わない。
設計ベースライン: 3モード遅延(mode k+3に適用)で確実動作。
楽観ケース(500MHz): 22ns処理でも2モード動作は境界的。保守的に3モード遅延を想定。
**モード境界タイミングハザード対策**:
worst case (ADC t=9ns + FF 27ns = t=36ns) ではmode k+2開始(t=20ns)に16ns超過。
設計ベースライン(400MHz): 3モード遅延(mode k+3に適用)で確実動作。
性能影響: macronode 4モード中2モードが固定基底のため、3モード遅延でも
output_Bモードへの適応基底適用が間に合う(Menicucci 2014構造で保証)。
Phase -1実測で500MHz動作+2モード動作可能と確認された場合、性能向上オプション。
Menicucci macronode latticeでは各macronode内4モードのうち2モードは適応不要であり、
3モード遅延でも設計制約内。(根拠: Menicucci 2014, PRL 113, 130501 — macronodeの
input_A/input_Bモードは固定X基底測定であり基底選択FF不要。output_A/output_Bのみ適応必要。
よってFF-1は全モードの半分にのみ適用、遅延スケジューリングに2モード分の余裕が確保される。)
---

## 3. FF-2: Byproduct補正（パウリフレーム追跡）

### 3.1 概要

測定型量子計算では、各測定結果に依存するパウリbyproductが蓄積する。これをリアルタイムで追跡し、最終結果から差し引く。

### 3.2 レイテンシ要件

```
表面符号1 QECサイクル: ~7μs (d=7, 98 modes/round × 7 rounds = 686 modes × 10ns)

パウリフレーム追跡:
  入力: GKPデコーダからのビット値 (0 or 1) × N_data_qubits
  処理: ルックアップテーブル更新 (XOR演算)
  出力: 累積パウリフレーム

  レイテンシ: <50ns (FPGA LUT, 余裕十分)

**Tゲートパイプライン制約**:
  MWPMデコーダ(510ns) + frame更新(50ns) = 560ns。
  クリフォードゲート: Pauli frame deferral可能 → タイミング制約なし。
  **Tゲート**: frame確定が必須。前QECサイクル終了後560ns以降のみ実行可能。
  → Tゲート最小間隔 = T_QEC + 560ns ≈ 7.4μs (QECサイクル6.86μs + デコーダ560ns)
  → magic state蒸留パイプラインはこの制約内でスケジューリングすること。
```

---

## 4. GKPデコーダのレイテンシ詳細

### 4.1 2段デコーダアーキテクチャ

```
ホモダイン出力 q_meas
    │
    ▼
[Stage 1: GKP内部デコーダ] ← 18.5ns (TIA 3ns + ADC 3ns + FPGA 12.5ns, FF-1内に含む, 設計ベースライン400MHz)
    │  q_grid = round(q_meas / √π) × √π
    │  δq = q_meas - q_grid
    │  bit = q_grid mod 2√π == 0 ? 0 : 1
    │  confidence = exp(-δq²/2σ²)
    │
    ├── bit値 → FF-1 (基底選択) : 27ns total (設計ベースライン400MHz, Flash ADC + パラレルDAC)
    │
    └── confidence → Stage 2 (表面符号デコーダ): buffered
            │
            ▼
[Stage 2: 表面符号デコーダ (ソフト情報入力)]
    │  1 QECサイクル分のconfidence値を蓄積 (~7μs分, d=7)
    │  重み付きUnion-Find: cluster growth rate ∝ confidence_i
    │
    │  レイテンシ: <500ns (Versal AIエンジン利用)
    │
    ▼
論理qubit値 + 論理パウリ補正
```

### 4.2 Stage 2のFPGAリソース

| リソース | Stage 1 (GKP) | Stage 2 (表面符号) | 合計 | VE2302搭載 | 使用率 |
|---------|---------|---|---------|---|---------|
| LUT | 5K | 70K | 75K | 350K | 21% |
| DSP | 20 | 80 | 100 | 700 | 14% |
| BRAM | 1KB | 1.5MB | ~1.5MB | 1.5MB (12Mb) | ~100% (d=7) |
| AIエンジン | 0 | 4 | 4 | 34 | 12% |

**VE2302 1枚で収容可能（d≤5）。** d=7はVE2802必須（BRAM 3MB、使用率~50%）。詳細は`08_decoder.md` §3.3参照。

---

## 5. QD制御のタイミング

Step B/C (QD支援GKP) では、QDトリガのタイミング制御も必要:

```
TDMクロック (100MHz)
    │
    ├── t=0: mode_k ホモダイン測定
    │
    ├── t=10ns: mode_k+1 (通常TDMモード)
    │
    ├── t=20ns: mode_k+2 (通常TDMモード)
    │
    └── t=N×10ns: mode_k+N (QD注入対象モード)
                    │
                    ├── QDトリガ: t=N×10ns - 5ns (事前トリガ)
                    │   electrical trigger → QD emission ~100ps後
                    │
                    └── QD光子がTDMストリームに合流
                        ├── 時間同期: ±100ps (電気トリガジッター)
                        ├── 位相同期: マスターレーザからの参照で補正
                        └── スペクトルフィルタ: FP cavity (step B参照)
```

QDトリガのレイテンシ要件:
- 電気トリガ精度: ±100ps (標準的パルスジェネレータで達成可能)
- FPGA→QDドライバ: <5ns
- **QDトリガはTDMクロックに同期してプログラム的に配置。FF-1とは独立。**

---

## 6. 全光学フィードフォワード（将来構想）

Phase 2.5以降の目標: 電気的フィードフォワードを排除し、全光学で実行。

| 方式 | レイテンシ | 根拠 | TRL |
|------|----------|------|-----|
| 電気的FF (Phase 0-1) | **27ns** (設計ベースライン) / 22ns (楽観) | 本設計 | 6 |
| ハイブリッドFF (Phase 2) | ~10ns | 光スイッチ + 最小電子回路 | 3 |
| **全光学FF (Phase 2.5+)** | **<1ns** | 非線形光学ゲート | 2 |

全光学FFが実現すれば、TDMクロックを**1GHz以上**に引き上げ可能。論理ゲートレートが10倍に向上。

---

## 7. タイミング図（1 QECサイクル）

```
t(ns)  0    10   20   30   ... 140  ... 980
       │    │    │    │        │        │
mode:  k   k+1  k+2  k+3     k+14    k+98
       │    │    │    │        │        │
Hom:   ▓    ▓    ▓    ▓   ...  ▓   ...  ▓    ← ホモダイン測定
       │    │    │    │        │        │
GKP:   ▒    ▒    ▒    ▒   ...  ▒   ...  ▒    ← GKPデコード(Stage1)
       │         │    │        │        │
FF-1:  ├──27ns──────┤  │        │        │    ← 基底角度設定(設計ベースライン400MHz, mode k+3に適用)
       │              │        │        │
       └──────────────┴────────┴────────┘
       |<--  1 syndrome round = 14 steps × 7 cols = 98 modes = 980ns  -->|
       |<---  d=7: 7 rounds = 686 modes = 6.86μs ≈ 7μs  --->|
                                                         │
                                                    Stage2: 表面符号デコード
                                                    (<500ns)
                                                         │
                                                    次QECサイクル開始
```

---

*本文書はCV方式のフィードフォワード制御チェーンの全レイテンシバジェットを定義し、100MHz TDMクロックでの動作可能性を実証したものである。TI ADC06D1500(6bit低レイテンシADC)+Pipeline ADC(14bit)並列構成+パラレルDAC(MAX5898)により設計ベースライン(400MHz)27nsレイテンシ（3モード遅延）、楽観ケース(500MHz)22ns（2-3モード遅延）を達成。macronode latticeの構造上許容可能。*
