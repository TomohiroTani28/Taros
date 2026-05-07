#!/usr/bin/env python3
"""Generate TAROS Investor Pitch Deck v4.1 (17 slides)
Fixes: text overlaps, layout variety, font sizing for Japanese text"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

# ── Design System ──
BG_DARK = RGBColor(0x1A, 0x23, 0x32)  # Dark navy
BG_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ACCENT = RGBColor(0x00, 0xBC, 0xD4)    # Cyan
ACCENT2 = RGBColor(0x26, 0xC6, 0xDA)
TEXT_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEXT_DARK = RGBColor(0x21, 0x21, 0x21)
TEXT_GRAY = RGBColor(0x75, 0x75, 0x75)
TEXT_LIGHT = RGBColor(0xB0, 0xBE, 0xC5)
CARD_BG = RGBColor(0xF5, 0xF5, 0xF5)
HIGHLIGHT = RGBColor(0xFF, 0x98, 0x00)  # Orange
RED_SOFT = RGBColor(0xEF, 0x53, 0x50)
GREEN = RGBColor(0x66, 0xBB, 0x6A)
PURPLE = RGBColor(0x7E, 0x57, 0xC2)

W = Inches(13.333)
H = Inches(7.5)

prs = Presentation()
prs.slide_width = W
prs.slide_height = H


def add_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_text(slide, left, top, width, height, text, size=18, bold=False,
             color=TEXT_DARK, align=PP_ALIGN.LEFT, font_name="Meiryo"):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top),
                                     Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = align
    return tf


def add_para(tf, text, size=18, bold=False, color=TEXT_DARK, align=PP_ALIGN.LEFT):
    p = tf.add_paragraph()
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.alignment = align
    p.font.name = "Meiryo"
    return p


def add_rect(slide, left, top, width, height, fill_color, border_color=None):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(left), Inches(top),
        Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def add_accent_line(slide, left, top, width):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(left), Inches(top),
        Inches(width), Pt(4))
    shape.fill.solid()
    shape.fill.fore_color.rgb = ACCENT
    shape.line.fill.background()


def add_header(slide, section_label, page_num=None):
    add_text(slide, 0.6, 0.3, 3, 0.4, "T A R O S", size=12, bold=True, color=ACCENT)
    add_accent_line(slide, 1.8, 0.48, 0.5)
    if page_num:
        add_text(slide, 11.5, 0.3, 1.5, 0.4, f"{page_num} / 17",
                 size=10, color=TEXT_GRAY, align=PP_ALIGN.RIGHT)
    add_text(slide, 0.6, 0.7, 5, 0.4, section_label, size=12, bold=True, color=ACCENT)


def card(slide, left, top, width, height, title, value, desc, title_size=11,
         value_size=28, desc_size=10, accent_top=True):
    add_rect(slide, left, top, width, height, CARD_BG)
    if accent_top:
        add_accent_line(slide, left, top, width)
    add_text(slide, left + 0.15, top + 0.15, width - 0.3, 0.3,
             title, size=title_size, color=TEXT_GRAY)
    add_text(slide, left + 0.15, top + 0.5, width - 0.3, 0.5,
             value, size=value_size, bold=True, color=ACCENT)
    add_text(slide, left + 0.15, top + 1.05, width - 0.3, 0.5,
             desc, size=desc_size, color=TEXT_GRAY)


# ════════════════════════════════════════════════════
# SLIDE 1: COVER — fixed text overlap
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_DARK)
add_accent_line(s, 0.8, 1.2, 0.06)
add_text(s, 0.95, 0.8, 10, 1.5, "TAROS", size=96, bold=True, color=TEXT_WHITE)
add_text(s, 0.95, 2.1, 10, 0.5,
         "D e s k t o p   P h o t o n i c   Q u a n t u m   C o m p u t e r",
         size=14, color=ACCENT)
# Split long Japanese title into 2 lines to prevent overlap
add_text(s, 0.95, 3.0, 11, 0.6,
         "AC アダプタで動く",
         size=28, bold=True, color=TEXT_WHITE)
add_text(s, 0.95, 3.5, 11, 0.6,
         "デスクトップ誤り訂正型光量子コンピュータ",
         size=28, bold=True, color=TEXT_WHITE)
add_text(s, 0.95, 4.2, 11, 0.5,
         "7-in-1 Quantum Platform  |  完全室温・109W  |  1,350万〜2,550万円",
         size=14, color=TEXT_LIGHT)
add_text(s, 0.95, 4.8, 11, 0.5,
         "購入初日から6つの商用モードが稼働 — 量子優位証明を待たずに価値を提供",
         size=13, bold=True, color=ACCENT2)
add_text(s, 0.8, 6.8, 3, 0.4, "I n v e s t o r   P i t c h", size=10, color=ACCENT)
add_text(s, 9.5, 6.8, 3.5, 0.4, "C o n f i d e n t i a l   |   v 4 . 1",
         size=10, color=TEXT_LIGHT, align=PP_ALIGN.RIGHT)

# ════════════════════════════════════════════════════
# SLIDE 2: VISION — 7-in-1 (7 cards, unique layout — keep)
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "V I S I O N", "2")
add_text(s, 0.6, 1.1, 12, 0.8,
         "1台で7役。購入初日から価値を届ける。", size=34, bold=True, color=TEXT_DARK)

modes = [
    ("Mode 1", "FTQC", "量子化学・量子重力", "Phase 0+", ACCENT),
    ("Mode 2", "CIM", "組合せ最適化\n~2,000スピン", "購入即日", GREEN),
    ("Mode 3", "QRC", "時系列予測\n異常検知", "購入即日", GREEN),
    ("Mode 4", "QRNG", "量子乱数\n~200Mbps", "購入即日", GREEN),
    ("Mode 5", "Sensing", "SQL以下\n精密測定", "購入即日", GREEN),
    ("Mode 6", "Imaging", "サブショットノイズ\n顕微鏡", "購入即日", GREEN),
    ("Mode 7", "Tensor", "AI推論加速", "購入即日", GREEN),
]

for i, (mode, name, desc, avail, clr) in enumerate(modes):
    x = 0.6 + i * 1.72
    y = 2.2
    add_rect(s, x, y, 1.6, 2.8, CARD_BG)
    add_accent_line(s, x, y, 1.6)
    add_text(s, x + 0.08, y + 0.15, 1.44, 0.25, mode, size=9, color=TEXT_GRAY)
    add_text(s, x + 0.08, y + 0.4, 1.44, 0.35, name, size=18, bold=True, color=TEXT_DARK)
    add_text(s, x + 0.08, y + 0.85, 1.44, 0.7, desc, size=10, color=TEXT_GRAY)
    # availability badge
    add_rect(s, x + 0.08, y + 2.1, 1.3, 0.35, clr)
    add_text(s, x + 0.08, y + 2.12, 1.3, 0.35, avail,
             size=10, bold=True, color=TEXT_WHITE, align=PP_ALIGN.CENTER)

add_text(s, 0.6, 5.3, 12, 0.5,
         "Mode 2-7は購入初日からSW変更のみで稼働。追加ハードウェアゼロ。全モード共通HW。",
         size=13, bold=True, color=TEXT_DARK)
add_text(s, 0.6, 5.8, 12, 0.4,
         "† 初期SW設定1-2週間を含む。Mode 1(FTQC)はファームウェア更新で段階的に進化。",
         size=10, color=TEXT_GRAY)

# ════════════════════════════════════════════════════
# SLIDE 3: THE PROBLEM — fixed title overlap, layout: left text + right cards (2×2)
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "T H E   P R O B L E M", "3")

# Left: big statement
add_text(s, 0.6, 1.1, 5.5, 0.7,
         "量子コンピュータは", size=28, bold=True, color=TEXT_DARK)
add_text(s, 0.6, 1.7, 5.5, 0.7,
         "「データセンター専用」で", size=28, bold=True, color=TEXT_DARK)
add_text(s, 0.6, 2.3, 5.5, 0.7,
         "止まっている", size=28, bold=True, color=TEXT_DARK)
add_text(s, 0.6, 3.1, 5.5, 0.8,
         "超伝導・イオン方式は希釈冷凍機 (15mK)\nまたは高真空イオントラップを必須とし、\n原理的に小型化が不可能。",
         size=12, color=TEXT_GRAY)

# Right: 2×2 grid cards
labels = ["冷 却", "消 費 電 力", "サ イ ズ", "価 格"]
values = ["15mK ~ 4K", "30~200kW", "部屋規模", "4.5~22.5億円"]
descs = ["希釈冷凍機 / He冷凍機", "施設の専用配電が必要",
         "既存建屋への設置に改装必要", "購入は政府・大企業のみ"]

for i in range(4):
    col = i % 2
    row = i // 2
    x = 6.8 + col * 3.1
    y = 1.2 + row * 2.1
    add_rect(s, x, y, 2.9, 1.9, CARD_BG)
    add_rect(s, x, y, 2.9, Inches(0.04).inches, RED_SOFT)
    add_text(s, x + 0.15, y + 0.15, 2.6, 0.3, labels[i], size=11, color=TEXT_GRAY)
    add_text(s, x + 0.15, y + 0.5, 2.6, 0.5, values[i], size=22, bold=True, color=TEXT_DARK)
    add_text(s, x + 0.15, y + 1.1, 2.6, 0.5, descs[i], size=10, color=TEXT_GRAY)

# Bottom bar
add_rect(s, 0.6, 5.8, 12, 0.6, CARD_BG)
add_text(s, 0.8, 5.85, 11.6, 0.5,
         "結果: 量子コンピュータを「実機で触れる」研究者は世界で1万人未満。教育・研究のボトルネック。",
         size=12, color=TEXT_DARK, align=PP_ALIGN.CENTER)

# ════════════════════════════════════════════════════
# SLIDE 4: OUR SOLUTION — fixed: spec card layout
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "O U R   S O L U T I O N", "4")
add_text(s, 0.6, 1.1, 12, 0.6,
         "光だから、室温で動く。光だから、デスクに置ける。",
         size=30, bold=True, color=TEXT_DARK)

sol_labels = ["重量", "消費電力", "冷凍機", "価格"]
sol_values = ["7.5kg", "109W", "0K", "1,800万円"]
sol_descs = ["Pro モデル(WDM込み)", "USB-PD EPR 駆動", "完全室温", "Pro モデル"]

for i in range(4):
    x = 0.6 + i * 3.05
    add_rect(s, x, 1.9, 2.85, 1.6, CARD_BG)
    add_text(s, x + 0.15, 2.0, 2.55, 0.25, sol_labels[i], size=11, color=TEXT_GRAY)
    add_text(s, x + 0.15, 2.25, 2.55, 0.5, sol_values[i],
             size=28, bold=True, color=ACCENT)
    add_text(s, x + 0.15, 2.8, 2.55, 0.35, sol_descs[i], size=10, color=TEXT_GRAY)

# HOW + WHY NOW — side by side with accent bars
add_rect(s, 0.6, 3.8, 5.8, 3.2, CARD_BG)
add_text(s, 0.8, 3.9, 5.4, 0.3, "H O W  —  技 術 ス タ ッ ク",
         size=11, bold=True, color=ACCENT)
tech = [
    ("PPLN導波路OPA", "13dB スクイーズド光 (NTT 12.1dB CW実証)"),
    ("macronode TDM クラスタ", "光ファイバ遅延線で時分割に論理qubitを量産"),
    ("GKP + 表面符号 (d=3/5/7)", "Phase 2+ PIC 統合で +1.8dB マージン確保"),
]
for j, (t, d) in enumerate(tech):
    y_off = 4.35 + j * 0.7
    add_accent_line(s, 0.8, y_off, 0.06)
    add_text(s, 1.0, y_off + 0.02, 5.2, 0.3, t, size=12, bold=True)
    add_text(s, 1.0, y_off + 0.3, 5.2, 0.3, d, size=10, color=TEXT_GRAY)

add_rect(s, 6.6, 3.8, 6.0, 3.2, CARD_BG)
add_text(s, 6.8, 3.9, 5.6, 0.3, "W H Y   N O W  —  今 、 成 立 す る 理 由",
         size=11, bold=True, color=ACCENT)
why = [
    ("PPLN導波路の量産化", "NTT・住友・nLight 商用ライン稼働"),
    ("Soft-info MWPM 閾値確立", "Noh-Chamberland 2022 で1.5%確定"),
    ("Versal FPGA 27ns FF", "光-電気-光ループが ns級で閉じる時代"),
    ("CVBQP ⊇ BQP 証明", "ITCS 2025: CV量子計算≧標準QC"),
]
for j, (t, d) in enumerate(why):
    y_off = 4.35 + j * 0.6
    add_accent_line(s, 6.8, y_off, 0.06)
    add_text(s, 7.0, y_off + 0.02, 5.4, 0.3, t, size=12, bold=True)
    add_text(s, 7.0, y_off + 0.28, 5.4, 0.3, d, size=10, color=TEXT_GRAY)

# ════════════════════════════════════════════════════
# SLIDE 5: DAY-1 VALUE — changed to 2×2 grid (not 4 columns)
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "D A Y - 1   V A L U E", "5")
add_text(s, 0.6, 1.1, 12, 0.6,
         "量子優位を待たない。購入初日から収益化。", size=30, bold=True, color=TEXT_DARK)
add_text(s, 0.6, 1.7, 12, 0.4,
         "量子コンピュータ業界最大の問題 —「いつ役に立つのか?」— に対する回答",
         size=13, color=TEXT_GRAY)

day1_modes = [
    ("Mode 2: CIM", "組合せ最適化",
     "OPA閾値以下動作で最大~2,000スピン。車両ルーティング・スケジューリング。競合CIM製品($5K-50K)を内蔵。"),
    ("Mode 3: QRC", "量子リザーバ計算",
     "TDMループ=量子リザーバ。時系列予測・異常検知。14bit soft-infoで高精度。"),
    ("Mode 4: QRNG", "量子乱数 ~200Mbps",
     "ホモダインで真空ゆらぎ測定。認証済み量子乱数生成。$5K-50K製品のサイドプロダクト。"),
    ("Mode 5-7", "Sensing / Imaging / Tensor",
     "SQL以下精密測定 / サブショットノイズ顕微鏡 / フォトニック行列演算でAI推論加速。"),
]

for i, (title, subtitle, desc) in enumerate(day1_modes):
    col = i % 2
    row = i // 2
    x = 0.6 + col * 6.15
    y = 2.3 + row * 1.7
    add_rect(s, x, y, 5.95, 1.5, CARD_BG)
    add_accent_line(s, x, y, 5.95)
    add_text(s, x + 0.2, y + 0.15, 2.2, 0.3, title, size=14, bold=True, color=TEXT_DARK)
    add_text(s, x + 2.5, y + 0.15, 3.2, 0.3, subtitle, size=12, color=ACCENT)
    add_text(s, x + 0.2, y + 0.55, 5.55, 0.8, desc, size=11, color=TEXT_GRAY)

add_rect(s, 0.6, 5.9, 12, 0.6, BG_DARK)
add_text(s, 0.8, 5.95, 11.6, 0.5,
         "投資家にとっての意味: FTQC完成前からMode 2-7で顧客価値を提供し、初期売上を確保。",
         size=13, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)

# ════════════════════════════════════════════════════
# SLIDE 6: TECHNICAL EDGE — horizontal chain (unique, keep)
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "T E C H N I C A L   E D G E", "6")
add_text(s, 0.6, 1.1, 12, 0.6,
         "性能の根拠 — 数字は文献と独立計算で裏付け済み",
         size=28, bold=True, color=TEXT_DARK)

chain = [
    ("13dB", "PPLN OPA\n生成スクイージング"),
    ("L=0.27dB", "全劣化 (BSモデル)\nPIC統合・GAWBS・QE込み"),
    ("9.3dB", "実効 σ_eff\nBS モデル (現実Δ=0.12)"),
    ("~4.9×10⁻³", "p_phys\n物理エラー率 (erfc)"),
    ("~3.3×10⁻⁴", "p_L (d=7, MWPM)\n製品要件 (理論限界 6.1×10⁻⁷)"),
]

for i, (val, desc) in enumerate(chain):
    x = 0.4 + i * 2.5
    bg_c = ACCENT if i == 4 else CARD_BG
    txt_c = TEXT_WHITE if i == 4 else TEXT_DARK
    add_rect(s, x, 2.0, 2.3, 1.8, bg_c)
    add_text(s, x + 0.1, 2.1, 2.1, 0.5, val, size=20, bold=True, color=txt_c,
             align=PP_ALIGN.CENTER)
    add_text(s, x + 0.1, 2.65, 2.1, 0.8, desc, size=9,
             color=TEXT_WHITE if i == 4 else TEXT_GRAY, align=PP_ALIGN.CENTER)
    if i < 4:
        add_text(s, x + 2.15, 2.4, 0.4, 0.4, "→", size=18, bold=True, color=ACCENT)

# Threshold margin bar
add_text(s, 0.6, 4.2, 12, 0.4,
         "閾値マージン — Phase 2+ PIC 統合での量子誤り訂正成立余裕",
         size=13, bold=True, color=TEXT_DARK)
# Green bar (sigma_eff)
add_rect(s, 0.6, 4.7, 9.5, 0.45, GREEN)
add_text(s, 0.8, 4.72, 4, 0.4, "実効 σ_eff (Phase 2+ PIC現実)", size=10,
         color=TEXT_WHITE)
add_text(s, 9.2, 4.72, 1.5, 0.4, "9.3 dB", size=12, bold=True,
         color=TEXT_WHITE, align=PP_ALIGN.RIGHT)
# Purple bar (threshold)
add_rect(s, 0.6, 5.25, 7.2, 0.45, PURPLE)
add_text(s, 0.8, 5.27, 3, 0.4, "閾値 (postselection)", size=10, color=TEXT_WHITE)
add_text(s, 6.8, 5.27, 1.5, 0.4, "7.5 dB", size=12, bold=True,
         color=TEXT_WHITE, align=PP_ALIGN.RIGHT)
add_text(s, 0.6, 5.85, 12, 0.4,
         "→ Phase 2+ PIC 余裕 +1.8dB (postselection) — 製品要件 p_L ≈ 3.3×10⁻⁴ を達成",
         size=12, color=TEXT_DARK)

# ════════════════════════════════════════════════════
# SLIDE 7: CV 3 ADVANTAGES — fixed text overlap, stacked horizontal layout
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "D E C I S I V E   A D V A N T A G E S", "7")
add_text(s, 0.6, 1.1, 12, 0.6,
         "CV方式の3つの決定的優位性", size=30, bold=True, color=TEXT_DARK)

advs = [
    ("1", "14bit soft-info",
     "全競合方式(超伝導/イオン/中性原子)は binary シンドローム。CV方式は14bitアナログ情報をデコーダに供給。MWPM閾値 1.5% は soft-info によって達成。同一物理エラー率で論理エラー率を桁違いに低減。"),
    ("2", "qumode = 無限次元ヒルベルト空間",
     "ボソニック場理論をネイティブにシミュレーション。格子ゲージ理論、Bose-Hubbard、分子振動 — DV方式では原理的に到達できない計算空間。CVBQP ⊇ BQP が理論的に証明済み (ITCS 2025)。"),
    ("3", "7-in-1 プラットフォーム",
     "同一HWで7つの動作モード。量子優位証明前から6モードで商用価値を提供。競合のどの方式でも実現不可能な多用途性。投資リスクを本質的に低減。"),
]

for i, (num, title, desc) in enumerate(advs):
    y = 1.9 + i * 1.75
    # Number circle
    add_rect(s, 0.6, y, 0.6, 0.6, ACCENT)
    add_text(s, 0.6, y + 0.08, 0.6, 0.5, num, size=22, bold=True,
             color=TEXT_WHITE, align=PP_ALIGN.CENTER)
    # Content card
    add_rect(s, 1.4, y, 11.2, 1.5, CARD_BG)
    add_text(s, 1.6, y + 0.1, 10.8, 0.4, title, size=18, bold=True, color=TEXT_DARK)
    add_text(s, 1.6, y + 0.55, 10.8, 0.85, desc, size=11, color=TEXT_GRAY)

# ════════════════════════════════════════════════════
# SLIDE 8: PRODUCT LINE — 3 columns (unique, keep with fixes)
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "P R O D U C T   L I N E", "8")
add_text(s, 0.6, 1.1, 12, 0.6,
         "単一プラットフォームで 3 製品 — d=3/5/7 スケーリング",
         size=28, bold=True, color=TEXT_DARK)

products = [
    ("Taros Edu", "", "1,350万円", [
        ("重量", "~4.3kg"), ("消費電力", "~104W"),
        ("論理 qubit", "1-10"), ("p_L", "~10⁻² (MWPM)")],
     "教育・QEC研究", "d = 3"),
    ("Taros Pro", "FLAGSHIP", "1,800万円", [
        ("重量", "~7.5kg"), ("消費電力", "~109W"),
        ("論理 qubit", "10-100"), ("p_L", "~10⁻⁴ (MWPM)")],
     "研究・VQE / QAOA", "d = 5"),
    ("Taros Max", "", "2,550万円", [
        ("重量", "~9.7kg"), ("消費電力", "~112W"),
        ("論理 qubit", "10-1,000+"), ("p_L", "~3.3×10⁻⁴ (MWPM)")],
     "FTQC・量子化学", "d = 7"),
]

for i, (name, badge, price, specs, use, d_val) in enumerate(products):
    x = 0.6 + i * 4.05
    border = ACCENT if badge else RGBColor(0xE0, 0xE0, 0xE0)
    add_rect(s, x, 1.9, 3.85, 4.4, BG_WHITE, border)
    add_text(s, x + 0.2, 2.0, 2.5, 0.4, name, size=20, bold=True, color=TEXT_DARK)
    add_text(s, x + 0.2, 2.35, 2.5, 0.25, d_val, size=11, color=ACCENT)
    if badge:
        add_rect(s, x + 2.6, 2.0, 1.05, 0.3, HIGHLIGHT)
        add_text(s, x + 2.6, 2.0, 1.05, 0.3, badge, size=9, bold=True,
                 color=TEXT_WHITE, align=PP_ALIGN.CENTER)
    add_text(s, x + 0.2, 2.7, 3.45, 0.5, price, size=26, bold=True, color=TEXT_DARK)
    for j, (label, val) in enumerate(specs):
        y = 3.3 + j * 0.4
        add_text(s, x + 0.2, y, 1.7, 0.35, label, size=10, color=TEXT_GRAY)
        add_text(s, x + 1.9, y, 1.75, 0.35, val, size=10, color=TEXT_DARK,
                 align=PP_ALIGN.RIGHT)
    add_rect(s, x + 0.2, 5.2, 3.45, 0.01, RGBColor(0xE0, 0xE0, 0xE0))
    add_text(s, x + 0.2, 5.3, 3.45, 0.4, use, size=12, bold=True, color=TEXT_DARK)

add_text(s, 0.6, 6.5, 12, 0.4,
         "単一光学プラットフォーム + PMF遅延線の長さ調整のみで3製品を展開 → 量産設計コスト 1/3",
         size=11, color=TEXT_GRAY, align=PP_ALIGN.CENTER)

# ════════════════════════════════════════════════════
# SLIDE 9: MARKET & COMPETITION — fixed title overlap
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "M A R K E T   &   C O M P E T I T I O N", "9")
add_text(s, 0.6, 1.1, 12, 0.6,
         "「量子コンピュータの Raspberry Pi」— ブルーオーシャン",
         size=26, bold=True, color=TEXT_DARK)

# Competition table
comp_headers = ["製品", "方式", "サイズ", "消費電力", "冷却", "価格"]
comp_data = [
    ["IBM QS Two", "超伝導", "部屋", "200kW+", "15mK", "22.5億円+"],
    ["IonQ Forte", "イオン", "ラック×3", "30kW", "高真空", "4.5億円+"],
    ["Xanadu Aurora", "フォトニック", "ラック多数", "100kW+", "4K", "15億円+"],
    ["Taros Pro", "CV 光子", "7.5kg", "109W", "完全室温", "1,800万円"],
]

for j, h in enumerate(comp_headers):
    x = 0.6 + j * 2.0
    add_rect(s, x, 1.85, 1.95, 0.35, BG_DARK)
    add_text(s, x + 0.08, 1.87, 1.8, 0.3, h, size=9, bold=True, color=TEXT_WHITE)

for ri, row in enumerate(comp_data):
    y = 2.25 + ri * 0.4
    bg = ACCENT if ri == 3 else (CARD_BG if ri % 2 == 0 else BG_WHITE)
    txt = TEXT_WHITE if ri == 3 else TEXT_DARK
    for j, val in enumerate(row):
        x = 0.6 + j * 2.0
        add_rect(s, x, y, 1.95, 0.38, bg)
        add_text(s, x + 0.08, y + 0.02, 1.8, 0.33, val, size=9,
                 bold=(ri == 3), color=txt)

# TAM/SAM/SOM — horizontal bars instead of 3 cards
add_text(s, 0.6, 4.2, 5, 0.35, "市場規模 — TAM / SAM / SOM", size=14, bold=True)

# TAM bar
add_rect(s, 0.6, 4.7, 11.5, 0.6, CARD_BG)
add_text(s, 0.8, 4.72, 1.5, 0.5, "T A M", size=10, bold=True, color=ACCENT)
add_text(s, 2.5, 4.72, 4.5, 0.5, "1,250機関 · 225億円", size=14, bold=True, color=TEXT_DARK)
add_text(s, 7.5, 4.75, 4, 0.5, "量子研究・開発全組織", size=10, color=TEXT_GRAY)

# SAM bar
add_rect(s, 0.6, 5.4, 8.5, 0.6, CARD_BG)
add_text(s, 0.8, 5.42, 1.5, 0.5, "S A M", size=10, bold=True, color=ACCENT)
add_text(s, 2.5, 5.42, 4.5, 0.5, "650機関 · 約117億円", size=14, bold=True, color=TEXT_DARK)
add_text(s, 7.0, 5.45, 2, 0.5, "CV/QEC/教育適合", size=10, color=TEXT_GRAY)

# SOM bar
add_rect(s, 0.6, 6.1, 5.0, 0.6, BG_DARK)
add_text(s, 0.8, 6.12, 1.5, 0.5, "S O M   Y 3", size=10, bold=True, color=ACCENT2)
add_text(s, 2.5, 6.12, 4.5, 0.5, "100機関 · 18億円", size=14, bold=True, color=TEXT_WHITE)

# ════════════════════════════════════════════════════
# SLIDE 10: VALIDATION — changed to 2×2 grid
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "V A L I D A T I O N", "10")
add_text(s, 0.6, 1.1, 12, 0.6,
         "机上の数字ではない — 既に独立検証済み",
         size=28, bold=True, color=TEXT_DARK)

validations = [
    ("100M", "shots", "Stim 量子シミュレーション",
     "p_phys=5×10⁻⁴, d=3/5/7 すべての論理エラー率予測を約1億ショットで再現。"),
    ("9件", "文 献", "公開文献との独立照合",
     "Noh-Chamberland 2022, Stafford-Menicucci 2025 など9件の査読済論文と数値突合。"),
    ("156q", "実 機", "IBM Quantum 実機検証",
     "ibm_fez (156 qubit) 上でデコーダ計算量・サイクル時間を実測。FPGA設計値と整合。"),
    ("確定版", "", "ノイズバジェット (BSモデル)",
     "GAWBS, EO消光比, AWG, PIC統合損失など13項目をBSモデルで個別計上。隠れた損失なし。"),
]

for i, (big, sub, title, desc) in enumerate(validations):
    col = i % 2
    row = i // 2
    x = 0.6 + col * 6.15
    y = 1.9 + row * 2.3
    add_rect(s, x, y, 5.95, 2.1, CARD_BG)
    # Big number on left
    add_text(s, x + 0.2, y + 0.15, 2.0, 0.6, big, size=36, bold=True, color=ACCENT)
    if sub:
        add_text(s, x + 0.2, y + 0.7, 2.0, 0.25, sub, size=10, color=TEXT_GRAY)
    # Content on right
    add_text(s, x + 2.3, y + 0.15, 3.4, 0.4, title, size=14, bold=True, color=TEXT_DARK)
    add_text(s, x + 2.3, y + 0.6, 3.4, 1.3, desc, size=11, color=TEXT_GRAY)

add_text(s, 0.6, 6.5, 12, 0.4,
         "→ 設計書 14本 (システム/ノイズ/GKP/位相ロック/FF/デコーダ/機械/工業デザイン他) 公開 — 完全な技術DD可",
         size=11, color=TEXT_DARK, align=PP_ALIGN.CENTER)

# ════════════════════════════════════════════════════
# SLIDE 11: ROADMAP — timeline with arrow design
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "R O A D M A P", "11")
add_text(s, 0.6, 1.1, 12, 0.6,
         "段階的検証 → プロトタイプ → 量産", size=30, bold=True, color=TEXT_DARK)

# Timeline line
add_rect(s, 0.6, 3.0, 12, 0.04, ACCENT)

phases = [
    ("Phase -1", "12ヶ月", "原理検証", "4.6億円", BG_DARK, TEXT_WHITE),
    ("Phase 0", "12-18ヶ月", "Edu試作 / Break-even", "1.8億円", CARD_BG, TEXT_DARK),
    ("Phase 1", "12-18ヶ月", "Pro 製品化", "1.5億円", CARD_BG, TEXT_DARK),
    ("Phase 2", "6-12ヶ月", "量産 (100台/年)", "0.8億円", CARD_BG, TEXT_DARK),
]

for i, (name, dur, desc, cost, bg, txt) in enumerate(phases):
    x = 0.6 + i * 3.05
    # Circle on timeline
    add_rect(s, x + 1.2, 2.85, 0.35, 0.35, ACCENT)
    # Card above/below alternating
    y_card = 1.8 if i % 2 == 0 else 3.3
    add_rect(s, x, y_card, 2.85, 2.5, bg)
    add_text(s, x + 0.15, y_card + 0.1, 2.55, 0.25, name, size=12, bold=True, color=ACCENT)
    add_text(s, x + 0.15, y_card + 0.35, 2.55, 0.2, dur, size=10,
             color=TEXT_LIGHT if bg == BG_DARK else TEXT_GRAY)
    add_text(s, x + 0.15, y_card + 0.65, 2.55, 0.5, desc, size=14, bold=True, color=txt)
    add_text(s, x + 0.15, y_card + 1.2, 2.55, 0.5, cost, size=22, bold=True,
             color=ACCENT if i == 0 else txt)

# Milestone bar
add_rect(s, 0.6, 6.1, 12, 0.7, CARD_BG)
add_text(s, 0.8, 6.15, 11.6, 0.6,
         "最重要マイルストーン: G-EXP1 (開始後2ヶ月) — 約800万円で Level A 成功確率を 25-35% → 50%超",
         size=13, bold=True, color=TEXT_DARK)

# ════════════════════════════════════════════════════
# SLIDE 12: RISK — split layout (unique, keep)
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "R I S K   A S S E S S M E N T", "12")
add_text(s, 0.6, 1.1, 12, 0.6,
         "リスクは透明に開示。レッドチーム評価を経た保守的見積り",
         size=26, bold=True, color=TEXT_DARK)

risks = [
    ("OPA 13dB パルス未実証",
     "NTT 12.1dB CW は実証済 → SiN clad 改良で 0.9dB ギャップ。Phase -1 で検証。"),
    ("MWPM / Soft-info 製品化",
     "Phase 0/1 は UF 350ns で実証 → Phase 2+ PIC で MWPM 510ns へ移行。製品要件 p_L~3.3×10⁻⁴。"),
    ("G-EXP1 結果未取得",
     "約800万円 / 約2,900万円(完全コスト) で Phase -1 開始後2ヶ月に実施。失敗時は DV-FBQC へフォールバック。"),
]

for i, (title, desc) in enumerate(risks):
    y = 2.0 + i * 1.1
    add_rect(s, 0.6, y, 7.2, 0.95, CARD_BG)
    add_accent_line(s, 0.6, y, 0.06)
    add_text(s, 0.8, y + 0.08, 6.8, 0.3, title, size=12, bold=True, color=TEXT_DARK)
    add_text(s, 0.8, y + 0.4, 6.8, 0.5, desc, size=10, color=TEXT_GRAY)

# Fallback & probability
add_rect(s, 8.2, 2.0, 4.4, 4.3, CARD_BG)
add_text(s, 8.4, 2.1, 4.0, 0.3, "フォールバック完備", size=14, bold=True, color=TEXT_DARK)
add_text(s, 8.4, 2.5, 4.0, 0.3, "何らかのFTQC実現確率", size=10, color=TEXT_GRAY)
add_text(s, 8.4, 2.9, 4.0, 0.7, "81 - 90 %", size=42, bold=True, color=ACCENT)
add_text(s, 8.4, 3.6, 4.0, 0.3, "(Level B+, 開始後約4年)", size=10, color=TEXT_GRAY)

add_text(s, 8.4, 4.1, 4.0, 0.25, "CV pure 81% / CV+QD 90%", size=11, bold=True, color=TEXT_DARK)
add_text(s, 8.4, 4.5, 4.0, 0.8,
         "CV不成立時は DV-FBQC 方式\n(本体28kg / 2.1kW / 約6,480万円)\nにフォールバック — 投資の下振れリスクを限定。",
         size=10, color=TEXT_GRAY)

# ════════════════════════════════════════════════════
# SLIDE 13: CAPITAL EFFICIENCY — stepped gates + competitor (unique, keep with tweaks)
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "C A P I T A L   E F F I C I E N C Y", "13")
add_text(s, 0.6, 1.1, 12, 0.6,
         "段階的に検証、最小資本で世界初へ", size=30, bold=True, color=TEXT_DARK)

gates = [
    ("75万円", "2週間", "原理判定", "GPU Stim シミュレーション"),
    ("800万円", "2ヶ月", "GKP光学実証", "装置直接費"),
    ("2,900万円", "5ヶ月", "完全コスト", "人件費込み"),
    ("4.6億円", "12ヶ月", "QEC Break-even", "世界初の論理エラー抑制"),
]

for i, (cost, dur, title, desc) in enumerate(gates):
    x = 0.6 + i * 3.05
    bg = ACCENT if i == 3 else CARD_BG
    txt = TEXT_WHITE if i == 3 else TEXT_DARK
    add_rect(s, x, 1.9, 2.85, 2.0, bg)
    add_text(s, x + 0.15, 2.0, 2.55, 0.5, cost, size=24, bold=True,
             color=txt, align=PP_ALIGN.CENTER)
    add_text(s, x + 0.15, 2.5, 2.55, 0.25, dur, size=10,
             color=TEXT_LIGHT if i == 3 else TEXT_GRAY, align=PP_ALIGN.CENTER)
    add_text(s, x + 0.15, 2.85, 2.55, 0.35, title, size=14, bold=True,
             color=txt, align=PP_ALIGN.CENTER)
    add_text(s, x + 0.15, 3.25, 2.55, 0.3, desc, size=10,
             color=TEXT_LIGHT if i == 3 else TEXT_GRAY, align=PP_ALIGN.CENTER)
    if i < 3:
        add_text(s, x + 2.7, 2.5, 0.4, 0.4, "▸", size=16, bold=True, color=ACCENT)

# Competitor funding — horizontal bar chart style
add_text(s, 0.6, 4.3, 12, 0.35, "競合の累計調達額 — 桁違いの資本効率",
         size=13, bold=True, color=TEXT_DARK)

comps = [
    ("PsiQuantum", "約1,500億円超", 9.0),
    ("IonQ", "約1,350億円", 8.1),
    ("Xanadu", "約560億円", 3.4),
    ("Taros (計画)", "約8.7億円", 0.4),
]

for i, (name, amount, bar_w) in enumerate(comps):
    y = 4.8 + i * 0.55
    is_taros = i == 3
    bar_color = ACCENT if is_taros else CARD_BG
    add_rect(s, 2.5, y, bar_w, 0.4, bar_color)
    add_text(s, 0.6, y + 0.02, 1.8, 0.35, name, size=11,
             bold=is_taros, color=ACCENT if is_taros else TEXT_DARK)
    # Place amount label just after the bar end
    label_x = 2.5 + bar_w + 0.15
    add_text(s, label_x, y + 0.02, 2.5, 0.35, amount, size=11,
             bold=True, color=ACCENT if is_taros else TEXT_DARK)

# ════════════════════════════════════════════════════
# SLIDE 14: FINANCIAL — fixed overlap, 2-row layout
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "F I N A N C I A L   P R O J E C T I O N", "14")
add_text(s, 0.6, 1.1, 12, 0.6,
         "黒字化から36億円 ARR を視野", size=30, bold=True, color=TEXT_DARK)

# Left: key metrics stacked
metrics = [
    ("黒字化", "Phase 2完了後 1〜2年", "量産30-50台で達成"),
    ("粗利率", "~33%", "規模効果で逓増"),
]
for i, (label, val, desc) in enumerate(metrics):
    y = 1.9 + i * 1.4
    add_rect(s, 0.6, y, 5.8, 1.2, CARD_BG)
    add_accent_line(s, 0.6, y, 5.8)
    add_text(s, 0.8, y + 0.1, 2.0, 0.3, label, size=11, color=TEXT_GRAY)
    add_text(s, 0.8, y + 0.4, 3.5, 0.45, val, size=22, bold=True, color=TEXT_DARK)
    add_text(s, 4.5, y + 0.45, 1.8, 0.35, desc, size=10, color=TEXT_GRAY)

# Right: ARR projections — big numbers
add_rect(s, 6.8, 1.9, 5.8, 2.8, BG_DARK)
add_text(s, 7.0, 2.0, 5.4, 0.3, "A R R   P R O J E C T I O N", size=10, bold=True, color=ACCENT)

add_text(s, 7.0, 2.5, 2.5, 0.3, "Y 3   A R R", size=10, color=TEXT_LIGHT)
add_text(s, 7.0, 2.8, 2.5, 0.6, "18億円", size=32, bold=True, color=TEXT_WHITE)
add_text(s, 7.0, 3.4, 2.5, 0.3, "100台 × 1,800万円", size=10, color=TEXT_LIGHT)

add_text(s, 9.8, 2.5, 2.5, 0.3, "Y 4   A R R", size=10, color=TEXT_LIGHT)
add_text(s, 9.8, 2.8, 2.5, 0.6, "36億円", size=32, bold=True, color=ACCENT)
add_text(s, 9.8, 3.4, 2.5, 0.3, "200台 (SAM 30%超)", size=10, color=TEXT_LIGHT)

# Bottom investment logic bar
add_rect(s, 0.6, 5.0, 12, 0.6, BG_DARK)
add_text(s, 0.8, 5.05, 11.6, 0.5,
         "投資論理: 失敗時上限 4.6億円 (Phase -1)、成功時 ARR 36億円 (Y4) — リスク調整後リターン ~3.5倍",
         size=13, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)

# ════════════════════════════════════════════════════
# SLIDE 15: 2030 MOONSHOT — 2×2 with center hub (unique, keep)
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "2 0 3 0   M O O N S H O T", "15")
add_text(s, 0.6, 1.1, 12, 0.6,
         "Taros が拓く4つの未来産業", size=30, bold=True, color=TEXT_DARK)

# Center diagram
add_rect(s, 4.6, 2.0, 3.6, 0.7, BG_DARK)
add_text(s, 4.6, 2.05, 3.6, 0.6, "Taros 7-in-1", size=18, bold=True,
         color=ACCENT, align=PP_ALIGN.CENTER)

moonshots = [
    (0.6, 2.9, "量子脳 (NeuroQ)",
     "CV量子直接互換フレームワーク\nC.elegans 302ニューロン→ロボット知能\n市場: $20B→$130B (2029)"),
    (6.6, 2.9, "量子ホログラム (QGH)",
     "QFTで干渉パターンN≈10⁶倍高速計算\nGKPフーリエ構造=ホログラム構造\n6G要件: 4.32Tbps"),
    (0.6, 4.9, "量子創薬・不老長寿",
     "プロトントンネリング(DNA変異の量子起源)\nセノリティクス分子の量子設計\nP450精度 71%→94%"),
    (6.6, 4.9, "ロボット知能",
     "CIMで50ms制御壁突破\nスクイーズド光でSQL超え力覚\n量子モジュール供給TAM ~$500M"),
]

for x, y, title, desc in moonshots:
    add_rect(s, x, y, 5.5, 1.7, CARD_BG)
    add_accent_line(s, x, y, 5.5)
    add_text(s, x + 0.15, y + 0.15, 5.2, 0.35, title, size=14, bold=True, color=TEXT_DARK)
    add_text(s, x + 0.15, y + 0.55, 5.2, 1.0, desc, size=10, color=TEXT_GRAY)

# ════════════════════════════════════════════════════
# SLIDE 16: THE ASK — split layout (unique, keep)
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_WHITE)
add_header(s, "T H E   A S K", "16")
add_text(s, 0.6, 1.1, 12, 0.6,
         "Phase -1 シード — 4.6億円 / 12ヶ月", size=30, bold=True, color=TEXT_DARK)

# RAISE box
add_rect(s, 0.6, 2.0, 4.5, 3.5, BG_DARK)
add_text(s, 0.8, 2.1, 4.1, 0.3, "R A I S E", size=10, bold=True, color=ACCENT)
add_text(s, 0.8, 2.5, 4.1, 0.8, "4.6 億円", size=48, bold=True, color=TEXT_WHITE)
add_text(s, 0.8, 3.4, 4.1, 0.7,
         "シード資金で全14タスクを実行し、\nPhase 0 移行判定の全データを取得",
         size=11, color=TEXT_LIGHT)
add_text(s, 0.8, 4.3, 4.1, 0.3, "K E Y   M I L E S T O N E", size=10, bold=True, color=ACCENT)
add_text(s, 0.8, 4.6, 4.1, 0.3, "G-EXP1 (開始後2ヶ月)", size=14, bold=True, color=TEXT_WHITE)
add_text(s, 0.8, 4.9, 4.1, 0.3, "Level A 成功確率 50%超への引き上げ",
         size=10, color=TEXT_LIGHT)

# USE OF FUNDS
add_text(s, 5.5, 2.0, 7, 0.3, "U S E   O F   F U N D S", size=10, bold=True, color=ACCENT)

funds = [
    ("人件費 (11名 × 12ヶ月)",
     "理論2 + 光源2 + CV計算2 + PIC1 + 冷却2 + 制御SW2",
     "約 2.9 億円"),
    ("光学実験装置・部品",
     "PPLN OPA, EOM, AWG, ホモダイン検出系, 位相ロック",
     "約 9,200万円"),
    ("GPU 計算 / 外部委託 / 施設",
     "Stim シミュレーション, GKP実験委託, クリーンブース",
     "約 8,300万円"),
]

for i, (title, desc, amount) in enumerate(funds):
    y = 2.5 + i * 1.2
    add_accent_line(s, 5.5, y, 0.06)
    add_text(s, 5.7, y + 0.05, 4.5, 0.3, title, size=13, bold=True, color=TEXT_DARK)
    add_text(s, 5.7, y + 0.35, 4.5, 0.4, desc, size=10, color=TEXT_GRAY)
    add_text(s, 10.5, y + 0.05, 2.0, 0.35, amount, size=16, bold=True,
             color=TEXT_DARK, align=PP_ALIGN.RIGHT)

# ════════════════════════════════════════════════════
# SLIDE 17: CLOSING
# ════════════════════════════════════════════════════
s = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(s, BG_DARK)
add_text(s, 0.8, 1.5, 11, 0.5,
         "T H E   F U T U R E   O F   Q U A N T U M   I S",
         size=14, bold=True, color=ACCENT)
add_text(s, 0.8, 2.2, 11, 2.0,
         "デスクトップに来る。", size=72, bold=True, color=TEXT_WHITE)
add_text(s, 0.8, 4.2, 11, 0.8,
         "室温 109W で動く誤り訂正型量子コンピュータを、世界の研究室・教室・企業 R&D に。\n"
         "購入初日から7つのモードで価値を届ける。",
         size=14, color=TEXT_LIGHT)
add_accent_line(s, 0.8, 5.2, 0.8)
add_text(s, 0.8, 5.4, 11, 0.3, "次 の ス テ ッ プ", size=10, bold=True, color=ACCENT)
add_text(s, 0.8, 5.7, 11, 0.5,
         "技術 DD パッケージ (設計書14本) のレビュー  →  タームシート協議  →  Phase -1 着手",
         size=14, color=TEXT_WHITE)
add_text(s, 0.8, 6.8, 8, 0.3,
         "T A R O S  ·  D e s k t o p   P h o t o n i c   Q u a n t u m   C o m p u t e r  ·  v 4 . 1",
         size=10, color=TEXT_LIGHT)

# ── SAVE ──
out_path = "/Users/tanitomohiro/Downloads/Taros/assets/TAROS_Investor_Pitch_Revised.pptx"
prs.save(out_path)
print(f"Saved: {out_path}")
print(f"Slides: {len(prs.slides)}")
