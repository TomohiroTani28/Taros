> **⚠ FROZEN (2026-05-04)**: 本文書はDV-FBQC v4.0 R6時点の設計を記録したものです。プロジェクトの主軸はCV方式に移行しています。最新設計は `design/00_overview.md` を参照してください。

## 7.2 しきい値マージン分析（全面改訂）

### 7.2.1 Boosted Fusion閾値

Boosted fusion（Type-II, ancilla Bell pair 2個使用）の閾値は、Gimeno-Segovia+ 2015 [Phys. Rev. X 5, 041007] により以下が示されている:

- **全損失閾値**: 6%（これは fusion gate のphoton loss threshold であり、end-to-end loss ではない）
- **注意**: 6%閾値はfusionゲート自体の損失に適用される。end-to-endの光子損失はerasureとして処理され、別の閾値体系で管理される。

### 7.2.2 Erasure閾値とDepolarizing閾値の分離管理

v2.0では全損失を単一の閾値で評価していたが、v3.0ではerasure errorとdepolarizing errorを分離して管理する。これはフォトニック系の重要な利点を活用するものである。

**表7.4: 誤り閾値の分離管理**

| 誤りの種類 | 発生メカニズム | Phase 3 推定値 | 閾値 | マージン | 出典 |
|---|---|---|---|---|---|
| Erasure | 光子損失（検出されない） | 36-40% | ~50% (SHYPS) | 10-14 pt | Stace+ 2009; SHYPS: Sahay+ 2023 |
| Depolarizing | HOM不完全性, 位相誤差, ダークカウント | 0.7-1.0% | ~2-3% | 1-2 pt | Bartolucci+ 2023; Bombin+ 2023 |

**符号依存性**:

| 符号 | Erasure閾値 | Depolarizing閾値 | 備考 |
|---|---|---|---|
| SHYPS (Sahay+ 2023) | ~50% | ~1.5% | erasure耐性が最も高い |
| 4D Hyperbolic Product Code | ~30% | ~3% | depolarizing耐性が高い |
| 表面符号 (Raussendorf lattice) | ~24.9% | ~2.9% | 基準; Stace+ 2009 |

**3パス並行戦略**:
- v3.0では SHYPS / 4D HPC / 表面符号の3符号を並行で開発・評価する
- Phase 1-2ではerasure率が高いため、SHYPS（erasure閾値~50%）を主パスとする
- Phase 3でerasure率が改善された場合、4D HPCへの移行も検討

### 7.2.3 Stimシミュレーション検証計画

v2.0ではerasure率・depolarizing率から論理誤り率を解析的に外挿していたが、v3.0ではStim [Gidney 2021, Quantum 5, 497] による数値シミュレーションで検証する。

**シミュレーション計画（Phase -1 で実行）**:

| シミュレーション | 入力パラメータ | 出力 | 計算規模 |
|---|---|---|---|
| SHYPS回路シミュレーション | p_erasure=40%, p_depol=1.0%, d=3,5,7,9 | 論理誤り率 p_L(d) | ~10⁸ shots / d → GPU数時間 |
| 4D HPC回路シミュレーション | 同上 | 同上 | 同上 |
| Boosted fusion回路モデル | fusion成功率97%, ancilla fidelity 99% | 有効p_erasure, 有効p_depol | 解析 + 数値 |
| 損失感度分析 | p_erasure をスイープ (30-55%) | 閾値マージンのマッピング | GPU数日 |

**判定基準**: Stimシミュレーションで p_L < 10⁻³（符号距離 d=7 以下で）が確認されない場合、Phase 2 の移行判定は不合格とする。

---
