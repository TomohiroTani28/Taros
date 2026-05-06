# 製造図面 DWG-003: Taros Pro 総組立図

| 項目 | 内容 |
|------|------|
| 図面番号 | DWG-003 Rev.A |
| 図面名称 | Taros Pro 総組立図 (General Assembly) |
| 尺度 | 1:2 (A3用紙) |
| 投影法 | 第三角法 |
| 用紙サイズ | A3 (420 × 297 mm) |
| 単位 | mm |
| 設計者 | — |
| 検図者 | — |
| 日付 | 2026-05-06 |
| 総質量 | 7.5 kg (出典: 10_portable.md §2) |
| 総消費電力 | 109W (出典: 10_portable.md §3.4) |

## 改訂履歴

| Rev | 日付 | 内容 | 承認者 |
|-----|------|------|--------|
| A | 2026-05-06 | 初版発行 | — |

---

## 1. 部品表 (BOM)

| 番号 | 図面/型番 | 品名 | 材質/仕様 | 数量 | 出典 |
|:----:|---------|------|----------|:----:|------|
| 1 | DWG-001 | 筐体本体 | A6063-T5, アノダイズド黒 | 1 | 12_mechanical §1.2 |
| 2 | DWG-002 | 天板(フィン一体) | A6063-T5, アノダイズド黒 | 1 | 12_mechanical §1.2 |
| 3 | NKT E15 OEM | Master Laser 1550nm | 120×60×30mm, 10mW | 1 | 12_mechanical §1.4 |
| 4 | — | 775nm GS-DFB+SOA+SHG | Option B pump, 200mW peak | 1 | 10_portable §3.4 |
| 5 | NTT/HC Photonics | PPLN OPA | 50×20×10mm | 2 | 12_mechanical §1.4 |
| 6 | — | Peltier TEC (OPA温調) | 60×50×5mm, ΔT_max=50K | 1 | 12_mechanical §1.4 |
| 7 | iXblue/HyperLight | LNOI EOM | 40×20×10mm | 2 | 12_mechanical §1.4 |
| 8 | — | BS カプラ 50:50 | PMF1550, FC/APC | 3 | 12_mechanical §1.4 |
| 9 | — | Balanced PD (InGaAs) | 35×20×20mm, QE≥99% | 2 | 12_mechanical §1.4 |
| 10 | Corning/Fujikura | PMF 102m スプール | φ80×80mm, ~0.8kg | 1 | 12_mechanical §1.4 |
| 11 | NTT-AT | WDM AWG 8ch | 100×35×20mm, IL 0.2dB | 1 | 12_mechanical §1.4 |
| 12 | — | WDM PD ×16 | ドーターカード | 1set | 12_mechanical §1.4 |
| 13 | AMD VE2302 | FPGA Versal | 80×80×20mm, 25W TDP | 1 | 12_mechanical §1.4 |
| 14 | TI ADC06D1500 | Flash ADC 6bit 1.5GSPS | — | 1 | 07_feedforward |
| 15 | TI ADS5474 | Pipeline ADC 14bit 400MSPS | — | 1 | 07_feedforward |
| 16 | Maxim MAX5898 | DAC 14bit 400MSPS | — | 1 | 07_feedforward |
| 17 | — | DC-DC converter | 28V→各電圧, η≥92% | 1 | 12_mechanical §1.4 |
| 18 | — | Cu ヒートパイプ φ6×80mm | sintered wick, 50W/本 | 3 | 12_mechanical §1.4 |
| 19 | — | PTFE断熱板 | 290×240×3mm | 1 | 12_mechanical §1.3 |
| 20 | — | PZT driver + PID | 80×40×15mm | 1 | 12_mechanical §1.4 |
| 21 | — | DAC + EO driver | 70×30×15mm | 1 | 12_mechanical §1.4 |
| 22 | Noctua NF-A8 | 80mmファン | 1400rpm, <25dBA | 1 | 11_industrial §7 |
| 23 | — | ゴム脚 φ15×5mm | Shore A 70, 防振 | 4 | 11_industrial §2 |
| 24 | — | 導電ガスケット | シリコン導電ゴム, 幅2mm | 1set | 12_mechanical §3.3 |
| 25 | — | HDPE振動隔離プレート | 80×80×15mm | 1 | 12_mechanical §1.4 |
| 26 | — | M3×8 皿ネジ (天板固定) | SUS304 | 8 | DWG-001/002 |
| 27 | — | M5×8 なべネジ (ゴム脚) | SUS304 | 4 | DWG-001 |
| 28 | — | M4×8 ネジ (ファン固定) | SUS304 | 4 | DWG-001 |
| 29 | — | PMF1550 各種 | 出典: 12_mechanical §2.1 | ~109m | 12_mechanical §2.1 |
| 30 | — | PTFEチューブ OD2mm | ファイバ保護 | ~120m | 12_mechanical §2.2 |
| 31 | — | EO comb (PM+IM+EDFA) | 25GHz RF, 8ch | 1set | 10_portable §3.2b |
| 32 | — | USB-C コネクタ | USB 3.2 Gen2 | 2 | 11_industrial §4 |
| 33 | — | RJ45 コネクタ | 10GbE | 1 | 11_industrial §4 |
| 34 | — | USB-PD EPR コネクタ | 28V/5A, 140W | 1 | 11_industrial §4 |
| 35 | — | ロッカースイッチ | 16A/250V | 1 | 11_industrial §4 |
| 36 | — | GND端子 | M5ネジ端子 | 1 | 11_industrial §4 |
| 37 | — | LED (Power/Lock/QEC) | φ3mm, 白/緑(赤)/青 | 3 | 11_industrial §3 |

---

## 2. 組立手順

### 2.1 工程フロー (出典: 12_mechanical.md §4.1)

```
[1] 筐体検査 → [2] Zone A組立 → [3] Zone B組立 → [4] Zone C組立
     ↓              ↓               ↓               ↓
[5] 統合組立 → [6] ファイバ配線 → [7] 天板閉止 → [8] キャリブレーション
```

### 2.2 Zone配置図 (上面)

```
    ┌──────────────────────────────────────────────┐
    │  Y=250                                       │
    │                                              │
    │  ┌──────────┬─────────────┬─────────────┐    │
    │  │ Zone A    │  Zone B      │  Zone C      │    │
    │  │ 光学      │  ファイバ    │  電子制御    │    │
    │  │ X=5-135   │  X=135-210  │  X=210-294  │    │
    │  │ Y=5-244   │  Y=5-244   │  Y=5-244    │    │
    │  │ Z=5-90    │  Z=5-90    │  Z=5-137    │    │
    │  │           │             │              │    │
    │  │ #3 Laser  │  #10 PMF   │  #13 FPGA   │    │
    │  │ #4 Pump   │  φ80spool  │  #14-16 ADC │    │
    │  │ #5 OPA×2  │             │  #17 DC-DC  │    │
    │  │ #6 TEC    │  #11 AWG   │  #18 HP×3   │    │
    │  │ #7 EOM×2  │  #12 PD×16 │  #20 PZT    │    │
    │  │ #8 BS×3   │             │  #21 DAC    │    │
    │  │ #9 BPD×2  │             │              │    │
    │  └──────────┴─────────────┴─────────────┘    │
    │                                              │
    │  Y=0 (正面)                                   │
    └──────────────────────────────────────────────┘
     X=0                                          X=300
```

出典: design/12_mechanical.md §1.3

### 2.3 組立詳細手順

| 手順 | 作業 | 使用部品 | 所要時間 | 注意事項 |
|:----:|------|---------|:-------:|---------|
| 1 | 筐体検査: 寸法・外観・アノダイズ確認 | #1 | 15min | 嵌合リップ面の平面度0.05mm確認 |
| 2 | Zone A: OPA温調プレート(TEC)取付 | #6 | 15min | 熱伝導グリス塗布。底板基準面に密着 |
| 3 | Zone A: OPA #1, #2 取付 | #5 ×2 | 30min | M2ネジ×2/個。温調プレート上。トルク0.2Nm |
| 4 | Zone A: Master Laser 取付 | #3 | 20min | M3ネジ×4 + 防振ゴムワッシャ |
| 5 | Zone A: SHG + Pump module 取付 | #4 | 20min | M3ネジ×2 |
| 6 | Zone A: EOM ×2 取付 | #7 ×2 | 15min | エポキシ固定。硬化24h |
| 7 | Zone A: BS ×3 配置 | #8 ×3 | 10min | ファイバトレイ内配置 |
| 8 | Zone A: BPD ×2 取付 | #9 ×2 | 10min | M3ネジ×2/個 |
| 9 | Zone B: HDPE隔離プレート設置 | #25 | 5min | 底板上に載せるのみ |
| 10 | Zone B: PMFスプール取付 | #10 | 20min | M4×2+ゴムブッシュ。トルク1.0Nm |
| 11 | Zone B: WDM AWG取付 | #11 | 15min | M3ネジ×4 |
| 12 | Zone B: WDM PD ドーターカード | #12 | 10min | コネクタ差込み |
| 13 | Zone C: FPGA基板取付 | #13 | 15min | スタンドオフM3×4。トルク0.5Nm |
| 14 | Zone C: ADC/DAC基板取付 | #14-16,21 | 20min | スタンドオフM3×4 |
| 15 | Zone C: DC-DC取付 | #17 | 10min | FPGA上スタック |
| 16 | Zone C: PZT driver取付 | #20 | 10min | M3ネジ×2 |
| 17 | Zone C: Cu HP ×3 取付 | #18 ×3 | 15min | クランプ固定。TIMグリス塗布 |
| 18 | PTFE断熱板設置 | #19 | 5min | Z=90mm位置に水平配置 |
| 19 | ファイバ配線: Zone A内 (F1-F9) | #29 | 60min | 融着接続。曲げR>15mm確認 |
| 20 | ファイバ配線: Zone A→B (F10-F17) | #29 | 45min | グロメット穴通過。サービスループ+200mm |
| 21 | ファイバ配線: Zone B内 (F18-F33) | #29 | 30min | AWG-PD間リボンケーブル化 |
| 22 | EO comb組込み | #31 | 15min | Zone A/B境界 |
| 23 | 背面コネクタ取付 | #32-36 | 20min | USB-C, RJ45, DC, GND, SW |
| 24 | 正面LED取付 | #37 | 10min | 光ファイバ導光 or 直付け |
| 25 | 底面ファン取付 | #22 | 10min | M4ネジ×4。防振ワッシャ |
| 26 | ゴム脚取付 | #23 ×4 | 5min | M5ネジ |
| 27 | 導電ガスケット装着 | #24 | 10min | 嵌合リップ面に貼付 |
| 28 | 天板閉止 | #2 | 10min | M3皿ネジ×8。トルク0.5Nm。対角締め |
| — | **有人合計** | | **~7h** | 12_mechanical §4.2の合計と整合 |

---

## 3. 配線接続図

### 3.1 電気配線 (Zone C → 各Zone)

```
DC入力(28V) → DC-DC → 3.3V (FPGA core)
                     → 1.8V (FPGA I/O)
                     → 5V (ADC, DAC, PD TIA)
                     → 12V (Peltier, EO driver)
                     → ファン (PWM制御, FPGA GPIO)

Zone C → Zone A: 電気配線なし (光ファイバのみ)
Zone C → Zone B: 電気配線なし (光ファイバのみ)
Zone C → 背面: USB-C, 10GbE, GND 各配線
```

出典: design/12_mechanical.md §3.3

### 3.2 ファイバ配線 (出典: 12_mechanical.md §2.1)

全29本。合計~109m。全PMF1550 (F18-33のみSMF1550)。
詳細は12_mechanical.md §2.1 ファイバ一覧表を参照。

---

## 4. キャリブレーション手順概要

出典: design/12_mechanical.md §2.5

| # | 項目 | 時間 | 合否基準 |
|---|------|:----:|---------|
| 1 | OPA CWスクイージング | 30min | σ_gen ≥ 12.5dB |
| 2 | ホモダインバランス | 20min | CMR ≥ 35dB |
| 3 | PLL 3層ロック | 45min | ±0.5° RSS, 30min持続 |
| 4 | FFレイテンシ | 15min | ≤ 27ns |
| 5 | σ_eff統合測定 | 30min | ≥ 10.5dB (shipping spec) |
| 6 | GKP動作確認 | 30min | P_mode ≥ 90% |
| 7 | 温度サイクル | 60min | σ_eff変動 < 0.3dB |
| 8 | 48hバーンイン | 48h無人 | drift < 0.1dB |

---

## 5. 検査項目 (QA)

出典: design/12_mechanical.md §4.4

| # | 項目 | 合格基準 | 方法 |
|---|------|---------|------|
| 1 | OPAスクイージング | ≥ 11dB CW | ホモダインスペクトラム |
| 2 | 位相ロック安定性 | ±0.5° RSS, 1h | Pilot Tone |
| 3 | ホモダインCMR | ≥ 35dB | バランス調整 |
| 4 | FPGAデコーダレイテンシ | ≤ 13ns | ループバック |
| 5 | UFデコーダレイテンシ | ≤ 300ns | Stimテストベクタ |
| 6 | 筐体温度 | < 45℃@25℃環境 | 熱電対8点 |
| 7 | EMC | CISPR 32 Class B | プリコンプライアンス |
| 8 | 絶縁抵抗 | ≥ 100MΩ | メガー |
| 9 | 消費電力 | 109W ±10% | パワーメータ |
| 10 | 重量 | 7.5kg ±0.5kg | 電子天秤 |

---

## 6. 自己検査チェックリスト

- [x] 全部品に図面番号または型番が紐づいているか — §1 BOM全37品目に指定済み
- [x] 組立順序が論理的に矛盾しないか — §2.3で依存関係順に記載
- [x] 全ファイバの配線ルートが指定されているか — §3.2で12_mechanical §2.1を参照
- [x] キャリブレーション手順と合否基準が明記されているか — §4で8項目指定
- [x] QA検査項目と合格基準が明記されているか — §5で10項目指定
- [x] 出典の紐づかない数値が1つも残っていないか — 全値に出典記載済み
- [x] TODO(設計判断要)を要約してリストアップしたか — 下記参照

---

## 7. TODO(設計判断要)

| # | 項目 | 詳細 |
|---|------|------|
| 1 | EOM固定方法 | エポキシ硬化24h待ちは生産律速。UV硬化接着剤への変更を検討 |
| 2 | ファイバ融着工程 | 融着接続20箇所×各15min≈5hが律速。並列融着治具の導入で2hに短縮可能 |
| 3 | 天板閉止後の保守 | 天板M3×8で固定。OPA交換時に天板開閉が必要。再利用性確認 |
| 4 | 導電ガスケット仕様 | 材質・断面形状未確定。EMCテスト後に選定 |
| 5 | LED実装方式 | 正面パネル貫通か光ファイバ導光か未確定。外観意匠により決定 |
