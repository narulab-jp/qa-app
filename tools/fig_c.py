# -*- coding: utf-8 -*-
"""冊C（複数資料比較）の資料。

  1セットにつき資料2〜3点。文章資料・統計表もSVGで作り、
  アプリと紙で同じものを見られるようにしてある。
  国・地域・数値はすべて架空で、図の中にその旨を書いている。
"""
import math

import fig_a
import fig_b
from figlib import (NOTE_FAKE, NOTE_MAP, circle, line, n, poly, rect, svg, txt,
                    sym_factory, sym_ta, sym_hatake, sym_kaju, sym_shinyou,
                    sym_torii, sym_school)

WRAP = 34          # 文章資料の1行の字数


def wrap(s, k=WRAP):
    out, cur = [], ""
    for ch in s:
        cur += ch
        if len(cur) >= k and ch in "。、）":
            out.append(cur)
            cur = ""
        elif len(cur) >= k + 4:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def textpanel(title, paras, note=NOTE_FAKE, w=720):
    lines = []
    for p in paras:
        lines.extend(wrap(p))
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    h = int(64 + len(lines) * 26 + 34)
    body = [txt(20, 28, title, 16, "start", "bold"), rect(20, 44, w - 40, h - 78, "none", 1)]
    for i, ln in enumerate(lines):
        body.append(txt(38, 74 + i * 26, ln, 14))
    body.append(txt(20, h - 12, note, 11))
    return svg(w, h, "\n".join(body), title)


def table(title, headers, rows, widths, note=NOTE_FAKE, w=720):
    rh = 42.0
    h = int(46 + rh * (len(rows) + 1) + 40)
    cols = [20.0]
    for wd in widths:
        cols.append(cols[-1] + wd)
    body = [txt(20, 28, title, 16, "start", "bold")]
    top = 46.0
    body.append(rect(cols[0], top, cols[-1] - cols[0], rh, "none", 1.4))
    for i, hd in enumerate(headers):
        parts = hd.split("\n")
        for j, p in enumerate(parts):
            y = top + rh / 2 + (j - (len(parts) - 1) / 2.0) * 15 + 5
            body.append(txt((cols[i] + cols[i + 1]) / 2, y, p, 12, "middle", "bold"))
    for k, row in enumerate(rows):
        ry = top + rh + k * rh
        body.append(rect(cols[0], ry, cols[-1] - cols[0], rh, "none", 1))
        for i, v in enumerate(row):
            if i == len(row) - 1 and len(str(v)) > 12:
                body.append(txt(cols[i] + 12, ry + rh / 2 + 5, v, 12))
            else:
                body.append(txt((cols[i] + cols[i + 1]) / 2, ry + rh / 2 + 5, v, 13,
                                "middle", "bold" if i == 0 else "normal"))
    for c in cols[1:-1]:
        body.append(line(c, top, c, top + rh * (len(rows) + 1), 1))
    body.append(txt(20, h - 14, note, 11))
    return svg(w, h, "\n".join(body), title)


# ======================================================================
# 架空大陸（いくつかの資料で共通に使う）
# ======================================================================
ARC = [(120, 70), (300, 50), (470, 80), (560, 150), (600, 260), (560, 360),
       (450, 430), (300, 460), (180, 420), (110, 330), (90, 200)]
ARC_POINTS = {
    "ア": (200, 130), "イ": (350, 120), "ウ": (500, 170),
    "エ": (200, 260), "オ": (350, 260), "カ": (500, 290),
    "キ": (230, 380), "ク": (380, 390),
}


def arc_base(body, title, note=NOTE_FAKE, W=720, H=560):
    body.insert(0, txt(20, 28, title, 16, "start", "bold"))
    body.insert(1, '<polygon points="%s" fill="#fff" stroke="#000" stroke-width="1.8"/>'
                % " ".join("%s,%s" % (n(p[0]), n(p[1])) for p in ARC))
    body.append(txt(20, H - 12, note, 11))
    return svg(W, H, "\n".join(body), title)


def map_plate():
    """プレート境界の模式図"""
    b = []
    bnd = [(120, 70), (210, 160), (300, 250), (360, 350), (420, 430)]
    b.append(poly(bnd, 3.2))
    for i in range(len(bnd) - 1):
        mx = ((bnd[i][0] + bnd[i + 1][0]) / 2, (bnd[i][1] + bnd[i + 1][1]) / 2)
        b.append(poly([(mx[0] + 10, mx[1] - 10), (mx[0] + 24, mx[1] + 2),
                       (mx[0] + 10, mx[1] + 14)], 1.4, fill="#000", close=True))
    b.append(poly([(560, 150), (580, 250), (560, 360)], 3.2, "10 6"))
    for (x, y) in [(250, 120), (300, 200), (350, 290), (400, 380)]:
        b.append(poly([(x, y - 9), (x + 8, y + 6), (x - 8, y + 6)], 1.4,
                      fill="#000", close=True))
    for (x, y) in [(300, 140), (340, 230), (390, 320), (200, 200), (250, 300)]:
        b.append(circle(x, y, 4.2, "#fff", 1.6))
    b.append(txt(150, 100, "境界P", 13, "start", "bold"))
    b.append(txt(575, 260, "境界Q", 13, "start", "bold"))
    ly = 470.0
    b.append(rect(60, ly, 600, 62, "none", 1))
    b.append(txt(72, ly + 20, "凡例", 12, "start", "bold"))
    b.append(line(80, ly + 40, 112, ly + 40, 3.2))
    b.append(txt(120, ly + 44, "境界P", 11))
    b.append(line(200, ly + 40, 232, ly + 40, 3.2, "10 6"))
    b.append(txt(240, ly + 44, "境界Q", 11))
    b.append(poly([(330, ly + 32), (338, ly + 46), (322, ly + 46)], 1.4,
                  fill="#000", close=True))
    b.append(txt(346, ly + 44, "火山", 11))
    b.append(circle(430, ly + 40, 4.2, "#fff", 1.6))
    b.append(txt(442, ly + 44, "地震の多い場所", 11))
    return arc_base(b, "架空大陸のプレート境界と火山・地震", NOTE_MAP)


def map_marks(title, groups, note=NOTE_FAKE):
    """架空大陸に記号を配る主題図"""
    b = []
    for (label, shape, pts) in groups:
        for (x, y) in pts:
            if shape == "circle":
                b.append(circle(x, y, 6, "#fff", 1.6))
            elif shape == "fill":
                b.append(circle(x, y, 6, "#000", 1.2))
            elif shape == "square":
                b.append(rect(x - 5.5, y - 5.5, 11, 11, "#fff", 1.6))
            elif shape == "tri":
                b.append(poly([(x, y - 7), (x + 6, y + 5), (x - 6, y + 5)], 1.5,
                              fill="#fff", close=True))
            else:
                b.append(poly([(x, y - 7), (x + 7, y), (x, y + 7), (x - 7, y)], 1.5,
                              fill="hatch:diag", close=True))
    for (nm, (x, y)) in sorted(ARC_POINTS.items()):
        b.append(rect(x - 30, y - 12, 24, 20, "#fff", 0))
        b.append(txt(x - 18, y + 4, nm, 14, "middle", "bold"))
    ly = 470.0
    b.append(rect(60, ly, 600, 62, "none", 1))
    b.append(txt(72, ly + 20, "凡例", 12, "start", "bold"))
    for k, (label, shape, _) in enumerate(groups):
        cx = 84.0 + k * 150.0
        if shape == "circle":
            b.append(circle(cx, ly + 40, 6, "#fff", 1.6))
        elif shape == "fill":
            b.append(circle(cx, ly + 40, 6, "#000", 1.2))
        elif shape == "square":
            b.append(rect(cx - 5.5, ly + 34.5, 11, 11, "#fff", 1.6))
        elif shape == "tri":
            b.append(poly([(cx, ly + 33), (cx + 6, ly + 45), (cx - 6, ly + 45)], 1.5,
                          fill="#fff", close=True))
        else:
            b.append(poly([(cx, ly + 33), (cx + 7, ly + 40), (cx, ly + 47),
                           (cx - 7, ly + 40)], 1.5, fill="hatch:diag", close=True))
        b.append(txt(cx + 14, ly + 44, label, 11))
    return arc_base(b, title, note)


def map_climate():
    """架空大陸の気候区（緯度帯で帯状に）"""
    b = []
    bands = [(50, 110, "hatch:dot", "寒帯・亜寒帯"),
             (110, 190, "hatch:diag", "温帯"),
             (190, 250, "#fff", "乾燥帯"),
             (250, 330, "hatch:grid", "サバナ"),
             (330, 470, "hatch:diagfine", "熱帯雨林")]
    for (y0, y1, fill, lab) in bands:
        band = [(p[0], min(max(p[1], y0), y1)) for p in ARC]
        band = [(x, y) for (x, y) in band]
        b.append('<defs><clipPath id="cl%d"><polygon points="%s"/></clipPath></defs>'
                 % (int(y0), " ".join("%s,%s" % (n(p[0]), n(p[1])) for p in ARC)))
        b.append('<g clip-path="url(#cl%d)">%s</g>'
                 % (int(y0), rect(0, y0, 720, y1 - y0, fill, 0)))
        b.append(line(90, y1, 610, y1, 0.8, "5 4"))
    for (nm, (x, y)) in sorted(ARC_POINTS.items()):
        b.append(rect(x - 32, y - 12, 26, 20, "#fff", 0))
        b.append(txt(x - 19, y + 4, nm, 14, "middle", "bold"))
    ly = 470.0
    b.append(rect(60, ly, 600, 62, "none", 1))
    b.append(txt(72, ly + 20, "凡例", 12, "start", "bold"))
    for k, (y0, y1, fill, lab) in enumerate(bands):
        cx = 76.0 + k * 118.0
        b.append(rect(cx, ly + 32, 22, 16, fill, 1.0))
        b.append(txt(cx + 26, ly + 45, lab, 10.5))
    return arc_base(b, "架空大陸の気候区の分布", NOTE_MAP)


def city_rings():
    """都市圏の模式図（同心円）"""
    W, H = 720, 560
    b = [txt(20, 28, "架空の都市Fの模式図（中心からの帯）", 16, "start", "bold")]
    cx, cy = 340.0, 250.0
    rings = [(60, "都心（官庁・大企業の本社）"), (120, "都心周辺（問屋・工場跡）"),
             (190, "住宅地"), (250, "新しい住宅地・郊外")]
    fills = ["#000", "hatch:diag", "hatch:dotfine", "#fff"]
    for k in range(len(rings) - 1, -1, -1):
        b.append(circle(cx, cy, rings[k][0], fills[k], 1.4))
    for (nm, r, ang) in [("ア", 30, -60), ("イ", 90, 20), ("ウ", 155, -30),
                         ("エ", 220, 40)]:
        x = cx + r * math.cos(math.radians(ang))
        y = cy + r * math.sin(math.radians(ang))
        b.append(circle(x, y, 11, "#fff", 1.6))
        b.append(txt(x, y + 5, nm, 13, "middle", "bold"))
    ly = 470.0
    b.append(rect(60, ly, 600, 62, "none", 1))
    b.append(txt(72, ly + 20, "凡例", 12, "start", "bold"))
    for k, (r, lab) in enumerate(rings):
        cxx = 76.0 + k * 152.0
        b.append(rect(cxx, ly + 32, 20, 16, fills[k], 1.0))
        b.append(txt(cxx + 24, ly + 45, lab, 9.5))
    b.append(txt(20, H - 12, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(b), "都市圏の模式図")


def factory_map():
    """工場の立地の模式図"""
    W, H = 720, 520
    b = [txt(20, 28, "架空の国Gの工業の分布", 16, "start", "bold")]
    b.append('<polygon points="80,80 620,80 620,420 80,420" fill="#fff" '
             'stroke="#000" stroke-width="1.6"/>')
    b.append(poly([(80, 300), (200, 290), (340, 300), (480, 296), (620, 306),
                   (620, 420), (80, 420)], 1.4, fill="hatch:wave", close=True))
    b.append(txt(600, 400, "海", 14, "end"))
    for (x, y) in [(140, 270), (230, 268), (320, 272), (410, 270), (500, 274),
                   (570, 276)]:
        b.append(sym_factory(x, y))
    for (x, y) in [(180, 140), (300, 150), (440, 130)]:
        b.append(circle(x, y, 5, "#000", 1.0))
    for (x, y) in [(120, 180), (260, 200), (520, 180)]:
        b.append(poly([(x, y - 7), (x + 7, y + 5), (x - 7, y + 5)], 1.5,
                      fill="hatch:diag", close=True))
    for (nm, x, y) in [("ア", 230, 240), ("イ", 300, 175), ("ウ", 520, 240),
                       ("エ", 130, 150)]:
        b.append(circle(x, y, 11, "#fff", 1.6))
        b.append(txt(x, y + 5, nm, 13, "middle", "bold"))
    ly = 436.0
    b.append(rect(60, ly, 600, 58, "none", 1))
    b.append(txt(72, ly + 18, "凡例", 12, "start", "bold"))
    b.append(sym_factory(84, ly + 40))
    b.append(txt(98, ly + 44, "臨海部の工場", 11))
    b.append(circle(250, ly + 40, 5, "#000", 1.0))
    b.append(txt(262, ly + 44, "炭田", 11))
    b.append(poly([(430, ly + 33), (437, ly + 45), (423, ly + 45)], 1.5,
                  fill="hatch:diag", close=True))
    b.append(txt(444, ly + 44, "鉄鉱石の産地", 11))
    b.append(txt(20, H - 12, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(b), "工業の分布")


def island_map():
    """架空の島国の模式地形図（簡略）"""
    W, H = 720, 520
    b = [txt(20, 28, "架空の島国Hの地形と土地利用", 16, "start", "bold")]
    b.append(rect(40, 46, 640, 380, "hatch:wave", 0))
    isl = [(150, 150), (300, 100), (470, 130), (560, 220), (520, 340),
           (360, 390), (210, 350), (140, 250)]
    b.append('<polygon points="%s" fill="#fff" stroke="#000" stroke-width="1.8"/>'
             % " ".join("%s,%s" % (n(p[0]), n(p[1])) for p in isl))
    for r, fill in ((110, "hatch:dotfine"), (70, "hatch:diag")):
        b.append(circle(350, 240, r, fill, 1.2))
    b.append(txt(350, 245, "山地", 13, "middle", "bold"))
    for (x, y) in [(200, 300), (250, 330), (300, 350), (420, 340), (470, 300)]:
        b.append(sym_ta(x, y))
    for (x, y) in [(200, 200), (240, 170), (450, 180), (490, 220)]:
        b.append(sym_kaju(x, y))
    for (nm, x, y) in [("ア", 190, 260), ("イ", 350, 150), ("ウ", 470, 250),
                       ("エ", 300, 320)]:
        b.append(circle(x, y, 11, "#fff", 1.6))
        b.append(txt(x, y + 5, nm, 13, "middle", "bold"))
    ly = 436.0
    b.append(rect(60, ly, 600, 58, "none", 1))
    b.append(txt(72, ly + 18, "凡例", 12, "start", "bold"))
    b.append(rect(84, ly + 32, 22, 14, "hatch:diag", 1.0))
    b.append(txt(112, ly + 44, "標高500m以上", 11))
    b.append(rect(250, ly + 32, 22, 14, "hatch:dotfine", 1.0))
    b.append(txt(278, ly + 44, "標高100〜500m", 11))
    b.append(sym_ta(430, ly + 40))
    b.append(txt(442, ly + 44, "田", 11))
    b.append(sym_kaju(500, ly + 40))
    b.append(txt(512, ly + 44, "果樹園", 11))
    b.append(txt(20, H - 12, NOTE_MAP, 11))
    return svg(W, H, "\n".join(b), "島国の地形")


def inland_map():
    """架空の内陸国とまわりの国"""
    W, H = 720, 520
    b = [txt(20, 28, "架空の内陸国Jとまわりの国", 16, "start", "bold")]
    b.append('<polygon points="60,60 660,60 660,440 60,440" fill="#fff" '
             'stroke="#000" stroke-width="1.2"/>')
    b.append(poly([(60, 60), (220, 60), (240, 200), (200, 340), (60, 360)],
                   1.4, fill="hatch:dotfine", close=True))
    b.append(txt(130, 210, "K国", 15, "middle", "bold"))
    b.append('<polygon points="220,60 470,60 480,210 240,200" fill="#fff" '
             'stroke="#000" stroke-width="1.4"/>')
    b.append(txt(350, 140, "L国", 15, "middle", "bold"))
    b.append(poly([(240, 200), (480, 210), (470, 380), (200, 340)],
                   2.2, fill="hatch:diag", close=True))
    b.append(txt(340, 300, "J国", 17, "middle", "bold"))
    b.append('<polygon points="470,60 660,60 660,440 470,380 480,210" fill="#fff" '
             'stroke="#000" stroke-width="1.4"/>')
    b.append(txt(570, 240, "M国", 15, "middle", "bold"))
    b.append(poly([(200, 340), (470, 380), (660, 440), (60, 440), (60, 360)],
                   1.4, fill="hatch:wave", close=True))
    b.append(txt(120, 415, "海", 14))
    b.append(txt(60, 470, "※ J国は海に面していない。", 12))
    b.append(txt(20, H - 12, NOTE_MAP, 11))
    return svg(W, H, "\n".join(b), "内陸国の位置")


def river_basin():
    """河川の流域の模式図"""
    W, H = 720, 480
    b = [txt(20, 28, "架空の河川Nの流域の模式図", 16, "start", "bold")]
    b.append('<polygon points="80,60 640,60 640,400 80,400" fill="#fff" '
             'stroke="#000" stroke-width="1.2"/>')
    b.append(poly([(100, 80), (340, 70), (420, 150), (380, 260), (240, 300),
                   (120, 240)], 1.4, fill="hatch:dotfine", close=True))
    b.append(txt(240, 170, "山地", 14, "middle", "bold"))
    b.append(poly([(200, 180), (280, 250), (360, 300), (450, 330), (560, 350),
                   (640, 356)], 3.0))
    b.append(poly([(150, 130), (230, 210), (280, 250)], 2.0))
    b.append(poly([(360, 120), (350, 220), (360, 300)], 2.0))
    for (nm, x, y) in [("ア", 240, 230), ("イ", 420, 320), ("ウ", 580, 348)]:
        b.append(circle(x, y, 12, "#fff", 1.6))
        b.append(txt(x, y + 5, nm, 13, "middle", "bold"))
    b.append(txt(470, 250, "平野", 14, "middle", "bold"))
    b.append(txt(80, 430, "※ ア・イ・ウは河川Nの上流・中流・下流の観測地点。", 12))
    b.append(txt(20, H - 12, NOTE_MAP, 11))
    return svg(W, H, "\n".join(b), "流域の模式図")


def coast_profile():
    """海岸の断面の模式図"""
    W, H = 720, 420
    b = [txt(20, 28, "架空の海岸Pの断面の模式図（左が内陸・右が海）", 16, "start", "bold")]
    b.append(poly([(60, 300), (180, 300), (200, 220), (330, 220), (350, 150),
                   (520, 150), (540, 90), (660, 90)], 2.4))
    b.append(poly([(60, 300), (180, 300), (180, 360), (60, 360)], 1.0,
                   fill="hatch:wave", close=True))
    b.append(txt(120, 335, "海", 13, "middle"))
    for (nm, x, y) in [("ア", 250, 210), ("イ", 430, 140), ("ウ", 600, 80),
                       ("エ", 190, 260)]:
        b.append(circle(x, y - 16, 11, "#fff", 1.6))
        b.append(txt(x, y - 11, nm, 13, "middle", "bold"))
    b.append(txt(60, 380, "※ 平らな面と急な崖が交互に並ぶ。", 12))
    b.append(txt(20, H - 12, NOTE_MAP, 11))
    return svg(W, H, "\n".join(b), "海岸の断面")


# ======================================================================
# 各セットの資料
# ======================================================================
FIGURES = {
    # --- 資源・産業（C01 は Phase 1 から続けて使う） ---
    "C01_energy.svg": lambda: fig_b.stackbars(
        fig_b.BAR_ENERGY, "資料1　架空の4か国の発電電力量の内訳（％）",
        "※ 訓練用に作成した架空の国と数値であり、実在の国ではない。"),
    "C01_table.svg": lambda: table(
        "資料2　架空の4か国の一人当たりGNIと国土のようす",
        ["国", "一人当たりGNI\n（ドル）", "就業者に占める\n第一次産業の割合(%)",
         "国土や資源のようす"],
        [["A国", "78,000", "2", "起伏が大きく、年降水量が多い"],
         ["B国", "42,000", "3", "石炭・石油・天然ガスにとぼしい"],
         ["C国", "25,000", "2", "国土の大半が砂漠。原油の輸出が経済の中心"],
         ["D国", "2,400", "38", "石炭を産出する。人口の多くが農村部に住む"]],
        [70, 145, 150, 315],
        "※ 訓練用に作成した架空の国と数値であり、実在の国ではない。"),

    # --- 自然環境（地形図・雨温図・階級区分図は冊A・冊Bの図をそのまま使う） ---
    "C_climate.svg": map_climate,
    "CN1_table.svg": lambda: table(
        "資料2　地形図中の3地区の土地利用（％）",
        ["地区", "田", "畑・果樹園", "宅地", "その他"],
        [["扇状地の中央", "4", "68", "18", "10"],
         ["扇状地の末端", "46", "24", "20", "10"],
         ["東の平野", "72", "8", "12", "8"]],
        [150, 100, 150, 100, 180]),
    "CN3_plate.svg": map_plate,
    "CN3_table.svg": lambda: table(
        "資料2　架空大陸の4地点で観測された地震と火山",
        ["地点", "過去100年の\n大地震の回数", "活火山の数", "地形のようす"],
        [["ア", "18", "9", "高く険しい山脈が連なる"],
         ["イ", "2", "0", "なだらかな平原が広がる"],
         ["エ", "1", "0", "古い岩石からなる低い山地"],
         ["カ", "14", "6", "海溝に沿って弧状の列島が並ぶ"]],
        [90, 165, 130, 315], NOTE_MAP),
    "CN4_text.svg": lambda: textpanel(
        "資料2　この地域の水害についての記録",
        ["この地域では、記録に残る大きな水害が過去に3回起きている。"
         "いずれも上流での大雨により堤防をこえた水が流れこんだもので、"
         "浸水が長く続いたのは、川からはなれた低い土地であった。",
         "川ぞいのやや高い帯状の土地は、古くから集落と畑に使われてきた。"
         "その外側の低い土地は水がたまりやすく、水田として使われている。"
         "近年、低い土地の一部に住宅地がつくられた。"],
        NOTE_MAP),
    "CN5_line.svg": lambda: fig_b.linechart(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        [("ア（上流）", [30, 28, 42, 60, 72, 88, 96, 78, 66, 48, 38, 32]),
         ("ウ（下流）", [120, 116, 168, 240, 288, 352, 384, 312, 264, 192, 152, 128])],
        "資料1　河川Nの月ごとの流量", "流量（m³/秒）", NOTE_FAKE, 400.0),
    "CN5_basin.svg": river_basin,
    "CN6_prof.svg": coast_profile,

    # --- 資源・産業 ---
    "CR2_table.svg": lambda: table(
        "資料2　架空の4か国のようす",
        ["国", "一人当たりGNI\n（ドル）", "自国で産出する\nおもな資源", "電力のようす"],
        [["カ国", "9,800", "石炭", "石炭火力が中心。大気汚染が問題"],
         ["キ国", "34,000", "天然ガス", "天然ガスの輸出が経済をささえる"],
         ["ク国", "46,000", "ほとんどない", "原油と天然ガスを輸入している"],
         ["ケ国", "58,000", "水力・地熱", "再生可能エネルギーの割合が高い"]],
        [70, 145, 150, 315]),
    "CR3_scatter.svg": lambda: fig_b.scatter(
        [("ア", 82, 12), ("イ", 68, 96), ("ウ", 24, 240), ("エ", 12, 44),
         ("オ", 45, 160), ("カ", 8, 18)],
        "資料1　架空の6か国の農業（土地生産性と労働生産性）",
        "土地生産性（農地1haあたりの生産額・万円）",
        "労働生産性（農民1人あたりの生産額・万円）", NOTE_FAKE, 100.0, 260.0),
    "CR3_text.svg": lambda: textpanel(
        "資料2　架空の6か国の農業のようす",
        ["ア国は国土がせまく人口が多い。小さな農地に人手と肥料をかけて"
         "収量を高めている。",
         "ウ国は広い農地を少ない人数で耕し、大型の機械を使う。"
         "農地1haあたりの収量は高くない。",
         "カ国は農地が乾燥しており、家畜を移動させながら飼う牧畜が中心である。"]),
    "CR4_map.svg": factory_map,
    "CR4_bars.svg": lambda: fig_b.stackbars(
        fig_b.BAR_EXPORT, "資料2　架空の4か国の輸出品目の内訳（％）", NOTE_FAKE),
    "CR5_line.svg": lambda: fig_b.linechart(
        [1970, 1985, 2000, 2015, 2025],
        [("ア", [79, 66, 52, 42, 38]), ("イ", [95, 98, 102, 105, 104]),
         ("ウ", [45, 48, 52, 56, 58])],
        "資料1　架空の3か国の食料自給率の移り変わり", "食料自給率（％）",
        NOTE_FAKE, 120.0),
    "CR5_table.svg": lambda: table(
        "資料2　架空の3か国のようす（2025年）",
        ["国", "農地面積\n（万ha）", "人口\n（百万人）", "食生活の変化"],
        [["ア国", "440", "126", "米の消費が減り、肉と小麦の消費が増えた"],
         ["イ国", "3,800", "68", "変化は小さい。穀物を多く輸出している"],
         ["ウ国", "1,700", "84", "肉の消費が増えたが、飼料は自給している"]],
        [70, 130, 120, 360]),
    "CR6_map.svg": lambda: map_marks(
        "資料1　架空大陸のおもな鉱産資源の分布",
        [("鉄鉱石", "tri", [(220, 140), (340, 120), (460, 160)]),
         ("石炭", "fill", [(250, 260), (370, 250), (480, 260)]),
         ("原油", "square", [(450, 370), (500, 320), (520, 360)]),
         ("銅", "diamond", [(200, 330), (245, 395)])], NOTE_MAP),
    "CR6_bars.svg": lambda: fig_b.stackbars(
        [("ア", [("鉄鉱石", 54), ("石炭", 26), ("原油", 4), ("その他", 16)]),
         ("イ", [("鉄鉱石", 8), ("石炭", 62), ("原油", 6), ("その他", 24)]),
         ("ウ", [("鉄鉱石", 4), ("石炭", 6), ("原油", 78), ("その他", 12)]),
         ("エ", [("鉄鉱石", 12), ("石炭", 10), ("原油", 8), ("その他", 70)])],
        "資料2　架空の4か国の鉱産物の産出額の内訳（％）", NOTE_FAKE),

    # --- 人口・都市・生活文化 ---
    "CP1_pyr.svg": lambda: fig_b.pyramids(
        [fig_b.PYR[0], fig_b.PYR[2]], "資料1　架空の2か国の人口ピラミッド"),
    "CP1_line.svg": lambda: fig_b.linechart(
        [1960, 1980, 2000, 2020, 2040],
        [("A国", [22, 38, 62, 96, 132]), ("C国", [88, 104, 118, 124, 118])],
        "資料2　架空の2か国の人口の移り変わり（2040年は推計）",
        "人口（百万人）", NOTE_FAKE, 140.0),
    "CP2_rings.svg": city_rings,
    "CP3_map.svg": lambda: map_marks(
        "資料1　架空大陸のおもな宗教の分布",
        [("宗教W", "circle", [(200, 130), (250, 170), (180, 210)]),
         ("宗教X", "fill", [(350, 120), (390, 170), (330, 210)]),
         ("宗教Y", "square", [(500, 170), (520, 240), (470, 280)]),
         ("宗教Z", "tri", [(230, 380), (330, 400), (400, 360)])], NOTE_MAP),
    "CP3_text.svg": lambda: textpanel(
        "資料2　架空大陸の宗教のようす",
        ["宗教Wは、豚肉を食べず、1日に数回、決まった方角に向かって祈る。"
         "断食の月がある。",
         "宗教Xは、牛を神聖なものとして牛肉を食べない。"
         "生まれによる身分の区別が長く残ってきた。",
         "宗教Yは、日曜日に礼拝を行い、大きな教会が町の中心にある。"]),
    "CP4_table.svg": lambda: table(
        "資料2　架空の地域の区ごとのようす",
        ["区", "面積\n（km²）", "人口\n（千人）", "15歳未満\n（％）",
         "65歳以上\n（％）"],
        [["ア", "120", "342", "9", "31"],
         ["オ", "150", "900", "16", "14"],
         ["ケ", "440", "132", "8", "42"],
         ["ウ", "380", "190", "11", "28"]],
        [70, 130, 130, 130, 220]),

    # --- 地誌 ---
    "CG1_text.svg": lambda: textpanel(
        "資料2　架空大陸の4地点のようす",
        ["ア　一年を通じて気温が低く、針葉樹の林が広がる。"
         "冬は地面が凍り、農業はほとんど行われない。",
         "ウ　一年中雨が少なく、川の水にたよったかんがい農業と、"
         "らくだを使った移動がみられる。",
         "カ　雨季と乾季がはっきりしており、丈の高い草原に樹木が点在する。",
         "ク　一年中高温で雨が多く、背の高い常緑の森林におおわれている。"],
        NOTE_MAP),
    "CG2_table.svg": lambda: table(
        "資料1　架空の4か国のようす",
        ["国", "一人当たりGNI\n（ドル）", "人口\n（百万人）", "おもな輸出品"],
        [["ア国", "1,200", "62", "コーヒー豆・切り花"],
         ["イ国", "6,800", "48", "鉄鉱石・大豆"],
         ["ウ国", "38,000", "12", "機械類・医薬品"],
         ["エ国", "24,000", "34", "原油・石油製品"]],
        [70, 145, 130, 335]),
    "CG3_map.svg": island_map,
    "CG3_bars.svg": lambda: fig_b.stackbars(
        [("ア", [("農業", 42), ("工業", 18), ("観光", 26), ("その他", 14)]),
         ("イ", [("農業", 8), ("工業", 12), ("観光", 62), ("その他", 18)]),
         ("ウ", [("農業", 14), ("工業", 46), ("観光", 22), ("その他", 18)]),
         ("エ", [("農業", 56), ("工業", 10), ("観光", 16), ("その他", 18)])],
        "資料2　島国Hの4地区の産業別生産額の内訳（％）", NOTE_FAKE),
    "CG4_map.svg": inland_map,
    # 事実だけを並べる。「〜だから〜である」という判断は書かない。
    # 判断を書くと、資料を読むだけで答えが決まってしまい、読図にならない。
    "CG4_text.svg": lambda: textpanel(
        "資料2　内陸国Jとまわりの国のようす",
        ["J国から港までの鉄道は、M国を通っている。"
         "K国には舗装された道路がなく、L国との間には標高3,000mを"
         "超える山脈がある。",
         "J国の輸出額の内訳は、銅71％、コバルト12％、木材7％、"
         "その他10％である。",
         "銅の国際価格の指数（2016年＝100）は、"
         "2016年62、2018年88、2020年71、2022年104、2024年58。"]),
}
