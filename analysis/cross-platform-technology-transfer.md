# 他方式量子コンピュータ技術のTaros転用分析

**Document ID**: PQC-ANALYSIS-XPLAT-v1.0
**Date**: 2026-05-07
**Status**: 調査完了
**対象**: Taros CV方式 (GKP + 表面符号, 1550nm TDM, Phase 0-1: 10-50論理qubit)

---

## Executive Summary

超伝導・トラップイオン・中性原子・シリコンスピン・トポロジカルの5方式と、
量子アルゴリズム最前線を調査した結果、以下の転用優先度が明確になった。

| 優先度 | 転用技術 | 出自 | Tarosへの影響 |
|--------|---------|------|-------------|
| **P0** | FPGA NNデコーダ (124ns) | 超伝導 (Google) | Stage 2デコーダ性能を3-5倍改善 |
| **P0** | ソフト情報付きqLDPC (SHYPS) | Photonic Inc. | 表面符号→qLDPC移行で物理qubit 20倍削減 |
| **P0** | Xanadu Si3N4 GKPオンチップ生成 | Xanadu (光) | Phase 2 PIC設計の直接参考 |
| **P1** | AlphaQubit 2 (NN decoder) | Google DeepMind | soft-info + NN = 最適デコーダ候補 |
| **P1** | IBM qLDPC FPGA decoder (480ns) | IBM | Relay-BP on AMD FPGA = 実装参考 |
| **P1** | QPE early-FTQC (25-100論理qubit) | 複数 | Phase 1-2のキラーアプリ特定 |
| **P2** | IonQ smooth gate (99.99%) | トラップイオン | GKPゲート忠実度の設計指針 |
| **P2** | NV-テレコム波長変換 (737→1350nm) | NVセンター | 将来のネットワーク接続 |
| **P2** | Microsoft トポロジカル保護 | トポロジカル | GKP符号のトポロジカル性活用 |

---

## A. 超伝導量子コンピュータ: デコーダ革命

### A.1 Google Willow (2024年12月~)

**成果**:
- 105 qubit superconducting processor
- QEC指数的誤り抑制を初実証: 3x3 → 5x5 → 7x7格子で符号化エラー率が2倍ずつ改善
- 論理エラー率 ~0.14%/cycle (d=7)
- Quantum Echoes (2025年10月): 初のハードウェア上検証可能な量子優位性

**Taros転用**:
- **指数的誤り抑制の検証方法論**: Tarosでもd=3→d=5→d=7でスケーリングを実証すべき。Phase 0でd=3, Phase 1でd=5の段階的検証計画に直接適用可能
- **注意**: Googleの論理エラー率0.14%は、Tarosの目標p_L~3.3x10^-4 (Phase 2+)より1桁悪い。CV方式のソフト情報優位性が有効に機能すれば、Tarosは超伝導方式と同等以上の性能を少ないリソースで達成しうる

### A.2 Google DeepMind AlphaQubit / AlphaQubit 2

**成果**:
- AlphaQubit: Recurrent Transformerベースのデコーダ。Sycamore実機データでMWPMより30%、テンソルネットワークより6%誤り低減
- **AlphaQubit 2 (2025-2026)**: 表面符号d=11までリアルタイムデコーディング (<1us/cycle)。Color codeでも初のリアルタイムデコーディング

**Taros転用 [P0-P1]**:
- **NNデコーダ + GKP soft-info の融合**: AlphaQubitのrecurrent transformer構造をGKPアナログ情報入力に適応させることで、現行のUF/MWPM soft-infoデコーダを大幅に超える性能が期待できる
- 具体的実装: Stage 1のp_err_i (連続値)をTransformerの入力特徴量として使用。格子点偏差delta_iの分布パターンを学習し、相関エラーを捕捉
- **リスク**: FPGA実装にはモデル圧縮が必要。VE2302/VE2802でのNN推論は要検証
- **推奨**: Phase 0ではUF soft-infoを使用し、並行してNN decoderをシミュレーションで訓練・検証

### A.3 FPGA NNデコーダ (550ns実証, 2026年5月)

**成果**:
- FPGA上NN推論124ns + 制御ループ合計550ns
- 超伝導QECサイクル1.25usに対し十分なマージン
- 124ns NN推論 = Taros Stage 2の設計目標 (<500ns)を大幅に下回る

**Taros転用 [P0]**:
- **直接適用可能**: TarosのQECサイクル6.86us (100MHz TDM)に対し、550ns全体レイテンシは8%以下
- Stage 2デコーダのNN化により、UF (350ns) → NN (124ns) + 高精度を同時達成の可能性
- FPGA実装のアーキテクチャ (NN重み量子化、パイプライン構造)を参考にすべき

### A.4 IBM: qLDPC符号 + リアルタイムデコーダ

**成果**:
- qLDPC (Bivariate Bicycle)符号: 表面符号比で物理qubit数を大幅削減
- IBM Relay-BP decoder: AMD FPGA上で480ns以内のリアルタイムデコーディング
- [[144,12,12]] BB符号: 12論理qubitを144物理qubitで実現 (表面符号d=12では最低288物理qubit必要)

**Taros転用 [P1]**:
- **表面符号→qLDPC移行ロードマップ**: Phase 2+でqLDPC導入を検討
- Relay-BPのFPGA実装技術をTarosデコーダ開発に活用
- ただしqLDPC符号はシンドローム抽出回路が複雑→TDMベースCV方式との整合性要検証

### A.5 Riverlane Local Clustering Decoder (LCD)

**成果**:
- Nature Communications掲載: リアルタイム、高精度、適応的なハードウェアデコーダ
- FPGA上で1us未満/ラウンド
- Deltaflow 3 (2026年末): "streaming logic"でQEC中の連続誤り訂正

**Taros転用 [P1]**:
- LCDのクラスタリング手法はTarosのUF decoderと類似→アルゴリズム比較検討
- "streaming logic"概念はTDM方式と親和性高い（時間方向にストリーミングされるsyndromeを連続処理）

---

## B. トラップイオン: 高忠実度ゲートとネットワーク接続

### B.1 IonQ: 99.99% 2-qubit fidelity (2025)

**成果**:
- Oxford Ionics "smooth gate" technique: 基底状態冷却なしで99.99%以上
- SPAM fidelity: 99.9993%
- 256-qubit prototype (2026)、1M qubit (2030) roadmap

**Taros転用 [P2]**:
- **GKPゲート忠実度設計指針**: イオントラップの99.99%ゲートは、GKP CZゲート (測定ベースCV)での目標忠実度設定の参考。Taros Phase 1のF_GKP=0.87-0.91は99%未満であり、改善余地を示唆
- smooth gate手法の「パルス整形による誤り抑制」原理は、OPAポンプパルス最適化に概念的に転用可能

### B.2 Quantinuum: 94論理qubit, beyond break-even (2026年3月)

**成果**:
- Helios: 48 error-corrected論理qubit (2:1物理/論理比)
- 94論理qubitでの量子計算実証: break-even超え、物理qubitより1桁以上低いエラー率
- Microsoft共同: 論理回路エラー率が物理回路の1/800

**Taros転用 [P1]**:
- **2:1比率の衝撃**: Quantinuumの2:1物理/論理qubit比は、表面符号の数百:1と比較して劇的に効率的。Tarosが将来qLDPC (SHYPS)を採用すれば同等の効率が狙える
- **QPE実機実行**: Quantinuumの化学分子シミュレーション (H2, STO-3G基底)は、Taros Phase 1での最初のアプリケーション候補として参考になる

### B.3 IonQ: 光子インターコネクト (2025)

**成果**:
- 2つの独立トラップイオンシステムを光子で接続: 初の商用量子コンピュータ間ネットワーク

**Taros転用 [P2]**:
- Tarosは本質的に光子ベース→テレコム波長(1550nm)での量子ネットワーク接続は自然な拡張
- Phase 2+でのマルチモジュール接続のアーキテクチャ参考

---

## C. 中性原子: 動的再配置とスケーラビリティ

### C.1 QuEra: 96論理qubit実証, 2:1比率 (2025)

**成果**:
- 96 verified論理qubit
- QEC overhead 100倍削減のアルゴリズム的fault tolerance技術
- 2025年: continuous operation, magic state distillation, dramatically reduced runtime overhead
- 2026: 100論理qubit / 10,000物理qubit (3世代目)

**Taros転用 [P1]**:
- **Magic state distillation効率化**: QuEraの手法をGKP表面符号のmagic state生成に適用。GKP符号はGaussianゲートが容易だが非GaussianゲートにはMagic stateが必要→distillation効率がTaros Phase 2+のボトルネック
- **動的再配置の思想**: 原子アレイの「必要な場所にqubitを移動」思想は、TDMベースの「時間的再配置」と等価→タイムスロット割り当て最適化に転用

### C.2 Harvard-QuEra: fault-tolerant architecture (2025)

**成果**:
- 96論理qubitで初の統合fault-tolerantアーキテクチャ
- below-threshold performance: スケーリングで論理エラー率が改善

**Taros転用 [P1]**:
- below-threshold検証の実験手法をTaros Phase 0 (d=3 break-even) に適用

---

## D. シリコンスピン / NVセンター: 室温接続とテレコム波長

### D.1 Diraq/imec: 99%+ fidelity in foundry chips (2025年9月)

**成果**:
- CMOS互換ファウンドリで99%以上の2-qubit fidelity
- EUVリソグラフィで量子ドットパターニング実証
- 商用半導体製造ラインとの完全互換性

**Taros転用 [P2]**:
- Phase 2+ PIC (Silicon Nitride)製造の参考: 300mmウェハ上での量子デバイス製造プロセス
- Tarosは既にPIC統合を計画 (Si3N4 on 300mm) → CMOS互換プロセスノウハウを活用

### D.2 シリコンスピンqubit: エラー検出 + 論理演算 (2026年2-3月)

**成果**:
- 安定化子によるシングルqubitエラー検出 (コヒーレンス保持)
- 5リン核スピンqubitsでの初の論理演算

**Taros転用 [P2]**:
- シリコンベースプラットフォームのエラー特性理解: 将来のSi3N4 PICとの共通基盤

### D.3 NVセンター: テレコム波長変換 (737→1350nm)

**成果**:
- 40km都市環境光ファイバでの量子もつれ分配
- 室温でのナノダイヤモンド-ナノアンテナ: 光子収集効率80%
- ゼロ磁場でのスピン制御技術

**Taros転用 [P2]**:
- **量子ネットワーク接続**: NVセンターの1350nm変換技術は、Tarosの1550nm系との将来的接続に関連
- ただし波長不一致 (1350 vs 1550nm) あり→QFC技術が必要
- 室温動作のNV量子メモリ + Taros光子プロセッサのハイブリッドは長期ビジョン

---

## E. Microsoft トポロジカル: Majorana 1

### E.1 Majorana 1 (2025年2月)

**成果**:
- 世界初のトポロジカルコアQPU: InAs/Al新材料スタック
- 8トポロジカルqubitを搭載、100万qubitスケーラビリティ設計
- QECオーバーヘッド従来比1/10
- DARPA US2QCプログラム最終段階に選出

**Taros転用 [P2]**:
- **GKPのトポロジカル保護との接点**: GKP符号はbosonic codeの一種であり、トポロジカル表面符号と連結することで「二重のトポロジカル保護」が得られる。Microsoftの10倍効率化アプローチの原理（トポロジカル保護による物理エラー率の本質的低減→QECオーバーヘッド削減）は、GKP符号の「ハードウェアレベルの連続変数エラー訂正」と概念的に等価
- **注意**: Majorana qubitは査読付き論文での完全な検証が未完了であり、技術的不確実性が残る

---

## F. 量子アルゴリズム: Taros Phase 0-1のキラーアプリ

### F.1 Early-FTQC QPE (25-100論理qubit)

**成果**:
- Kanasugi et al. (2026年3月): 鉄-硫黄クラスタ、CYP450活性部位、CO2利用触媒の基底状態エネルギー推定
  - 20-50 spatial orbitals → ~10^5物理qubitが必要
  - ランタイム: 数日~数週間

**Taros転用 [P0-P1]**:
- **Phase 1 (10-50論理qubit)で実行可能なアプリ特定**:
  - 小規模分子 (H2, LiH, H2O): d=3-5, 2-10論理qubitで実行可能 → Phase 0の最初のデモ
  - 中規模活性空間 (20 orbitals): ~50論理qubit → Phase 1後半
- **Single-ancilla Trotter-based QPE**: 必要量子ビット数が少なく、Tarosのリソースに適合
- **推奨**: Quantinuumの H2 QPEパイプライン (InQuanto) を参考にPhase 0アプリを設計

### F.2 量子最適化 (QAOA/VQE)

**成果**:
- 交通最適化: ハイブリッド量子アニーリングがGurobiの1%以内で渋滞25%削減
- 2026: 7,500 two-qubit gates実行可能
- 実用的ハイブリッド量子古典ループ

**Taros転用 [P1-P2]**:
- QAOA/VQEはNISQに最適化されており、Tarosの低~中規模論理qubitでは量子位相推定(QPE)の方が効率的
- ただしPhase 0の初期デモとしてVQEは有用 (回路深度が浅い)

### F.3 量子化学: Roche Alzheimer事例 (2025)

**成果**:
- 量子分子シミュレーション: Alzheimer候補薬3種を18ヶ月で特定 (従来4-6年)

**Taros転用 [P1-P2]**:
- 製薬応用は最も商業的価値が高い → ビジネスケース構築の参考
- ただしRocheの規模は大規模FTQC → Taros Phase 0-1では基礎分子に限定

---

## G. Taros直接関連: GKPオンチップ + qLDPC

### G.1 Xanadu: Si3N4 GKPオンチップ生成 (Nature, 2025年6月)

**成果**:
- 300mm Si3N4ウェハ上での超低損失フォトニックチップ
- 高効率光子数分解検出器 (>99%) とファイバ結合
- GKP状態のオンチップ生成を初実証
- 室温動作互換

**Taros転用 [P0]**:
- **Phase 2 PIC設計の直接参考**: Tarosの計画するSi3N4 PIC統合と同一プラットフォーム
- 300mmウェハプロセスのプロセスフロー参考
- GKP状態生成のパラメータ (squeezing level, postselection率) をTarosの04_gkp-protocol.mdと比較検証すべき
- **差異**: Xanaduは DV方式 (光子数分解+postselection)、TarosはCV方式 (ホモダイン+OPA) → 生成方法は異なるがチップ基盤は共通

### G.2 Photonic Inc.: SHYPS qLDPC (2025年2月)

**成果**:
- 表面符号比20倍の物理qubit削減
- Single-shot error correction (1回の測定で訂正)
- フォトニックプラットフォームに自然適合 (非局所接続)
- Fusion-based実装での解析

**Taros転用 [P0-P1]**:
- **最重要転用候補の一つ**: TarosがPhase 2+で表面符号からSHYPS/qLDPCに移行すれば:
  - d=7表面符号で必要な~200物理qubit → ~10-20物理qubitで同等の論理保護
  - TDMの時間リソースを大幅削減
- **課題**: qLDPC符号のシンドローム抽出がTDMアーキテクチャでどう実装されるか要検証
- Photonic Inc.の「fusion-based」実装はDV-FBQC前提→CV方式への適応は研究課題

### G.3 Soft-Info + qLDPC GKPデコーダ (2025年5月)

**成果**:
- qLDPC-GKP連接符号のcircuit-level noise下での性能分析
- リアルタイムソフト情報が連接デコーディングで大幅な性能向上
- 事前計算エラー確率では改善僅少 → リアルタイムsoft-infoが本質的

**Taros転用 [P0]**:
- **Tarosの2段デコーダ (08_decoder.md) の設計検証**:
  - Stage 1のp_err_i (GKP soft-info) → Stage 2 (表面符号/qLDPC) へのリアルタイム伝搬が性能の鍵
  - 事前計算weight vs リアルタイムweight: Tarosは現在リアルタイム計算を採用 (p_err_i = erfc(|delta|/(sigma*sqrt(2)))/2) → 正しい設計選択を確認
- この論文がMWPMの表面符号+GKPでの優位性を示唆→Tarosの「UF + soft-info vs MWPM + soft-info」選択に影響

---

## H. 統合転用ロードマップ

### Phase -1 (現在, Go/No-Go)

| 転用技術 | 実装方法 | 工数 | 期待効果 |
|---------|---------|------|---------|
| Willow指数的誤り抑制検証法 | d=3→d=5スケーリング実験計画策定 | 1週間 | Go/No-Go判定精度向上 |
| Bosonic Pauli+シミュレータ | GKP表面符号のclassicalシミュレーション | 2週間 | U1-U7未検証仮定の事前検証 |

### Phase 0 (break-even実証)

| 転用技術 | 実装方法 | 工数 | 期待効果 |
|---------|---------|------|---------|
| FPGA NNデコーダ (124ns) | VE2302上に小型NNを実装、UF fallback併用 | 3ヶ月 | デコーダレイテンシ 350→150ns、精度+15% |
| soft-info qLDPC論文の知見 | Stage 1→2のリアルタイムsoft-info伝搬最適化 | 1ヶ月 | p_L改善 (3.3e-4 → ~1e-4?) |
| H2 QPEデモ (Quantinuum参考) | d=3, 2-4論理qubitでVQE/QPE | 2ヶ月 | 初の実用デモンストレーション |

### Phase 1 (10-50論理qubit)

| 転用技術 | 実装方法 | 工数 | 期待効果 |
|---------|---------|------|---------|
| AlphaQubit 2型NNデコーダ | Transformer + GKP soft-info、VE2802実装 | 6ヶ月 | MWPM/UF比 30%+エラー低減 |
| qLDPC (SHYPS)評価 | CV-TDM上でのシンドローム抽出回路設計 | 6ヶ月 | 将来的に物理qubit 5-20倍削減 |
| QPE化学シミュレーション | LiH, H2O, 小活性空間 (10-20 orbital) | 4ヶ月 | 量子化学キラーアプリ |
| Magic state distillation効率化 | QuEra手法のCV適応 | 3ヶ月 | 非Gaussianゲートコスト低減 |

### Phase 2+ (製品化)

| 転用技術 | 実装方法 | 工数 | 期待効果 |
|---------|---------|------|---------|
| Si3N4 PIC (Xanadu参考) | 300mmウェハプロセス、GKP生成統合 | 12ヶ月 | PIC量産、コスト大幅削減 |
| qLDPC移行 | 表面符号→SHYPS/BB符号切り替え | 12ヶ月 | 物理リソース20倍削減 |
| テレコム量子ネットワーク | 1550nm + IonQ型光インターコネクト | 18ヶ月 | マルチモジュール接続 |

---

## I. 方式間比較: Tarosの競争優位性

| 指標 | 超伝導 (Google) | イオン (Quantinuum) | 中性原子 (QuEra) | **Taros CV (Phase 2+)** |
|-----|---------|---------|---------|---------|
| 動作温度 | 15mK | 室温 (真空) | ~1uK | **室温** |
| 論理エラー率 | 0.14% (d=7) | ~0.1% | ~0.1% | **~0.033% (d=7, MWPM)** |
| QECサイクル | ~1us | ~10ms | ~1ms | **~6.86us** |
| スケーラビリティ | 希釈冷凍機制限 | shuttling制限 | atom数制限 | **TDM無制限 (時間方向)** |
| デスクトップ可能 | 不可 | 不可 | 不可 | **可能** |
| soft-info | なし (binary) | なし (binary) | なし (binary) | **14bit連続値** |
| 装置コスト (目標) | $10M+ | $10M+ | $5M+ | **$50K-$200K** |

**Tarosの決定的優位**: 室温動作 + ソフト情報 + TDMスケーラビリティ + デスクトップサイズ + 低コスト

**Tarosの課題**: 論理エラー率はまだ理論予測段階、GKP状態の高品質生成が未実証 (sigma_gen >= 12.5dB)

---

## J. 最重要アクションアイテム (Top 5)

1. **FPGA NNデコーダ調査**: arXiv:2605.04892 (2026年5月)のFPGA NN decoder実装を精読し、Taros VE2302/VE2802への適用可能性を評価。124ns推論がGKP soft-info入力で達成可能か検証

2. **qLDPC-GKP soft-info論文の精読**: arXiv:2505.06385のリアルタイムsoft-info手法を08_decoder.mdのStage 2設計に反映。MWPM vs UF vs NN decoderのGKP環境での比較シミュレーション

3. **Xanadu Si3N4 GKPチップ (Nature)の詳細分析**: 損失バジェット、squeezing level、postselection率をTaros設計と比較。300mm Si3N4プロセスのスペックを02_opa-source.md / PIC計画に反映

4. **Early-FTQC QPEアプリケーション選定**: arXiv:2603.22778を参考に、Phase 0-1 (2-50論理qubit)で実行可能な分子シミュレーションターゲットを選定。H2→LiH→H2Oの段階的デモ計画

5. **SHYPS qLDPC符号のCV-TDM適合性評価**: Photonic Inc.の論文を分析し、fusion-based → measurement-based CV方式への変換可能性を評価。20倍リソース削減の恩恵は巨大

---

## Sources

### A. 超伝導量子コンピュータ
- [Google Willow quantum chip](https://blog.google/innovation-and-ai/technology/research/google-willow-quantum-chip/)
- [Quantum error correction below the surface code threshold (Nature)](https://www.nature.com/articles/s41586-024-08449-y)
- [Quantum Echoes - verifiable quantum advantage](https://blog.google/technology/research/quantum-echoes-willow-verifiable-quantum-advantage/)
- [AlphaQubit - Google DeepMind](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/alphaqubit-quantum-error-correction/)
- [Learning high-accuracy error decoding (Nature)](https://www.nature.com/articles/s41586-024-08148-8)
- [Real-time Surface-Code Error Correction Using FPGA NN Decoder](https://arxiv.org/abs/2605.04892)
- [Scalable real-time neural decoder for topological codes](https://arxiv.org/abs/2512.07737)
- [IBM large-scale FTQC path](https://www.ibm.com/quantum/blog/large-scale-ftqc)
- [IBM Nighthawk and Loon quantum chips](https://newsroom.ibm.com/2025-11-12-ibm-delivers-new-quantum-processors,-software,-and-algorithm-breakthroughs-on-path-to-advantage-and-fault-tolerance)
- [IBM qLDPC Nature cover paper](https://www.ibm.com/quantum/blog/nature-qldpc-error-correction)
- [IBM FPGA QEC on AMD FPGAs](https://www.hpcwire.com/2025/10/28/ibm-touts-affordable-quantum-error-correction-on-amd-fpgas/)
- [Riverlane Local Clustering Decoder](https://www.riverlane.com/news/riverlane-unveils-first-hardware-decoder-to-deliver-real-time-scalable-quantum-error-correction)
- [QpiAI Union-Find decoder on Kaveri](https://thequantuminsider.com/2026/03/25/qpiai-high-speed-quantum-error-correction-decoder/)
- [QUEKUF: FPGA Union Find Decoder](https://dl.acm.org/doi/full/10.1145/3733239)
- [Scalable FPGA Architecture for qLDPC (GARI)](https://arxiv.org/abs/2605.01035)

### B. トラップイオン
- [IonQ 99.99% two-qubit gate fidelity](https://postquantum.com/quantum-research/ionq-record-2025/)
- [Quantinuum logical qubit breakthrough](https://www.quantinuum.com/blog/a-new-breakthrough-in-logical-quantum-computing-reveals-the-scale-of-our-industry-leadership)
- [Quantinuum 94 logical qubits demonstration](https://thequantuminsider.com/2026/03/10/quantinuum-researchers-demonstrates-quantum-computations-with-dozens-of-protected-logical-qubits/)
- [IonQ photonic interconnect](https://www.ionq.com/news/ionq-achieves-key-photonic-interconnect-milestone-demonstrating-networked-quantum-systems-using-entanglement)

### C. 中性原子
- [Neutral Atom Quantum Computing 2026 - IEEE Spectrum](https://spectrum.ieee.org/neutral-atom-quantum-computing)
- [QuEra 2025 record year](https://www.prnewswire.com/news-releases/quera-computing-marks-record-2025-as-the-year-of-fault-tolerance-and-over-230m-of-new-capital-to-accelerate-industrial-deployment-302635960.html)
- [QuEra 2:1 qubit ratio QEC breakthrough](https://www.networkworld.com/article/4165592/quera-claims-quantum-error-correction-breakthrough-with-2-to-1-qubit-ratio.html)

### D. シリコンスピン / NVセンター
- [Diraq/imec 99%+ fidelity in foundry chips (Nature)](https://www.nature.com/articles/s41586-025-09531-9)
- [Silicon quantum processor error detection](https://phys.org/news/2026-02-silicon-quantum-processor-qubit-errors.html)
- [Silicon quantum logical operations](https://phys.org/news/2026-03-silicon-quantum-logical.html)
- [Diamond NV center quantum networks](https://www.jstage.jst.go.jp/article/jsaprev/2025/0/2025_250420/_article)
- [Hybrid diamond photonics 2025](https://www.nature.com/articles/s44172-025-00398-2)
- [Telecom qubit in silicon - UCSB](https://news.ucsb.edu/2026/022402/robust-new-telecom-qubit-silicon)

### E. トポロジカル
- [Microsoft Majorana 1](https://azure.microsoft.com/en-us/blog/quantum/2025/02/19/microsoft-unveils-majorana-1-the-worlds-first-quantum-processor-powered-by-topological-qubits/)
- [Microsoft quantum roadmap](https://quantum.microsoft.com/en-us/vision/quantum-roadmap)
- [Expert review of Microsoft topological qubit claim](https://physicsworld.com/a/experts-weigh-in-on-microsofts-topological-qubit-claim/)

### F. アルゴリズム
- [Practical Quantum Advantage on Partially Fault-Tolerant QC (PRX)](https://link.aps.org/doi/10.1103/PhysRevX.15.021057)
- [Enabling Chemically Accurate QPE in Early-FTQC](https://arxiv.org/abs/2603.22778)
- [Quantum Error-Corrected Molecular Energies](https://arxiv.org/abs/2505.09133)
- [QPE with 25-100 logical qubits perspective](https://arxiv.org/html/2506.19337v2)
- [Quantinuum quantum chemistry with logical qubits](https://www.quantinuum.com/press-releases/quantum-chemistry-progresses-meaningfully-towards-a-fault-tolerant-regime-using-logical-qubits)

### G. GKP / Photonic / qLDPC
- [Integrated photonic GKP source (Nature)](https://www.nature.com/articles/s41586-025-09044-5)
- [Xanadu on-chip GKP qubit announcement](https://www.xanadu.ai/press/xanadu-unveils-first-on-chip-error-resistant-photonic-qubit)
- [Photonic SHYPS qLDPC codes](https://photonic.com/technology/error-correction/)
- [Fault Tolerant Decoding of qLDPC-GKP with soft information](https://arxiv.org/abs/2505.06385)
- [Bosonic Pauli+ GKP simulation](https://quantum-journal.org/papers/q-2024-11-26-1539/)
- [GKP qudits break-even (Google/Yale)](https://thequantuminsider.com/2025/05/15/google-and-yale-team-demonstrates-error-corrected-qudits-that-beat-break-even/)
- [Fusion-based qLDPC with quantum emitters](https://www.nature.com/articles/s41534-026-01233-y)
- [Distributed BB codes in modular architecture](https://arxiv.org/abs/2605.04663)
- [Low-overhead surface-GKP code (Amazon)](https://www.amazon.science/publications/very-low-overhead-fault-tolerant-quantum-error-correction-with-the-surface-gkp-code)
