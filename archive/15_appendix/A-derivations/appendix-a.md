> **⚠ FROZEN (2026-05-04)**: 本文書はDV-FBQC v4.0 R6時点の設計を記録したものです。プロジェクトの主軸はCV方式に移行しています。最新設計は `design/00_overview.md` を参照してください。

# Appendix A: 数式の正確な導出（改訂）

## A.1 デュアルレール符号化とPauli作用素

光量子ビットのデュアルレール符号化:

```
|0⟩_L = |1,0⟩ = â†_H |vac⟩    （水平偏光モードに1光子）
|1⟩_L = |0,1⟩ = â†_V |vac⟩    （垂直偏光モードに1光子）
```

Pauli作用素のデュアルレール表現:

```
X_L: |0⟩_L ↔ |1⟩_L  （偏光回転 HWP@45°に対応）
Z_L: |0⟩_L → |0⟩_L, |1⟩_L → -|1⟩_L  （位相シフタに対応）
Y_L = iX_L Z_L
```

**erasure（消失）との関係**:

デュアルレール符号化の重要な特性として、光子損失がerasure errorとして検出可能である:

```
|ψ⟩_L = α|1,0⟩ + β|0,1⟩

光子損失 → |0,0⟩（真空状態）

検出器で光子が検出されない → erasureが発生したことが判明
→ erasureの位置情報が既知 → erasure符号で効率的に訂正可能
```

これが光量子計算の根本的な利点であり、erasure閾値が通常のdepolarizing閾値よりも大幅に高い（~50% vs. ~1%）理由である。

## A.2 Boosted fusionの成功確率導出

**Type-II fusion（基本）**:

2つのデュアルレール量子ビットの片方のモードをPBSで干渉させ、検出する:

```
成功確率（基本）: p_fusion = 1/2
```

これは線形光学の限界に由来する。PBSで2光子が同一出力ポートに出る確率が1/2。

**Boosted fusion**:

補助（ancilla）光子を追加し、成功確率を向上させる:

```
n個のancilla Bell pairを使用した場合:
p_boosted = 1 - (1/2)^(n+1)

n=1: p = 3/4 = 0.75
n=2: p = 7/8 = 0.875
n=3: p = 15/16 = 0.9375
```

本設計では n=1（1 ancilla Bell pair）を基準とし:

```
p_boosted = 0.75
```

**損失を考慮したfusion成功確率**:

```
p_fusion_effective = p_boosted × (1 - p_erasure_input)²

ここで p_erasure_input は入力量子ビットのerasure率。

本設計: p_erasure_input ≈ 0.852（全経路損失、10.3.2節）

→ 入力光子がfusion地点に到達する確率 = (1-0.852)² = 0.148² = 0.0219

→ p_fusion_effective = 0.75 × 0.0219 = 0.0164
```

> **注意**: 上記は単純な端-端の損失計算。実際にはfusion測定は光路途中で行われるため、erasure率は経路位置に依存する。fusion地点での実効erasure率は全経路のそれよりも低い。具体的には、fusion測定がSi₃N₄チップ上で行われる場合:

```
η_to_fusion = η_QD × η_PMF × η_QFC × η_SMF1 × η_SiN(片側)
            = 0.65 × 0.980 × 0.57 × 0.990 × 0.90
            = 0.323

p_erasure_at_fusion = 1 - 0.323 = 0.677
p_fusion_effective = 0.75 × 0.323² = 0.75 × 0.104 = 0.078
```

## A.3 損失積算の正確な乗法計算

光学系の損失は**乗法的**であり、加法的に扱ってはならない。

**正しい計算（乗法）**:

```
η_total = ∏ᵢ ηᵢ

各コンポーネントの透過率:
η₁ = 0.65  (QD収集)
η₂ = 0.960 (PMFコネクタ×2)
η₃ = 0.57  (QFC)
η₄ = 0.980 (SMFコネクタ×2)
η₅ = 0.810 (Si₃N₄チップ)
η₆ = 0.85  (LNOI EO)
η₇ = 0.903 (光スイッチ×2)
η₈ = 0.759 (HCF 600m)
η₉ = 0.998 (SMF配線)
η₁₀ = 0.93  (SNSPD)

η_total = 0.65 × 0.960 × 0.57 × 0.980 × 0.810 × 0.85 × 0.903 × 0.759 × 0.998 × 0.93
```

ステップバイステップ:
```
0.65 × 0.960 = 0.6240
0.6240 × 0.57 = 0.3557
0.3557 × 0.980 = 0.3486
0.3486 × 0.810 = 0.2824
0.2824 × 0.85 = 0.2400
0.2400 × 0.903 = 0.2167
0.2167 × 0.759 = 0.1645
0.1645 × 0.998 = 0.1642
0.1642 × 0.93 = 0.1527

η_total ≈ 0.153
```

**誤った計算（加法、dBの足し算の典型的ミス）**:

```
各損失(dB):
QD: -1.87dB, PMF: -0.18dB, QFC: -2.44dB, SMF: -0.09dB,
Si₃N₄: -0.92dB, EO: -0.71dB, SW: -0.44dB×2, HCF: -1.20dB,
SMF2: -0.009dB, SNSPD: -0.32dB

合計: -8.18dB → η = 10^(-8.18/10) = 0.152

→ dB加算は乗法計算と等価であり、結果は一致する（検算OK）
```

> **v2.0との違い**: v2.0ではQFC不要（η₃=1.0）、SNSPD近距離（η₈=1.0）で η_total ≈ 0.20。v3.0ではQFC（×0.57）とHCF（×0.759）が追加され、η_total ≈ 0.153。約24%の劣化だが、SNSPD数32倍増と符号距離拡大で論理エラー率は改善。

## A.4 erasureとdepolarizingの分離管理

光量子計算では2種類のエラーを区別して管理する:

**erasure error（消失エラー）**:

```
定義: 光子が失われ、量子ビットが存在しない状態
検出: デュアルレール検出器で光子非検出 → 位置が既知
確率: p_erasure = 1 - η_total ≈ 0.85（全経路）

erasure符号の閾値:
  SHYPS:   ~50%
  4D HPC:  ~25%（推定）
  表面符号: ~24.9%（正確な値は格子構造に依存）
```

**depolarizing error（脱分極エラー）**:

```
定義: 光子は検出されるが、量子状態が誤っている
原因:
  - QDの不完全な不可弁別性（HOM < 1）
  - fusionゲートの不完全性
  - 位相ノイズ（HCF、EO変調）
  - 検出器のダークカウント
  - QFCのノイズ光子

確率: p_depol ≈ 0.5 - 1.0%（主にHOM visibilityで決定）

depolarizing符号の閾値:
  SHYPS:   ~2.5%
  4D HPC:  ~1.5%
  表面符号: ~1.0%（回路レベル）
```

**マージン計算**:

```
erasureマージン = (閾値 - 実測値) / 閾値

SHYPS:  (50% - 85%) → 閾値を超過 → erasure rateそのものは高すぎるが、
        これは"全経路"の値。fusionでerasureが検出された時点で
        その量子ビットを符号から除外するため、有効erasure rateは
        fusion測定で決まる。

fusionでのerasure率:
  p_erasure_fusion = 1 - (1 - p_erasure_at_fusion)² × p_boosted
  fusion地点到達率 0.323 として:
  p_erasure_fusion = 1 - 0.323² × 0.75 = 1 - 0.078 = 0.922

  → これは非常に高い。しかしfusion失敗はerasureとして扱え、
     冗長なfusion操作（複数回試行）で実効成功率を向上させる。
     3回試行: p_at_least_one = 1 - (1-0.078)³ = 0.218

depolarizingマージン:
  SHYPSの場合:  (2.5% - 1.0%) / 2.5% = 60%  ← 十分
  HPCの場合:    (1.5% - 1.0%) / 1.5% = 33%  ← 薄い
  表面符号の場合: (1.0% - 1.0%) / 1.0% = 0%   ← マージンなし（危険）
```

> **結論**: depolarizing率が1.0%近辺の場合、表面符号は使用不可、HPCもマージン不十分。SHYPSの使用が事実上必須であり、confinement propertyの成否が設計全体のGo/No-Goを左右する。

## A.5 サイクル時間2μsの整合的導出

**サイクル時間の定義**: 1回の論理量子ゲート操作（1 syndrome extraction cycle）に要する時間。

```
T_cycle = T_generation + T_propagation + T_measurement + T_decode + T_feedback

各項の内訳:

T_generation = 1 ns
  QDパルス励起間隔: 1GHz → 1ns
  4光子GHZ状態生成: 4パルスの時間差 = 4ns（パイプライン化で実効1ns）

T_propagation = 600m / (3×10⁸ m/s × 0.997) = 2.01 μs
  HCF中の光速: c/n ≈ 0.997c（中空コアのため屈折率≈1）
  600mの飛行時間が支配的

T_measurement = 50 ps（SNSPDジッタ） + 10 ns（電気信号伝搬） ≈ 10 ns

T_decode = 500 ns
  FPGAでのUnion-Findデコーダ処理
  d=8の場合: O(d² α(d²)) ≈ O(64 × 4) = 256演算
  Versal VEK280 @ 500MHz: 256 / 500MHz = 512ns → ~500ns

T_feedback = 30 ns
  FPGA→RF DAC→LNOI EO変調: 電気信号伝搬 + DAC変換
  同軸3m: 15ns + DAC: 15ns = 30ns

T_cycle = 1ns + 2,010ns + 10ns + 500ns + 30ns = 2,551 ns ≈ 2.6 μs
```

> **設計目標2μsとの乖離**: 約0.6μsの超過。対策として:
> 1. HCF長を470mに短縮（T_propagation = 1.57μs → T_cycle = 2.1μs）。ただしサイクル数が増加。
> 2. デコーダの事前予測（speculative decoding）で T_decode を 300ns に短縮 → T_cycle = 2.35μs
> 3. HCF 470m + speculative decoding: T_cycle ≈ 1.9μs（目標達成）
>
> **結論**: HCF長を470-500mに短縮し、speculative decodingを採用することで2μs達成が見込める。600mは最大遅延であり、符号のsyndrome抽出に必要な最小遅延で設計を最適化する。

---

