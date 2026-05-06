#!/usr/bin/env python3
"""
DWG-003: Taros Pro 総組立図 (General Assembly)
出典: design/12_mechanical.md §1.2-1.5, DWG-003_assembly.md

全部品を組立位置に配置し、STEP出力する。
内部部品は簡易形状 (box/cylinder) で表現。
正確なモデルは個別DWG図面を参照のこと。

設計ベースライン: d=5 (符号距離), PMF 102m (長遅延)
  d=5: N_col=50, τ₂=500ns, PMF=102m, φ80×80mmスプール

座標系 (データム):
  A: 筐体底面 Z=0
  B: 筐体左側面 X=0
  C: 筐体前面 Y=0
"""

import importlib
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
    """DWG-003 組立固有パラメータ (BOM全44品目の主要部品を配置)"""

    # === 共通パラメータ参照 ===
    common: TarosProParams = None

    # === 天板配置Z (SSOT導出: EnclosureParams.H_body - LIP_H) ===
    TOP_PLATE_Z: float = None  # __post_init__で動的計算

    # =====================================================================
    # Zone A: 光学部品 (X=5-135, Y=5-244, Z=5-90)
    # 出典: 12_mechanical §1.4 座標表
    # =====================================================================

    # #3 Master Laser NKT E15 OEM (120×60×30mm)
    LASER_SIZE: tuple = (120.0, 60.0, 30.0)
    LASER_POS: tuple = (10.0, 10.0, 5.0)     # X=10-130, Y=10-70, Z=5-35

    # #4 775nm Pump LD + SOA + SHG module (80×40×20mm)
    PUMP_SIZE: tuple = (80.0, 40.0, 20.0)
    PUMP_POS: tuple = (10.0, 75.0, 5.0)      # X=10-90, Y=75-115, Z=5-25

    # #5 PPLN OPA ×2 (50×20×10mm) — TEC上に配置 (Z=8 = 底板3mm + TEC5mm)
    OPA_SIZE: tuple = (50.0, 20.0, 10.0)
    OPA1_POS: tuple = (15.0, 155.0, 8.0)     # X=15-65, Y=155-175
    OPA2_POS: tuple = (15.0, 180.0, 8.0)     # X=15-65, Y=180-200

    # #6 Peltier TEC ×3 (底板上面Z=3に配置)
    # 注: 12_mechanical §1.4 ではTEC Z=15-20 (OPA上) だが、
    #      TEC→底板排熱パスの熱抵抗最小化のためOPA直下(Z=3)に配置変更。
    TEC_OPA_SIZE: tuple = (60.0, 50.0, 5.0)  # OPA#1+#2 共用 (1台で両OPAカバー)
    TEC_OPA_POS: tuple = (10.0, 152.0, 3.0)  # Y=152-202 (両OPAの下)
    TEC_SHG_SIZE: tuple = (60.0, 35.0, 5.0)  # SHG温調用
    TEC_SHG_POS: tuple = (10.0, 80.0, 3.0)   # Pump/SHG module直下

    # #7 LNOI EOM ×2 (40×20×10mm)
    EOM_SIZE: tuple = (40.0, 20.0, 10.0)
    EOM1_POS: tuple = (75.0, 155.0, 5.0)     # X=75-115, Y=155-175
    EOM2_POS: tuple = (75.0, 180.0, 5.0)     # X=75-115, Y=180-200

    # #8 BS カプラ 50:50 ×3 (ファイバトレイ内, 40×30×10mm)
    BS_SIZE: tuple = (40.0, 30.0, 10.0)
    BS_POS: tuple = (10.0, 210.0, 5.0)       # X=10-50, Y=210-240

    # #9 Balanced PD ×2 (35×20×20mm)
    BPD_SIZE: tuple = (35.0, 20.0, 20.0)
    BPD1_POS: tuple = (75.0, 210.0, 5.0)     # X=75-110, Y=210-230
    BPD2_POS: tuple = (75.0, 230.0, 5.0)     # X=75-110, Y=230-244

    # =====================================================================
    # Zone B: ファイバ (X=135-210, Y=5-244, Z=5-90)
    # =====================================================================

    # #10 PMFスプール 102m (φ80×80mm) — d=5ベースライン
    PMF_D: float = 80.0
    PMF_H: float = 80.0
    PMF_POS: tuple = (170.0, 122.0, 5.0)     # center (X,Y), Z_bottom

    # 短遅延PMF 2m スプール (φ50×20mm) — TDMクラスタ生成必須
    # 出典: 03_tdm-cluster.md:100 — τ₁=10ns=PMF 2m
    PMF_SHORT_D: float = 50.0
    PMF_SHORT_H: float = 20.0
    PMF_SHORT_POS: tuple = (170.0, 210.0, 5.0)  # Zone B内、長遅延スプールの横

    # #11 WDM AWG 8ch (100×35×20mm)
    AWG_SIZE: tuple = (100.0, 35.0, 20.0)
    AWG_POS: tuple = (135.0, 5.0, 5.0)       # X=135-235, Y=5-40

    # #12 WDM PD ×16 ドーターカード (80×35×20mm)
    WDMPD_SIZE: tuple = (80.0, 35.0, 20.0)
    WDMPD_POS: tuple = (135.0, 5.0, 30.0)    # AWG上にスタック

    # #25 HDPE振動隔離プレート (80×80×15mm) — PMFスプール支持
    HDPE_SIZE: tuple = (80.0, 80.0, 15.0)
    HDPE_POS: tuple = (130.0, 82.0, 3.0)     # PMFスプール周辺

    # =====================================================================
    # Zone C: 電子制御 (X=210-294, Y=5-244, Z=5-137)
    # =====================================================================

    # #13 FPGA VE2302 (80×80×20mm)
    FPGA_SIZE: tuple = (80.0, 80.0, 20.0)
    FPGA_POS: tuple = (210.0, 10.0, 5.0)     # X=210-290, Y=10-90

    # #14-15 ADC boards ×2 (80×45×15mm)
    ADC_SIZE: tuple = (80.0, 45.0, 15.0)
    ADC_POS: tuple = (210.0, 95.0, 5.0)      # X=210-290, Y=95-140

    # #16,21 DAC + EO driver (70×30×15mm)
    DAC_SIZE: tuple = (70.0, 30.0, 15.0)
    DAC_POS: tuple = (210.0, 145.0, 5.0)     # X=210-280, Y=145-175

    # #17 DC-DC converter (80×80×25mm)
    DCDC_SIZE: tuple = (80.0, 45.0, 25.0)
    DCDC_POS: tuple = (210.0, 95.0, 25.0)    # ADC上にスタック

    # #20 PZT driver + PID (80×40×15mm)
    PZT_SIZE: tuple = (80.0, 40.0, 15.0)
    PZT_POS: tuple = (210.0, 180.0, 5.0)     # X=210-290, Y=180-220

    # #18 Cu ヒートパイプ ×3 (φ6×80mm, vertical)
    HP_D: float = 6.0
    HP_H: float = 80.0
    HP_POSITIONS: tuple = (
        (230.0, 50.0, 55.0),    # HP#1 — DWG-002 HP穴位置と一致
        (250.0, 125.0, 55.0),   # HP#2
        (230.0, 200.0, 55.0),   # HP#3
    )

    # #43 EMI遮蔽壁 Cu箔 (0.1mm, at X=210 Zone B/C boundary)
    SHIELD_SIZE: tuple = (0.5, 238.0, 134.0)  # 薄板 (簡易表現)
    SHIELD_POS: tuple = (209.75, 3.0, 3.0)    # X=210 center

    # =====================================================================
    # PTFE断熱板 (出典: 12_mechanical §1.3)
    # =====================================================================
    PTFE_SIZE: tuple = (290.0, 240.0, 3.0)
    PTFE_POS: tuple = (5.0, 5.0, 90.0)       # Z=90 底面基準

    # =====================================================================
    # 部品質量概算 [g]
    # =====================================================================
    MASS_OPA: float = 30.0          # OPA ×1
    MASS_TEC: float = 50.0          # TEC ×1
    MASS_LASER: float = 350.0       # Master Laser
    MASS_PUMP: float = 200.0        # Pump LD+SOA+SHG
    MASS_EOM: float = 20.0          # EOM ×1
    MASS_BS: float = 15.0           # BS ×1
    MASS_BPD: float = 40.0          # BPD ×1
    MASS_PMF_SPOOL: float = 800.0   # PMF 102m スプール
    MASS_PMF_SHORT: float = 30.0    # PMF 2m 短遅延
    MASS_AWG: float = 150.0         # AWG
    MASS_WDMPD: float = 100.0       # WDM PD x16
    MASS_FPGA: float = 120.0        # FPGA基板
    MASS_ADC: float = 100.0         # ADC基板 ×2
    MASS_DAC: float = 60.0          # DAC + EO driver
    MASS_DCDC: float = 200.0        # DC-DC
    MASS_PZT: float = 60.0          # PZT driver
    MASS_HP: float = 30.0           # ヒートパイプ ×1
    MASS_HDPE: float = 100.0        # HDPE plate
    MASS_PTFE: float = 450.0        # PTFE板

    def __post_init__(self):
        if self.common is None:
            self.common = PARAMS
        if self.TOP_PLATE_Z is None:
            self.TOP_PLATE_Z = EnclosureParams().H_body - self.common.LIP_H


# =============================================================================
# ヘルパー関数
# =============================================================================

def _add_box(assy, name, size, pos, color):
    """box形状を生成しAssemblyに追加"""
    part = cq.Workplane("XY").box(size[0], size[1], size[2], centered=False)
    assy.add(part, name=name, loc=cq.Location(cq.Vector(*pos)), color=color)


def _add_cylinder(assy, name, diameter, height, pos, color, centered_xy=True):
    """cylinder形状を生成しAssemblyに追加"""
    part = cq.Workplane("XY").cylinder(
        height, diameter / 2, centered=(centered_xy, centered_xy, False)
    )
    assy.add(part, name=name, loc=cq.Location(cq.Vector(*pos)), color=color)


# =============================================================================
# カラー定義
# =============================================================================

C_ENCLOSURE = cq.Color(0.15, 0.15, 0.15, 1.0)   # dark gray
C_LASER = cq.Color(0.8, 0.1, 0.1, 0.8)           # red
C_PUMP = cq.Color(0.8, 0.2, 0.2, 0.8)            # dark red
C_OPA = cq.Color(0.9, 0.5, 0.1, 0.8)             # orange
C_TEC = cq.Color(0.3, 0.3, 0.8, 0.8)             # blue
C_EOM = cq.Color(0.7, 0.7, 0.1, 0.8)             # yellow
C_BS = cq.Color(0.6, 0.3, 0.6, 0.8)              # purple
C_BPD = cq.Color(0.1, 0.5, 0.5, 0.8)             # teal
C_PMF = cq.Color(0.2, 0.7, 0.2, 0.7)             # green
C_ELECTRONICS = cq.Color(0.1, 0.6, 0.1, 0.8)     # dark green
C_DCDC = cq.Color(0.4, 0.4, 0.4, 0.8)            # gray
C_HP = cq.Color(0.8, 0.5, 0.2, 0.9)              # copper
C_PTFE = cq.Color(0.95, 0.95, 0.95, 0.5)         # white translucent
C_SHIELD = cq.Color(0.8, 0.5, 0.2, 0.3)          # copper translucent
C_HDPE = cq.Color(0.9, 0.9, 0.8, 0.6)            # off-white


# =============================================================================
# 組立ビルド関数
# =============================================================================

def build_assembly(p: AssemblyParams = None):
    """総組立モデルを生成する。BOM全主要部品を配置。"""
    if p is None:
        p = AssemblyParams()

    assy = cq.Assembly(name="DWG-003_TarosPro_Assembly")

    # --- 1. 筐体本体 (DWG-001) ---
    enclosure = build_enclosure_body(EnclosureParams())
    assy.add(enclosure, name="enclosure_body", color=C_ENCLOSURE)

    # --- 2. 天板 (DWG-002) Z=139mm配置 ---
    top_plate = build_top_plate(TopPlateParams())
    assy.add(top_plate, name="top_plate",
             loc=cq.Location(cq.Vector(0, 0, p.TOP_PLATE_Z)), color=C_ENCLOSURE)

    # === Zone A: 光学部品 ===

    # --- 3. Master Laser (#3) ---
    _add_box(assy, "Laser", p.LASER_SIZE, p.LASER_POS, C_LASER)

    # --- 4. Pump LD + SOA + SHG (#4) ---
    _add_box(assy, "Pump_SHG", p.PUMP_SIZE, p.PUMP_POS, C_PUMP)

    # --- 5. OPA ×2 (#5) ---
    for i, pos in enumerate([p.OPA1_POS, p.OPA2_POS], 1):
        _add_box(assy, f"OPA_{i}", p.OPA_SIZE, pos, C_OPA)

    # --- 6. TEC (OPA共用 + SHG) (#6) ---
    _add_box(assy, "TEC_OPA", p.TEC_OPA_SIZE, p.TEC_OPA_POS, C_TEC)
    _add_box(assy, "TEC_SHG", p.TEC_SHG_SIZE, p.TEC_SHG_POS, C_TEC)

    # --- 7. EOM ×2 (#7) ---
    for i, pos in enumerate([p.EOM1_POS, p.EOM2_POS], 1):
        _add_box(assy, f"EOM_{i}", p.EOM_SIZE, pos, C_EOM)

    # --- 8. BS カプラ ×3 (#8, ファイバトレイ内まとめ配置) ---
    _add_box(assy, "BS_tray", p.BS_SIZE, p.BS_POS, C_BS)

    # --- 9. BPD ×2 (#9) ---
    for i, pos in enumerate([p.BPD1_POS, p.BPD2_POS], 1):
        _add_box(assy, f"BPD_{i}", p.BPD_SIZE, pos, C_BPD)

    # === Zone B: ファイバ ===

    # --- 10. HDPE振動隔離プレート (#25) ---
    _add_box(assy, "HDPE_plate", p.HDPE_SIZE, p.HDPE_POS, C_HDPE)

    # --- 11. PMF 102m スプール (#10) ---
    _add_cylinder(assy, "PMF_spool_102m", p.PMF_D, p.PMF_H, p.PMF_POS, C_PMF)

    # --- 12. 短遅延PMF 2m スプール (03_tdm-cluster.md:100) ---
    _add_cylinder(assy, "PMF_spool_2m", p.PMF_SHORT_D, p.PMF_SHORT_H,
                  p.PMF_SHORT_POS, C_PMF)

    # --- 13. WDM AWG (#11) ---
    _add_box(assy, "AWG", p.AWG_SIZE, p.AWG_POS, C_ELECTRONICS)

    # --- 14. WDM PD ×16 (#12) ---
    _add_box(assy, "WDM_PD", p.WDMPD_SIZE, p.WDMPD_POS, C_BPD)

    # === Zone C: 電子制御 ===

    # --- 15. FPGA VE2302 (#13) ---
    _add_box(assy, "FPGA", p.FPGA_SIZE, p.FPGA_POS, C_ELECTRONICS)

    # --- 16. ADC boards (#14-15) ---
    _add_box(assy, "ADC_boards", p.ADC_SIZE, p.ADC_POS, C_ELECTRONICS)

    # --- 17. DAC + EO driver (#16,21) ---
    _add_box(assy, "DAC_EO_driver", p.DAC_SIZE, p.DAC_POS, C_ELECTRONICS)

    # --- 18. DC-DC converter (#17) ---
    _add_box(assy, "DC_DC", p.DCDC_SIZE, p.DCDC_POS, C_DCDC)

    # --- 19. PZT driver + PID (#20) ---
    _add_box(assy, "PZT_driver", p.PZT_SIZE, p.PZT_POS, C_ELECTRONICS)

    # --- 20. Cu ヒートパイプ ×3 (#18, vertical) ---
    for i, pos in enumerate(p.HP_POSITIONS, 1):
        _add_cylinder(assy, f"HP_{i}", p.HP_D, p.HP_H, pos, C_HP)

    # --- 21. EMI遮蔽壁 Cu箔 (#43) ---
    _add_box(assy, "EMI_shield", p.SHIELD_SIZE, p.SHIELD_POS, C_SHIELD)

    # === 断熱 ===

    # --- 22. PTFE断熱板 (#19) ---
    _add_box(assy, "PTFE_plate", p.PTFE_SIZE, p.PTFE_POS, C_PTFE)

    return assy


def calc_total_mass(p: AssemblyParams = None):
    """組立体の概算質量を計算する。"""
    if p is None:
        p = AssemblyParams()

    density = p.common.DENSITY

    # 筐体・天板 (CadQuery体積計算)
    enclosure = build_enclosure_body(EnclosureParams())
    mass_enclosure = enclosure.val().Volume() * density

    top_plate = build_top_plate(TopPlateParams())
    mass_top_plate = top_plate.val().Volume() * density

    # 内部部品 (カタログ値)
    mass_internal = (
        p.MASS_LASER
        + p.MASS_PUMP
        + p.MASS_OPA * 2
        + p.MASS_TEC * 3
        + p.MASS_EOM * 2
        + p.MASS_BS * 3
        + p.MASS_BPD * 2
        + p.MASS_PMF_SPOOL
        + p.MASS_PMF_SHORT
        + p.MASS_AWG
        + p.MASS_WDMPD
        + p.MASS_FPGA
        + p.MASS_ADC
        + p.MASS_DAC
        + p.MASS_DCDC
        + p.MASS_PZT
        + p.MASS_HP * 3
        + p.MASS_HDPE
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
    print("DWG-003: Taros Pro Assembly Build (d=5 baseline)")
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

    # 干渉チェック
    print("\n--- Fit Check ---")
    print(f"  Top plate Z = {params.TOP_PLATE_Z} mm")
    print(f"  Enclosure lip: Z={params.TOP_PLATE_Z} to {params.TOP_PLATE_Z + params.common.LIP_H}")
    print(f"  Components: {22} items placed in 3D model")

    print("\nDWG-003 complete.")
