### 5.11 Floquet符号のSingle-Shot QEC（v4.0 R4新規、Breuckmann提案 C22）

2025年にDavydova+がFloquet符号のSingle-Shot性を証明した。これはFBQCアーキテクチャの計算速度を根本的に変える。

#### 5.11.1 Single-Shot QECの効果

従来のQEC（表面符号・SHYPS等）では、信頼性のあるシンドロームを得るために**d回の繰り返し測定**が必要:
```
T_logical_cycle = d × T_physical_cycle
d=7, T_physical=2μs → T_logical = 14μs
```

Single-Shot QECでは**1回の測定で十分**:
```
T_logical_cycle = 1 × T_physical_cycle = 2μs
```

**7倍の高速化**（d=7の場合）。

#### 5.11.2 Floquet Interleavingとの組み合わせ（Rudolph提案 C16）

Floquet符号のA/B/C周期的スタビライザ測定をインターリービングサイクルに同期:

| 構成 | インターリービング深度 | Single-Shot | 論理qubit | サイクル時間 | Tゲートレート |
|------|---------------------|-----------|----------|-----------|------------|
| R3（通常） | 8 | なし | 32 | 4μs | ~250kHz |
| R4（Floquet同期） | 8 | **あり** | **42** | **2μs** | **3.5MHz** |

#### 5.11.3 Floquet-GB符号の適用可能性

GB符号はFloquet構造と互換性がある。GB符号のcyclic対称性がFloquet符号の周期的測定と自然に対応するため、**Floquet-GB符号**としてSingle-Shot + 高符号レートの両立が可能。

検証課題:
- Floquet-GB符号のStimシミュレーション（Phase -1で実施、計算コスト~100GPU時間）
- erasure閾値の確認（Floquet化による閾値変化の定量評価）

