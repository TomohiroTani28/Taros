#!/usr/bin/env python3
"""
DWG-001: Taros Pro 筐体本体 (Lower Body)
出典: design/12_mechanical.md §1.1-1.2, design/11_industrial-design.md §2

材質: A6063-T5
加工: CNC 5軸
表面処理: 硫酸アノダイズド 黒 膜厚15μm (JIS H 8601 AA15)

寸法体系:
  外寸: 300 × 250 × 142 mm (W × D × H_body)  ← 12_mechanical §1.2
  肉厚: 底板 3mm, 側板 3mm                      ← 12_mechanical §1.2
  内寸: 294 × 244 × 136 mm                     ← 導出: (300-6)×(250-6)×(142-3-3)
  ※天板(DWG-002)と合わせて外寸 300×250×160mm (フィン18mm込み)

# TODO(設計判断要): 内寸高さ 12_mechanical記載137mmと導出値136mmに1mm差異。
#   天板嵌合部の段差(1mm)で吸収と推定。Phase 0a試作で確定のこと。
"""

import cadquery as cq
from dataclasses import dataclass
from taros_params import TarosProParams, PARAMS


@dataclass
class EnclosureParams:
    """DWG-001 筐体本体固有パラメータ"""

    # === 共通パラメータ参照 ===
    common: TarosProParams = None

    # === 本体高さ (出典: 12_mechanical.md §1.2) ===
    H_body: float = 142.0   # 本体高さ [mm] — Z方向 (天板含まず: 160 - 18fin = 142)

    # === ゴム脚 (出典: 11_industrial-design.md §2) ===
    FOOT_D: float = 15.0          # ゴム脚直径 [mm]
    FOOT_INSET: float = 20.0      # 角からのインセット [mm]
    FOOT_BORE_D: float = 4.2      # M5タップ下穴径 [mm] (JIS: φ4.2 for M5×0.8)
    FOOT_BORE_DEPTH: float = 8.0  # 下穴深さ [mm]

    # === 側面スリット (出典: 12_mechanical.md §1.2) ===
    SLIT_N: int = 12          # 片側本数
    SLIT_W: float = 2.0       # 幅 [mm]
    SLIT_L: float = 200.0     # 長さ [mm] — Y方向
    SLIT_Z_START: float = 30.0    # 開始Z [mm]
    SLIT_Z_END: float = 118.0     # 終了Z [mm]
    SLIT_PITCH: float = 8.0       # ピッチ [mm]
    SLIT_Y_START: float = 25.0    # Y開始 [mm]

    # === ファン開口 (出典: 11_industrial-design.md §7, 12_mechanical §4.2) ===
    FAN_SIZE: float = 80.0          # ファンサイズ [mm] — Noctua NF-A8
    FAN_MOUNT_PITCH: float = 71.5   # 取付穴ピッチ [mm]
    FAN_BORE_D: float = 4.5         # M4ネジ穴径 [mm]
    FAN_X_CENTER: float = 150.0     # 底面中央X
    FAN_Y_CENTER: float = 125.0     # 底面中央Y

    # === グロメット穴 (出典: 12_mechanical.md §2.2) ===
    GROMMET_D: float = 10.0    # φ10mm — Zone A-B間ファイバ通過
    GROMMET_X: float = 135.0   # X位置 (Zone A/B境界)
    GROMMET_Y1: float = 80.0
    GROMMET_Y2: float = 170.0
    GROMMET_Z: float = 50.0

    # === Zone間仕切り取付溝 (出典: 12_mechanical §1.3) ===
    PTFE_Z: float = 90.0       # 溝底面Z位置 [mm]
    PTFE_T: float = 3.0        # 板厚 [mm]
    PTFE_GROOVE_D: float = 1.5 # 溝深さ [mm] (側壁に切り込み)

    # === 天板固定ネジ穴 ===
    TOP_SCREW_D: float = 2.5       # M3タップ下穴 [mm]
    TOP_SCREW_DEPTH: float = 8.0

    # === 背面ポート開口 (出典: 11_industrial-design.md §4) ===
    # USB-C ×2
    USBC_W: float = 9.0
    USBC_H: float = 3.5
    USBC_X1: float = 60.0
    USBC_X2: float = 90.0
    USBC_Z: float = 20.0

    # 10GbE RJ45
    RJ45_W: float = 16.0
    RJ45_H: float = 14.0
    RJ45_X: float = 140.0
    RJ45_Z: float = 15.0

    # DC入力 (USB-PD EPR)
    DC_W: float = 9.0
    DC_H: float = 3.5
    DC_X: float = 220.0
    DC_Z: float = 20.0

    # GND端子
    GND_D: float = 8.0
    GND_X: float = 250.0
    GND_Z: float = 25.0

    # 電源SW開口
    SW_W: float = 20.0
    SW_H: float = 13.0
    SW_X: float = 270.0
    SW_Z: float = 18.0

    def __post_init__(self):
        if self.common is None:
            self.common = PARAMS


def build_enclosure_body(p: EnclosureParams = None):
    """筐体本体を生成"""
    if p is None:
        p = EnclosureParams()

    c = p.common  # 共通パラメータ

    # 導出寸法
    W = c.W
    D = c.D
    H_body = p.H_body
    T_side = c.T_side
    T_bottom = c.T_bottom
    LIP_W = c.LIP_W
    LIP_H = c.LIP_H
    W_inner = W - 2 * T_side       # 294mm
    D_inner = D - 2 * T_side       # 244mm
    H_inner = H_body - T_bottom    # 139mm (側板内面高さ)

    # 1. 外殻ブロック
    body = cq.Workplane("XY").box(W, D, H_body, centered=False)

    # 2. 内部くり抜き (底板3mm残し)
    body = (
        body
        .faces(">Z")
        .workplane()
        .move(T_side, T_side)
        .rect(W_inner, D_inner, centered=False)
        .cutBlind(-(H_inner))
    )

    # 3. 天板嵌合段差 (上端内側にリップ)
    body = (
        body
        .faces(">Z")
        .workplane()
        .move(T_side - LIP_W, T_side - LIP_W)
        .rect(W_inner + 2 * LIP_W, D_inner + 2 * LIP_W, centered=False)
        .cutBlind(-LIP_H)
    )

    # 4. 側面スリット (左右対称)
    for i in range(p.SLIT_N):
        z = p.SLIT_Z_START + i * p.SLIT_PITCH
        # 左側面 (X=0)
        body = (
            body
            .faces("<X")
            .workplane()
            .move(p.SLIT_Y_START, z)
            .rect(p.SLIT_L, p.SLIT_W, centered=False)
            .cutBlind(-T_side)
        )
        # 右側面 (X=300)
        body = (
            body
            .faces(">X")
            .workplane()
            .move(-(p.SLIT_Y_START + p.SLIT_L), z)
            .rect(p.SLIT_L, p.SLIT_W, centered=False)
            .cutBlind(-T_side)
        )

    # 5. 底面ファン開口 (円形φ75mm + 取付穴4箇所)
    body = (
        body
        .faces("<Z")
        .workplane()
        .move(p.FAN_X_CENTER, p.FAN_Y_CENTER)
        .circle(p.FAN_SIZE / 2 - 5)  # φ70mm開口
        .cutBlind(-T_bottom)
    )
    # ファン取付穴 M4 × 4
    half_p = p.FAN_MOUNT_PITCH / 2
    for dx, dy in [(-half_p, -half_p), (half_p, -half_p),
                   (-half_p, half_p), (half_p, half_p)]:
        body = (
            body
            .faces("<Z")
            .workplane()
            .move(p.FAN_X_CENTER + dx, p.FAN_Y_CENTER + dy)
            .circle(p.FAN_BORE_D / 2)
            .cutBlind(-T_bottom)
        )

    # 6. ゴム脚ネジ穴 M5 × 4 (底面)
    foot_positions = [
        (p.FOOT_INSET, p.FOOT_INSET),
        (W - p.FOOT_INSET, p.FOOT_INSET),
        (p.FOOT_INSET, D - p.FOOT_INSET),
        (W - p.FOOT_INSET, D - p.FOOT_INSET),
    ]
    for fx, fy in foot_positions:
        body = (
            body
            .faces("<Z")
            .workplane()
            .move(fx, fy)
            .circle(p.FOOT_BORE_D / 2)
            .cutBlind(-p.FOOT_BORE_DEPTH)
        )

    # 7. 天板固定ネジ穴 M3 × 8 (上端面)
    for sx, sy in c.TOP_SCREW_POSITIONS:
        body = (
            body
            .faces(">Z")
            .workplane()
            .move(sx - W / 2, sy - D / 2)
            .circle(p.TOP_SCREW_D / 2)
            .cutBlind(-p.TOP_SCREW_DEPTH)
        )

    # 8. 背面ポート開口
    # USB-C ×2
    for ux in [p.USBC_X1, p.USBC_X2]:
        body = (
            body
            .faces(">Y")
            .workplane()
            .move(ux - W / 2, p.USBC_Z)
            .rect(p.USBC_W, p.USBC_H)
            .cutBlind(-T_side)
        )

    # RJ45
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(p.RJ45_X - W / 2, p.RJ45_Z)
        .rect(p.RJ45_W, p.RJ45_H)
        .cutBlind(-T_side)
    )

    # DC入力
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(p.DC_X - W / 2, p.DC_Z)
        .rect(p.DC_W, p.DC_H)
        .cutBlind(-T_side)
    )

    # GND端子穴
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(p.GND_X - W / 2, p.GND_Z)
        .circle(p.GND_D / 2)
        .cutBlind(-T_side)
    )

    # 電源SW
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(p.SW_X - W / 2, p.SW_Z)
        .rect(p.SW_W, p.SW_H)
        .cutBlind(-T_side)
    )

    return body


if __name__ == "__main__":
    import os
    out_dir = os.path.dirname(os.path.abspath(__file__))

    params = EnclosureParams()
    result = build_enclosure_body(params)

    # STEP出力
    step_path = os.path.join(out_dir, "DWG-001_enclosure_body.step")
    cq.exporters.export(result, step_path)
    print(f"STEP exported: {step_path}")

    # STL出力
    stl_path = os.path.join(out_dir, "DWG-001_enclosure_body.stl")
    cq.exporters.export(result, stl_path, exportType="STL")
    print(f"STL exported: {stl_path}")

    # DXF出力 (上面図)
    dxf_path = os.path.join(out_dir, "DWG-001_enclosure_body_top.dxf")
    cq.exporters.export(result, dxf_path, exportType="DXF")
    print(f"DXF exported: {dxf_path}")

    # 質量計算
    volume_mm3 = result.val().Volume()
    density = params.common.DENSITY  # g/mm^3
    mass_g = volume_mm3 * density
    print(f"Volume: {volume_mm3:.1f} mm^3")
    print(f"Mass: {mass_g:.1f} g ({mass_g/1000:.3f} kg) [{params.common.MATERIAL}]")

    print("DWG-001 complete.")
