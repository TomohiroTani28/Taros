> **⚠ FROZEN (2026-05-04)**: 本文書はDV-FBQC v4.0 R6時点の設計を記録したものです。プロジェクトの主軸はCV方式に移行しています。最新設計は `design/00_overview.md` を参照してください。

### 1.2C v4.0 R4（第4ラウンド専門家会議）での主要変更概要

第4ラウンドの7人専門家会議により、アーキテクチャレベルの刷新を含む14項目（C15-C28）の合意事項を反映した。

**3本柱の刷新**:

1. **Primary符号をSHYPS→GB符号 [[144,12,12]] に変更**: confinement property証明済み、デコーダ（BP+OSD）成熟、符号レート8.33%（SHYPSの6.25%超）、IBM量子ハードウェアで実証済み。SHYPSはSecondaryに降格（SS5.2改訂）
2. **Floquet符号のSingle-Shot QEC活用**: 2025年にSingle-Shot性が証明済み。サイクル時間をd倍短縮（d=7で14μs→2μs）。Tゲートレート7倍高速化（SS5.11新規）
3. **Ambiguity Clusteringデコーダ**: 表面符号・GB符号に対しデコーディング計算量O(1)を実現。レイテンシ<10ns。Sliding Window不要、マジック状態蒸留のHCF追加遅延不要（SS9.5新規）

**光源系の刷新**:

4. **決定論的ベル対生成（biexciton cascade）**: 補助ベル対のヘラルド試行を不要にし、必要QD数をさらに1/2に（SS4.10新規）
5. **QDM（Quantum Dot Molecule）によるリソースステート直接生成**: QDM 3個で6光子リソースステートを1サイクル生成。必要QD数: 弾道式330→QDM ~80個（SS4.11新規）
6. **QD間アイソレータ（Ce:YIG）のPIC集積**: dipole-dipole相互作用を遮断しQD間距離10μmに縮小、PIC面積1/25（SS3.6.7新規）

**検出系・遅延系**:

7. **Upconversion検出PoC**: 室温Si SPADによる検出の原理実証。Phase 0追加実験$50K（SS12.5追記）
8. **Photon Harvesting Architecture**: WI-SNSPDの不良素子を光スイッチで迂回し実質歩留95%（SS6.4.1C新規）
9. **SNCM（超伝導ナノワイヤ光メモリ）**: HCF遅延線をオンチップメモリに置換、体積1/40（SS3.6.8新規）

**その他**:

10. **erasure率3定義の統一**: 全経路/ヘラルド後/弾道式実効の3定義を明確化（SS4.7.3新規）
11. **Phase 0.5をQDM 8個に拡張**: entangled pair品質検証を追加（SS12.5追記）
12. **PCF solid-coreの中遅延採用**: 曲げ半径2cmで中遅延を最適化（SS3.6.9新規）
13. **Measurement-Free QECのPhase 2+オプション**: デコーダ不要の自律的QEC（SS5.12新規）
14. **成功確率再上方修正**: Phase 2レベルA確率45%→55-60%（SS13.5改���）

