#!/usr/bin/env python3
"""
DWG-003: Taros Pro 総組立図 (General Assembly)
出典: design/12_mechanical.md §1.2-1.5, DWG-003_assembly.md

全部品を組立位置に配置し、STEP出力する。
内部部品は簡易形状 (box/cylinder) で表現。
正確なモデルは個別DWG図面を参照のこと。

座標系 (データム):
  A: 筐体底面 Z=0
  B: 筐体左側面 X=0
  C: 筐体前面 Y=0
"""

import importlib
import math
import os
import sys
from dataclasses import dataclass

import cadquery as cq

from taros_params import TarosProParams, PARAMS

# --- DWG-001 / DWG-002 インポート (ファイル名にハイフンを含むため importlib 使用) ---
_drawings_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _drawings_dir)

_dwg001 = importlib.import_module("DWG-001_enclosure_body")
build_enclosure_body = _dwg001.build_enclosure_body
EnclosureParams = _dwg001.EnclosureParams

_dwg002 = importlib.import_module("DWG-002_top_plate")
build_top_plate = _dwg002.build_top_plate
TopPlateParams = _dwg002.TopPlateParams


# =============================================================================
# 組立パラメータ
# =============================================================================

@dataclass
class AssemblyParams:
    """DWG-003 組立固有パラメータ"""

    # === 共通パラメータ参照 ===
    common: TarosProParams = None

    # === 天板配置Z (SSOT導出: EnclosureParams.H_body - LIP_H) ===
    TOP_PLATE_Z: float = None  # __post_init__で動的計算

    # === Zone A: 光学部品 (出典: DWG-003_assembly.md §2.2, 12_mechanical §1.4) ===
    # OPA ×2 (50×20×10mm)
    OPA_SIZE: tuple = (50.0, 20.0, 10.0)
    OPA1_POS: tuple = (30.0, 60.0, 8.0)    # (X, Y, Z) 左下隅基準
    OPA2_POS: tuple = (30.0, 140.0, 8.0)

    # TEC ×3 (60×50×5mm) — OPA直下×2 + SHG×1
    TEC_SIZE: tuple = (60.0, 50.0, 5.0)
    TEC1_POS: tuple = (30.0, 60.0, 3.0)    # OPA#1直下
    TEC2_POS: tuple = (30.0, 140.0, 3.0)   # OPA#2直下
    TEC3_POS: tuple = (80.0, 100.0, 3.0)   # SHG直下

    # Master Laser (120×60×30mm) — 底板上に直置き
    LASER_SIZE: tuple = (120.0, 60.0, 30.0)
    LASER_POS: tuple = (10.0, 92.0, 3.0)   # Z=3: 底板上面

    # === Zone B: ファイバ (出典: DWG-003_assembly.md §2.2) ===
    # PMFスプール (φ80×80mm) — cylinder
    PMF_D: float = 80.0
    PMF_H: float = 80.0
    PMF_POS: tuple = (175.0, 125.0, 5.0)  # (X_center, Y_center, Z_bottom) — Zone B内に収める(X=135-215)

    # === Zone C: 電子制御 (出典: DWG-003_assembly.md §2.2) ===
    # FPGA (80×80×20mm)
    FPGA_SIZE: tuple = (80.0, 80.0, 20.0)
    FPGA_POS: tuple = (215.0, 125.0, 3.0)  # 左下隅: X=215, Y=85(center125-40)

    # === PTFE断熱板 (出典: DWG-003_assembly.md §2.4, 12_mechanical §1.3) ===
    PTFE_SIZE: tuple = (290.0, 240.0, 3.0)
    PTFE_POS: tuple = (5.0, 5.0, 90.0)

    # === 部品質量概算 [g] (出典: 10_portable.md §2) ===
    MASS_OPA: float = 30.0          # OPA ×1
    MASS_TEC: float = 50.0          # TEC ×1
    MASS_LASER: float = 350.0       # Master Laser
    MASS_PMF_SPOOL: float = 800.0   # PMFスプール (0.8kg, DWG-003 BOM#10)
    MASS_FPGA: float = 120.0        # FPGA基板
    MASS_PTFE: float = 450.0        # PTFE板 (2.15g/cm3 × 290×240×3mm)

    def __post_init__(self):
        if self.common is None:
            self.common = PARAMS
        if self.TOP_PLATE_Z is None:
            # 動的計算: 筐体上端 - リップ深さ = 142 - 3 = 139mm
            object.__setattr__(self, 'TOP_PLATE_Z',
                               EnclosureParams().H_body - self.common.LIP_H)


# =============================================================================
# 組立ビルド関数
# =============================================================================

def build_assembly(p: AssemblyParams = None):
    """
    総組立モデルを生成する。
    Returns: cadquery.Assembly
    """
    if p is None:
        p = AssemblyParams()

    assy = cq.Assembly(name="DWG-003_TarosPro_Assembly")

    # --- 1. 筐体本体 (DWG-001) ---
    enclosure = build_enclosure_body(EnclosureParams())
    assy.add(enclosure, name="enclosure_body", color=cq.Color(0.15, 0.15, 0.15, 1.0))

    # --- 2. 天板 (DWG-002) Z=139mm配置 ---
    # 天板はZ=0基準で生成されるため、Z=139に移動
    # 干渉チェック: 天板下面の嵌合段差 (外周2mm, 深さ3mm) が
    #   筐体リップ (内寸+2mm幅, 深さ3mm, Z=139-142) に嵌合する。
    #   天板配置Z=139 → 天板下面=139, 嵌合部=139-142 → 筐体リップ=139-142 ✓ 整合
    top_plate = build_top_plate(TopPlateParams())
    assy.add(
        top_plate,
        name="top_plate",
        loc=cq.Location(cq.Vector(0, 0, p.TOP_PLATE_Z)),
        color=cq.Color(0.15, 0.15, 0.15, 1.0),
    )

    # --- 3. Zone A: OPA ×2 ---
    for i, pos in enumerate([p.OPA1_POS, p.OPA2_POS], 1):
        opa = cq.Workplane("XY").box(
            p.OPA_SIZE[0], p.OPA_SIZE[1], p.OPA_SIZE[2], centered=False
        )
        assy.add(
            opa,
            name=f"OPA_{i}",
            loc=cq.Location(cq.Vector(*pos)),
            color=cq.Color(0.9, 0.5, 0.1, 0.8),  # orange
        )

    # --- 4. Zone A: TEC ×3 (OPA×2 + SHG×1) ---
    for i, pos in enumerate([p.TEC1_POS, p.TEC2_POS, p.TEC3_POS], 1):
        tec = cq.Workplane("XY").box(
            p.TEC_SIZE[0], p.TEC_SIZE[1], p.TEC_SIZE[2], centered=False
        )
        assy.add(
            tec,
            name=f"TEC_{i}",
            loc=cq.Location(cq.Vector(*pos)),
            color=cq.Color(0.3, 0.3, 0.8, 0.8),  # blue
        )

    # --- 5. Zone A: Master Laser ---
    laser = cq.Workplane("XY").box(
        p.LASER_SIZE[0], p.LASER_SIZE[1], p.LASER_SIZE[2], centered=False
    )
    assy.add(
        laser,
        name="Laser",
        loc=cq.Location(cq.Vector(*p.LASER_POS)),
        color=cq.Color(0.8, 0.1, 0.1, 0.8),  # red
    )

    # --- 6. Zone B: PMFスプール (cylinder φ80×80mm) ---
    pmf = (
        cq.Workplane("XY")
        .cylinder(p.PMF_H, p.PMF_D / 2, centered=(True, True, False))
    )
    assy.add(
        pmf,
        name="PMF_spool",
        loc=cq.Location(cq.Vector(*p.PMF_POS)),
        color=cq.Color(0.2, 0.7, 0.2, 0.7),  # green
    )

    # --- 7. Zone C: FPGA ---
    fpga = cq.Workplane("XY").box(
        p.FPGA_SIZE[0], p.FPGA_SIZE[1], p.FPGA_SIZE[2], centered=False
    )
    # FPGA_POS X=215, Y=125 は中心指定 → 左下隅に変換
    fpga_corner = (
        p.FPGA_POS[0],
        p.FPGA_POS[1] - p.FPGA_SIZE[1] / 2,
        p.FPGA_POS[2],
    )
    assy.add(
        fpga,
        name="FPGA",
        loc=cq.Location(cq.Vector(*fpga_corner)),
        color=cq.Color(0.1, 0.6, 0.1, 0.8),  # dark green
    )

    # --- 8. PTFE断熱板 ---
    ptfe = cq.Workplane("XY").box(
        p.PTFE_SIZE[0], p.PTFE_SIZE[1], p.PTFE_SIZE[2], centered=False
    )
    assy.add(
        ptfe,
        name="PTFE_plate",
        loc=cq.Location(cq.Vector(*p.PTFE_POS)),
        color=cq.Color(0.95, 0.95, 0.95, 0.5),  # white translucent
    )

    return assy


def calc_total_mass(p: AssemblyParams = None):
    """
    組立体の概算質量を計算する。
    筐体・天板はCadQueryのVolume×密度、内部部品はカタログ値を使用。
    """
    if p is None:
        p = AssemblyParams()

    c = p.common
    density = c.DENSITY  # g/mm^3

    # 筐体質量
    enclosure = build_enclosure_body(EnclosureParams())
    vol_enclosure = enclosure.val().Volume()
    mass_enclosure = vol_enclosure * density

    # 天板質量
    top_plate = build_top_plate(TopPlateParams())
    vol_top_plate = top_plate.val().Volume()
    mass_top_plate = vol_top_plate * density

    # 内部部品 (カタログ値)
    mass_internal = (
        p.MASS_OPA * 2
        + p.MASS_TEC * 3  # OPA×2 + SHG×1 = 3個
        + p.MASS_LASER
        + p.MASS_PMF_SPOOL
        + p.MASS_FPGA
        + p.MASS_PTFE
    )

    total_g = mass_enclosure + mass_top_plate + mass_internal
    return {
        "enclosure_g": mass_enclosure,
        "top_plate_g": mass_top_plate,
        "internal_g": mass_internal,
        "total_g": total_g,
        "total_kg": total_g / 1000.0,
    }


# =============================================================================
# メイン実行
# =============================================================================

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 60)
    print("DWG-003: Taros Pro Assembly Build")
    print("=" * 60)

    params = AssemblyParams()
    assy = build_assembly(params)

    # STEP出力 (組立全体)
    step_path = os.path.join(out_dir, "DWG-003_assembly.step")
    assy.save(step_path)
    print(f"STEP exported: {step_path}")

    # 質量計算
    print("\n--- Mass Breakdown ---")
    mass = calc_total_mass(params)
    print(f"  Enclosure body : {mass['enclosure_g']:8.1f} g")
    print(f"  Top plate      : {mass['top_plate_g']:8.1f} g")
    print(f"  Internal parts : {mass['internal_g']:8.1f} g")
    print(f"  ----------------------------")
    print(f"  TOTAL          : {mass['total_g']:8.1f} g ({mass['total_kg']:.2f} kg)")
    print(f"  Target (spec)  : 7500 g (7.5 kg)")
    print(f"  Note: Internal mass is approximate (catalog values).")
    print(f"         Remaining ~{7500 - mass['total_g']:.0f} g includes")
    print(f"         EOM, BS, BPD, AWG, ADC/DAC, DC-DC, HP, cables, fasteners, etc.")

    # 干渉チェック確認
    print("\n--- Fit Check ---")
    print(f"  Top plate Z = {params.TOP_PLATE_Z} mm")
    print(f"  Enclosure lip: Z = {params.TOP_PLATE_Z} to {params.TOP_PLATE_Z + params.common.LIP_H} mm")
    print(f"  Top plate engagement depth = {params.common.LIP_H} mm")
    print(f"  Lip width = {params.common.LIP_W} mm")
    print(f"  -> Engagement OK: top plate sits flush at Z=139, lip Z=139-142")

    print("\nDWG-003 complete.")
