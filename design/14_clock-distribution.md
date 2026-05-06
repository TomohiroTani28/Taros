# クロック分配・同期設計書

**Document ID**: PQC-CV-CLK-v1.0
**Last Updated**: 2026-05-06
**Status**: Draft
**前提**: 100MHz TDMクロックを全サブシステムで同期

---

## 1. 概要

TDM macronode方式では、100MHz (10ns周期) のクロックで以下の5サブシステムを同期する必要がある:

1. **OPAパルストリガ** (Option B: パルスポンプレーザ100MHz)
2. **ADCサンプルクロック** (Flash 6bit + Pipeline 14bit)
3. **FPGA処理クロック** (400MHz内部PLL生成)
4. **DAC出力タイミング** (FF制御信号)
5. **LO位相設定** (ホモダイン検出基準位相)

クロック間の相対ジッタが大きいと、ADCサンプリングがTDMモード境界を跨ぎ、
モード間クロストークを引き起こす。10ns周期に対し±0.5nsのガード帯域を確保するため、
全パスで**相対ジッタ < 20ps RMS**を要求する。

---

## 2. マスタークロック源

| パラメータ | 仕様 | 根拠 |
|-----------|------|------|
| タイプ | VCXO (電圧制御水晶発振器) | 低ジッタ、低コスト |
| 周波数 | 100MHz | TDMクロック = 1/T_mode |
| 位相ノイズ | < −155 dBc/Hz @ 100kHz offset | 統合ジッタ < 50fs (12kHz-20MHz) |
| 出力 | LVPECL差動 | ファンアウトバッファ入力 |
| 候補部品 | SiTime SiT9501 or Abracon ASFL1 | $5-15, 低ジッタVCXO |

**Option B パルスOPA構成**:
- マスタークロック100MHz → パルスレーザトリガ (電気的同期)
- パルスレーザのrep-rate = マスタークロック (外部トリガモード)
- レーザjitter < 1ps RMS (光パルスタイミング vs 電気トリガ)

---

## 3. クロック分配ツリー

```
[100MHz VCXO]
    │ LVPECL
    ▼
[ファンアウトバッファ: TI CDCLVD1208 (1:8, additive jitter < 50fs)]
    │
    ├── Ch1 → パルスレーザトリガ (100MHz)
    │         遅延調整: プログラマブル遅延線 (0-10ns, 10ps分解能)
    │
    ├── Ch2 → Flash ADC サンプルクロック (100MHz → ADC内部PLL 1.5GHz)
    │         位相調整: FPGA IDELAYE3 (78ps/tap × 512tap)
    │
    ├── Ch3 → Pipeline ADC サンプルクロック (100MHz → **外部PLL 400MHz生成**)
    │         注: ADS5474はADC内部divider非搭載。外部PLL (TI LMX2594等)で100MHz→400MHz逓倍必要
    │
    ├── Ch4 → FPGA PL REF_CLK (100MHz → MMCM 400MHz PL clock)
    │         FPGA内部PLL: ジッタ < 2ps RMS (Versal MMCM spec)
    │
    ├── Ch5 → DAC更新クロック (100MHz)
    │
    ├── Ch6 → LO位相制御 DAC (100MHz, EO comb駆動同期)
    │
    └── Ch7-8 → 予備 / WDM拡張用
```

---

## 4. ジッタバジェット

| パス | ジッタ源 | 寄与 (RMS) | 累積 |
|------|---------|-----------|------|
| VCXO | 発振器位相ノイズ | 50fs | 50fs |
| ファンアウト | CDCLVD1208 additive | 50fs | 71fs |
| PCBトレース | 差動ペア伝搬 (10cm) | 20fs | 74fs |
| **OPAパルストリガ** | レーザ外部トリガjitter | 1ps | **1.0ps** |
| **ADCサンプル** | ADC aperture jitter (ADC06D1500) | 0.2ps | **0.2ps** |
| **FPGA MMCM** | PLL jitter | 2ps | **2.0ps** |

**最悪ケース相対ジッタ** (OPA trigger vs ADC sample):
√(1.0² + 0.2²) ≈ **1.02ps RMS** → 10ns周期の0.01%。**仕様20ps RMSに対し20倍マージン。**

---

## 5. ADCサンプル位相アライメント

### 5.1 問題

ADCは各TDMモード (10ns) の中央でサンプリングすべき。パルスレーザの光パルスと
ADCサンプリング窓のタイミングオフセットが1ns以上あると、隣接モードの光が混入する。

### 5.2 対策

1. **起動時キャリブレーション**: パルスOPAのトリガ遅延を調整し、
   ホモダイン出力のピーク位置とADCサンプリングを合わせる
2. **FPGA IDELAYE3**: 78ps/tap のプログラマブル遅延で微調整
3. **動作中モニタリング**: ADC出力の隣接モード相関をFPGAで計算し、
   遅延を自動追従 (Phase -1 FW実装)

---

## 6. FPGA内部クロックドメイン

```
REF_CLK 100MHz → MMCM → 400MHz PL domain (設計ベースライン)
                       → 100MHz AXI domain
                       → 200MHz DDR4 controller (使用時)

全PL FFs: 400MHz同期 (CDC不要)
ADC I/F: LVDS → IOB register (100MHz) → 400MHz domain crossing (2-FF同期)
DAC I/F: 400MHz → IOB register → パラレルバス出力
```

---

## 7. Phase -1 検証項目

| 項目 | 測定方法 | Go基準 |
|------|---------|--------|
| VCXO→ADC相対ジッタ | オシロスコープ TIE測定 | < 5ps RMS |
| パルスレーザ→ADCサンプル位相 | ADC出力波形観測 | 位相マージン > 2ns |
| FPGA MMCM出力ジッタ | Vivado timing report | setup slack > 0.5ns |
| モード間クロストーク | 隣接モード相関測定 | < −30dB |

---

*本文書はTDM 100MHzクロックの分配・同期設計を定義する。全サブシステム間の相対ジッタ < 20ps RMSを
確保し、TDMモード間クロストークを防止する。Phase -1で実験的に検証予定。*
