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

# === 基本パラメータ (出典: 12_mechanical.md §1.2) ===
W = 300.0   # 幅 [mm] — X方向
D = 250.0   # 奥行 [mm] — Y方向
H_body = 142.0  # 本体高さ [mm] — Z方向 (天板含まず: 160 - 18fin = 142)

T_bottom = 3.0   # 底板厚 [mm] — 12_mechanical §1.2
T_side = 3.0     # 側板厚 [mm] — 12_mechanical §1.2

# 天板嵌合段差 (本体上端に天板を載せるための段差)
LIP_W = 2.0      # 段差幅 [mm]
LIP_H = 3.0      # 段差深さ [mm] — 天板板厚と同一

# 内部寸法 (導出)
W_inner = W - 2 * T_side       # 294mm
D_inner = D - 2 * T_side       # 244mm
H_inner = H_body - T_bottom    # 139mm (側板内面高さ)

# === ゴム脚 (出典: 11_industrial-design.md §2) ===
FOOT_D = 15.0    # ゴム脚直径 [mm]
FOOT_INSET = 20.0  # 角からのインセット [mm]
FOOT_BORE_D = 5.5  # M5ネジ下穴径 [mm]
FOOT_BORE_DEPTH = 8.0  # 下穴深さ [mm]

# === 側面スリット (出典: 12_mechanical.md §1.2) ===
SLIT_N = 12       # 片側本数
SLIT_W = 2.0      # 幅 [mm]
SLIT_L = 200.0    # 長さ [mm] — Y方向
SLIT_Z_START = 30.0   # 開始Z [mm]
SLIT_Z_END = 130.0    # 終了Z [mm]
SLIT_PITCH = 8.0      # ピッチ [mm]
SLIT_Y_START = 25.0   # Y開始 [mm]

# === ファン開口 (出典: 11_industrial-design.md §7, 12_mechanical §4.2) ===
FAN_SIZE = 80.0       # ファンサイズ [mm] — Noctua NF-A8
FAN_MOUNT_PITCH = 71.5  # 取付穴ピッチ [mm]
FAN_BORE_D = 4.5      # M4ネジ穴径 [mm]
FAN_X_CENTER = 150.0  # 底面中央X
FAN_Y_CENTER = 125.0  # 底面中央Y

# === グロメット穴 (出典: 12_mechanical.md §2.2) ===
GROMMET_D = 10.0  # φ10mm — Zone A-B間ファイバ通過
GROMMET_X = 135.0  # X位置 (Zone A/B境界)
GROMMET_Y1 = 80.0
GROMMET_Y2 = 170.0
GROMMET_Z = 50.0

# === Zone間仕切り取付溝 ===
# PTFE断熱板 (Z=93, 3mm厚) 用の溝 — 12_mechanical §1.3
PTFE_Z = 90.0     # 溝底面Z位置 [mm]
PTFE_T = 3.0      # 板厚 [mm]
PTFE_GROOVE_D = 1.5  # 溝深さ [mm] (側壁に切り込み)

# === 天板固定ネジ穴 ===
TOP_SCREW_POSITIONS = [
    (30, 30), (150, 30), (270, 30),    # 前面3箇所
    (30, 125),            (270, 125),   # 側面2箇所
    (30, 220), (150, 220), (270, 220),  # 背面3箇所
]
TOP_SCREW_D = 2.5   # M3タップ下穴 [mm]
TOP_SCREW_DEPTH = 8.0

# === 背面ポート開口 (出典: 11_industrial-design.md §4) ===
# USB-C ×2
USBC_W = 9.0
USBC_H = 3.5
USBC_Y = D  # 背面 (Y=250)
USBC_X1 = 60.0
USBC_X2 = 90.0
USBC_Z = 20.0

# 10GbE RJ45
RJ45_W = 16.0
RJ45_H = 14.0
RJ45_X = 140.0
RJ45_Z = 15.0

# DC入力 (USB-PD EPR)
DC_W = 9.0
DC_H = 3.5
DC_X = 220.0
DC_Z = 20.0

# GND端子
GND_D = 8.0
GND_X = 250.0
GND_Z = 25.0

# 電源SW開口
SW_W = 20.0
SW_H = 13.0
SW_X = 270.0
SW_Z = 18.0


def build_enclosure_body():
    """筐体本体を生成"""

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
    for i in range(SLIT_N):
        z = SLIT_Z_START + i * SLIT_PITCH
        # 左側面 (X=0)
        body = (
            body
            .faces("<X")
            .workplane()
            .move(SLIT_Y_START, z)
            .rect(SLIT_L, SLIT_W, centered=False)
            .cutBlind(-T_side)
        )
        # 右側面 (X=300)
        body = (
            body
            .faces(">X")
            .workplane()
            .move(-(SLIT_Y_START + SLIT_L), z)
            .rect(SLIT_L, SLIT_W, centered=False)
            .cutBlind(-T_side)
        )

    # 5. 底面ファン開口 (円形φ75mm + 取付穴4箇所)
    body = (
        body
        .faces("<Z")
        .workplane()
        .move(FAN_X_CENTER, FAN_Y_CENTER)
        .circle(FAN_SIZE / 2 - 5)  # φ70mm開口
        .cutBlind(-T_bottom)
    )
    # ファン取付穴 M4 × 4
    half_p = FAN_MOUNT_PITCH / 2
    for dx, dy in [(-half_p, -half_p), (half_p, -half_p),
                   (-half_p, half_p), (half_p, half_p)]:
        body = (
            body
            .faces("<Z")
            .workplane()
            .move(FAN_X_CENTER + dx, FAN_Y_CENTER + dy)
            .circle(FAN_BORE_D / 2)
            .cutBlind(-T_bottom)
        )

    # 6. ゴム脚ネジ穴 M5 × 4 (底面)
    foot_positions = [
        (FOOT_INSET, FOOT_INSET),
        (W - FOOT_INSET, FOOT_INSET),
        (FOOT_INSET, D - FOOT_INSET),
        (W - FOOT_INSET, D - FOOT_INSET),
    ]
    for fx, fy in foot_positions:
        body = (
            body
            .faces("<Z")
            .workplane()
            .move(fx, fy)
            .circle(FOOT_BORE_D / 2)
            .cutBlind(-FOOT_BORE_DEPTH)
        )

    # 7. 天板固定ネジ穴 M3 × 8 (上端面)
    for sx, sy in TOP_SCREW_POSITIONS:
        body = (
            body
            .faces(">Z")
            .workplane()
            .move(sx - W / 2, sy - D / 2)
            .circle(TOP_SCREW_D / 2)
            .cutBlind(-TOP_SCREW_DEPTH)
        )

    # 8. 背面ポート開口
    # USB-C ×2
    for ux in [USBC_X1, USBC_X2]:
        body = (
            body
            .faces(">Y")
            .workplane()
            .move(ux - W / 2, USBC_Z)
            .rect(USBC_W, USBC_H)
            .cutBlind(-T_side)
        )

    # RJ45
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(RJ45_X - W / 2, RJ45_Z)
        .rect(RJ45_W, RJ45_H)
        .cutBlind(-T_side)
    )

    # DC入力
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(DC_X - W / 2, DC_Z)
        .rect(DC_W, DC_H)
        .cutBlind(-T_side)
    )

    # GND端子穴
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(GND_X - W / 2, GND_Z)
        .circle(GND_D / 2)
        .cutBlind(-T_side)
    )

    # 電源SW
    body = (
        body
        .faces(">Y")
        .workplane()
        .move(SW_X - W / 2, SW_Z)
        .rect(SW_W, SW_H)
        .cutBlind(-T_side)
    )

    return body


if __name__ == "__main__":
    import os
    out_dir = os.path.dirname(os.path.abspath(__file__))

    result = build_enclosure_body()

    # STEP出力
    step_path = os.path.join(out_dir, "DWG-001_enclosure_body.step")
    cq.exporters.export(result, step_path)
    print(f"STEP exported: {step_path}")

    # DXF出力 (上面図)
    dxf_path = os.path.join(out_dir, "DWG-001_enclosure_body_top.dxf")
    cq.exporters.export(result, dxf_path, exportType="DXF")
    print(f"DXF exported: {dxf_path}")

    print("DWG-001 complete.")
