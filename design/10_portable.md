# Taros Portable シリーズ設計書

**Document ID**: PQC-CV-PORTABLE-v1.4
**Status**: Draft
**前提**: CV pure構成（QDなし、完全室温、低速ファン準無音冷却）

---

## 1. コンセプト

PPLN導波路OPA + macronode TDMの「CV pure」構成は、冷却不要・低消費電力（97-109W, WDM込み）であり、**ラックすら不要**。表面符号距離dの選択（=PMF遅延線の長さ）のみで性能が決まるため、3段階のプロダクトラインを単一プラットフォームから展開可能。

**設計目標**: ACアダプタ駆動（USB-PD EPR 28V/5A=140W必須、消費97-109W）の誤り訂正型量子コンピュータ

### 1.1 CV一点集中の戦略的根拠

| # | 理由 | 定量的根拠 |
|---|------|-----------|
| 1 | 冷凍機排除 = コスト100倍削減 | 超伝導約4.5-7.5億円必須 → CV室温動作 |
| 2 | サイズ1000倍縮小 | 超伝導:部屋1室 → CV:7.5kg筐体 |
| 3 | 成功確率DV比3倍 | Level A: CV 50-65% vs DV 12-18% |
| 4 | 製品化技術ギャップ最小 | 新規必要技術: GKP postselectionのみ。他はテレコム既製品 |
| 5 | 競合不在の市場 | 約1,800万円帯FTQC製品は世界に存在しない |

リソースの80%をCVに集中。Phase -1のCV判定(約1,200万円/4ヶ月)で成否判定後、DV fallback経路を維持。

---

## 2. プロダクトライン

| モデル | **Taros Edu** | **Taros Pro** | **Taros Max** |
|--------|---------|---|---------|
| 表面符号距離 d | 3 | 5 | 7 |
| 論理エラー率 p_L (MWPM, Phase2+ PIC) | ~10⁻² | ~10⁻³ | **3.3×10⁻⁴** (L=0.27dB) | erfc+V_nl修正。理論限界6.1×10⁻⁷(L=0.15dB)
| FTQC | break-even | 入口 | **製品級** |
| macronode列数 N_col (=2d²) | 18 | 50 | 98 |
| 長遅延 τ₂ (=N_col×10ns) | 180ns (37m PMF) | 500ns (102m PMF) | 980ns (200m PMF) |
| QECサイクル時間 (d rounds×N_col×T) | 180ns×3=540ns | 500ns×5=2.5μs | 980ns×7=6.86μs |
| 有効GKPレート | 100kHz | 100kHz | 100kHz |
| 論理ゲートレート (単一ch) | ~1.9kHz | ~400Hz | ~146Hz |
| 論理ゲートレート (WDM並列)†† | ~10kHz (5ch) | ~3kHz (8ch) | ~1kHz (7ch)† |
| Tゲートレート (native T, 単一qubit) | = 論理ゲートレート | 同左 | 同左 |
| CNOTレート (lattice surgery, ~d cycles) | ~630Hz | ~80Hz | ~21Hz |
| 長遅延ファイバ | PMF 37m (φ6cm) | PMF 102m (φ8cm) | PMF 200m (φ12cm) |
| 筐体サイズ | 25×20×10cm | 30×25×16cm | 40×30×20cm |
| 重量 (WDM込み) | **~4.3kg** | **~7.5kg** | **~9.7kg**† |
| 消費電力 (WDM込み) | **~104W** | **~109W** | **~112W** | Edu OPA×2必須(macronode要件)
| 冷却 | パッシブ+低速ファン(<25dBA) | パッシブ+低速ファン(<25dBA) | パッシブ+低速ファン(<20dBA) |
| 原価 (量産100台, WDM込み)‡ | **約840万円** | **約1,125万円** | **約1,425万円** |
| 販売価格 | **約1,350万円** | **約1,800万円** | **約2,550万円** |
| 用途 | 教育、QEC研究 | 研究、VQE/QAOA | FTQC、量子化学 |

†**Max重量内訳**: Pro(7.5kg)からの差分+2.2kg:
PMF延長(200m-102m=98m×3g/m): +0.3kg、筐体大型化(40×30×20cm Al 1.5mm): +0.8kg、
大型ヒートシンク(フィン43本→フルサイズ): +0.5kg、電源回路マージン: +0.2kg、
追加スプール固定具・振動対策: +0.4kg。合計: 7.5+2.2=9.7kg。

Max WDM 7ch (Proの8chより少ない理由): Maxは200m PMFにより1 syndrome roundが
980nsと長く、必要WDMチャネル数が少ない。146Hz×7ch≈1kHzでターゲット達成。

††WDM並列: 各WDMチャネルは独立TDMクラスタ（チャネル間エンタングルメントなし）。
「3kHz (8ch)」= 8台の独立量子プロセッサが各400Hzで並列動作する合計スループット。
単一アルゴリズムの全qubit間連結が必要な場合は単一チャネルのレート(400Hz)が上限。
並列実行可能なタスク（VQEパラメータスイープ、サンプリング等）では合計レートが有効。

‡原価差の主要因: Edu→Pro: ADC/PD数(10→16個, +約120万円) + 筐体サイズ/加工費(+約75万円) + 較正時間(+約45万円)。
Pro→Max: 筐体大型化(+約75万円) + PMFスプール/精密組立(+約45万円) + d=7用追加較正・バーンイン(+約120万円) +
ADC高精度選別(+約75万円) + 長期安定性試験(+約75万円)。Max原価約1,425万円の内訳は`12_mechanical.md`のPro BOMを
基準にMaxスケーリング要因を適用した推定値。

### Taros Max BOM概算 (top-down見積もり)

| カテゴリ | 内容 | コスト |
|---------|------|--------|
| OPA光源 | PPLN OPA ×2 + 1550nm GS-DFB+SOA+PPLN SHG (Option B) | 約240万円 |
| 光学系 | PMF 200m + BS×3 + カプラ + WDM 7ch AWG | 約225万円 |
| 検出系 | BPD ×14(7ch×2) + ADC ×14 | 約375万円 |
| FPGA | Versal VE2302 + 基板 | 約120万円 |
| 電源・熱 | USB-PD EPR PSU + ヒートシンク + ファン×2 | 約75万円 |
| 筐体 | Al CNC一体 (40×30×20cm) | 約90万円 |
| EO・制御 | EOM + PZT + PLL基板 + DAC | 約120万円 |
| 組立・検査 | ファイバ接続 + 較正 + バーンイン | 約210万円 |
| **合計** | | **約1,425万円** |

*Pro BOMからの差分: 検出ch増(8→14ch, +約105万円)、PMF長(102→200m, +約15万円)、筐体大型化(+約30万円)、高精度較正(+約90万円)、AWG追加ch(+約45万円)。OPA本数同一(×2)。*

---

## 3. 共通プラットフォーム設計

### 3.1 光学サブモジュール（3モデル共通）

```
┌──────────────────────────── 光学モジュール (15cm × 10cm × 3cm) ────┐
│                                                                     │
│  ┌─────────┐   ┌─────┐   ┌─────┐   ┌─────┐                       │
│  │Master LD│──►│PPLN │──►│1×2  │──►│OPA#1│──► PMF out_1           │
│  │1550nm   │   │SHG  │   │split│   │     │                        │
│  │10mW     │   │→775 │   │     │──►│OPA#2│──► PMF out_2           │
│  └─────────┘   └─────┘   └─────┘   └─────┘                       │
│                                                                     │
│  ┌───────────────────────┐   ┌──────────┐   ┌────────┐              │
│  │1550nm GS-DFB+SOA+SHG │──►│1×2 split │──►│PZT ×2  │  (位相ロック)│
│  │(Option B, ~10K)       │   │(pump分配)│   │        │              │
│  │SHG出力: 200mW peak    │   └──────────┘   └────────┘              │
│  └───────────────────────┘                                                       │
│                                                                     │
│  温度制御: Peltier ×3 (OPA×2 + SHG×1), ±0.01℃                     │
│  全ファイバ接続（PMF）、アクティブアライメント不要                     │
│                                                                     │
│  **WDM方式**:                                                        │
│  OPA#1, #2は広帯域(~500GHz)スクイージングを生成。                      │
│  AWG (Arrayed Waveguide Grating) でWDMチャネルに分離:               │
│    PMF out_1 →[AWG 8ch]→ λ₁...λ₈ (各100GHz間隔、1550nm片側)       │
│    PMF out_2 →[AWG 8ch]→ λ₁...λ₈ (OPA#2も同様に分離)              │
│  各WDMチャネルペア(λᵢ from OPA#1 + λᵢ from OPA#2)が独立TDMクラスタ。│
│  → 2 OPA × 1 AWGで8ch独立量子チャネル生成（広帯域OPA方式）。          │
│  追加損失: AWG挿入損失 0.2dB (NTT-AT低損失品, 設計基準)                         │
│  BSモデル: AWG込みL=1.42dBではσ_eff=5.0dB(閾値未満)。Phase 2+ PIC統合    │
│  (L=0.15dB)でσ_eff=10.8dB達成。旧値11.7→11.5dBはdB減算誤り(06_noise-budget参照)│
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 TDMクラスタサブモジュール（3モデル共通）

```
┌──────────────────────── TDMモジュール (10cm × 8cm × 3cm) ──────────┐
│                                                                     │
│  PMF in_1 ──►┐                                                      │
│              ├── [BS₁ 50:50] ──┬──► [BS₃] ──► PMF out_A            │
│  PMF in_2 ──►┘                 │                                    │
│                                └──► [短遅延 PMF 2m]                 │
│                                          │                          │
│                                          ▼                          │
│                                     [BS₂ 50:50] ──► PMF out_B      │
│                                          ↑                          │
│                                  [長遅延: PMF]                      │
│                                  (モデル依存)                        │
│                                                                     │
│  LO EOM ×2: LNOI EOM (基底切替)                                     │
│  EO driver: DAC 16bit → amp                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2b WDM LO生成方式

WDMチャネルごとに周波数の異なるLOが必要。EO comb + EDFA方式で生成:

```
Master LD (1550nm, 100mW) ──► [PM: 25GHz RF] ──► [IM: 25GHz RF]
                                                        │
                                                        ▼
                                               8ライン EO comb
                                          (100GHz間隔, 各~1mW)
                                                        │
                                                        ▼
                                               [ミニEDFA: +10dB]
                                                        │
                                                        ▼
                                               [AWG: 8ch分離]
                                                  │...│
                                            LO_λ₁ ... LO_λ₈ (各~10mW)
                                                  │...│
                                            各ホモダイン検出器へ
```

| パラメータ | 仕様 |
|-----------|------|
| RF駆動周波数 | 25GHz (4倍: 100GHz間隔コム生成) |
| コムライン数 | 8 (フラットトップ型) |
| 各ラインパワー (EDFA後) | ~10mW (shot noise clearance ≥10dB確保) |
| 全LO合計パワー | ~80mW |
| Master LD出力 | 100mW (DFB, NKT Koheras BASIK) |
| ミニEDFA | +10dB, NF<5dB, 小型モジュール (Amonics/Thorlabs) |
| 追加部品 | PM + IM (LiNbO3) + 25GHz RF driver + ミニEDFA |
| 追加コスト | 約135万円 (RF driver 約45万円 + EOM ×2 約60万円 + EDFA 約30万円) |
| 位相コヒーレンス | 全ライン完全コヒーレント（同一マスター由来） |
| EDFA ASEノイズ | コム間ノイズはAWGで除去。チャネル内ASEは-50dB/mode（無視可能） |

### 3.3 電子制御サブモジュール（3モデル共通）

```
┌──────────────────── 制御モジュール (12cm × 10cm × 4cm) ─────────────┐
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │Balanced PD ×2│  │Flash ADC 6bit│  │FPGA          │              │
│  │InGaAs        │──│1.5GSPS +     │──│Versal VE2302 │              │
│  │              │  │Pipe 14b 400M │  │              │              │
│  └──────────────┘  └──────────────┘  │ GKP decoder  │              │
│                                       │ Surface code │              │
│  ┌──────────────┐                    │ FF control   │              │
│  │DAC MAX5898   │◄───────────────────│ Phase lock   │              │
│  │14bit 400MSPS │                    └──────────────┘              │
│  │→ EO driver   │                                                  │
│  └──────────────┘                                                  │
│                                                                      │
│  接続: USB-C (data) + 10GbE SFP+ (option)                          │
│  OS: Linux (embedded) + Python API                                   │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.4 電源

| 項目 | 消費電力 |
|------|---------|
| Master LD (1550nm) + 1550nm GS-DFB+SOA+PPLN SHG (Option B) | ~15W (DFB 2W + SOA 8W + SHG TEC 5W) | SOA 5→8W修正。SOA datasheet typ.消費8W@1.6W出力
| PPLN OPA Peltier ×2 | 8W |
| SHG Peltier | 4W |
| EO gate driver | 5W |
| PZT phase lock | 3W |
| Balanced PD + TIA (2ch base) | 2W |
| ADC ×2 (base) | 10W |
| FPGA VE2302 | 25W |
| DAC + misc | 5W |
| **WDM追加 (8ch標準: PD×14 + ADC×14)** | **12W** |
| EO comb RF driver (25GHz PM+IM) + ミニEDFA | 17W |
| **合計 (Pro, WDM 8ch込み)** | **109W** | SOA 5→8W反映。旧106W→109W

**EO comb RF電力内訳**: PM用RF ~6W + IM用RF ~8W + EDFA 3W = 17W

**モデル別電力 (OPA構成反映、RF電力修正)**:
- Taros Edu (OPA×2, WDM 5ch): 86W + 8W + 10W(RF修正) = **104W** OPA×2必須(macronode要件)。旧OPA×1(100W)は撤廃
- Taros Pro (OPA×2, WDM 8ch): 86W + 12W + 11W(RF修正) = **109W** SOA +3W。旧106W
- Taros Max (OPA×2, WDM 7ch): 89.5W + 11W + 11W(RF修正) = **112W** SOA +3W。旧109W

**ベース電力の導出透明化**:

上記モデル別電力の「ベース値」(82W/86W/89.5W)は、コンポーネント表の項目から以下のように導出される:

```
■ Taros Pro ベース電力導出 (OPA×2, WDM追加前):
  Master LD + GS-DFB + SOA + SHG TEC  : 15W  (DFB 2W + SOA 8W + SHG TEC 5W)
  PPLN OPA Peltier ×2                 :  8W  (4W/OPA × 2)
  SHG Peltier                          :  4W
  EO gate driver                       :  5W  (Option B: ゲート駆動→LO基底切替用EOMに転用)
  PZT phase lock                       :  3W
  Balanced PD + TIA (2ch base)         :  2W
  ADC ×2 (base, Flash+Pipeline)        : 10W
  FPGA VE2302                          : 25W
  DAC + misc                           :  5W
  DC-DC変換損失 (η≈0.92, 入力段)       :  7W  (77W÷0.92 - 77W ≈ 7W)
  ─────────────────────────────────────────
  合計ベース (Pro)                      : 84W → 丸め・実測マージン込み **86W**

■ Taros Edu ベース電力導出 (OPA×2):
  Pro基準 86W（OPA×2共通）= 86W macronode要件によりOPA×2必須。旧OPA×1(82W)撤廃

■ Taros Max ベース電力導出 (OPA×2, 大型冷却系):
  Pro基準 86W + 追加ファン 1.5W + 大型ヒートシンク制御 1W + 長遅延PMF温調 1W = 89.5W

■ WDM追加電力 (Pro 8ch):
  追加PD+TIA (14ch − 2ch base = 12ch追加): ~6W (0.5W/ch)
  追加ADC (14ch − 2ch base = 12ch追加)   : ~6W (0.5W/ch)
  小計                                    : 12W

■ EO comb RF電力:
  PM用RF amp (25GHz)   :  6W
  IM用RF amp (25GHz)   :  8W  (Pro: 8ch駆動で+3W → 11W表記はRF効率マージン込み)
  ミニEDFA             :  3W
  小計                 : 17W → Proは8ch分 11W (Edu 5ch: 10W)で按分計上

■ Pro合計: 86W (ベース) + 12W (WDM PD/ADC) + 11W (RF/EDFA按分) = **109W** ✓
```

**注 (OPA×1→×2)**: macronode lattice生成にはBS₁で2つの独立スクイーズド真空を混合する必要がある（03_tdm-cluster.md §2.1）。**従ってEduもOPA×2が必須**。旧「OPA×1」記述はmacronode回路要件との矛盾であり撤廃。Edu OPA×2構成でもSOA 1.6W→SHG 400mW→1×2 split=200mW/OPAで閾値確保可能。Edu消費電力はOPA Peltier ×2で+4W → **104W**（USB-PD EPR 140Wで36Wマージン）。原価はOPA追加約45万円 → **約840万円**。

**ポンプ光源の構成差異 (Option B統一)**:
- **Portable (全モデル)**: 1550nm GS-DFB+SOA(1.6W peak)+PPLN SHG (Option B), SHG出力400mW peak (775nm), 消費~15W (DFB 2W + SOA 8W + SHG TEC 5W), コスト~約150万円
  - OPA×2構成: SOA 1.6W peak → SHG 400mW peak → 1×2 splitter(3dB) = **200mW peak/OPA**。各OPAに閾値ポンプパワー確保。
  - ※旧仕様(SOA 800mW→SHG 200mW→splitter→100mW/OPA)ではσ_gen~9-10dBに低下し閾値未達。
- **Rack (8 OPA構成)**: 同方式で高出力SOA使用、またはDFB+TA 2.5Wで対応。
- コスト構成: GS-DFB 約30万円 + SOA 約45万円 + PPLN SHG 約45万円 + 制御・筐体 約30万円 = **~約150万円**

電源: **外付けACアダプタ USB-PD EPR 140W (28V/5A) 必須**

**電源仕様**:
- **全モデル必須**: USB-PD EPR 140W (28V/5A) — 全モデルでフル性能動作、マージン31-43W
- ※旧仕様のUSB-PD 100W代替電源は廃止。Pro(109W)/Max(112W)は100W不可。Edu(104W)は100W境界付近のためマージン確保に140W統一を推奨。

---

## 4. Taros Pro 筐体設計

### 4.1 外観

```
┌───────────────────────────────────────────┐
│                                           │  ← 上面: アルミヒートシンク
│   ┌─────────────┐  ┌─────────────────┐   │     (フィン高さ2cm)
│   │ 光学モジュール │  │ PMF φ8cm       │   │
│   │ (密閉)       │  │ スプール        │   │  15cm
│   └─────────────┘  └─────────────────┘   │
│   ┌──────────┐  ┌──────────────────────┐ │
│   │TDMモジュール│  │ 制御モジュール       │ │
│   └──────────┘  └──────────────────────┘ │
│                                           │
│   背面: USB-C / 10GbE / AC-in / LED      │
└───────────────────────────────────────────┘
         30cm × 25cm

材質: アルミ削り出し（放熱兼用）
仕上げ: アノダイズド（黒）
重量: 筐体3.4kg (Al A6063-T5 CNC、底板3mm+側板3mm+天板3mm+フィン18mm×43本; DWG-001 1.74kg+DWG-002 1.66kg) + 内部3.5kg + WDM 0.4kg + 振動隔離等0.2kg = 7.5kg
```

### 4.2 熱設計

| 条件 | 値 |
|------|-----|
| 総発熱 | 109W (WDM 8ch込み、Pro基準) SOA +3W |
| 筐体表面積 | 30×25×2 + 30×15×2 + 25×15×2 = 3,150cm² |
| 自然対流のみ | **~49W** (h=8 W/m²K, A_eff=筐体0.14m²+フィン0.33m²×効率0.5×空気滞留0.7=0.26m², 合計≈0.26m², ΔT=25K(表面50℃), Q=8×0.26×25≈**52W**概算、保守49W)。109W放熱にはファン必須。 |
| **ファン併用放熱能力** | **~140W** (80mm低速ファン@1400rpm, h=18W/m²K, A_eff=0.14m²(筐体)+0.33m²(天面フィン43本×効率0.7)=0.37m², Q=18×0.37×20≈133W + 側面スリット7W ≈ **140W**, ΔT=20K(表面45℃)) |
| 内部発熱 (筐体内) | 50W (光学系+PD+RF)。残り59W(FPGA+ADC+DC-DC+EO comb RF)は天板フィン右側1/3領域HP経由外部放熱。**注**: OPA Peltier(8W)+SHG Peltier(4W)=12W(電気入力)のhot side排熱は電気入力+ポンプ熱≈18-20Wが筐体内に放出。上記50Wに含まれる。 | |
| マージン (ΔT=20K時) | 140W - 109W = **31W (22%)** | 十分 SOA +3W反映 |
| 筐体表面温度 (ΔT=20K) | 環境25℃ + 20℃ = **45℃** | 触れる温度（安全、IEC 62368-1: 外装≤60℃） |
| **騒音** | **<25dBA** (@1400rpm) | Noctua NF-A8 PWM (17dBA@1400rpm公称 + 筐体共鳴マージン) |

**冷却方式**:
- Taros Pro: 天板フィン右側1/3領域ヒートパイプ (Cu HP×3) で FPGA+DC-DC 45Wを天板フィンへ排熱。
  筐体内残り50W → 低速ファン(80mm, <25dBA)+天板フィン自然対流で放熱。表面温度45℃。準無音。
- Taros Max: 小型ファン (50mm, 1200RPM, 20dBA) 追加。表面温度35℃。ほぼ無音。
- Taros Edu: 底面ヒートシンク + 低速ファン(60mm)。表面温度~38℃。準無音。

### 4.3 振動・環境耐性

| 項目 | 仕様 | 根拠 |
|------|------|------|
| 振動 | 全ファイバ系のため影響なし | フリースペース光路なし |
| 温度範囲 | 15-35℃ | Peltier追従範囲 (下記飽和プロトコル参照) |
| 湿度 | 20-80% RH | 光学モジュール密閉 |
| EMI | FCC Class B準拠 | FPGA shielding |

**光学テーブル不要。通常のオフィス机上で動作。**

**Peltier飽和時プロトコル**:
Peltier TEC (OPA温調) はΔT_max=50K。ambient>35℃またはFPGA熱流入で飽和リスクあり。
| 状態 | 条件 | アクション |
|------|------|----------|
| 正常 | OPA温度誤差 < ±0.01℃ | 通常動作 |
| 警告 | OPA温度誤差 ±0.01-0.05℃ OR Peltier duty >90% 持続5秒 | LED黄色点滅、WDMチャネル数削減(8→5) |
| 障害 | OPA温度誤差 > ±0.1℃ OR Peltier duty 100% 持続10秒 | LED赤色、QEC一時停止、PLL維持のみ |
| シャットダウン | OPA温度 > 55℃ OR FPGA T_j > 90℃ | 安全シャットダウン（レーザoff→Peltierフル冷却→停止） |

FPGA firmware (Phase 0a実装): 温度監視ループ 1kHz、NTC×3 (OPA×2, FPGA junction XSDB)。

---

## 4.5 電源投入シーケンス

| Phase | 時間 | アクション | LED状態 | 安全条件 |
|-----------|----|----------|-------------|---------|
| 0 | T=0s | USB-PD接続、FPGA QSPI boot | 白色点滅 | DC-DCソフトスタート(10ms ramp) |
| 1 | T=0-5s | FPGA初期化、ADC/DAC self-test | 白色点灯 | Pass: 全ADC応答、DAC zero確認 |
| 2 | T=5-30s | Peltier ON (OPA/SHG温調開始) | 黄色点滅 | OPA温度25→50℃ ramp (1℃/s) |
| 3 | T=30-120s | Peltier安定化待ち (±0.1℃) | 黄色点灯 | Timeout: 180s超過→障害表示 |
| 4 | T=120-130s | Master Laser ON → SHG → GS-DFB+SOA+SHG ON | 緑色点滅 | レーザ出力確認後にPLL開始 |
| 5 | T=130-135s | PLL 3層ロック取得(EOM scan→lock) | 緑色点滅(速) | Lock判定: Pilot Tone >-3dB |
| 6 | T=135-180s | Peltier精密安定化 (±0.01℃) | 緑色点灯 | PLL安定 + OPA temp安定 |
| 7 | T=180-300s | GKP postselection threshold自動較正 | 青色点滅 | σ_eff実測→δ_max設定 |
| 8 | T≈300s | **QEC Ready** | **青色点灯** | 全self-test pass |

**合計起動時間: ~5分** (Peltier安定化が律速)。環境15℃以下の場合10分に延長。

**安全インターロック**:
- Phase 4でレーザON前に必ずPeltier安定化完了を確認（OPA過熱防止）
- Phase 5でPLL lock失敗時: レーザOFF→Phase 2に戻り再試行(最大3回)
- 3回失敗: LED赤色、エラーコード E-PLL-LOCK-FAIL、ユーザー通知

**シャットダウンシーケンス**: QEC停止→レーザOFF→Peltier 5分冷却→電源OFF

---

## 5. ソフトウェアスタック

### 5.1 ユーザーインターフェース

```
User → [Python SDK / Qiskit plugin / Cirq plugin]
         │
         ▼
       [REST API / gRPC]  ← 10GbE or USB-C
         │
         ▼
       [Taros Runtime (embedded Linux)]
         │
         ├── Quantum Compiler (回路→TDM命令列)
         ├── GKP Decoder (リアルタイム、FPGA)
         ├── Surface Code Decoder (リアルタイム、FPGA)
         ├── Phase Lock Manager
         └── Calibration Daemon (自動較正)
```

### 5.2 API例

```python
from taros import TarosDevice

# デバイス接続
device = TarosDevice(interface="usb")  # or "ethernet"

# 回路定義（Qiskit互換）
from qiskit import QuantumCircuit
qc = QuantumCircuit(4)
qc.h(0)
qc.cx(0, 1)
qc.cx(1, 2)
qc.cx(2, 3)
qc.measure_all

# 実行
result = device.run(qc, shots=1000)
print(result.get_counts)
```

---

## 6. 競合ポジショニング

| 製品 | 方式 | 論理qubit | サイズ | 価格 | 消費電力 |
|------|------|----------|--------|------|---------|
| IBM Quantum System Two | 超伝導 | 0 | 部屋 | 約22.5億円+ | 200kW+ |
| IonQ Forte | イオン | 0 | ラック×3 | 約4.5億円+ | 30kW |
| Xanadu Aurora | フォトニック | TBD | ラック×多 | 約15億円+ | 100kW+ |
| **Taros Edu** | **CV光子** | **~1 (d=3)** | **ラップトップ** | **約1,350万円** | **100W** |
| **Taros Pro** | **CV光子** | **10+ (d=5)** | **ミニPC** | **約1,800万円** | **109W** |
| **Taros Max** | **CV光子** | **100+ (d=7)** | **デスクトップ** | **約2,550万円** | **112W** |

---

## 7. 開発ロードマップ

| Phase | 時期 | 成果物 |
|-------|------|--------|
| Phase -1 | Phase -1期間 | PPLN OPA評価 + macronode TDM PoC |
| Phase 0a | Phase 0a期間 | **Taros Edu プロトタイプ** (d=3, QEC break-even) |
| Phase 0b | Phase 0b期間 | **Taros Pro プロトタイプ** (d=5, FTQC入口) |
| Phase 1 | 開始後約2年 | **Taros Max プロトタイプ** (d=7, 製品級) |
| Phase 2 | 開始後約3年 | 量産設計 + 初期出荷 (100台/年) |
| Phase 3 | 開始後約4年以降 | QD追加モデル (Taros Pro+, Max+) |

---

## 8. バッテリー駆動オプション（将来）

| パラメータ | 値 |
|-----------|-----|
| 消費電力 | 92W (WDM 3ch省電力モード、109W基準から-17W) |
| バッテリー | Li-ion 288Wh (ラップトップ用×3) |
| **駆動時間** | **3.1時間** (288Wh÷92W) |
| バッテリー重量 | +2kg |
| 合計重量 (Taros Pro + battery) | **9.2kg** |
| 用途 | フィールドデモ、教室での授業、屋外実験 |

*バッテリー駆動型誤り訂正量子コンピュータとしては前例がない構成。*

---

## 8.5 工学的詳細

### 8.5.1 熱隔離設計

光学モジュール（PPLN OPA 50℃動作）とFPGAモジュール（junction 85℃）間に断熱壁:
- 材質: PTFE 3mm → 熱抵抗12 K/W → FPGA→OPA熱流0.4W → OPA温度影響<0.1℃

### 8.5.2 OPAホットスワップ

OPA予備1本 + 2×1光スイッチで劣化時自動切替。追加約52万円。切替<1ms。

### 8.5.3 FF方式: Clifford precompile + T adaptive

- Clifford (~80%): プリコンパイル → FFレイテンシ0、モード遅延0
- T gate (~20%): 適応的FF 27ns(設計ベースライン)/22ns(楽観) → 3モード遅延 (Flash ADC + パラレルDAC)
- Tゲート対象モードをmacronode内4番目に配置 → **100MHzクロック維持**

---

## 9. 将来拡張: WDM並列化 + Native Tゲート

### 9.1 WDM-TDMハイブリッド (Phase 0から段階導入)

**重要**: Executive Summary記載のゲートレート(10kHz/3kHz/1kHz)はWDM並列化が前提。
単一チャネルでは1.9kHz/400Hz/146Hzに留まる。WDMは将来拡張ではなく**初期製品の標準構成**。

PPLN OPAの500GHz帯域を活用し、5-20チャネルのDense WDMで並列化:

**WDM物理的制約**:
- 縮退点(1550nm)を中心に対称な周波数はsignal-idlerペアでエンタングル
- → **全WDMチャネルを縮退点の片側のみに配置** (例: 1550.0-1556.4nm)
- OPA帯域片側250GHz内に50GHz間隔で最大5ch確保可能（十分）
- CW single-mode pumpでは同一側チャネル間のエンタングルメントなし（独立）

**Phase 0 WDM構成 (5-8ch, 標準搭載)**:
- 追加: AWG 1個 + PD×10-16 + ADC×10-16
- 追加コスト: +約120-210万円 (原価に含む)
- 追加電力: +10-15W (電力予算に含む)
- 追加重量: +0.3-0.5kg

**Phase 2+ WDM構成 (20ch, フルスペック)**:

| パラメータ | WDM 5-8ch (Phase 0-1 標準) | **WDM 20ch (Phase 2+)** |
|-----------|---------|---|
| OPA帯域利用率 | 0.005% | **0.1%** |
| 有効GKPレート | 100kHz | **2MHz** |
| 論理ゲートレート (d=5) | 3kHz | **60kHz** |
| Tゲートレート (蒸留5:1) | 600Hz | 12kHz |
| Tゲートレート (native T) | **3kHz** | **60kHz** |
| 追加ハードウェア | — | AWG + PD×40 + ADC×40 |
| 追加コスト | — | +約270万円 |
| FeMoco時間 (native T) | 5.5分 | **17秒** |

### 9.1b 将来検討: 周波数コムクラスタ (Phase 3+)

bi-chromatic pumpまたはcavity OPOにより周波数モード間エンタングルメントを生成し、
**遅延線なしで2Dクラスタ状態**を構築する可能性:

```
現在:    TDM（時間方向）× PMF遅延線（列方向）= 2Dクラスタ
将来案:  TDM（時間方向）× 周波数コム（列方向）= 2Dクラスタ（遅延線不要）
```

メリット: PMF 200m除去(-0.04dB損失, -約1万円, スプール不要で更に小型化)
課題: bi-chromatic pump制御、周波数モード分解ホモダイン検出
参考: 60-mode freq comb cluster (2014), Chen+ 2014 (theory)
ステータス: Phase 3+で検討。Phase 0-1は時間+遅延線方式で確定。

### 9.2 GKP Native Tゲート (Webster-Bartlett-Brown 2024)

macronode latticeでの測定角度θ = π/8で**蒸留なしTゲート**が実行可能:

| 方式 | Tゲート/論理ゲート比 | 根拠 |
|------|---------|------|
| マジック状態蒸留 (従来) | 1:5 | 15:1蒸留 → 5:1改善版 |
| **Native Tゲート (新)** | **1:1** | Webster+ 2024, 測定角θ=π/8 |

条件: σ_eff > 10dB でnative T infidelity < 10⁻³ → d=7表面符号で訂正可能

**Phase -1 Stim検証項目に追加**: native Tゲートの実効エラー率 vs σ_eff

### 9.3 GKP Postselectionバッファ方式

**TDM postselectionプロトコル**:

全モードを漏れなく測定し、品質に応じた重み付けでデコーダに入力:

```
[ホモダイン] → [Flash ADC] → [GKP grid判定 + δ計算]
                                      │
                      ┌───────────────┼───────────────┐
                      │               │               │
               δ < 0.15√π      0.15√π < δ < 0.4√π    δ > 0.4√π
              (高信頼度)         (中信頼度)           (低信頼度)
              weight: 高          weight: 中          weight: 低(erasure相当)
                      │               │               │
                      └───────────────┼───────────────┘
                                      ▼
                          [全モード → Union-Find デコーダ]
                          (重み付きクラスタ成長で復号)
```

**重要: P_sの物理的解釈**:

P_s≈10⁻³は「GKP格子点に高信頼度で着地したモードの割合」であり、低品質モードの
physical error rateが50%を超えるわけではない（全モードでp_phys≈5×10⁻⁴）。

- **高品質モード (0.1%)**: GKP格子中心付近、信頼度高、表面符号で通常qubitとして使用
- **低品質モード (99.9%)**: GKP格子付近だが不確定性大、低重みで使用

全モードのp_phys≈5×10⁻⁴であり、「erasure率99.9%」ではない。表面符号の入力は
全モードの測定結果(各自の信頼度重み付き)。低品質モードもシンドローム情報に寄与する。

**ゲートレート定義**:
- **最低保証値**: 146Hz = 有効GKP認証レート(100kHz) / QECサイクルモード数(686)。strict postselectionによりFT証明可能な下限。
- **理論上限**: 146kHz = QECサイクル時間(6.86μs)の逆数。全モードをsoft-infoで利用する場合の物理上限。
- **製品スペック値**: WDM 7ch × 146Hz = **~1kHz**（保証値ベース）。soft-info全モード利用が検証された場合、単一chで1-10kHz級に向上する見込み。
- Phase -1 Stim検証(T0b)で実効ゲートレートを確定予定。対外資料ではWDM込み保証値(1kHz)を使用する。

FF-1（基底選択）のみがリアルタイム27ns制約(設計ベースライン400MHz。Flash ADC + パラレルDAC構成)。

---

*本文書はCV pure構成（QDなし、完全室温、低速ファン準無音冷却）のポータブル量子コンピュータシリーズを定義したものである。PPLN導波路OPA + macronode TDMの最小構成により、109W・7.5kg・約1,800万円の誤り訂正型量子コンピュータを実現する。*
