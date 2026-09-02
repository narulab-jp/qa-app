# -*- coding: utf-8 -*-
"""冊A（地形図読図）の図版。

  地形はすべて下の height 関数（標高の式）から等高線を計算で起こしている。
  目分量で線を引いていないので、図と正解が必ず一致する。
  実在の地域ではなく、訓練用の模式地形図である。
"""
import math

from figlib import (NOTE_MAP, circle, esc, gauss, join, line, marching, mark, n,
                    poly, rect, smax, svg, sym_arechi, sym_city, sym_factory,
                    sym_hatake, sym_hosp, sym_hs, sym_kaju, sym_koban,
                    sym_kouyou, sym_kuwa, sym_post, sym_roujin, sym_sankaku,
                    sym_school, sym_shinyou, sym_suijun, sym_ta, sym_tera,
                    sym_torii, sym_hakubutsu, txt, SYMBOLS)

W, H = 720, 620
MX0, MX1, MY0, MY1 = 40.0, 620.0, 30.0, 450.0
U1000 = 145.0          # 1000m にあたる図上の長さ（2万5千分の1で4cm）


def sigm(v, edge, w):
    """段丘崖のような急な段差。w が小さいほど崖が急になる。"""
    return 1.0 / (1.0 + math.exp(-(v - edge) / w))


# ======================================================================
def draw_map(hfun, levels, thick, rivers=(), sea=None, landuse=(), builds=(),
             marks=(), seclines=(), legend=(), extra="", note=NOTE_MAP,
             label="訓練用の模式地形図", scale=True, spots=()):
    """地形図を1枚描く。等高線は hfun から計算する。"""
    body = ['<g clip-path="url(#frame)">']
    if sea:
        body.append(poly(sea, 1.4, fill="hatch:wave", close=True))
    labels = []
    for lv in levels:
        lines = [ln for ln in join(marching(hfun, MX0, MX1, MY0, MY1, 4.0, float(lv)))
                 if len(ln) >= 3]
        for ln in lines:
            body.append(poly(ln, 1.6 if lv in thick else 0.7))
        if lv in thick and lines:
            lines.sort(key=len, reverse=True)
            for ln in lines[:2]:
                for frac in (0.3, 0.7):
                    p = ln[int(len(ln) * frac)]
                    if MX0 + 26 < p[0] < MX1 - 30 and MY0 + 20 < p[1] < MY1 - 16:
                        labels.append((p[0], p[1], str(lv)))
                        break
    for riv in rivers:
        for off in (-2.2, 2.2):
            body.append(poly([(p[0], p[1] + off) for p in riv], 1.2))
    for (fn, pts) in landuse:
        for (x, y) in pts:
            body.append(fn(x, y))
    for (fn, x, y) in builds:
        body.append(fn(x, y))
    for (x, y) in spots:          # 標高点は標高の式から計算して書く
        body.append(circle(x, y, 1.5, "#000", 0.5) +
                    txt(x + 5, y + 4, "%.1f" % hfun(x, y), 10.5))
    for (x, y, v) in labels:
        body.append(rect(x - 13, y - 10, 26, 14, "#fff", 0) +
                    txt(x, y, v, 11, "middle", "bold"))
    for (x1, y1, x2, y2, a, b) in seclines:
        body.append(line(x1, y1, x2, y2, 1.3, "7 4"))
        body.append(mark(x1, y1, a, 8.0))
        body.append(mark(x2, y2, b, 8.0))
    body.append(extra)
    body.append("</g>")
    body.append(rect(MX0, MY0, MX1 - MX0, MY1 - MY0, "none", 1.6))
    for (x, y, lab) in marks:
        body.append(mark(x, y, lab))
    # 方位
    body.append('<g><path d="M655 60 L648 100 L655 92 L662 100 Z" fill="#000"/>'
                '<path d="M655 60 v40" stroke="#000" stroke-width="1"/>'
                + txt(655, 52, "N", 14, "middle", "bold") + "</g>")
    if scale:
        bx, by = 430.0, 478.0
        body.append(rect(bx, by, U1000, 9, "#fff", 1.2))
        body.append(rect(bx, by, U1000 / 2, 9, "#000", 0))
        body.append(txt(bx, by + 24, "0", 11, "middle"))
        body.append(txt(bx + U1000 / 2, by + 24, "500", 11, "middle"))
        body.append(txt(bx + U1000, by + 24, "1000m", 11, "middle"))
        body.append(txt(bx, by - 7, "2万5千分の1", 12))
    if legend:
        lx, ly = 46.0, 468.0
        rows = (len(legend) + 1) // 2
        body.append(rect(lx, ly, 336, 26 + rows * 21, "none", 1))
        body.append(txt(lx + 10, ly + 17, "凡例", 12, "start", "bold"))
        for k, (kind, lab) in enumerate(legend):
            cx = lx + 24 + (k % 2) * 168
            cy = ly + 38 + (k // 2) * 21
            if kind == "thin":
                body.append(line(cx - 12, cy - 3, cx + 12, cy - 3, 0.7))
            elif kind == "thick":
                body.append(line(cx - 12, cy - 3, cx + 12, cy - 3, 1.6))
            elif kind == "river":
                body.append(line(cx - 12, cy - 5, cx + 12, cy - 5, 1.2))
                body.append(line(cx - 12, cy - 1, cx + 12, cy - 1, 1.2))
            elif kind == "sea":
                body.append(rect(cx - 12, cy - 9, 24, 12, "hatch:wave", 0.8))
            elif kind == "spot":
                body.append(circle(cx, cy - 3, 1.5, "#000", 0.5))
            elif kind == "bank":
                body.append(line(cx - 12, cy - 3, cx + 12, cy - 3, 2.4))
            else:
                body.append(kind(cx, cy - 2))
            body.append(txt(cx + 18, cy, lab, 11))
    body.append(txt(MX0, 606, note, 11))
    body.append('<defs><clipPath id="frame"><rect x="%s" y="%s" width="%s" '
                'height="%s"/></clipPath></defs>'
                % (n(MX0), n(MY0), n(MX1 - MX0), n(MY1 - MY0)))
    return svg(W, H, "\n".join(body), label)


def grid(x0, x1, y0, y1, sx, sy, skip=None):
    """記号を並べる座標を作る。skip(x,y) が真の場所は置かない。"""
    out = []
    y = y0
    while y <= y1:
        x = x0
        while x <= x1:
            if not (skip and skip(x, y)):
                out.append((x, y))
            x += sx
        y += sy
    return out


LEG_BASE = [("thin", "主曲線（10mごと）"), ("thick", "計曲線（50mごと）")]


def tri(hfun, x, y):
    """三角点。標高は地形の式から計算して書く。"""
    return (lambda px, py: sym_sankaku(px, py, "%.1f" % hfun(px, py)), x, y)


def suijun(hfun, x, y):
    return (lambda px, py: sym_suijun(px, py, "%.1f" % hfun(px, py)), x, y)


# ======================================================================
# A01　扇状地（支谷つき）
# ======================================================================
APEX = (300.0, 240.0)


def h_a01(x, y):
    plain = 34.0 - 0.010 * max(0.0, x - APEX[0])
    m = (128.0
         - 0.44 * (x - MX0)
         - 52.0 * gauss(y, 240.0, 62.0)                 # 本流の谷
         + 32.0 * gauss(y, 120.0, 55.0)                 # 尾根
         - 15.0 * gauss(y, 405.0, 85.0)                 # 南の低み
         - 30.0 * gauss(y, 340.0, 38.0) * gauss(x, 130.0, 110.0))   # 支谷（川なし）
    if x > APEX[0]:
        m *= gauss(x, APEX[0], 50.0)
    dx = (x - APEX[0]) if x >= APEX[0] else (APEX[0] - x) * 3.0
    fan = plain + 28.0 - 0.16 * math.hypot(dx, (y - APEX[1]) * 0.95)
    return smax(smax(plain + m, fan, 5.0), plain, 4.0)


def map_a01():
    riv = [(MX0, 243), (110, 241), (180, 240), (250, 239), (300, 240),
           (350, 243), (405, 248), (460, 252), (520, 256), (575, 258), (MX1, 259)]
    fan = grid(322, 460, 196, 292, 23, 24,
               lambda x, y: (math.hypot(x - 300, (y - 240) * .95) > 150
                             or abs(y - 250) < 12))
    return draw_map(
        h_a01, list(range(40, 200, 10)), (50, 100, 150),
        rivers=[riv],
        landuse=[(sym_kaju, fan[0::2]), (sym_hatake, fan[1::2]),
                 (sym_ta, grid(508, 586, 180, 320, 26, 30, lambda x, y: abs(y - 254) < 14)
                  + grid(500, 578, 330, 386, 26, 28)),
                 (sym_shinyou, [(70, 90), (110, 66), (152, 100), (95, 150), (140, 168),
                                (75, 200), (120, 212), (188, 88), (218, 130), (188, 175),
                                (72, 300), (215, 300), (95, 400), (205, 396), (246, 200),
                                (252, 330), (60, 288), (168, 396)])],
        builds=[(sym_school, 352, 300), (sym_torii, 430, 196), (sym_post, 470, 300),
                tri(h_a01, 112, 122), tri(h_a01, 556, 190)],
        marks=[(350, 330, "P"), (350 + U1000, 330, "Q"), (395, 175, "R"),
               (130, 340, "X"), (170, 120, "Y")],
        extra=line(350, 330, 350 + U1000, 330, 1, "5 3"),
        legend=LEG_BASE + [("river", "河川"), (sym_ta, "田"), (sym_hatake, "畑"),
                           (sym_kaju, "果樹園"), (sym_shinyou, "針葉樹林"),
                           (sym_torii, "建物・神社など")],
        label="扇状地の模式地形図")


# ======================================================================
# A02　河岸段丘
# ======================================================================
def h_a02(x, y):
    base = 42.0 - 0.008 * (x - MX0)
    d = abs(y - 250.0)
    h = base
    h += 20.0 * sigm(d, 40.0, 3.0)      # 低位段丘への崖
    h += 30.0 * sigm(d, 95.0, 3.0)      # 中位段丘への崖
    h += 40.0 * sigm(d, 150.0, 3.0)     # 高位段丘への崖
    return h


def map_a02():
    riv = [(MX0, 252), (140, 250), (250, 249), (360, 250), (470, 251), (MX1, 253)]
    return draw_map(
        h_a02, list(range(40, 140, 10)), (50, 100),
        rivers=[riv],
        landuse=[(sym_ta, grid(70, 570, 224, 276, 40, 26,
                               lambda x, y: abs(y - 251) < 10)),
                 (sym_hatake, grid(70, 570, 170, 202, 42, 26)
                  + grid(70, 570, 300, 332, 42, 26)),
                 (sym_kuwa, grid(80, 560, 78, 120, 48, 28)
                  + grid(80, 560, 382, 424, 48, 28))],
        builds=[(sym_school, 210, 186), (sym_post, 300, 320), (sym_torii, 430, 320),
                (sym_city, 160, 322), tri(h_a02, 500, 96)],
        spots=[(250, 250), (250, 186), (250, 96), (480, 250), (480, 130)],
        marks=[(120, 250, "P"), (120 + U1000, 250, "Q"), (330, 186, "R"),
               (330, 96, "S"), (330, 218, "T")],
        extra=line(120, 250, 120 + U1000, 250, 1, "5 3"),
        legend=LEG_BASE + [("river", "河川"), ("spot", "標高点（m）"),
                           (sym_ta, "田"), (sym_hatake, "畑"),
                           (sym_kuwa, "茶畑"), (sym_city, "市役所")],
        label="河岸段丘の模式地形図")


# ======================================================================
# A03　三角州と氾濫原（低地。標高点で読む）
# ======================================================================
RIV_A03 = [(210, MY0), (222, 90), (232, 150), (246, 210), (268, 262),
           (300, 300), (350, 328), (410, 344), (470, 352), (540, 356), (MX1, 358)]


def h_a03(x, y):
    """西に台地（等高線が出る）、東は低地（標高点で示す）。
       川ぞいは自然堤防で少し高く、離れた後背湿地は低い。"""
    plat = 68.0 - 0.03 * (x - MX0)
    edge = 1.0 - sigm(x, 190.0, 6.0)
    near = _dist_gauss(x, y, RIV_A03, 34.0)
    far = _dist_gauss(x, y, RIV_A03, 95.0)
    low = 5.4 - 0.004 * (x - 190.0) + 2.4 * near - 1.4 * (1.0 - far)
    return low + (plat - low) * edge


def map_a03():
    riv = RIV_A03
    riv2 = [(300, 300), (330, 250), (352, 200), (368, 150), (376, 90), (380, MY0)]
    return draw_map(
        h_a03, list(range(10, 80, 10)), (50,),
        rivers=[riv, riv2],
        landuse=[(sym_ta, grid(400, 600, 160, 300, 28, 28)
                  + grid(300, 600, 380, 424, 30, 30)),
                 (sym_hatake, grid(240, 340, 90, 140, 26, 24)),
                 (sym_kuwa, grid(70, 160, 90, 400, 34, 40))],
        builds=[(sym_school, 430, 130), (sym_torii, 268, 216), (sym_post, 470, 396),
                (sym_koban, 520, 130), (sym_hosp, 560, 300), (sym_factory, 240, 400)],
        spots=[(280, 170), (430, 336), (540, 348), (330, 400), (470, 280),
               (250, 320), (150, 240), (580, 420)],
        marks=[(400, 342, "P"), (470, 240, "Q"), (150, 300, "R"), (330, 410, "S")],
        legend=LEG_BASE + [("river", "河川"), ("spot", "標高点（m）"),
                           (sym_ta, "田"), (sym_hatake, "畑"), (sym_kuwa, "茶畑"),
                           (sym_factory, "工場")],
        label="三角州と氾濫原の模式地形図")


# ======================================================================
# A04　台地を刻む谷
# ======================================================================
def h_a04(x, y):
    top = 92.0 - 0.015 * (x - MX0)
    v = 0.0
    for (cy, w, d, x0) in [(120.0, 30.0, 46.0, 620.0), (250.0, 26.0, 44.0, 560.0),
                           (370.0, 28.0, 42.0, 600.0)]:
        v += d * gauss(y, cy, w) * sigm(x0 - x, 0.0, 24.0)
    return top - v


def map_a04():
    return draw_map(
        h_a04, list(range(40, 110, 10)), (50, 100),
        rivers=[[(MX1, 122), (500, 121), (400, 120), (300, 120), (210, 119)],
                [(MX1, 252), (500, 251), (400, 250), (310, 250)],
                [(MX1, 372), (500, 371), (400, 370), (300, 370), (230, 369)]],
        landuse=[(sym_ta, grid(300, 600, 108, 134, 30, 26)
                  + grid(340, 600, 240, 264, 30, 26)
                  + grid(320, 600, 358, 384, 30, 26)),
                 (sym_hatake, grid(90, 600, 174, 200, 34, 26)
                  + grid(90, 600, 300, 326, 34, 26)),
                 (sym_kouyou, grid(90, 260, 60, 96, 40, 30)
                  + grid(90, 260, 400, 430, 40, 30))],
        builds=[(sym_school, 380, 190), (sym_post, 470, 312), (sym_torii, 250, 190),
                (sym_hs, 540, 190), (sym_roujin, 200, 312), tri(h_a04, 90, 190)],
        marks=[(360, 120, "X"), (360, 190, "Y"), (250, 250, "Z"), (520, 190, "W")],
        legend=LEG_BASE + [("river", "河川"), (sym_ta, "田"), (sym_hatake, "畑"),
                           (sym_kouyou, "広葉樹林"), (sym_school, "小・中学校"),
                           (sym_roujin, "老人ホーム")],
        label="台地を刻む谷の模式地形図")


# ======================================================================
# A05　海岸段丘
# ======================================================================
def h_a05(x, y):
    """東が海。西へ向かって段丘が高くなる。"""
    if x >= 540.0:
        return -2.0
    h = 4.0 + 0.004 * (540.0 - x)
    h += 26.0 * sigm(500.0 - x, 0.0, 5.0)
    h += 34.0 * sigm(370.0 - x, 0.0, 5.0)
    h += 40.0 * sigm(210.0 - x, 0.0, 6.0)
    h -= 26.0 * gauss(y, 300.0, 34.0) * sigm(500.0 - x, 0.0, 30.0)   # 段丘を刻む谷
    return h


def map_a05():
    sea = [(540, MY0), (546, 120), (540, 240), (548, 360), (542, MY1),
           (MX1, MY1), (MX1, MY0)]
    return draw_map(
        h_a05, list(range(10, 130, 10)), (50, 100),
        sea=sea,
        rivers=[[(200, 302), (300, 300), (400, 301), (500, 302), (540, 303)]],
        landuse=[(sym_ta, grid(400, 510, 180, 260, 28, 26)),
                 (sym_hatake, grid(230, 350, 90, 400, 30, 34)),
                 (sym_kuwa, grid(70, 180, 90, 400, 34, 38))],
        builds=[(sym_school, 460, 130), (sym_torii, 420, 356), (sym_post, 480, 356),
                tri(h_a05, 100, 200), suijun(h_a05, 470, 232)],
        marks=[(300, 200, "P"), (300 + U1000 * 0.6, 200, "Q"), (450, 200, "R"),
               (300, 300, "X"), (300, 380, "Y")],
        extra=line(300, 200, 300 + U1000 * 0.6, 200, 1, "5 3"),
        legend=LEG_BASE + [("river", "河川"), ("sea", "海"), (sym_ta, "田"),
                           (sym_hatake, "畑"), (sym_kuwa, "茶畑"),
                           (sym_suijun, "水準点")],
        label="海岸段丘の模式地形図")


# ======================================================================
# A06　丘陵（断面図用）
# ======================================================================
def h_a06(x, y):
    h = 20.0
    h += 120.0 * gauss(x, 180.0, 95.0) * gauss(y, 180.0, 95.0)    # 西の高い丘
    h += 80.0 * gauss(x, 450.0, 80.0) * gauss(y, 300.0, 80.0)     # 東の低い丘
    h += 26.0 * gauss(x, 320.0, 70.0) * gauss(y, 240.0, 90.0)     # 鞍部
    return h


def map_a06():
    return draw_map(
        h_a06, list(range(20, 160, 10)), (50, 100, 150),
        landuse=[(sym_kouyou, grid(80, 280, 80, 300, 44, 44)),
                 (sym_shinyou, grid(380, 540, 220, 380, 42, 42)),
                 (sym_ta, grid(80, 200, 380, 420, 30, 28))],
        builds=[tri(h_a06, 180, 180), tri(h_a06, 450, 300),
                (sym_school, 130, 400)],
        seclines=[(90, 180, 560, 180, "A", "B"), (180, 60, 180, 430, "C", "D")],
        legend=LEG_BASE + [(sym_kouyou, "広葉樹林"), (sym_shinyou, "針葉樹林"),
                           (sym_ta, "田"), (sym_sankaku, "三角点")],
        label="丘陵の模式地形図（断面図用）")


# ======================================================================
# A07　山地の水系
# ======================================================================
def h_a07(x, y):
    h = 210.0 - 0.30 * (y - MY0)
    for (pts, w, d) in [([(120, MY0), (150, 120), (170, 230), (200, 330), (240, MY1)], 30.0, 60.0),
                        ([(330, MY0), (330, 110), (320, 200), (280, 290)], 24.0, 46.0),
                        ([(520, MY0), (490, 120), (430, 220), (350, 300)], 24.0, 46.0)]:
        h -= d * _dist_gauss(x, y, pts, w)
    h += 30.0 * gauss(x, 460.0, 70.0) * gauss(y, 100.0, 90.0)
    return h


def _dist_gauss(x, y, pts, w):
    best = 1e9
    for i in range(len(pts) - 1):
        best = min(best, _seg_dist(x, y, pts[i], pts[i + 1]))
    return math.exp(-(best / w) ** 2)


def _seg_dist(px, py, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    wx, wy = px - a[0], py - a[1]
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / L))
    return math.hypot(px - (a[0] + t * vx), py - (a[1] + t * vy))


def map_a07():
    r1 = [(120, MY0), (150, 120), (170, 230), (200, 330), (240, MY1)]
    r2 = [(330, MY0), (330, 110), (320, 200), (280, 290), (250, 330)]
    r3 = [(520, MY0), (490, 120), (430, 220), (350, 300), (285, 320)]
    return draw_map(
        h_a07, list(range(50, 260, 10)), (50, 100, 150, 200),
        rivers=[r1, r2, r3],
        landuse=[(sym_shinyou, grid(60, 600, 60, 420, 62, 62))],
        builds=[tri(h_a07, 460, 100), tri(h_a07, 90, 90)],
        marks=[(250, 150, "X"), (400, 130, "Y"), (215, 400, "P"),
               (215 + U1000 * 0.8, 400, "Q")],
        extra=line(215, 400, 215 + U1000 * 0.8, 400, 1, "5 3"),
        seclines=[(80, 260, 600, 260, "A", "B")],
        legend=LEG_BASE + [("river", "河川"), (sym_shinyou, "針葉樹林"),
                           (sym_sankaku, "三角点")],
        label="山地の水系の模式地形図")


# ======================================================================
# A08　市街地（地図記号）
# ======================================================================
def h_a08(x, y):
    return 12.0 + 0.01 * (620.0 - x)


def map_a08():
    roads = ""
    for yy in (110, 200, 290, 380):
        roads += line(60, yy, 600, yy, 2.2)
    for xx in (120, 240, 360, 480, 570):
        roads += line(xx, 50, xx, 430, 2.2)
    rail = (line(150, 50, 150, 430, 3.4) +
            line(150, 50, 150, 430, 1.4, "10 10"))
    return draw_map(
        h_a08, [], (),
        landuse=[(sym_ta, grid(500, 590, 310, 370, 26, 26)),
                 (sym_hatake, grid(390, 470, 310, 370, 26, 26))],
        builds=[(sym_city, 200, 155), (sym_school, 300, 155), (sym_hs, 420, 155),
                (sym_post, 200, 245), (sym_hosp, 300, 245), (sym_koban, 420, 245),
                (sym_torii, 530, 155), (sym_tera, 530, 245),
                (sym_factory, 200, 335), (sym_hakubutsu, 300, 335),
                (sym_roujin, 300, 420), (sym_kaju, 560, 420),
                suijun(h_a08, 90, 245), tri(h_a08, 90, 155)],
        extra=roads + rail,
        marks=[(200, 155, "ア"), (300, 245, "イ"), (420, 245, "ウ"), (530, 245, "エ"),
               (300, 335, "オ"), (200, 335, "カ")],
        legend=[("bank", "道路"), ("thin", "鉄道（破線を重ねた線）")],
        scale=True, label="市街地の模式地形図（地図記号）")


# ======================================================================
# A09　低地の防災
# ======================================================================
def h_a09(x, y):
    low = 5.0 - 0.003 * (x - MX0)
    lev = 2.6 * gauss(y, 250.0, 26.0)                  # 自然堤防
    back = -1.4 * (gauss(y, 170.0, 46.0) + gauss(y, 340.0, 46.0))   # 後背湿地
    old = -1.0 * gauss(y, 350.0, 18.0) * gauss(x, 380.0, 150.0)     # 旧河道
    plat = 34.0 * sigm(110.0 - x, 0.0, 7.0)            # 西の台地
    return low + lev + back + old + plat


def map_a09():
    riv = [(MX0, 254), (130, 252), (240, 250), (360, 250), (480, 251), (MX1, 253)]
    bank = (poly([(130, 232), (240, 230), (360, 230), (480, 231), (MX1, 233)], 2.6) +
            poly([(130, 272), (240, 270), (360, 270), (480, 271), (MX1, 273)], 2.6))
    old = poly([(230, 350), (300, 344), (380, 348), (450, 354), (520, 350)], 1.0, "4 3")
    return draw_map(
        h_a09, list(range(10, 50, 10)), (50,),
        rivers=[riv],
        landuse=[(sym_ta, grid(180, 600, 150, 196, 30, 26)
                  + grid(180, 600, 320, 384, 30, 30)),
                 (sym_hatake, grid(180, 600, 224, 278, 34, 26,
                                   lambda x, y: abs(y - 251) < 14))],
        builds=[(sym_school, 260, 300), (sym_post, 400, 224), (sym_torii, 300, 224),
                (sym_hosp, 500, 300), (sym_roujin, 350, 170)],
        spots=[(220, 200), (320, 240), (440, 240), (300, 360), (480, 360),
               (80, 300), (560, 180)],
        marks=[(320, 236, "P"), (350, 172, "Q"), (300, 356, "R"), (80, 240, "S")],
        extra=bank + old,
        legend=LEG_BASE + [("river", "河川"), ("bank", "堤防"), ("spot", "標高点（m）"),
                           (sym_ta, "田"), (sym_hatake, "畑"), (sym_roujin, "老人ホーム")],
        label="低地の模式地形図（防災）")


# ======================================================================
# A10　谷底平野と段丘
# ======================================================================
def h_a10(x, y):
    base = 70.0 - 0.03 * (x - MX0)
    d = abs(y - 240.0)
    h = base + 20.0 * sigm(d, 60.0, 4.0) + 40.0 * sigm(d, 140.0, 14.0)
    h += 20.0 * gauss(x, 560.0, 70.0) * sigm(d, 140.0, 14.0)
    return h


def map_a10():
    riv = [(MX0, 242), (140, 240), (260, 239), (380, 240), (500, 241), (MX1, 243)]
    return draw_map(
        h_a10, list(range(40, 180, 10)), (50, 100, 150),
        rivers=[riv],
        landuse=[(sym_ta, grid(80, 580, 208, 272, 36, 30,
                               lambda x, y: abs(y - 241) < 12)),
                 (sym_hatake, grid(80, 580, 140, 172, 40, 26)
                  + grid(80, 580, 310, 342, 40, 26)),
                 (sym_shinyou, grid(80, 580, 60, 96, 52, 30)
                  + grid(80, 580, 390, 424, 52, 30))],
        builds=[(sym_school, 250, 154), (sym_post, 380, 326), tri(h_a10, 560, 90)],
        marks=[(160, 240, "P"), (160 + U1000 * 0.5, 240, "Q"),
               (300, 172, "R"), (300, 120, "S")],
        extra=line(160, 240, 160 + U1000 * 0.5, 240, 1, "5 3"),
        seclines=[(300, 60, 300, 420, "A", "B")],
        legend=LEG_BASE + [("river", "河川"), (sym_ta, "田"), (sym_hatake, "畑"),
                           (sym_shinyou, "針葉樹林"), (sym_school, "小・中学校")],
        label="谷底平野と段丘の模式地形図")


# ======================================================================
# 断面図（4つの候補）
# ======================================================================
def profile_series(hfun, p0, p1, kinds, N=90):
    """4つの候補の断面（標高の並び）を返す。正解は kinds の "real" の位置。"""
    xs = [i / float(N - 1) for i in range(N)]
    real = [hfun(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t) for t in xs]
    lo, hi = min(real), max(real)

    def make(kind):
        if kind == "real":
            return real[:]
        if kind == "flip":
            return real[::-1]
        if kind == "flat":
            return [lo + (v - lo) * 0.42 for v in real]
        if kind == "invert":
            return [lo + hi - v for v in real]
        if kind == "shift":
            k = int(N * 0.22)
            return real[k:] + real[:k]
        return real[:]
    return [make(k) for k in kinds], lo, hi


def profiles(hfun, p0, p1, kinds, label):
    """断面図の候補を4つ並べて描く。正解は kinds の中の "real" の位置。"""
    N = 90
    series, lo, hi = profile_series(hfun, p0, p1, kinds, N)
    span = max(20.0, hi - lo)
    pw, ph = 300.0, 130.0
    cols, rowh = 2, 176.0
    Wp, Hp = 700, int(60 + rowh * 2 + 40)
    body = [txt(20, 28, "%s　断面図の候補" % label, 15, "start", "bold")]
    for i, vals in enumerate(series):
        ox = 30 + (i % cols) * (pw + 40)
        oy = 60 + (i // cols) * rowh
        body.append(rect(ox, oy, pw, ph, "none", 1.0))
        body.append(txt(ox + 6, oy - 6, "①②③④"[i], 13, "start", "bold"))
        pts = []
        for k, v in enumerate(vals):
            px = ox + pw * (k / float(N - 1))
            py = oy + ph - 10 - (ph - 24) * (v - lo) / span
            pts.append((px, py))
        body.append(poly(pts, 1.8))
        body.append(txt(ox + 4, oy + ph + 14, label[0], 11))
        body.append(txt(ox + pw - 4, oy + ph + 14, label[-1], 11, "end"))
    body.append(txt(20, Hp - 12,
                    "※ 縦は強調してある。左右の向きは図の%s→%sに合わせてある。"
                    % (label[0], label[-1]), 11))
    return svg(Wp, Hp, "\n".join(body), "断面図の候補")


FIGURES = {
    "A01_map.svg": map_a01,
    "A02_map.svg": map_a02,
    "A03_map.svg": map_a03,
    "A04_map.svg": map_a04,
    "A05_map.svg": map_a05,
    "A06_map.svg": map_a06,
    "A07_map.svg": map_a07,
    "A08_map.svg": map_a08,
    "A09_map.svg": map_a09,
    "A10_map.svg": map_a10,
    "A06_profAB.svg": lambda: profiles(h_a06, (90, 180), (560, 180),
                                       PROF["A06_profAB.svg"][0], "A−B"),
    "A06_profCD.svg": lambda: profiles(h_a06, (180, 60), (180, 430),
                                       PROF["A06_profCD.svg"][0], "C−D"),
    "A07_profAB.svg": lambda: profiles(h_a07, (80, 260), (600, 260),
                                       PROF["A07_profAB.svg"][0], "A−B"),
    "A10_profAB.svg": lambda: profiles(h_a10, (300, 60), (300, 420),
                                       PROF["A10_profAB.svg"][0], "A−B"),
}

# 断面図の候補の並びと、その線の両端。正解（"real"）の位置が答えになる。
PROF = {
    "A06_profAB.svg": (["flat", "real", "invert", "flip"], h_a06, (90, 180), (560, 180)),
    "A06_profCD.svg": (["invert", "shift", "real", "flat"], h_a06, (180, 60), (180, 430)),
    "A07_profAB.svg": (["flip", "flat", "invert", "real"], h_a07, (80, 260), (600, 260)),
    "A10_profAB.svg": (["real", "flat", "shift", "invert"], h_a10, (300, 60), (300, 420)),
}
