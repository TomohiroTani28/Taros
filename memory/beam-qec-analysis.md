# Beam QEC/デコーダ/性能分析 - 2026-05-08 完了報告

## 分析範囲
- design/00_overview.md, _parameters.md, 04_gkp-protocol.md, 06_noise-budget.md, 08_decoder.md, 13_performance.md
- analysis/FEASIBILITY_CONSISTENCY_REPORT.md, phase-minus1-execution.md, bom.md, risk.md

## 主要発見

### ✅ PASS: パラメータ整合性
- σ_eff（8.5dB Phase 1、≈9.3dB Phase 2+ 現実的、10.8dB 理論限界）: 全文書統一
- p_L値: ±0.1×10⁻⁴の誤差で統一
- beamsplitter モデル V_eff = η×V_sqz+(1−η)+V_non-loss universal適用
- erfc再計算 + V_non-loss=0.010 SNU補正も正しく反映

### 🚨 重大矛盾 5件 (MAJOR)

**M1: σ_eff v3.6補正の遡及反映が不完全**
- V_non-loss=0.010 SNU値が06_noise-budget.md§2.3に記載されるも、_parameters.md§2.2では「non-loss込み」としか記載なし
- 影響: シミュレーション±5%精度内での差分確認に

**M2: UF vs MWPM選択基準が曖昧（最重大リスク）**
- Phase 1: UF primary (p_L~4×10⁻³, 製品要件超過)
- Phase 2+: MWPM primary (p_L~3.3×10⁻⁴, 製品達成)
- **性能差30倍なのに根拠が「実験用ベースライン」と軽く記載**
- **潜在リスク**: Phase 1でUF検証成功→Phase 2+でMWPM切替時に予期しない再評価発生

**M3: 有限エネルギーGKP(Δ)のGo/No-Go基準が不明確**
- 04_gkp-protocol.md: Δ<0.15(製品), <0.10(目標)
- 06_noise-budget.md: Δ=0.20でd=9検討、Δ=0.3で動作不能
- **未定義**: Phase -1でΔ≥0.15実測時の判定フロー

**M4: Phase 0-1 WDM導入リスク未計上**
- Phase -1: Option B, WDMなし, L=0.39dB, σ_eff=8.5dB
- Phase 0-1: WDM導入時 L→0.59dB予想
- **未記載**: σ_eff低下推定値、コスト影響、margin喪失対応

**M5: Phase 1 break-even定義の物理妥当性未確認**
- 記載: p_L(MWPM)≈4.4×10⁻³を「break-even実証」
- **問題**: p_L > p_err なので厳密にはbreak-evenではなく「閾値超過」
- 論文根拠Stafford-Menicucci-Walshe 2025の精読が必須

### 🟡 軽微矛盾 3件 (MINOR)

- N1: FEASIBILITY_CONSISTENCY_REPORT.md(5/7)は v3.6修正未反映の可能性
- N2: 配線損失合計値差分0.03dB(0.61vs0.64dB)の説明不足
- N3: phase-minus1-execution.md T0bでUF/MWPM性能差定量評価が明記なし

## Phase -1確認項目（優先度順）

### P0（Go決定の前提）
1. T0b Stimで以下を定量化:
   - UF soft-info p_th_UF=1.0% (GKPノイズモデル検証)
   - MWPM soft-info p_th=1.5% (Noh-Chamberland確認)
   - UF vs MWPMの性能比較表作成 → Phase 1/2+選択根拠実証

2. T0a-T0c光学実験でMilestone追加:
   - Δ<0.15測定方法確定(Wigner vs ホモダインσ_meas)
   - Go/No-Goフロー明記(Δ≥0.15時→d=9拡張?条件付きNo-Go?)

### P1（Phase 0設計着手前）
- WDM導入時σ_eff推定値、コスト影響、margin対応戦略を整理
- Phase 1→2+移行でのUF→MWPM切替リスク評価

## 最終評価
- **物理矛盾**: なし ✓
- **実験計画の曖昧性**: 3件（M2, M3, M4）→ phase-minus1-execution.md詳細化で解消可能
- **信頼度**: design仕様の内部一貫性は高い。実験・移行時の分岐戦略が未整理

## 他チームへのメッセージ
- **Akira**: EO gate損失矛盾について追加回答待ち（05_phase-lock.md確認依頼）
- **Delta**: p_acc=93%の根拠確認依頼（04_gkp-protocol.md §2.2）
- **Cross**: archive参照パス、FROZEN banner確認中
- **team-lead**: 上記5件MAJORリスク、3件MINORについて Phase -1 Task詳細化を推奨
