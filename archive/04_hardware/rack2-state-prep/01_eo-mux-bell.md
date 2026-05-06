> **⚠ FROZEN (2026-05-04)**: 本文書はDV-FBQC v4.0 R6時点の設計を記録したものです。プロジェクトの主軸はCV方式に移行しています。最新設計は `design/00_overview.md` を参照してください。

## 6.2 Rack 2: 状態準備・多重化（LNOI EO制御）

### 6.2.1 LNOI EO位相シフタ

v2.0ではBaTiO₃ベースのEOシフタを想定していたが、Critical Reviewにおいて以下が指摘された:
- BaTiO₃のLoss tangentが高く（>1dB/cm）、集積化時の累積損失が許容範囲を超える
- BaTiO₃ PICの商用ファウンドリが存在しない（研究段階に留まる）
- LNOIは商用MPWサービスが利用可能（HyperLight Technologies, Lume Photonics）

v3.0ではLNOI EO位相シフタを全面採用する。

**表6.4: LNOI EO位相シフタ仕様**

| パラメータ | 仕様値 | 根拠・出典 |
|---|---|---|
| プラットフォーム | X-cut LNOI（薄膜LiNbO₃ on SiO₂/Si） | Wang+ 2018, Nature 562, 101; 商用: HyperLight |
| 半波長電圧 (Vπ) | ~5 V（電極長10mm） | HyperLight公開データ: Vπ·L ~ 5 V·cm; 10mm → Vπ = 5V |
| 変調帯域 | > 40 GHz（3dB） | 本設計では1GHz以下で十分; Wang+ 2018 実証値 > 100 GHz |
| 応答時間 | < 1 ns | EO効果は本質的にfs応答; 制限要因はRC時定数 |
| 消光比 | > 25 dB（MZI構成時） | HyperLight仕様; 典型実証値 25-30 dB |
| 挿入損失 | < 0.5 dB / シフタ | LNOI導波路損失 ~0.03 dB/cm × 10mm + 結合損失; 商用品実測値 0.3-0.5 dB |
| 動作温度 | 室温 | LNOIはクライオ動作も可能だが、本設計ではRack 2は室温 |
| チップサイズ | ~20mm x 5mm（MZI 1個） | HyperLight MPWのダイサイズ |
| 駆動電子回路 | 50Ω整合ドライバ, 振幅5V, 帯域1GHz | 商用品: SHF 804EA相当; 50MHz駆動には十分 |

### 6.2.2 時間多重化設計（深さ4）

QD光子源の確率的性質（50MHzでon-demand発光だが、端面→ファイバ効率が確定的でない）に対し、時間多重化（temporal multiplexing）によりヘラルド単一光子の供給確率を向上させる。

**多重化パラメータ**:

| パラメータ | 値 | 根拠 |
|---|---|---|
| 多重化深さ | 4（= 4タイムビンから1光子を選択） | MUX深さ m=4 で供給確率 P = 1-(1-η)^4; η=57% → P = 96.6% |
| スイッチング素子 | LNOI MZI（2x2） | 表6.4の仕様に準拠 |
| スイッチ段数 | log₂(4) = 2段 | バイナリツリー構成 |
| 遅延ファイバ長 | 1τ = 20ns → 4.0m (SMF-28), 2τ = 8.0m | τ = QD繰り返し周期 = 1/50MHz = 20ns |
| 遅延ファイバ損失 | < 0.01 dB (4m SMF-28 @ 1550nm) | SMF-28損失 0.18 dB/km × 0.004km |
| MUX全体の追加損失 | < 1.2 dB（スイッチ2段 × 0.5dB + 遅延 + 接続損失） | 各スイッチ0.5dB × 2段 = 1.0dB + ファイバ接続0.2dB |
| ヘラルド信号 | QD励起パルスとの同期カウントによるタイミング情報 | 検出信号は不要（on-demand源のため発光タイミングは既知） |

**注**: GaAs QD + open cavityの高効率源（η_end-to-end = 57%）を用いる場合、MUX深さ4で供給確率96.6%は十分である。仮にη = 40%に低下しても、P = 1-(1-0.4)^4 = 87%であり、MUX深さを8に拡張すれば P > 98% に到達可能。

### 6.2.3 Boosted Fusion用 Ancilla Bell状態生成

Boosted fusion [Grice 2011, Phys. Rev. A 84, 042331; Ewert & van Loock 2014, Phys. Rev. Lett. 113, 140403] では、補助的なBell状態 |Φ⁺⟩ を消費して融合成功確率を50%（bare fusion）から最大97%（Type-II boosted, 2 ancilla Bell pairs使用）へ引き上げる。

**Bell状態生成プロトコル**:

1. 2つの単一光子をPBS（偏光ビームスプリッタ）で入力
2. 50:50ビームスプリッタで干渉
3. 一方のポートで光子検出→ヘラルドにより他方にBell状態が射影

**表6.5: Ancilla Bell状態生成仕様**

| パラメータ | 値 | 根拠 |
|---|---|---|
| 生成方式 | ヘラルドBell状態（Type-I fusion成功をヘラルドとして利用） | Bartolucci+ 2023, Nature Commun. 14, 912 |
| 成功確率（bare） | 50% / 試行 | 線形光学の基本限界 |
| 必要供給レート | Boosted fusion 1回あたりBell pair 2個 | Ewert & van Loock 2014 |
| 品質（fidelity） | > 99%（生成時点） | 入力光子の不区別性（HOM > 98%）に依存; シミュレーションで検証要 |
| 光子消費 | 4光子 / Bell pair（成功率50%で平均2試行） | 12 QD × 50MHz = 600MHz の光子供給のうち、~30%をancilla生成に割当 |

**Rack 2 消費電力**: ~0.8 kW（EO駆動電子回路: ~0.5kW, 制御ロジック: ~0.3kW）
**Rack 2 設置面積**: 標準19インチラック 1本（42U）

---

