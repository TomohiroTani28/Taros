#!/usr/bin/env python3
"""
Taros Pro 共通パラメータ定義
出典: design/12_mechanical.md, design/11_industrial-design.md

全図面スクリプトから import して使用する SSOT (Single Source of Truth)。
"""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class TarosProParams:
    """Taros Pro 筐体共通パラメータ"""

    # === 外寸 (出典: 12_mechanical.md §1.2) ===
    W: float = 300.0        # 幅 [mm] — X方向
    D: float = 250.0        # 奥行 [mm] — Y方向
    H_total: float = 160.0  # 全高 [mm] (筐体+天板フィン)

    # === 壁厚 (出典: 12_mechanical.md §1.2) ===
    T_side: float = 3.0     # 側板厚 [mm]
    T_bottom: float = 3.0   # 底板厚 [mm]

    # === 天板嵌合段差 (出典: 12_mechanical.md §1.2) ===
    LIP_W: float = 2.0      # 段差幅 [mm]
    LIP_H: float = 3.0      # 段差深さ [mm] — 天板板厚と同一

    # === 天板固定ネジ穴位置 (出典: 12_mechanical.md §1.2) ===
    TOP_SCREW_POSITIONS: Tuple[Tuple[float, float], ...] = (
        (30, 32.5), (150, 32.5), (270, 32.5),      # 前面3箇所 (フィン干渉回避Y+2.5mm)
        (30, 127.5),              (270, 127.5),     # 側面2箇所
        (30, 222.5), (150, 222.5), (270, 222.5),   # 背面3箇所
    )

    # === 材料物性 ===
    MATERIAL: str = "A6063-T5"
    DENSITY: float = 0.00269    # [g/mm^3] — A6063-T5 (2690 kg/m^3)
    SURFACE_TREATMENT: str = "硫酸アノダイズド 黒 膜厚15um (JIS H 8601 AA15)"


# シングルトンインスタンス (便宜上)
PARAMS = TarosProParams()
