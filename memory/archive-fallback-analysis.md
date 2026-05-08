# Archive & Fallback 分析メモ (2026-05-08)

## Summary
Cross による archive/ + fallback/ 全文精読完了。
- **FROZENバナー**: 全ファイル適切 ✅
- **DV/CV分離**: 明確 ✅
- **内部矛盾**: 3つの重要な不整合を発見 🔴

## 発見内容

### 1. QFC効率の曖昧性
**archive/02_physical-layer/qfc/01_lnoi-qfc.md** §4.3.2-3.4
- R6目標: end-to-end > 75% (保守) / > 82% (楽観)
- C44注記: 「5デバイス中4で>75%再現」→ 82%の再現性が曖昧
- **量産リスク**: 単一デバイス性能≠量産ロット性能

### 2. 符号仕様の不連続性（v4.0 R6 → v5.0）
**archive/ vs fallback/ の符号選択**
- archive (v4.0 R6): **GB [[144, 12, 12]]** (Primary)
  - 物理qubit: 144
  - 論理qubit: 12
  - 位置づけ: R4で SHYPS から昇格

- fallback/02 (v5.0): **Floquet-GB [[72, 12, 6]]** (Desktop)
  - 物理qubit: 72 (半減)
  - 論理qubit: 12 (同等)
  - 新機能: Single-Shot対応
  - 問題: これは「v4.0継承」ではなく新設計

### 3. 損失定義の複数層構造
**archive/02_physical-layer/photon-efficiency/01_loss-budget-overview.md** §4.4
- 層1: **全経路η = 14.4%** (QD → 検出)
- 層2: **ヘラルド後η = 84.7%** (リソースステート生成後)
- 符号閾値の評価では層2を使用すべき
- **design/ との対応関係が未確認**

## fallback/ 内部矛盾

### v4.0 継承 vs 新技術選択
**fallback/02_dv-fbqc-desktop-v5.0.md** SS0:9行目
- 主張: 「v4.0 R6の56合意事項C1-C56を全継承」
- 実装: 実際には6つのBreakthrough (B1-B6) を新統合
  - B1: InP QD 1550nm (C43の「Phase 2オプション」→ Phase D/D+ で Primary に昇格)
  - B2: PsiQuantum Omega (新情報)
  - B3: PT205 8.6kg (v4.0では未定義の冷却器)
  - B4: WI-SNSPD 99.73% (新プロセス)
  - B5: Floquet符号 6.3% 閾値 (新技術)
  - B6: GB-FBQC実装論文 (新論文)

**結論**: fallback/02 は「v4.0の拡張」というより「v4.0をベースとした新設計 v5.0」

## archive/ × fallback/ パラメータ対応表

| パラメータ | archive (v4.0 R6) | fallback/02 (v5.0) | 差分 | 検証状態 |
|-----------|-----------------|------------------|------|--------|
| **筐体** | 60m² (Phase 0) / 2.5m² (Phase 1) | **60×40×50cm (Desktop)** | 体積大幅削減 | 要確認 |
| **符号** | GB [[144,12,12]] | **Floquet-GB [[72,12,6]]** | 物理qubit半減 | ❌ 矛盾 |
| **SNSPD数** | 1,500-3,000個 (Phase 1) | **~1,000個 (v5.0)** | 1/3 削減 | 要確認 |
| **冷却器** | PT 4.2K (v4.0では言及なし) | **PT205 2.5K, 8.6kg** | 新型 | ❌ 矛盾 |
| **QFC** | 0.57 → 0.75/0.82 (R6 C44) | **除去 (InP QD 1550nm)** | Phase 2→Phase Dで前倒し | ❌ 矛盾 |
| **論理qubit** | 4-12 (Phase 1 保証) / 42-100 (Phase 2) | **12 (Desktop) / 48 (4モジュール)** | 同レベル | ✅ 整合 |
| **消費電力** | 8kW (Phase 1) / 6kW (Phase 2) | **2.1kW (Desktop)** | 1/4 削減 | 要確認 |
| **コスト (量産)** | 不明確 | **~約6,480万円/台** | 初量産価格 | 要確認 |

## design/ との整合確認が必須な項目

1. **QFC効率定義**: design/ は archive/R6 の 0.75/0.82 をどう扱っているか
2. **GB符号仕様**: design/ が使用する GB [[n, k, d]] のパラメータ
3. **損失バジェット**: design/ のヘラルド後η / 全経路η の定義
4. **PT冷却器**: design/ のPT205 vs 他モデルの選択根拠
5. **SNSPD数**: design/ と fallback/02 の 1,000個 の整合性

## 参照ファイル
- archive/README.md (l.1-20): 適切なFROZENバナー
- archive/00_summary/metadata.md: v4.0 R6 全体構成
- archive/01_architecture/01_abstract.md: 詳細な改訂履歴
- fallback/01_deskside-vision.md: デスクトップ概念設計
- fallback/02_dv-fbqc-desktop-v5.0.md: v5.0 完全設計書
- fallback/03_hybrid-pic-design.md: CV+QD ハイブリッド（最新位置づけ未確認）
