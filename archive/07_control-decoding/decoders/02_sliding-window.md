> **⚠ FROZEN (2026-05-04)**: 本文書はDV-FBQC v4.0 R6時点の設計を記録したものです。プロジェクトの主軸はCV方式に移行しています。最新設計は `design/00_overview.md` を参照してください。

## 9.4 Sliding Windowデコーダとソフト情報デコーディング（v4.0 R3新規）

### 9.4.1 Sliding Windowデコーダ（Higgott提案）

v4.0のSS9.1-9.3ではデコーダレイテンシ<2μsをハード要件としているが、**Sliding Window方式**によりデコーダレイテンシの制約を大幅に緩和する。

**原理**:
1. 各サイクルのシンドロームを順次蓄積
2. 過去W個のサイクル分のシンドロームウィンドウでデコード
3. 最古のサイクルの復号結果のみを確定し、パウリフレームに反映
4. ウィンドウを1サイクル分スライドして次のデコードを開始

```
時間軸:  t=1  t=2  t=3  t=4  t=5  t=6  t=7 ...
Window1: [===W=5===]
Window2:      [===W=5===]
Window3:           [===W=5===]
確定:    t=1       t=2       t=3
```

**レイテンシの扱い**:
- デコーダの処理時間: W × T_cycle（例: W=10, T=2μs → **20μs**）
- パウリフレーム追跡により、この遅延は**データ面では問題にならない**
- 蒸留レーンのフィードフォワードのみ、追加HCF遅延（~6km）で対応

### 9.4.2 ハイブリッドデコーダ構成（R3推奨）

Sliding WindowによりGPUデコーダがデータ面で使用可能になるため、Phase 1のデコーダ構成を以下に変更する。

| 処理面 | v4.0構成 | R3推奨構成 | メリット |
|--------|---------|-----------|---------|
| データ��� | FPGA×2（Union-Find） | **GPU×1（Belief Matching、Sliding Window）** | アルゴリズム柔軟性、閾値改善+4.6pt |
| 蒸留面 | GPU×1（MWPM） | **FPGA×1（Union-Find、リアルタイム）** | 蒸留フィードフォワードの確実性 |

**コスト影響**: FPGA×2($40K) + GPU×1($30K) = $70K → FPGA×1($20K) + GPU×1($30K) = **$50K**（$20K削減）

### 9.4.3 Belief Matching + Soft Information（Higgott提案）

PyMatching v3で実装された**Belief Matching + Soft Information**デコーダにより、erasure閾値を大幅に改善する。

**Soft Information**の供給源:
1. **MKID方式SNSPD**: 各検出器の共振周波数シフト量から、光子検出の確信度（0-1の連続値）を取得
2. **CNN demux（SS15.3）**: 行列読み出しの信号から、各ピクセルの発火確率を連続値で出力
3. **QD状態監視**: 各QDの現在の出力品質（HOM visibility推定値）をリアルタイムで供給

**デコーダへの入力形式**:
```
Hard syndrome:  [0, 1, 1, 0, 1, 0, ...]  (binary)
Soft syndrome:  [0.02, 0.95, 0.87, 0.05, 0.99, 0.03, ...]  (probability)
Erasure mask:   [0, 0, 0, 1, 0, 0, ...]  (binary)
Confidence:     [0.98, 0.90, 0.85, 0.10, 0.99, 0.97, ...]  (0-1)
```

**閾値改善の定量的効果**:

| デコーダ構成 | erasure閾値 | depolarizing閾値 | GPU処理時間(d=7) |
|------------|------------|-----------------|-----------------|
| Union-Find（hard） | 24.9% | 1.0% | — |
| MWPM（hard） | 24.9% | 1.0% | <1ms |
| Belief Matching（hard） | 26.5% | 1.1% | <5ms |
| **Belief Matching + Soft** | **29.5%** | **1.3%** | **<5ms** |
| **Belief Matching + Soft + 相関erasure** | **~34%** | **~1.5%** | **<10ms** |

**レベルA到達への影響**:
- v4.0: η>0.866必要（erasure閾値24.9%）
- R3（Belief Matching + Soft + 相関erasure）: η>**0.82**必要（実効閾値~34%）
- **必要η改善量: 5.3%ポイント削減** → Phase 2でのレベルA到達確率を大幅に改善

### 9.4.4 Phase別デコーダ移行計画（R3更新）

| Phase | デコーダ | データ��� | 蒸留面 | レイテンシ | 消費電力 |
|-------|---------|---------|--------|----------|---------|
| **Phase 0** | GPU (H200) | MWPM/UF/QNBP並列評価 | MWPM（バッチ） | <1ms | 2.8kW |
| **Phase 1（R3）** | **GPU+FPGA** | **Belief Matching+Soft（Sliding Window）** | **Union-Find（FPGA、リアルタイム）** | **20μs（データ面）/ <2μs（蒸���面）** | **330W** |
| **Phase 2（R3）** | **ASIC+GPU** | **ASIC（Belief Matching+相関erasure）** | **ASIC** | **<500ns** | **50W** |

