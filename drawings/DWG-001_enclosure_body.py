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
  くり抜き深さ: 294 × 244 × 139 mm              ← 導出: (300-6)×(250-6)×(142-3)
  有効内部空間 (天板嵌合後): 294 × 244 × 136 mm ← 導出: (142-3底板-3リップ)
  ※天板(DWG-002)と合わせて外寸 300×250×160mm (フィン18mm込み)

# 内寸高さ: 136mm確定。12_mechanical.md:L30 を 136mm に統一済み。
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
    FOOT_BORE_DEPTH: float = 2.5  # 下穴深さ [mm] (底板厚3mm以内、貫通防止)

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
    # TODO(設計判断要): グロメット穴はZone A/B間の内部仕切壁(X=135)を貫通する設計。
    # EMI遮蔽壁(X=210)は Step 9 で実装済み。Zone A/B間仕切壁は未実装。
    # Phase 0a で仕切構造確定後にグロメット穴も実装のこと。
    GROMMET_D: float = 10.0    # φ10mm — Zone A-B間ファイバ通過
    GROMMET_X: float = 135.0   # X位置 (Zone A/B境界)
    GROMMET_Y1: float = 80.0
    GROMMET_Y2: float = 170.0
    GROMMET_Z: float = 50.0

    # === Zone間仕切り取付溝 (出典: 12_mechanical §1.3) ===
    PTFE_Z: float = 90.0       # 溝底面Z位置 [mm]
    PTFE_T: float = 3.0        # 板厚 [mm]
    PTFE_GROOVE_D: float = 1.5 # 溝深さ [mm] (側壁に切り込み)
    PTFE_GROOVE_ENABLED: bool = True  # 溝加工有効化フラグ

    # === EMI遮蔽壁取付溝 (出典: 12_mechanical §3.3, DWG-003 BOM #43) ===
    # Zone B/C 境界 (X=210) に銅箔シールド壁 (0.1mm Cu) の取付溝
    SHIELD_X: float = 210.0        # X位置 [mm] (Zone B/C境界)
    SHIELD_GROOVE_W: float = 1.0   # 溝幅 [mm] (0.1mm Cu箔 + 接着マージン)
    SHIELD_GROOVE_D: float = 1.5   # 溝深さ [mm] (底板3mmのうち1.5mm)
    SHIELD_GROOVE_ENABLED: bool = True

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
        # SLIT_Z_END 整合性チェック
        expected_z_end = self.SLIT_Z_START + (self.SLIT_N - 1) * self.SLIT_PITCH
        assert abs(self.SLIT_Z_END - expected_z_end) < 0.01, (
            f"SLIT_Z_END={self.SLIT_Z_END} != calculated {expected_z_end}"
        )


def build_enclosure_body(p: EnclosureParams = None):
    """筐体本体を生成

    座標系注意:
      CadQuery の faces().workplane() は面の重心を原点とするため、
      絶対座標 (x, y) を指定するには .move(x - center_x, y - center_y) とする。
      - >Z/<Z 面: center = (W/2, D/2)
      - <X/>X 面: center = (D/2, H_body/2)  ※local X=Y方向, local Y=Z方向
      - >Y 面:    center = (W/2, H_body/2)  ※local X=X方向, local Y=Z方向
    """
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
    H_inner = H_body - T_bottom    # 139mm (くり抜き深さ)

    # 1. 外殻ブロック
    body = cq.Workplane("XY").box(W, D, H_body, centered=False)

    # 2. 内部くり抜き (底板3mm残し)
    # >Z面中心 = (W/2, D/2)。centered=True の rect は面中心に対称配置
    body = (
        body
        .faces(">Z")
        .workplane()
        .rect(W_inner, D_inner)
        .cutBlind(-H_inner)
    )

    # 3. 天板嵌合段差 (上端内側にリップ)
    # リップ領域: 298×248mm (= W_inner+2*LIP_W × D_inner+2*LIP_W)、面中心に対称
    body = (
        body
        .faces(">Z")
        .workplane()
        .rect(W_inner + 2 * LIP_W, D_inner + 2 * LIP_W)
        .cutBlind(-LIP_H)
    )

    # 4. 側面スリット (左右対称)
    # スリット中心 Y = SLIT_Y_START + SLIT_L/2 = 25 + 100 = 125 = D/2 (Y対称)
    for i in range(p.SLIT_N):
        z = p.SLIT_Z_START + i * p.SLIT_PITCH
        for face_sel in ["<X", ">X"]:
            body = (
                body
                .faces(face_sel)
                .workplane()
                .move(0, z - H_body / 2)
                .rect(p.SLIT_L, p.SLIT_W)
                .cutBlind(-T_side)
            )

    # 5. 底面ファン開口 (円形φ70mm + 取付穴4箇所)
    # <Z面中心 = (W/2, D/2)。ファン中心 = (150, 125) = 面中心 → offset (0, 0)
    body = (
        body
        .faces("<Z")
        .workplane()
        .move(p.FAN_X_CENTER - W / 2, p.FAN_Y_CENTER - D / 2)
        .circle(p.FAN_SIZE / 2 - 5)  # φ70mm開口
        .cutBlind(-T_bottom)
    )
    # ファン取付穴 M4 × 4 (ザグリ φ8×1mm + 通し穴 φ4.5)
    half_p = p.FAN_MOUNT_PITCH / 2
    for dx, dy in [(-half_p, -half_p), (half_p, -half_p),
                   (-half_p, half_p), (half_p, half_p)]:
        # ザグリ φ8×1mm
        body = (
            body
            .faces("<Z")
            .workplane()
            .move(p.FAN_X_CENTER + dx - W / 2, p.FAN_Y_CENTER + dy - D / 2)
            .circle(4.0)
            .cutBlind(-1.0)
        )
        # 通し穴 φ4.5
        body = (
            body
            .faces("<Z")
            .workplane()
            .move(p.FAN_X_CENTER + dx - W / 2, p.FAN_Y_CENTER + dy - D / 2)
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
            .move(fx - W / 2, fy - D / 2)
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

    # 8. PTFE断熱板取付溝 (4面側壁内面, Z=90mm)
    # faces("<X") は外壁面(X=0)を選択するため、cutBlind では外面側に溝ができてしまう。
    # 内壁面に溝を作るには Step 9 (EMI溝) と同じ transformed+box+cut 方式を使用する。
    # 溝位置: 各壁の内面から PTFE_GROOVE_D (1.5mm) 切り込み
    if p.PTFE_GROOVE_ENABLED:
        gd = p.PTFE_GROOVE_D  # 1.5mm
        pt = p.PTFE_T          # 3.0mm (溝高さ = PTFE板厚)
        pz = p.PTFE_Z          # 90.0mm (溝底面Z)

        # 左壁内面溝: X = T_side - gd .. T_side (= 1.5 .. 3.0)
        left_groove = (
            cq.Workplane("XY")
            .transformed(offset=(T_side - gd, T_side, pz))
            .box(gd, D_inner, pt, centered=False)
        )
        body = body.cut(left_groove)

        # 右壁内面溝: X = W - T_side .. W - T_side + gd (= 297.0 .. 298.5)
        right_groove = (
            cq.Workplane("XY")
            .transformed(offset=(W - T_side, T_side, pz))
            .box(gd, D_inner, pt, centered=False)
        )
        body = body.cut(right_groove)

        # 前壁内面溝: Y = T_side - gd .. T_side (= 1.5 .. 3.0)
        front_groove = (
            cq.Workplane("XY")
            .transformed(offset=(T_side, T_side - gd, pz))
            .box(W_inner, gd, pt, centered=False)
        )
        body = body.cut(front_groove)

        # 後壁内面溝: Y = D - T_side .. D - T_side + gd (= 247.0 .. 248.5)
        back_groove = (
            cq.Workplane("XY")
            .transformed(offset=(T_side, D - T_side, pz))
            .box(W_inner, gd, pt, centered=False)
        )
        body = body.cut(back_groove)

    # 9. EMI遮蔽壁取付溝 (底板上面, X=210, Zone B/C境界)
    # 銅箔シールド壁(0.1mm Cu, 238×134mm)の底板側固定溝
    if p.SHIELD_GROOVE_ENABLED:
        shield_groove = (
            cq.Workplane("XY")
            .transformed(offset=(p.SHIELD_X, T_side, T_bottom))
            .box(p.SHIELD_GROOVE_W, D_inner, p.SHIELD_GROOVE_D,
                 centered=(True, False, False))
        )
        body = body.cut(shield_groove)

    # 10. 背面ポート開口
    # >Y面: local X=X方向, local Y=Z方向, center=(W/2, H_body/2)
    # USB-C ×2
    for ux in [p.USBC_X1, p.USBC_X2]:
        body = (
            body
            .faces(">Y")
            .workplane()
            .move(ux - W / 2, p.USBC_Z - H_body / 2)
            .rect(p.USBC_W, p.USBC_H)
            .cutBlind(-T_side)
        )

    # RJ45
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(p.RJ45_X - W / 2, p.RJ45_Z - H_body / 2)
        .rect(p.RJ45_W, p.RJ45_H)
        .cutBlind(-T_side)
    )

    # DC入力
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(p.DC_X - W / 2, p.DC_Z - H_body / 2)
        .rect(p.DC_W, p.DC_H)
        .cutBlind(-T_side)
    )

    # GND端子穴
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(p.GND_X - W / 2, p.GND_Z - H_body / 2)
        .circle(p.GND_D / 2)
        .cutBlind(-T_side)
    )

    # 電源SW
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(p.SW_X - W / 2, p.SW_Z - H_body / 2)
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
