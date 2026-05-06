# アーキテクチャ方式選定

**Last Updated**: 2026-05-06

---

## 方式比較

| | **CV+QD ハイブリッド（採用）** | DV-FBQC（フォールバック） | 超伝導（参考） |
|---|:---:|:---:|:---:|
| 動作温度 | **完全室温**（QD追加時のみ4K、QDはオプション） | 4K（SNSPD全数） | 15mK |
| 閾値マージン | v2.0修正: 現離散光学→閾値未達(5.0dB<7.5dB); Phase 2+ PIC→**+3.4dB**(PS)/+0.9dB(全モード) | -10pt | +30pt |
| デスクサイド化 | **可能（~109W, ~7.5kg）** | 困難（2.1kW, 51kg） | 不可能 | [v3.2]
| 論理qubitスケーリング | **TDM: 追加HW $0** (逐次処理: 1000 qubit回路(10⁶ Tゲート)の実行時間はd=7で全モード~1秒 / strict~16分。並列処理はWDM拡張で対応) | SNSPD比例増加 | 物理qubit比例増加 |
| 量産性 | **ウェハプロセス** | 個別光学組立 | 希釈冷凍機 |

## 選定根拠

1. **閾値超過 (Phase 2+ PIC)**: v2.0修正: σ_eff=10.9dB(Phase 2+ PIC) > σ_th=7.5dB(PS)/10dB(全モード). マージン+3.4/+0.9dB。現離散光学(σ_eff=5.0dB)では閾値未達→ロードマップ実行が必須
2. **室温動作**: 1550nm光子の熱雑音 n_th=3×10⁻¹⁴ → 完全に無視可能
3. **TDMスケーリング**: 論理qubit数が物理リソースに依存しない唯一の方式
4. **QDなし構成の成立**: pure CV（QD=0）でも Phase 2+ PIC時 p_L≈7×10⁻⁵ (MWPM, d=7, L=0.27dB, QE≥99%, non-loss noise込み) → ≲10⁻⁴。L≤0.20dBで<10⁻⁵確実達成。理論限界p_L≈5.7×10⁻⁷はL=0.15dB+QE99%+Δ=0の全条件達成時のみ（v3.4修正）

**ゲートレート注記**: 単一chでの実効CNOTレートは~21Hz(d=7, QECサイクル7回×146Hz/7)。実用的な量子化学計算(10⁶ Tゲート)は全モード~1秒 / strict~16分で完了(WDM 7ch時)。WDM 7chで~1kHz Tゲート(strict)/~135kHz(全モード)/~146Hz CNOT。

## 設計判断ログ

| 判断 | 日付 | 根拠 | 関連ファイル |
|------|------|------|-------------|
| bow-tie OPO → PPLN導波路OPA | 2026-05 | 体積1/120, コスト1/7, アライメントフリー | `design/02_opa-source.md` |
| MWPM → Union-Find decoder | 2026-05 | レイテンシ旧MWPM→280ns(UF), DDR4不要 | `design/08_decoder.md` |
| Union-Find → MWPM復帰 (製品デコーダ) | 2026-05 | v3.2: 製品要件p_L<10⁻⁵。現実的PIC(L=0.27dB)でUF d=7~5×10⁻⁴>10⁻⁵のためMWPM必須。MWPM d=7で~2-5×10⁻⁵(境界達成)。理論限界(L=0.15dB)ではMWPM 5.7×10⁻⁷で十分マージン。UFは実験用 | `design/08_decoder.md` |
| パッシブ冷却 → 低速ファン | 2026-05 | 自然対流~34W < 必要109W | `design/12_mechanical.md` |
| 775nm EOM → 1550nm EOM + SHG | 2026-05 | 775nm導波路EOM非存在 | `design/05_phase-lock.md` |
| WDM AWG追加 | 2026-05 | 低損失AWG(0.2dB)。v2.0: σ_effはビームスプリッタモデルで再計算 | `design/06_noise-budget.md` |
| ADC: FPGA内蔵6bit → 外部Flash ADC (ADC06D1500) | 2026-05 | FPGA内蔵精度不足。外部Flash 6bit 1.5GSPS: 3ns | `design/07_feedforward.md` |
| 775nm 2W DFB → DFB + TA 500mW | 2026-05 | 2W単体DFBは市販品非存在 | `design/10_portable.md` |
| EO comb 10mW → 100mW + EDFA | 2026-05 | 10mW/ch LOが量子ノイズ限界に必要 | `design/10_portable.md` |
| σ_eff dB減算 → BSモデル | 2026-05 | dB減算は物理的に不正確(V_sqz<<1-η)。BSモデルで全面再計算 | `design/06_noise-budget.md` |
| Option A (CW+EO gate) → Option B (パルスOPA) | 2026-05 | EO gate 0.3dB損失が閾値マージンに致命的 | `design/02_opa-source.md` |
| v2.2統合修正 (Session 9-10) | 2026-05-06 | P_s記号廃止→p_acc/P_round分離、V_anti=20 SNU表記統一、GKP Fidelity BS model修正(F=0.94→0.87-0.91)、リスク確率ベイジアン化(80%→63%/81%)、Stim統計的不確かさ注記、Phase -1実験構成明示(Option B, AWGなし, σ_eff=8.8dB) | 全design/, analysis/, experiments/ |
| **v3.1統合修正 (Session 11)** | 2026-05-06 | **p_L 3段階化(10⁻³/10⁻⁵/10⁻⁶)**: 製品スペックp_L<10⁻⁵(現実的PIC L=0.27dB)、理論限界10⁻⁶(L=0.15dB全条件達成時)。**Phase 1 σ_gen 15→13dBに下方修正**(目的をbreak-even実証に限定)。**PIC損失バジェット修正**: L=0.15dBはオンチップのみ、OPA結合込み現実的楽観L=0.27dB。**QE≥98%をGo/No-Go G6追加**。**Phase -1を12ヶ月/$3.04Mに正式確定**。Tゲートパイプラインハザード制約追加。PMF切断精度±1mm→±50μm。OPO→OPA用語統一。 | 全design/, analysis/ |
| **v3.3統合修正 (Session 13)** | 2026-05-06 | **p_L表記「<10⁻⁵」→「≲10⁻⁵(目標)」**: 現実的L=0.27dBでMWPM~2-5×10⁻⁵(境界)。L≤0.20dBで<10⁻⁵確実。**DAC MAX5898 group delay修正**: 2cycle@400MHz=5ns(旧4nsは計算ミス)→FF合計27ns。**σ_eff旧値9.4dB→8.8dB一括修正**(01_sys-arch, 02_opa-source, 00_overview)。**QE≥99%前提明示**: L=0.27dBバジェットはQE≥99%前提。QE=98%ならL≤0.20dB必須。**106W→109W残存11箇所修正**。133W→140W修正。GKP実験$42K/5ヶ月統一。SNSPD 500→1000残存修正。 | 全design/, analysis/, fallback/, experiments/ |

### Xanadu Auroraとの差別化

| 観点 | Xanadu Aurora | **Taros** |
|------|:---:|:---:|
| 市場 | クラウドQC (データセンター) | **デスクトップ教育・研究機器** |
| 価格帯 | 非公開（クラウド提供のみ） | **$90K-$170K** |
| サイズ | 部屋サイズ | **~7.5kg ポータブル** |
| 冷却 | SNSPD (4K冷凍機) | **完全室温** |
| 起動 | 数時間 (冷却) | **<5分 (電源ON→位相ロック確立)** |
| 顧客 | Fortune 500 / 政府機関 | **大学・研究所 (100台/年)** |
| 方式 | CV+GKP+TDM (同一) | CV+GKP+TDM (同一) |

**差別化の本質**: 技術方式は類似するが、ターゲット市場が根本的に異なる。
Tarosは「量子コンピュータのRaspberry Pi」— QEC教育・研究のアクセス民主化。
Xanaduのクラウドサービスに対し、Tarosはオンプレミス研究ツールとして補完的位置づけ。

## フォールバック条件

以下のいずれかが判明した場合、DV-FBQC方式に切り替え:
1. PPLN OPAで12dB以上のスクイージングが再現不能
2. macronode TDMの実効閾値がσ_th > 10dBと判明
3. GKP postselection成功率が10⁻⁵未満

フォールバック設計: `fallback/` ディレクトリ参照
