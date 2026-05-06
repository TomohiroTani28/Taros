### 4.10 決定論的ベル対生成（v4.0 R4新規、Rudolph提案 C15）

R3の弾道式RSGでは補助ベル対をヘラルド方式で生成するが（成功率50%/試行）、**biexciton-exciton cascade**からのentangled photon pairを用いることで、ベル対生成を決定論的に行える。

#### 4.10.1 Biexciton Cascade原理

GaAs QDのbiexciton状態（XX）は、exciton状態（X）を経て基底状態（0）に遷移する際、2つの光子を放出する:

```
|XX⟩ → |X_H⟩|γ_H⟩ + |X_V⟩|γ_V⟩ → |0⟩(|H,V⟩ + |V,H⟩)/√2
```

この2光子は偏光entangled Bell状態 |Φ⁺⟩ を形成する。

| パラメータ | 値 | 根拠 |
|-----------|-----|------|
| Entanglement fidelity | >0.90 | Huber+ 2018, Nat. Commun.; Liu+ 2019 |
| 生成確率 | **決定論的**（QD励起ごとに1ペア） | Cascade emission |
| HOM visibility（pair内） | >0.95 | Pair内の光子は本質的に不識別的 |
| Fine-structure splitting (FSS) | <1μeV必要 | FSSが大きいとentanglement劣化。GaAs QDで達成可能 |

#### 4.10.2 Boosted Fusionへの適用

決定論的ベル対により:
- ヘラルド試行不要 → ベル対供給レートがQD繰り返しレートと一致
- Boosted fusion 1回あたりの光子: 12光子（4融合+8補助）→ **8光子（4融合+4決定論ペア）**
- 弾道式RSGとの組合せで、必要QD数: R3の330個 → **~165個**

#### 4.10.3 課題: Fine-Structure Splitting制御

FSS<1μeVの歩留まりは~20%（GaAs QDウェハ全体）。対策:
- ストレインチューニング（ピエゾ素子でQDに応力印加）でFSSを能動的に制御
- Phase 0aの実験1にbiexciton cascade検証を追加（追加コスト$30K）

### 4.11 QDM（Quantum Dot Molecule）によるリソースステート直接生成（v4.0 R4新規、Senellart提案 C18）

縦方向に結合した2つのQD（QD molecule）から、4光子GHZ状態を直接生成する。

#### 4.11.1 QDM構造

```
      ┌─────────┐
      │  QD_top  │  ← 上層InAs QD
      ├─────────┤
      │ GaAs    │  ← トンネル障壁（~4nm）
      │ barrier │
      ├─────────┤
      │ QD_bot  │  ← 下層InAs QD
      └─────────┘
```

トンネル障壁を介した電子的結合により、QDMは4つのexciton状態を持ち、適切な励起シーケンスで4光子entangled stateを決定論的に放出する [Reindl+ 2019, Sci. Adv.]。

#### 4.11.2 リソースステート生成への応用

| 方式 | 必要光源数/RS | 生成確率 | 品質 |
|------|------------|---------|------|
| ヘラルド式（v4.0） | QD 6個 | ~1% | 高（ヘラルド確認） |
| 弾道式（R3） | QD 6個（k≥4） | ~15-34% | 中（欠損あり） |
| **QDM式（R4）** | **QDM 3個** | **~5-10%** | **高（entanglement保証）** |

QDM 3個で6光子リソースステート: 各QDMが2光子entangled pairを放出し、3ペアをfusionで結合。

#### 4.11.3 Phase 1必要数（R5歩留まり再評価 C31）

> **v4.0 R5修正**: QDM歩留まりの正直な再評価。R4の15%は楽観的であった。

| 歩留まりファクター | 確率 | 根拠 |
|---|---|---|
| MBE成長でQD対が形成 | ~60% | 上下QDのサイズ・位置整合 |
| トンネル結合エネルギー適切（±5meV） | ~50% | 障壁厚±0.5nm制御 |
| FSS < 1μeV（ストレインチューニングなし） | ~20% | GaAs QDの分布 |
| FSS < 1μeV（**ストレインチューニングあり**） | **~70%** | ピエゾ能動制御 |
| 上下QD波長差±0.1nm以内 | ~40% | Starkチューニング補償範囲 |
| **総合歩留まり（ストレインなし）** | **~2.4%** | 0.60×0.50×0.20×0.40 |
| **総合歩留まり（ストレインあり）** | **~8.4%** | 0.60×0.50×0.70×0.40 |

- QDM ~80個に必要な評価数: 80 / 0.084 ≈ **950個**（ストレインあり）
- ウェハレベルPLマッピングで1/3に絞り込み: 実測対象~320個
- Phase 0.5でQDM 8個の同時運転デモを実施

**QDM Go/No-Goゲート（Phase 0b、C32）**:
- **Go（QDM採用）**: entanglement fidelity >0.85、歩留まり >5%、4光子GHZ fidelity >0.80
- **No-Go（通常QD回帰）**: 弾道式RSG + biexciton cascade（通常QD ~165個）のまま進行。Phase 1コスト+$700K（$1.2M→$1.9M）、論理qubit 42→20-30に縮小

---

