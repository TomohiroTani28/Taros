> **⚠ DEPRECATED**: 本文書はDV-FBQC方式に基づいており、CV方式移行に伴い数値（コスト・確率・スケジュール）は現行計画と大幅に異なります。CV方式の最新情報: `analysis/bom.md`, `analysis/risk.md`, `analysis/development-cost-summary.md`

## 16.8 最優先アクション

セクション16の内容を実現するための最優先アクション（Phase -1と並行、6ヶ月以内）を以下に規定する。

| # | アクション | 投資額 | 期待成果 |
|---|---|---|---|
| 1 | Floquet-FBQC符号のシミュレーション研究 | 約500万円 | 閾値マージン拡大の定量的評価 |
| 2 | Phase 0最小構成の調達・構築 | 約4,500万円 | 基礎実証データの取得 |
| 3 | ベイズ-GNN/Transformerデコーダ PoC | 約500万円 | デコーダ性能の実証 |
| 4 | NICT量子ネットワーク計画との連携協議 | 渡航費程度 | 量子インターネット展開の基盤 |
| 5 | 産業パートナー初期コンタクト | 渡航費程度 | 金融（量子乱数）、通信（QKD）分野の収益化準備 |

### 16.8A R3追加最優先アクション（v4.0 R3新規）

第3ラウンド専門家会議で特定された統合フォトニクス技術の検証に向けた追加アクション:

| # | アクション | 投資額 | 期待成果 | 担当専門家 |
|---|---|---|---|---|
| 6 | Transfer Printing基礎実証（16 QD on SiN PIC） | 約800万円 | QD→PIC結合損失0.3dBの実証、歩留まり95%の確認 | Senellart |
| 7 | WI-SNSPD試作（64素子 on SiN導波路） | 約600万円 | 検出効率>99%、歩留まり80%の確認 | Berggren |
| 8 | LNOI+SiNヘテロジニアス集積テストチップ | 約500万円 | チップ内LNOI-SiN結合損失<0.1dBの実証 | Lončar |
| 9 | Belief Matching+Soft InformationのStimベンチマーク | 約200万円 | erasure閾値29.5%の数値確認 | Higgott |
| 10 | 弾道的RSGのStimシミュレーション | 約200万円 | k≥4弾道方式のerasure率・閾値マージン定量化 | Rudolph, Breuckmann |
| 11 | DNANFコンパクトスプール試作（曲げ半径5cm、100m） | 約300万円 | 長期信頼性（1000時間）の実測データ取得 | Poletti |
| 12 | 相関erasureデコーディングのプロトタイプ実装 | 約300万円 | 相関利用による閾値改善+3-5ptの実証 | Breuckmann |

**R3追加アクション合計**: 約2,900万円（既存アクション約6,000万円と合算で約8,900万円）

### 16.8B R4追加最優先アクション（v4.0 R4新規）

第4ラウンド専門家会議で特定されたアーキテクチャ刷新に向けた追加アクション:

| # | アクション | 投資額 | 期待成果 | 担当専門家 |
|---|---|---|---|---|
| 13 | GB符号 [[144,12,12]] のFBQC融合ネットワーク埋め込み設計 | 約400万円 | Tanner graph→fusion network変換の完成、Stim閾値マップ | Breuckmann |
| 14 | Floquet-GB符号のStimシミュレーション（~100GPU時間） | 約200万円 | Single-Shot + GB符号の組み合わせerasure閾値の定量化 | Breuckmann, Higgott |
| 15 | Ambiguity Clusteringルックアップテーブル生成（GB d=12） | 約300万円 | 16MBテーブル生成、FPGA実装仕様書 | Higgott |
| 16 | QDM biexciton cascade実証（4個のQDM） | 約500万円 | entanglement fidelity >0.85、4光子GHZ状態品質 | Senellart |
| 17 | 決定論的ベル対のFSS制御実証（ストレインチューニング） | 約300万円 | FSS<1μeV制御の成功率>50% | Senellart |
| 18 | Upconversion検出PoC（PPLN+Si SPAD） | 約50万円 | 室温検出効率の実測値、g²(0)劣化評価 | Lončar |
| 19 | Ce:YIG磁気光学アイソレータのSiN PIC集積テスト | 約400万円 | アイソレーション>20dB、挿入損失<0.5dB | Lončar, Senellart |
| 20 | Photon Harvesting回路のシミュレーション設計 | 約100万円 | EOスイッチ配置最適化、迂回損失バジェット | Berggren |
| 21 | SNCM（超伝導ナノワイヤ光メモリ）の文献調査・PoC計画 | 約50万円 | 保存時間>1μs、効率>90%の達成可能性評価 | Berggren |

**R4追加アクション合計**: 約2,300万円

### 16.8C R5追加最優先アクション（v4.0 R5新規）

| # | アクション | 投資額 | 期待成果 | 担当 |
|---|---|---|---|---|
| 22 | ソフトウェアスタック Layer 1-2（RTOS + HAL） | $100K | Phase 0制御系基盤 | Higgott |
| 23 | ソフトウェアスタック Layer 3（符号インターフェース） | $150K | GB/Floquet/表面符号抽象化 | Higgott, Breuckmann |
| 24 | Pilot Tone同期モジュール設計・試作 | $30K | ±1ps位相同期実証 | Rudolph |
| 25 | CNOT並列化コンパイラ プロトタイプ | $80K | GB符号lattice surgeryの並列度~10実証 | Breuckmann, Higgott |
| 26 | Flip-Chip Bonding プロセス確立 | $200K | LNOI on SiN歩留まり85%実証 | Lončar |
| 27 | クライオサイクル試験（300K↔4.2K、1000回） | $50K | CTE差動収縮耐性確認 | Lončar, Berggren |
| 28 | QCI自動テストフレームワーク v1 | $100K | 日次回帰テスト自動化 | Higgott |

**R5追加アクション合計**: 約$710K（約1,070万円）
**全ラウンド合算（R1-R5）**: $400K + $193K + $153K + $710K = **約$1.46M（Phase -1投資）**
**Phase 0実験計画（SS12.5）**: $1.1M
**ソフトウェアスタック残（Layer 4-5、Phase 1）**: $500K
**Phase -1〜Phase 1の総ソフトウェア+ハードウェア投資**: **約$3.06M**

> この$3.06Mは、Phase 1「保証された成果物」（4-8論理qubitレベルB実証、$2.2M）と重複する部分を含む。純増分は~$0.86Mであり、R3-R4技術が成功した場合のアップサイド（42論理qubit、3.5MHz Tゲート）に対する投資として合理的。

### 16.8D R6追加最優先アクション（v4.0 R6新規）

第6ラウンド専門家会議で特定された量産化・QFC改善・製造標準に向けた追加アクション:

| # | アクション | 投資額 | 期待成果 | 担当 |
|---|---|---|---|---|
| 29 | QFC 12ch並列検証 + 82%プロセス再現 | $120K | QFC効率0.75-0.82の12ch同時達成確認 | Senellart, Lončar |
| 30 | InP QD 1550nm直接発光評価（QFC除去パス検証） | $80K | V>0.95+g²(0)<0.02+輝度>0.40のGo/No-Go | Senellart |
| 31 | SNSPD Mist CVD + KrFステッパ量産プロセス確立 | $150K | 歩留まり82%（1,500素子）、コスト$30/素子の検証 | Berggren |
| 32 | GB [[72,12,6]] Stimシミュレーション | $30K | 最小構成用符号のerasure閾値定量化 | Breuckmann |
| 33 | クライオパッケージング標準設計・試作 | $60K | V-groove光接続+NbTiフレックスRF配線の評価 | Lončar |
| 34 | Transfer Printingダイアタッチ自動化プロトタイプ | $200K | 300 QD/4時間、歩留まり97%の実証 | Berggren, Senellart |
| 35 | 自動較正パイプライン Layer 1（物理較正）実装 | $50K | PIDフィードバック+ベイズ最適化のFPGA実装 | Higgott, Berggren |
| 36 | RTNLEソフトウェア開発 | $50K | ベイズノイズ推定エンジンのGPU実装 | Higgott |
| 37 | 量子ベンチマークスイート v1 | $20K | QV/CLOPS/LER/TPS/MTBF/FER自動測定フレームワーク | Higgott |
| 38 | SNSPD BIST機能設計・試作 | $10K | オンチップテスト光源+分配導波路の検証 | Berggren |
| 39 | QD自動PL-HOM連続評価装置導入 | $30K | QDスクリーニング速度1hr/QD→6min/QDの確認 | Senellart |
| 40 | クライオ環境HCF基礎特性評価 | $20K | 4.2KでのHCF損失・位相安定性の実測 | Poletti |
| 41 | On-chip QFCテストチップ設計 | $20K | LNOI+SiN PIC上QFCの設計仕様書 | Lončar |

**R6追加アクション合計**: **$840K**（約1,260万円）
**全ラウンド合算（R1-R6）**: $1.46M + $840K = **約$2.30M（Phase -1投資）**
**Phase 0実験計画（SS12.5）**: $1.1M
**ソフトウェアスタック残（Layer 4-5、Phase 1）**: $500K
**Phase -1〜Phase 1の総投資**: **約$3.90M**

> R6の追加$840Kは、(1) QFC効率改善でηを0.48→0.53-0.57に引き上げ（レベルB確率+5pt）、(2) SNSPD量産でコスト$255K削減（Phase 1以降のランニング効果）、(3) 自動較正・RTNLEで運用信頼性を確保する投資。ROIは初年度から正。

---

