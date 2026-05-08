# 3段階GKP状態生成プロトコル

**Document ID**: PQC-CV-GKP-PROTO-v1.4
**Status**: Draft
**前提**: macronode TDM (`03_tdm-cluster.md`) + PPLN OPA (`02_opa-source.md`)

---

## 1. 3段階アプローチの概要

GKP状態生成を3段階に分割し、各段階でGo/No-Goを判定する。

| Step | 方式 | QD数 | 特徴的確率 | GKPレート | 忠実度F | Phase |
|------|------|------|-----------|----------|---------|-------|
| **A** | CVのみ (postselection) | 0 | p_acc~93% (acceptance rate) | 100kHz | **0.87-0.91**† | Phase 0前期 |
| **B** | QD photon subtraction | 2 | ~2×10⁻³ (herald rate) | 200kHz | 0.95 | Phase 0後期 |
| **C** | QD deterministic breeding | 4 | ~0.5 (breeding成功率) | 50MHz | 0.98 | Phase 1 |

†: F値はBS modelに基づく。Phase -1 discrete (Option B, 13dB, L=0.39dB) σ_eff=8.5dB→F≈0.87。Phase 2+ PIC (L=0.15dB, 13dB) σ_eff=10.8dB→F≈0.91。旧値F=0.93-0.94はdB減算公式σ_eff=σ_gen−Lによる過大推定 — 06_noise-budget §2.3参照。「特徴的確率」欄はStep Aではp_acc(acceptance rate)、Step Bではherald rate、Step Cではbreeding成功率を使用。旧P_s記号は廃止(§2.2参照)。σ_eff 8.8→8.5, 10.9→10.8

**根拠**: Step Aだけで表面符号break-even（Menicucci postselection閾値7.5dB）を実証可能。QDがなくてもCV方式のFTQCが成立する。

---

## 2. Step A: Pure CV Postselection GKP

### 2.1 プロトコル

```
[PPLN OPA] → squeezing 13dB
     │
     ▼
[TDM cluster state] (macronode lattice)
     │
     ├── mode_k: ホモダイン測定 → q_k
     │                              │
     │                              ▼
     │                    [Postselection判定]
     │                    q_k mod √π ∈ [-δ, +δ] ?
     │                              │
     │                    Yes ──────┤──── No (棄却)
     │                              │
     │                              ▼
     ├── mode_k+1: [GKP qubit ヘラルド成功]
     │
     (続行)
```

### 2.2 パラメータ

| パラメータ | 値 | 根拠 |
|-----------|-----|------|
| スクイージング | **σ_eff=8.5dB (Phase 1, L=0.39dB) / ≈9.3dB (Phase 2+ PIC現実的, L=0.27dB) / 10.8dB (理論限界, L=0.15dB)** | BSモデル: V_eff=η×V_sqz+(1-η)+V_nl。erfc再計算+V_non-loss全項目合算 |
| Postselection窓 δ | 0.19 √π (運用値) | per-mode合格率93%を達成する閾値。Stafford+ 2025最適値0.15√πは高品質モード選択用(P_mode~84%) |
| per-mode高信頼率 | **93%** (δ<0.19√π) | 各モード独立。低信頼7%はerasure weight |
| P_round (全モード高信頼/round) | ~10⁻³ | 0.93^98≈8×10⁻⁴。strict postselection時のみ関連。**旧P_s記号は廃止** |
| TDMクロック | 100MHz | |
| **実効QECレート (全モード利用)** | **~146kHz** | 1/T_QEC = 1/6.86μs。全モードsoft-info UF |
| **実効QECレート (strict post.)** | **~120Hz** | P_round=8×10⁻⁴, 146kHz×8×10⁻⁴≈117Hz→概算~120Hz |
| GKP忠実度 F | **0.87 (Phase -1 discrete) / 0.91 (Phase 2+ PIC)** | BSモデル修正。旧0.93/0.94はdB減算による過大推定 |
| 有効GKP σ_eff | **8.5-10.8dB** (Phase依存、BSモデル) | Phase 1: 8.5dB, Phase 2+現実的: ≈9.3dB, 理論限界: 10.8dB。erfc再計算+V_non-loss修正。06_noise-budget §2.3参照 |
| 有限エネルギー Δ | **< 0.15** (製品要件) / < 0.10 (目標) | δ=0.19√π運用窓でΔ≈0.12-0.15。δ=0.15√π厳格窓でΔ<0.10。(06_noise-budget §3, experiments/03_numerical-verification §2.5) |

**記号定義の明確化 (旧P_s記号廃止)**:

| 記号 | 定義 | 値 | 用途 |
|------|------|-----|------|
| **p_acc** | 単一モード acceptance rate | ~93% (@δ=0.19√π) | Go/No-Go基準、設計パラメータ |
| **P_round** | 1ラウンド全モード同時高信頼率 | p_acc^98 ≈ 8×10⁻⁴ | strict mode参考値のみ |

- 全モードが100MHzでホモダイン測定され、bit+confidence値としてデコーダに入力される（破棄なし）
- p_acc=93%: 格子偏差δ<δ_maxの判定。低信頼モード(7%)もerasure weightで利用
- P_round=10⁻³ = p_acc^98: strict modeのみ関連（Go/No-Go基準には使用しない）
- **通常運用**: 全モード利用 → ゲートレート = 1/T_QEC ≈ 146kHz（P_round無関係）
- **strict mode**: 高信頼ラウンド待機 → ゲートレート ≈ 146Hz（最高品質、Δ→0近似有効）
- **旧P_sとの対応**: 01_gkp-optical.mdの「P_s≈11%」は単一モードpostselection通過率(=p_acc×窓幅補正)であり、P_roundとは別量。混同防止のためP_s記号は全文書で廃止。

### 2.3 Step Aで可能な実証

| 実証項目 | 条件 | 意義 |
|---------|------|------|
| GKP状態のWigner関数測定 | F > 0.85 | 光学GKP実証（Campagne-Ibarcq+ 2020の超伝導系に続く光学系初） |
| GKP + 表面符号 d=3 | p_L < p_phys | **QEC break-even** |
| GKP soft info decoder動作 | レイテンシ < 1μs | デコーダ検証 |

**Go/No-Go (Step A → B)**:
- Full Go: F_GKP > 0.85 AND 表面符号d=3 break-even AND Δ < 0.15
- Conditional Go: F_GKP > 0.80 AND Δ < 0.18（Phase 2+ PICでの改善を前提に続行）
- No-Go: F_GKP < 0.80 OR Δ > 0.20 → 原因究明（損失 or スクイージング不足 or postselection窓最適化）

### 2.4 有限エネルギーGKPの設計 (Δパラメータ)

**背景**: Ideal GKP状態 |0_GKP⟩ は無限光子数を要する。実装可能なGKP状態は有限エネルギーで格子構造が崩れ始める。この劣化を定量化するのが Δ (finite-energy parameter)。

**Δの定義**:
- Wigner関数が理想的な格子ピーク(delta functions)から広がった幅を σ_W で測定
- Δ ≈ σ_W（ホモダイン測定では σ_meas ≈ Δ/√2）
- **Δ < 0.15 が CV FTQC の hard requirement** (Menicucci 2014, Stafford-Menicucci 2025)

**Phase -1 T0a での測定プロトコル**:

| 手法 | 測定ショット数 | 精度 | 実装難易度 | 推奨性 |
|------|-----------|------|----------|--------|
| **Wigner tomography** | 18,000 ホモダイン点 + GPU再構成 | ±0.02 | 中 | ★★★ **推奨** |
| Adaptive Bayesian | 100-300 点/quadrature, 反復改善 | ±0.03 | 高 | ★★ （高速化可） |
| Homodyne variance | 粗推定 | ±0.05 | 低 | ★ （参考値のみ） |

**Wigner tomography 詳細**:
1. ホモダイン検出器: 位相 θ = 0°, 45°, ..., 355° (360°/2° = 180 points)
2. 各位相で 100 quadratures スイープ (position q or momentum p)
3. 合計 180 × 100 = 18,000 測定点
4. GPU で inverse Radon transform + Fourier reconstruction (200ms/result)
5. **精度**: ±0.02 (Δ < 0.15 判別に十分)

**Go/No-Go 判定マトリクス**:

| Δ値範囲 | F_GKP への影響 | Phase 0 判定 | Phase 1b 必須条件 | DV fallback |
|--------|----------|----------|------------|----------|
| **Δ < 0.10** | F > 0.88 | **Full Go** | 不要 | — |
| **0.10 ≤ Δ < 0.12** | F ≈ 0.86-0.88 | **Go** | σ_gen 最適化 optional | — |
| **0.12 ≤ Δ < 0.15** | F ≈ 0.84-0.86 | **Conditional** | σ_gen ≥ 13dB required, OPA tuning (M3-M8, +6週) | QD Step B必須 |
| **Δ ≥ 0.15** | F < 0.84 | **No-Go** | — | → DV v5.0 fallback 確定 |

**根拠**:
- Menicucci (2014): d=3 break-even で F ≥ 0.85 必要、Δ < 0.12 で達成可
- Stafford-Menicucci (2025): threshold は Δ ≤ 0.15 (soft margin), 推奨 Δ < 0.10 (hard margin)
- CV GKP では Δ が増加すると: (1) 論理エラー率上昇, (2) soft-info decoder効果減少, (3) break-even σ_eff 要件上昇

**Phase -1 実施スケジュール**:

```
Week 1-2: Wigner tomography 初期測定 (3独立測定)
        → Δ値決定 (±0.02 tolerance)
        → Go/Conditional/No-Go 即座判定

Week 3-8 (Conditional時のみ): σ_gen 最適化実験
        → OPA tuning (パラメータスイープ)
        → GKP protocol Step A→B 遷移条件検討
        → bi-weekly Δ trending (安定性確認)

Month 2-3 (T0b-T0c 並行): Δ 月次測定継続
        → 全 Phase -1 期間で Δ 監視
```

**Cost & Timeline**:
- Wigner 測定装置: ~$150K (ホモダイン検出+光学系)
- 外部解析委託: ~$50K (NTT/学内ラボ協業)
- Total T0a cost addition: +$200K
- Timeline impact: +2週 (nominal), +6週 (Conditional with optimization)

---

## 3. Step B: QD Photon Subtraction GKP

### 3.1 プロトコル

```
[PPLN OPA] → squeezing 13dB → [TDM cluster state]
                                      │
                                      ▼ (特定モード)
                                [Beam splitter R=0.1]
                                   /         \
                              0.9            0.1
                               │              │
                               │         [QD photon injection]
                               │              │ InP QD 1550nm
                               │              │ single photon |1>
                               │              ▼
                               │         [PBS + SNSPD]
                               │              │
                               │         detection? ──── No (retry next mode)
                               │              │
                               │         Yes (photon subtracted!)
                               │              │
                               ▼              ▼
                        [GKP state heralded with enhanced quality]
```

### 3.2 物理的説明

1. TDMクラスタの特定モードからBS (R=0.1) で光子を一部取り出す
2. QDからの単一光子をこの取り出しポートに注入（Hong-Ou-Mandel干渉）
3. SNSPD（PNR対応）で光子数を測定
4. 特定の光子数パターン検出時 → 残りのモードがGKP状態にヘラルドされる

**QD光子の役割**: 非ガウス操作（photon subtraction/addition）を**決定論的に**供給。SPDCベースの確率的photon subtractionと異なり、QDは毎クロック確実に光子を供給するため成功確率が飛躍的に向上。

### 3.3 パラメータ

| パラメータ | 値 | 根拠 |
|-----------|-----|------|
| QD数 | 2 | 1つ=photon subtraction, 1つ=photon addition |
| QD種 | InAs/InP QD 1550nm (C-band) | QFC不要。最新: 不識別性91.7%、g²(0)=0.0028、1.28GHz動作実証 (Nature Comms 2026) |
| QD繰り返し率 | 100MHz (クロック同期) | 電気的トリガ |
| Photon subtraction成功率 | ~10% per trial | BS R=0.1 × SNSPD 95% |
| QD実効光子供給率 | **2%** | 輝度0.40 × spectral filter透過率5% |
| GKP忠実度 F | **0.95** | σ_eff=12dBでの理論値（QD V=0.95考慮後） |
| 有効GKP σ_eff | **~12dB** | QD支援により閾値-3dB緩和 |
| **GKPヘラルドレート** | **200kHz** | 100MHz × 0.002 = 200kHz |

### 3.4 QD-CVモードマッチング設計

**最重要課題**: QD光子（パルス幅~100ps）とCVモード（モードスロット~10ns = 1/100MHz）の時間的モードマッチング。[OPAパルス幅3ns, ホモダイン測定窓7ns, 合計10nsモードスロット]

| パラメータ | QD光子 | CVモード | 解決策 |
|-----------|--------|---------|--------|
| パルス幅 | ~100ps | ~10ns | QD cavity lifetime延長 or spectral filtering |
| スペクトル幅 | ~5GHz (Purcell) | ~100MHz (OPA帯域制限) | Fabry-Perot filter (F=50) |
| 空間モード | ガウシアン (SMF) | ガウシアン (PMF) | ファイバモード変換 |
| 偏波 | 線偏光 | 線偏光 (PMF軸) | PMFアライメント |

**Spectral filtering**: QDのスペクトル(5GHz)をFP filter(FSR=100GHz, F=50 → 帯域2GHz)で100MHzに制限。透過率 100MHz/2GHz = 5%。輝度は低下するが、モードマッチングが飛躍的に改善。

**実効輝度**: QD輝度0.40 × filter透過率0.05 = 2% → 100MHz × 0.02 = 2MHz単一光子レート。十分。

### 3.5 Go/No-Go (Step B → C)

- Go: F_GKP > 0.90 AND GKPレート > 5MHz AND 表面符号d=5 QEC動作
- No-Go: F_GKP < 0.88 → モードマッチング改善 or QD品質向上

---

## 4. Step C: QD Deterministic Breeding

### 4.1 プロトコル

```
[PPLN OPA] → cat state (|α> + |-α>, α≈1.5)
     │
     ▼
[QD#1 photon] + [QD#2 photon] → entangled pair
     │
     ▼
[Beam splitter: cat × QD pair]
     │
     ▼
[Homodyne measurement on ancilla modes]
     │
     ▼ (measurement result)
[Displacement correction]
     │
     ▼
[GKP state] (high fidelity, near-deterministic)
```

### 4.2 Breeding回路の詳細

Vasconcelos+ (2010) + Bourassa+ (2021) のbreeding protocolをQD支援で改良:

1. OPA squeezing + QD photon subtractionでsqueezed cat state生成: |ψ_cat> = N(|α> + |-α>), α = √(π/2) ≈ 1.25
2. QD entangled pair (InP QD on-demand pairs, 98.3%ペア放出率) で非ガウスアンシラ準備
3. BS干渉 + ホモダイン測定でGKP状態をヘラルド
4. 測定結果に基づくdisplacement補正（フィードフォワード）

### 4.3 パラメータ

| パラメータ | 値 | 根拠 |
|-----------|-----|------|
| QD数 | 4 (2 pairs) | 2 entangled pairs for breeding |
| Cat state amplitude α | 1.25 | √(π/2), GKP格子間隔に整合 |
| Breeding成功確率 | **~49%** (理論値、未検証) | 2段breeding, 各段~70% (0.70²=0.49)。Vasconcelos+ 2010 + Bourassa+ 2021の超伝導系理論を光学系に外挿。**Phase 0でGaussian state simulationによる独立検証必須**。光学実装での実効成功率は30-49%の範囲と見込む。 |
| GKP忠実度 F | **0.98** | breeding + 高スクイージング |
| 有効GKP σ_eff | **~14dB** | F=0.98に相当（表§1の値と統一） |
| **GKPヘラルドレート** | **~49MHz** | 100MHz × 0.49 |

---

## 5. 段階的スケジュール

```
Phase 0a前半   Q2   Q3   Q4  | 開始後約2年 前半   Q2   Q3   Q4
━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━
                         |
Step A ████████████████    |                        Pure CV GKP実証
                 ↓ Go    |
Step B      ████████████████████████               QD photon subtraction
                         |       ↓ Go
Step C                   |  ████████████████████   Deterministic breeding
                         |
マイルストーン:           |
  ├─ GKP Wigner (Q1)    |  ├─ 表面符号d=5 (Q1)
  ├─ Break-even (Q3)    |  ├─ d=7 FTQC (Q3)
  └─ QD統合開始 (Q4)    |  └─ 50+ 論理qubit (Q4)
```

---

## 6. 必要設備・投資

| Step | 追加設備 | 投資 |
|------|---------|------|
| A | OPAモジュール + TDMクラスタ + ホモダイン + FPGA | 約1,200万円 |
| B | InP QD ×2 + PNR-SNSPD ×4 + PT205 + spectral filter | 約3,000万円 |
| C | InP QD ×4 (entangled pairs) + breeding光学系 | 約2,250万円 |
| **合計** | | **約6,450万円** |

---

*本文書はGKP状態生成を3段階に分割して各段階でGo/No-Goを設定するリスク低減戦略を定義したものである。Step AのみでQEC break-evenが達成可能であり、QDが不要な「保証パス」を確立する。*
