# Taros パラメータレジストリ (Single Source of Truth)

**Document ID**: PQC-PARAMS-v1.0
**Last Updated**: 2026-05-06
**Status**: 確定版

> 本文書はプロジェクト全体のパラメータ定義の単一真実源（SSOT）です。
> 他の文書がパラメータ値を引用する場合、本文書を参照元とすること。
> CV方式の詳細パラメータは `design/00_overview.md` 正規パラメータ表を参照。

---

## 1. Phase 定義（統一版）

プロジェクト全体で統一するPhase番号と年代の対応表。

| Phase | 年代 | CV方式（主軸） | DV-FBQC方式（凍結） | 主要マイルストーン |
|-------|------|---------------|--------------------|--------------------|
| **-1** | 2026 | $3.08M, GKP実験+Stim検証 | — | Go/No-Go判定 |
| **0a** | 2027 Q1-Q2 | Taros Edu プロトタイプ (d=3) | — | QEC break-even |
| **0b** | 2027 Q3-Q4 | Taros Pro プロトタイプ (d=5) | — | 製品プロトタイプ |
| **1** | 2028 | Taros Max プロトタイプ (d=7) | Phase 1: 8ラック構成 | 製品設計完了 |
| **2** | 2029-2030 | 量産設計 (100台/年) | Phase 2: クライオPIC | 量産立ち上げ |
| **3** | 2030+ | WDM 20ch フルスペック | — | 高性能FTQC |

> **注**: archive/ 配下のDV方式文書では「Phase 0/1/2/3」が上記と異なる定義で使用されている場合があります。
> archive/のPhase定義は凍結されており、本表のCV方式列が正式です。

---

## 2. CV方式パラメータ（主軸）

`design/00_overview.md` の正規パラメータ表が正式値。以下は要約。

### 2.1 光源・スクイージング

| パラメータ | 記号 | 正規値 | 根拠文書 |
|-----------|------|--------|----------|
| 生成スクイージング | σ_gen | 13 dB | design/02_opa-source |
| ポンプ波長 | λ_pump | 775 nm (SHG from 1550nm) | design/02_opa-source |
| 信号波長 | λ_signal | 1550 nm | design/02_opa-source |
| TDMクロック | f_TDM | 100 MHz | design/03_tdm-cluster |

### 2.2 損失・ノイズ

| パラメータ | 記号 | Phase 1 (離散) | Phase 2+ PIC (現実的) | Phase 2+ PIC (理論限界) | 根拠文書 |
|-----------|------|---------------|----------------------|------------------------|----------|
| 全光学損失 | L_total | 0.39 dB | 0.27 dB | 0.15 dB | design/06_noise-budget |
| 全光学透過率 | η_total | 0.914 | 0.940 | 0.966 | design/06_noise-budget |
| 実効スクイージング | σ_eff | 8.8 dB | 9.5-10.2 dB | 10.9 dB | design/06_noise-budget |
| 物理エラー率 | p_phys | 7.5×10⁻³ | 2-4×10⁻³ | 9.9×10⁻⁴ | design/13_performance |

### 2.3 QEC性能

| パラメータ | 記号 | 正規値 | 条件 | 根拠文書 |
|-----------|------|--------|------|----------|
| 閾値 (soft-info MWPM) | p_th_eff | 1.5% | Noh-Chamberland 2022 | design/08_decoder |
| 閾値 (保守 hard MWPM) | p_th | 0.59% | 文献値 | design/13_performance |
| 論理エラー率 d=7 (MWPM, Phase 2+ PIC理論限界) | p_L | 5.7×10⁻⁷ | L=0.15dB, Δ=0, QE=99% | design/13_performance |
| 論理エラー率 d=7 (MWPM, Phase 2+ PIC現実的) | p_L | ~7×10⁻⁵ | L=0.27dB, non-loss noise込み | design/06_noise-budget |
| デコーダ遅延 (MWPM製品) | t_dec | 510 ns | @400MHz | design/08_decoder |
| デコーダ遅延 (UF実験) | t_dec | 350 ns | @400MHz | design/08_decoder |
| フィードフォワード (FF-1) | t_FF | 27 ns | @400MHz | design/07_feedforward |

### 2.4 製品仕様

| パラメータ | Taros Edu | Taros Pro | Taros Max | 根拠文書 |
|-----------|-----------|-----------|-----------|----------|
| 表面符号距離 | d=3 | d=5 | d=7 | design/00_overview |
| 重量 | ~4.3 kg | ~7.5 kg | ~9.7 kg | design/00_overview |
| 消費電力 | ~100 W | ~109 W | ~112 W | design/00_overview |
| 原価 | $53K | $75K | $95K | analysis/bom |
| 販売価格 | $90K | $120K | $170K | analysis/bom |

---

## 3. DV-FBQC方式パラメータ（凍結・参考）

> **⚠ 凍結**: 以下の値は DV-FBQC v4.0 R6 (2026-05-04) 時点で凍結されています。
> archive/ 配下の文書を参照する際のリファレンスとしてのみ使用してください。

### 3.1 光源

| パラメータ | 記号 | R6最終値 | 注記 |
|-----------|------|----------|------|
| QD材料 | — | GaAs (925nm) / InP (1550nm) | archive/02_physical-layer/quantum-dots/ |
| QD収集効率 | η_QD | 0.57 (現状) → 0.85 (Phase 1目標) | **注意: 文書間で0.57/0.60/0.65/0.85が混在** |
| QD繰り返し周波数 | f_QD | 76 MHz (Ti:Sa同期) | archive/04_hardware/rack1-source |
| QFC変換効率 (end-to-end) | η_QFC | 0.57 (Phase 0) → 0.75-0.82 (R6目標) | **注意: Phase 1で0.57 vs 0.87が混在** |
| QFCポンプ波長 | λ_pump_QFC | 2,290 nm | エネルギー保存: 1/925-1/1550=1/2290 |
| Boosted fusion成功率 | P_fusion | 97% (n=4) | **注意: n=1/2/4の3値が文書間で混在** |

### 3.2 損失バジェット

| パラメータ | 記号 | R6最終値 | 注記 |
|-----------|------|----------|------|
| HCF 600m損失 | L_HCF | 0.07 dB (@0.11dB/km) | **注意: 1.2dBは誤記** |
| SNSPD検出効率 | η_SNSPD | 95% (@2.5K) / 98% (@0.8K) / 99.7% (WI-SNSPD) | Phase/技術依存 |
| 全経路透過率 | η_total | ~14.4% (Phase 0) | 符号閾値比較には使用不可（ヘラルド後損失を使用） |
| ヘラルド後透過率 | η_post-herald | ~84.7% (Phase 0改善前) | 符号関連erasure率の計算に使用 |
| ヘラルド後erasure率 | ε_herald | ~30.4% (Phase 0) | **注意: ~21%は改善後の値で誤適用** |

### 3.3 QEC符号

| 符号 | パラメータ | Erasure閾値 | 優先度 (R6) | 注記 |
|------|-----------|-------------|-------------|------|
| GB [[144,12,12]] | Primary | **未計算（要Stim実行）** | Primary (R4で昇格) | 閾値・性能データ欠如 |
| GB [[72,12,6]] | 最小構成 | **未計算** | Primary (R6追加) | Phase 0-1向け |
| SHYPS [[400,25,8]] | Secondary | ~50% | Secondary (R4でPrimaryから降格) | **注意: 24.9%は表面符号の値の誤適用** |
| 4D HPC | — | ~22-25% / ~30% | — | **注意: 2値が混在** |
| 表面符号 | Tertiary | ~24.9% | Tertiary | Bartolucci+ 2023 |

### 3.4 弾道RSG成功確率

| 透過率 η | 成功確率 P(k≥4) | 注記 |
|----------|----------------|------|
| 0.5 | 0.344 | Phase 1相当 |
| 0.7 | **0.744** | Phase 2相当。**旧値0.930は誤り** |
| 0.85 | 0.953 | Phase 3相当 |

---

## 4. 共通コンポーネントパラメータ

DV/CV方式で共通の物理コンポーネントの正規値。

| コンポーネント | パラメータ | 正規値 | 注記 |
|--------------|-----------|--------|------|
| HCF (NANF) | 損失 | 0.11 dB/km | Lumenisity 2023 |
| PMF | 損失 | 0.35 dB/km | 標準PMF @1550nm |
| LNOI EO MZM | 挿入損失 | 0.3 dB (arm loss) | DC arm + RF core |
| Si₃N₄ PIC | 導波路損失 | 0.01 dB/cm | Ligentec ANT |
| InGaAs PD | 量子効率 | 99% (設計目標) / 95% (市販品) | QE≥98%必須 |

---

## 5. コスト正式文書（3文書限定）

| 文書 | 内容 | 最終更新 |
|------|------|----------|
| `analysis/bom.md` | 製品BOM（原価・販売価格・TCO） | 2026-05-05 |
| `analysis/development-cost-summary.md` | 開発費全体（Phase -1~2: $5.78M） | 2026-05-06 |
| `analysis/phase-minus1-execution.md` | Phase -1 詳細実行計画 ($3.08M) | 2026-05-05 |

> 他の文書がコスト数値を引用する場合、上記3文書のいずれかを参照元として明記すること。

---

## 6. 文書体系

| ディレクトリ | 状態 | 内容 |
|-------------|------|------|
| `design/` | **生きた文書（正式）** | CV方式 Taros Portable 設計 |
| `analysis/` | **生きた文書（正式）** | コスト・リスク・ロードマップ |
| `experiments/` | **生きた文書（正式）** | 実験計画・数値検証 |
| `fallback/` | **参考（DV代替）** | DV-FBQC v5.0 Desktop フォールバック |
| `archive/` | **凍結（レガシー）** | DV-FBQC v4.0 R6 設計（2026-05-04凍結） |

---

*本文書はプロジェクトの全パラメータ定義を一元管理するためのレジストリである。パラメータの変更は本文書を起点とし、関連文書に伝播させること。*
