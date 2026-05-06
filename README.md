# Taros — デスクトップ光量子コンピュータ

<p align="center">
  <img src="assets/taros-pro-6view.png" alt="Taros Pro 6-view render" width="720">
</p>

**プロジェクト名**: Taros (Tabletop-scale Room-temperature Optical System)
**目標**: ACアダプタで動くポータブル誤り訂正型光量子コンピュータの実現
**Last Updated**: 2026-05-06

---

## ビジョン

> **「電源コンセントとLANケーブルで動く量子コンピュータ」**

超伝導方式（IBM/Google）はmK冷凍機が必須で原理的にデスクサイド化不可能。
フォトニック方式のみが到達可能な形態であり、Tarosの決定的差別化要因。

---

## 主要スペック

| 指標 | 値 |
|------|-----|
| 方式 | ハイブリッドCV+QD（PPLN導波路OPA + macronode TDM） |
| 実効スクイージング | σ_eff = 5.0dB (現離散光学) / 8.5dB (Phase 1) / **≈9.3dB** (Phase 2+ PIC 現実的, L=0.27dB) — v3.6 BSモデル |
| 物理エラー率 | Phase 2+ PIC現実的: p_err ≈ 4.9×10⁻³ (v3.6, L=0.27dB) |
| 論理エラー率 (d=7, Phase 2+ PIC) | **製品仕様: p_L ≈3.3×10⁻⁴ (L=0.27dB, QE≥99%, MWPM)**† / L≤0.17dBで<10⁻⁵ / 理論限界: 6.1×10⁻⁷ (全条件達成時) [v3.6] |
| 性能段階 | Phase 1: break-even(p_L~10⁻³) / Phase 2+: 製品FTQC(p_L≲10⁻³, L=0.27dB; <10⁻⁵, L≤0.17dB) / 理論限界(p_L<10⁻⁶) [v3.6] |
| 閾値マージン | v3.6修正: 現離散光学→閾値未達; Phase 1→+1.0dB(PS); Phase 2+ PIC→+1.8dB(PS)/−0.7dB(全モード) |
| フィードフォワード | 27ns設計ベースライン(400MHz) / 22ns楽観(500MHz)、3モード遅延 |
| デコーダ | **510ns (MWPM製品, 400MHz)** / 350ns (UF実験, 400MHz)（パイプライン動作、FF非律速）[v3.6: 現実的PIC(L=0.27dB)でMWPM d=7≈3.3×10⁻⁴] |
| 消費電力 | ~109W (Portable Pro) / ~1.5kW (Rack) [v3.2: SOA +3W] |
| 冷却 | 低速ファン準無音（QDなし構成は完全室温） |
| 論理qubit | 10〜1,000+（TDM逐次拡張） |

†**v3.3 3段階スペック定義**:
- Phase 1 (離散光学系, 13dB, L=0.39dB): p_L ~ 10⁻³ — QEC break-even実証
- Phase 2+ PIC (現実的, 13dB, L=0.27dB, QE≥99%): p_L ≈ 3.3×10⁻⁴ — 製品目標 (MWPM d=7) [v3.6]
- Phase 2+ PIC (L≤0.17dB達成時): p_L < 10⁻⁵ — 製品スペック確実達成 [v3.6]
- 理論限界 (L=0.15dB, QE=99%, Δ=0): p_L ≈ 6.1×10⁻⁷ — 設計上限 (全条件同時達成時) [v3.6]
現実的推定は「5つの前提条件(Δ<0.12, OPA≥13dB, PLL≥500kHz, QE≥99%, L_total≤0.27dB)」の達成度に依存。
詳細: `design/13_performance.md` §3シナリオ表。

---

## ディレクトリ構造

```
Taros/
├── README.md              # 本ファイル
├── ARCHITECTURE.md        # 方式選定の根拠と設計判断
│
├── design/                # ★ 主軸設計（CV方式）— 上流→下流の論理順
│   ├── 00_overview.md              # エグゼクティブサマリー
│   ├── 01_system-architecture.md   # ハイブリッドCV+QDシステム設計
│   ├── 02_opa-source.md            # PPLN導波路OPA スクイージング光源
│   ├── 03_tdm-cluster.md           # macronode TDMクラスタ生成回路
│   ├── 04_gkp-protocol.md          # 3段階GKP生成プロトコル
│   ├── 05_phase-lock.md            # 3層位相ロックアーキテクチャ
│   ├── 06_noise-budget.md          # CVノイズバジェット（全損失項目）
│   ├── 07_feedforward.md           # フィードフォワードレイテンシ 27ns(設計)/22ns(楽観)
│   ├── 08_decoder.md               # Union-Find GKP+表面符号デコーダ
│   ├── 09_rack-design.md           # 20Uハーフラック設計
│   ├── 10_portable.md              # Taros Portableシリーズ (Edu/Pro/Max)
│   ├── 11_industrial-design.md     # 工業デザイン
│   ├── 12_mechanical.md            # 機械工学設計
│   ├── 13_performance.md           # 性能予測モデル
│   └── 14_clock-distribution.md   # クロック分配・同期設計
│
├── experiments/           # 実験計画
│   ├── 01_gkp-optical.md           # GKP光学生成実験（装置$42K/完全コスト$198K/5ヶ月）
│   ├── 02_virtual-experiments.md   # 仮想実験シミュレーション
│   ├── 03_numerical-verification.md # 数値検証レポート（独立再計算）
│   ├── 04_ibm-quantum-verification.md # IBM Quantum実機検証（ibm_fez 156q）
│   ├── 05_verification-plan.md       # GKP/TDM/Decoder検証計画と費用
│   ├── ibm_quantum_analysis.json    # IBM実機解析データ
│   ├── ibm_quantum_job.json         # IBM実機ジョブ定義
│   └── ibm_quantum_results.json     # IBM実機実行結果
│
├── analysis/              # 分析・計画
│   ├── risk.md                     # CV方式成功確率評価
│   ├── bom.md                      # 統合BOM比較
│   ├── roadmap.md                  # Phase 0-2ロードマップ
│   ├── phase-minus1-execution.md   # Phase -1実行計画（14タスク/$3.08M/12ヶ月）[v3.1確定]
│   └── development-cost-summary.md  # 開発費用全体サマリー
│
├── drawings/              # 製造図面 (CadQuery STEP/DXF + 仕様書)
│   ├── DWG-001_enclosure_body.*     # 筐体本体 (.py/.step/.dxf/.md)
│   ├── DWG-002_top_plate.*          # 天板フィン一体 (.py/.step/.dxf/.md)
│   └── DWG-003_assembly.md          # 総組立図
│
├── assets/                # 画像・レンダリング・資料
│   ├── taros-pro-6view.png         # Taros Pro 6面レンダリング (README サムネイル)
│   ├── exterior-render.png         # 外観レンダリング
│   ├── TAROS_Investor_Pitch.pdf           # 投資家向けピッチデック (PDF, GitHub閲覧可)
│   └── TAROS_Investor_Pitch_Revised.pptx  # 投資家向けピッチデック (編集用)
│
├── fallback/              # DV-FBQCフォールバック設計
│   ├── 01_deskside-vision.md       # DV-FBQC版デスクサイドQC
│   ├── 02_dv-fbqc-desktop-v5.0.md  # DV-FBQC Desktop v5.0 (28kg/2.1kW)
│   └── 03_hybrid-pic-design.md     # ハイブリッドPIC設計
│
└── archive/               # DV-FBQC v4.0 R6 レガシー設計（参照用）
    ├── README.md                   # アーカイブ説明
    ├── 00_summary/                 # エグゼクティブサマリー（DV基盤）
    ├── 01_architecture/            # DV-FBQCアーキテクチャ
    ├── 02_physical-layer/          # 物理層（QD, QFC, Fusion）
    ├── 03_logical-layer/           # 論理層（GB符号, SHYPS, 表面符号, GKP）
    ├── 04_hardware/                # ハードウェア（8ラック構成）
    ├── 05_loss-budget/             # 損失予算
    ├── 06_performance/             # 性能予測（DV版）
    ├── 07_control-decoding/        # 制御・デコーダ
    ├── 08_layout-cooling/          # レイアウト・冷却
    ├── 09_bom-cost/                # BOM・コスト
    ├── 11_risk-assessment/         # リスク評価（※10_は欠番）
    ├── 12_references/              # 参考文献
    ├── 13_ml-subsystem/            # MLサブシステム
    ├── 14_future-vision/           # 将来ビジョン
    ├── 15_appendix/                # 付録 A-E
    └── 16_changelog/              # バージョン履歴
```

---

## クイックナビゲーション

### 読む順序（推奨）

1. `design/00_overview.md` — 全体像を把握
2. `design/01_system-architecture.md` — システム構成
3. `design/06_noise-budget.md` — 性能の根拠
4. `design/13_performance.md` — 論理エラー率予測
5. `experiments/01_gkp-optical.md` — 次のアクション

### 目的別

| 目的 | 参照先 |
|------|--------|
| 投資家向け説明 | `design/00_overview.md` + [`Investor Pitch (PDF)`](assets/TAROS_Investor_Pitch.pdf) |
| 技術デューデリジェンス | `design/06_noise-budget.md` + `design/13_performance.md` |
| 実験計画 | `experiments/` |
| コスト見積もり | `analysis/bom.md` |
| リスク評価 | `analysis/risk.md` |
| 製品仕様 | `design/10_portable.md` |
| DV方式との比較 | `fallback/` + `archive/` |

---

## 設計パラメータチェーン

```
PPLN OPA σ_gen=13dB ──┐  v2.0 ビームスプリッタモデル (旧 σ_gen−L は不正確)
                       ├──→ σ_eff = 5.0dB (現離散, L=1.42dB)
L_total (Phase依存) ──┘         / 8.5dB (Phase 1, L=0.39dB, 13dB, non-loss込み)
                                / ≈9.3dB (Phase 2+ PIC現実的, L=0.27dB, non-loss込み) → p_L≈3.3×10⁻⁴ (MWPM)
                                / 10.8dB (Phase 2+ PIC理論限界, L=0.15dB) → p_L≈6.1×10⁻⁷ (MWPM)
(design/06_noise-budget.md v3.6)                                  (design/13_performance.md)
```

---

*CV方式の正確な数値は `design/` を参照。`archive/` の数値（8ラック/42.5kW/2,760kg等）はDV-FBQC旧設計のもの。*
