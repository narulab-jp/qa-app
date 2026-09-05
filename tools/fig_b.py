# -*- coding: utf-8 -*-
"""冊B（統計判読）の図版。

  数値はすべて下の表に書いた架空の値で、目盛も軸もこのスクリプトが描く。
  実在の統計は使っていない（図の中にも架空である旨を書いている）。
"""
import math

from figlib import (NOTE_FAKE, circle, line, n, poly, rect, svg, txt)

FILL4 = ["hatch:diag", "#000", "hatch:dot", "#fff"]


# ======================================================================
# 雨温図・ハイサーグラフ
# ======================================================================
CLIMO1 = [
    ("ア", [26, 26, 27, 27, 27, 26, 26, 26, 26, 26, 26, 26],
     [230, 220, 240, 250, 230, 180, 160, 170, 190, 220, 240, 250]),
    ("イ", [8, 9, 11, 15, 19, 23, 26, 26, 22, 17, 12, 9],
     [80, 70, 60, 50, 30, 10, 5, 8, 35, 80, 95, 90]),
    ("ウ", [-15, -13, -6, 3, 11, 17, 20, 18, 12, 4, -4, -12],
     [25, 20, 25, 35, 50, 70, 85, 80, 60, 45, 35, 30]),
    ("エ", [25, 25, 23, 19, 15, 12, 12, 14, 17, 20, 22, 24],
     [110, 105, 115, 90, 80, 60, 55, 60, 75, 95, 105, 115]),
]
CLIMO2 = [
    ("オ", [12, 15, 20, 26, 31, 34, 35, 34, 31, 25, 18, 13],
     [3, 2, 2, 1, 0, 0, 0, 0, 0, 1, 2, 3]),                       # 砂漠
    ("カ", [-4, -2, 4, 11, 17, 22, 24, 23, 17, 10, 3, -2],
     [12, 10, 14, 22, 38, 46, 40, 34, 26, 20, 16, 12]),           # ステップ
    ("キ", [5, 5, 7, 9, 12, 15, 17, 17, 15, 11, 8, 6],
     [70, 55, 55, 50, 55, 50, 45, 55, 60, 75, 80, 80]),           # 西岸海洋性
    ("ク", [27, 28, 28, 27, 26, 25, 25, 26, 27, 27, 27, 27],
     [10, 8, 25, 90, 190, 250, 260, 240, 200, 120, 40, 12]),      # サバナ
]
CLIMO3 = [
    ("サ", [-24, -22, -16, -6, 3, 11, 15, 12, 5, -4, -14, -21],
     [10, 8, 10, 12, 20, 40, 55, 50, 35, 20, 14, 10]),            # 亜寒帯冬季少雨
    ("シ", [22, 22, 20, 16, 12, 9, 9, 11, 14, 17, 19, 21],
     [40, 45, 60, 85, 110, 120, 110, 95, 70, 55, 45, 40]),        # 南半球の西岸海洋性
    ("ス", [16, 17, 19, 23, 26, 28, 28, 28, 27, 24, 20, 17],
     [8, 12, 25, 45, 130, 260, 300, 270, 190, 60, 12, 6]),        # 温暖冬季少雨
    ("セ", [1, 2, 6, 12, 18, 22, 25, 26, 22, 16, 9, 3],
     [45, 50, 70, 90, 110, 150, 160, 140, 130, 100, 70, 50]),     # 温暖湿潤
]
T_MIN, T_MAX, P_MAX = -30.0, 40.0, 320.0


def climo_panel(ox, oy, w, h, name, temp, prec):
    s = [rect(ox, oy, w, h, "none", 1.2),
         txt(ox + 8, oy + 20, "地点" + name, 15, "start", "bold"),
         txt(ox + 10, oy + 40, "降水量(mm)", 11),
         txt(ox + w - 10, oy + 40, "気温(℃)", 11, "end")]
    px0, py0 = ox + 46.0, oy + h - 30.0
    pw, ph = w - 92.0, h - 78.0

    def yp(mm):
        return py0 - ph * (mm / P_MAX)

    def yt(c):
        return py0 - ph * ((c - T_MIN) / (T_MAX - T_MIN))

    for mm in (100, 200, 300):
        s.append(line(px0, yp(mm), px0 + pw, yp(mm), 0.4, "3 3"))
        s.append(txt(px0 - 6, yp(mm) + 4, str(mm), 10, "end"))
    for c in (-20, -10, 0, 10, 20, 30, 40):
        s.append(txt(px0 + pw + 6, yt(c) + 4, str(c), 10))
    s.append(line(px0, py0 - ph, px0, py0, 1.1))
    s.append(line(px0 + pw, py0 - ph, px0 + pw, py0, 1.1))
    s.append(line(px0, py0, px0 + pw, py0, 1.1))
    s.append(line(px0, yt(0), px0 + pw, yt(0), 0.8, "6 3"))
    s.append(txt(px0 + pw + 6, yt(0) - 6, "0℃", 9))
    bw = pw / 12.0
    for i, mm in enumerate(prec):
        s.append(rect(px0 + i * bw + bw * 0.18, yp(mm), bw * 0.64,
                      py0 - yp(mm), "#000", 0))
    pts = [(px0 + (i + 0.5) * bw, yt(c)) for i, c in enumerate(temp)]
    s.append(poly(pts, 2))
    for (x, y) in pts:
        s.append(circle(x, y, 2.6, "#fff", 1.4))
    for i in (0, 3, 6, 9, 11):
        s.append(txt(px0 + (i + 0.5) * bw, py0 + 14, str(i + 1), 10, "middle"))
    s.append(txt(px0 + pw / 2, py0 + 27, "月", 10, "middle"))
    return "".join(s)


def climo(data, title):
    W, H = 720, 660
    pw, ph = 330.0, 280.0
    body = [txt(20, 26, title, 16, "start", "bold")]
    for k, (name, t, p) in enumerate(data):
        body.append(climo_panel(20 + (k % 2) * (pw + 20), 44 + (k // 2) * (ph + 24),
                                pw, ph, name, t, p))
    body.append(txt(20, 648, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(body), title)


def hyther(data, title):
    """ハイサーグラフ（横に降水量、縦に気温をとり、月を線で結ぶ）"""
    W, H = 720, 660
    pw, ph = 330.0, 280.0
    body = [txt(20, 26, title, 16, "start", "bold")]
    for k, (name, t, p) in enumerate(data):
        ox = 20 + (k % 2) * (pw + 20)
        oy = 44 + (k // 2) * (ph + 24)
        body.append(rect(ox, oy, pw, ph, "none", 1.2))
        body.append(txt(ox + 8, oy + 20, "地点" + name, 15, "start", "bold"))
        x0, y0 = ox + 52.0, oy + ph - 34.0
        w, h = pw - 78.0, ph - 68.0
        body.append(line(x0, y0 - h, x0, y0, 1.1))
        body.append(line(x0, y0, x0 + w, y0, 1.1))
        for mm in (0, 100, 200, 300):
            xx = x0 + w * mm / P_MAX
            body.append(line(xx, y0, xx, y0 - h, 0.4, "3 3"))
            body.append(txt(xx, y0 + 14, str(mm), 10, "middle"))
        for c in (-20, 0, 20, 40):
            yy = y0 - h * (c - T_MIN) / (T_MAX - T_MIN)
            body.append(line(x0, yy, x0 + w, yy, 0.4, "3 3"))
            body.append(txt(x0 - 6, yy + 4, str(c), 10, "end"))
        pts = [(x0 + w * p[i] / P_MAX,
                y0 - h * (t[i] - T_MIN) / (T_MAX - T_MIN)) for i in range(12)]
        body.append(poly(pts + [pts[0]], 1.6))
        for i, (x, y) in enumerate(pts):
            body.append(circle(x, y, 2.4, "#fff", 1.2))
            if i in (0, 6):
                body.append(txt(x + 6, y - 5, "%d月" % (i + 1), 10))
        body.append(txt(x0 + w / 2, oy + ph - 6, "降水量(mm)", 10, "middle"))
        body.append(txt(ox + 8, oy + 40, "気温(℃)", 10))
    body.append(txt(20, 648, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(body), title)


# ======================================================================
# 人口ピラミッド
# ======================================================================
AGES = ["0〜4", "5〜9", "10〜14", "15〜19", "20〜24", "25〜29", "30〜34",
        "35〜39", "40〜44", "45〜49", "50〜54", "55〜59", "60〜64", "65〜69",
        "70〜74", "75〜79", "80以上"]
# 各階級が全人口に占める割合（男・女それぞれ、単位％）。合計100％になるよう作った。
PYR = [
    ("A", "富士山型", [7.4, 6.6, 5.8, 5.1, 4.4, 3.8, 3.2, 2.7, 2.2, 1.8, 1.4,
                      1.1, 0.8, 0.6, 0.4, 0.2, 0.1],
     [7.1, 6.4, 5.6, 4.9, 4.3, 3.7, 3.2, 2.7, 2.3, 1.9, 1.5, 1.2, 0.9, 0.7,
      0.5, 0.3, 0.2]),
    ("B", "つりがね型", [3.3, 3.3, 3.3, 3.3, 3.3, 3.3, 3.3, 3.2, 3.1, 3.0, 2.8,
                       2.6, 2.3, 1.9, 1.5, 1.0, 0.6],
     [3.2, 3.2, 3.2, 3.2, 3.2, 3.2, 3.2, 3.2, 3.1, 3.0, 2.9, 2.7, 2.5, 2.2,
      1.8, 1.4, 1.0]),
    ("C", "つぼ型", [1.9, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.3, 3.6, 3.7, 3.5,
                    3.3, 3.1, 2.9, 2.5, 1.8, 1.2],
     [1.8, 1.9, 2.1, 2.3, 2.5, 2.7, 2.9, 3.2, 3.5, 3.7, 3.6, 3.4, 3.3, 3.1,
      2.9, 2.4, 2.1]),
    ("D", "ひょうたん型", [2.2, 2.4, 2.6, 2.6, 1.5, 1.2, 1.6, 2.2, 2.8, 3.4,
                        3.8, 4.0, 4.2, 4.0, 3.4, 2.4, 1.6],
     [2.1, 2.3, 2.5, 2.5, 1.4, 1.1, 1.5, 2.1, 2.7, 3.3, 3.8, 4.1, 4.3, 4.2,
      3.7, 2.9, 2.3]),
]
def _norm100(rows):
    """男女の合計がちょうど100％になるようにそろえる（架空の値なので比だけを保つ）"""
    out = []
    for row in rows:
        m, f = list(row[-2]), list(row[-1])
        k = 100.0 / (sum(m) + sum(f))
        m = [round(v * k, 1) for v in m]
        f = [round(v * k, 1) for v in f]
        d = round(100.0 - sum(m) - sum(f), 1)
        f[8] = round(f[8] + d, 1)          # 端数は中央の階級で合わせる
        out.append(tuple(list(row[:-2]) + [m, f]))
    return out


PYR = _norm100(PYR)
PYR_TIME = [
    ("1965年", PYR[0][2], PYR[0][3]),
    ("1995年", PYR[1][2], PYR[1][3]),
    ("2025年", PYR[2][2], PYR[2][3]),
]


def pyramid_panel(ox, oy, w, h, name, male, female, show_ages):
    """人口ピラミッド1つぶん。

      ★2026-09-05 直したこと
        ・年齢の目盛を、まん中の軸の上に重ねて書いていた。棒がその上に
          かぶさって読めなかったので、左に専用の欄を作って外へ出した。
        ・小さく置かれる図なので、年齢は2段おき→4段おきに減らし、
          そのぶん文字を大きくした（7.5→12）。
        ・「男（％）」「女（％）」が横軸の数字に重なっていたので、
          パネルの左下・右下の隅に寄せた。
    """
    s = [rect(ox, oy, w, h, "none", 1.2),
         txt(ox + w / 2, oy + 20, name, 14, "middle", "bold")]
    lab_w = 46.0 if show_ages else 0.0      # 年齢を書く左の欄
    cx = ox + lab_w + (w - lab_w) / 2.0
    top, bot = oy + 32.0, oy + h - 40.0
    bh = (bot - top) / len(AGES)
    half = (w - lab_w) / 2.0 - 18.0
    mx = 8.0
    for i in range(len(AGES)):
        yy = bot - (i + 1) * bh
        for (v, sgn, fill) in ((male[i], -1, "hatch:diag"), (female[i], 1, "#fff")):
            ww = half * v / mx
            s.append(rect(cx if sgn > 0 else cx - ww, yy + 1, ww, bh - 2, fill, 0.8))
        if show_ages and i % 4 == 0:
            s.append(txt(ox + 5, yy + bh - 2, AGES[i], 12, "start"))
    s.append(line(cx, top, cx, bot, 1.0))
    s.append(line(cx - half - 6, bot, cx + half + 6, bot, 1.0))
    for v in (2, 4, 6, 8):
        for sgn in (-1, 1):
            xx = cx + sgn * half * v / mx
            s.append(line(xx, bot, xx, bot + 5, 0.8))
            s.append(txt(xx, bot + 17, str(v), 11, "middle"))
    s.append(txt(ox + 5, oy + h - 6, "男（％）", 11, "start"))
    s.append(txt(ox + w - 5, oy + h - 6, "女（％）", 11, "end"))
    return "".join(s)


def pyramids(data, title, show_ages=True):
    W = 720
    cols = 2 if len(data) == 4 else 3
    rows = (len(data) + cols - 1) // cols
    pw = (W - 20 * (cols + 1)) / float(cols)
    ph = 300.0
    H = int(44 + rows * (ph + 20) + 30)
    body = [txt(20, 26, title, 16, "start", "bold")]
    for k, item in enumerate(data):
        nm = item[0] + ("国" if len(item[0]) == 1 else "")
        male, female = item[-2], item[-1]
        body.append(pyramid_panel(20 + (k % cols) * (pw + 20),
                                  44 + (k // cols) * (ph + 20),
                                  pw, ph, nm, male, female, show_ages))
    body.append(txt(20, H - 12, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(body), title)


# ======================================================================
# 三角グラフ
# ======================================================================
TRI4 = [("ア", 62, 16, 22), ("イ", 28, 30, 42), ("ウ", 9, 33, 58), ("エ", 2, 22, 76)]
TRI_TIME = [("1950年", 48, 22, 30), ("1975年", 20, 34, 46),
            ("2000年", 7, 31, 62), ("2025年", 3, 24, 73)]


def triangle(points, title, note):
    W, H = 660, 640
    S = 470.0
    ox, oy = 100.0, 545.0
    ax = (ox, oy)
    bx = (ox + S, oy)
    cx = (ox + S / 2, oy - S * math.sqrt(3) / 2)

    def pt(p1, p2, p3):
        """第1次 p1・第2次 p2・第3次 p3（％）→ 座標"""
        return (ax[0] * p1 / 100.0 + bx[0] * p2 / 100.0 + cx[0] * p3 / 100.0,
                ax[1] * p1 / 100.0 + bx[1] * p2 / 100.0 + cx[1] * p3 / 100.0)

    body = [txt(20, 26, title, 16, "start", "bold")]
    for v in range(10, 100, 10):
        body.append(poly([pt(v, 100 - v, 0), pt(v, 0, 100 - v)], 0.4, "3 3"))
        body.append(poly([pt(100 - v, v, 0), pt(0, v, 100 - v)], 0.4, "3 3"))
        body.append(poly([pt(100 - v, 0, v), pt(0, 100 - v, v)], 0.4, "3 3"))
    body.append(poly([ax, bx, cx], 1.6, close=True))
    for v in range(0, 101, 20):
        p = pt(v, 100 - v, 0)
        body.append(txt(p[0], p[1] + 18, str(v), 11, "middle"))
        p = pt(0, 100 - v, v)
        body.append(txt(p[0] + 14, p[1] + 4, str(v), 11))
        p = pt(100 - v, 0, v)
        body.append(txt(p[0] - 14, p[1] + 4, str(v), 11, "end"))
    body.append(txt(ox + S / 2, oy + 42, "第一次産業（％）　→", 12, "middle"))
    body.append(txt(ox + S + 44, oy - S * 0.42, "第二次産業（％）", 12, "middle"))
    body.append(txt(ox - 52, oy - S * 0.42, "第三次産業（％）", 12, "middle"))
    for (nm, p1, p2, p3) in points:
        p = pt(p1, p2, p3)
        body.append(circle(p[0], p[1], 5.5, "#000", 1.2))
        body.append(rect(p[0] + 8, p[1] - 20, 46, 16, "#fff", 0))
        body.append(txt(p[0] + 10, p[1] - 8, nm, 12, "start", "bold"))
    body.append(txt(20, H - 12, note, 11))
    return svg(W, H, "\n".join(body), title)


# ======================================================================
# 帯グラフ
# ======================================================================
BAR_ENERGY = [
    ("A", [("水力", 85), ("火力", 10), ("原子力", 0), ("その他", 5)]),
    ("B", [("水力", 10), ("火力", 20), ("原子力", 65), ("その他", 5)]),
    ("C", [("水力", 0), ("火力", 95), ("原子力", 0), ("その他", 5)]),
    ("D", [("水力", 20), ("火力", 70), ("原子力", 0), ("その他", 10)]),
]
BAR_ENERGY2 = [
    ("カ", [("石炭", 68), ("石油", 12), ("天然ガス", 8), ("その他", 12)]),
    ("キ", [("石炭", 6), ("石油", 34), ("天然ガス", 46), ("その他", 14)]),
    ("ク", [("石炭", 22), ("石油", 38), ("天然ガス", 24), ("その他", 16)]),
    ("ケ", [("石炭", 4), ("石油", 18), ("天然ガス", 10), ("その他", 68)]),
]
BAR_EXPORT = [
    ("サ", [("機械類", 74), ("鉱産資源", 3), ("食料・農産物", 6), ("その他", 17)]),
    ("シ", [("機械類", 4), ("鉱産資源", 87), ("食料・農産物", 3), ("その他", 6)]),
    ("ス", [("機械類", 6), ("鉱産資源", 4), ("食料・農産物", 71), ("その他", 19)]),
    ("セ", [("機械類", 8), ("鉱産資源", 74), ("食料・農産物", 5), ("その他", 13)]),
]


def stackbars(data, title, note, keys=None):
    W = 720
    body = [txt(20, 26, title, 16, "start", "bold")]
    bx, bw = 100.0, 540.0
    keys = keys or [k for (k, _) in data[0][1]]
    fills = dict(zip(keys, FILL4))
    for k, (name, parts) in enumerate(data):
        by = 58.0 + k * 62.0
        body.append(txt(bx - 14, by + 22, name + "国", 14, "end", "bold"))
        x = bx
        for (lab, v) in parts:
            if v <= 0:
                continue
            w = bw * v / 100.0
            body.append(rect(x, by, w, 32, fills[lab], 1.1))
            if w >= 40:
                body.append(rect(x + w / 2 - 15, by + 8, 30, 15, "#fff", 0))
                body.append(txt(x + w / 2, by + 20, str(v), 12, "middle", "bold"))
            x += w
        body.append(txt(bx, by + 48, "0", 10, "middle"))
        body.append(txt(bx + bw, by + 48, "100", 10, "middle"))
    ly = 58.0 + len(data) * 62.0 + 8
    H = int(ly + 42 + 34)
    body.append(rect(60, ly, 600, 42, "none", 1))
    for k, lab in enumerate(keys):
        cx = 76.0 + k * (600.0 / len(keys))
        body.append(rect(cx, ly + 13, 26, 16, fills[lab], 1.1))
        body.append(txt(cx + 32, ly + 26, lab, 11.5))
    body.append(txt(20, H - 12, note, 11))
    return svg(W, H, "\n".join(body), title)


# ======================================================================
# 折れ線・時系列
# ======================================================================
TRANS_YEARS = [1900, 1920, 1940, 1960, 1980, 2000, 2020]
TRANS = [("出生率", [42, 41, 38, 33, 24, 16, 11]),
         ("死亡率", [38, 32, 24, 14, 9, 8, 9])]
URBAN_YEARS = [1960, 1975, 1990, 2005, 2020]
URBAN = [("ア", [12, 18, 27, 41, 58]), ("イ", [62, 70, 76, 80, 84]),
         ("ウ", [30, 42, 54, 64, 70]), ("エ", [8, 10, 14, 21, 32])]


def linechart(years, series, title, ylab, note, ymax, marks=("o", "s", "t", "d")):
    W, H = 720, 470
    ox, oy = 90.0, 380.0
    w, h = 560.0, 300.0
    body = [txt(20, 26, title, 16, "start", "bold")]
    step = ymax / 5.0
    for i in range(6):
        v = step * i
        yy = oy - h * v / ymax
        body.append(line(ox, yy, ox + w, yy, 0.4, "3 3"))
        body.append(txt(ox - 8, yy + 4, "%g" % v, 11, "end"))
    body.append(line(ox, oy - h, ox, oy, 1.1))
    body.append(line(ox, oy, ox + w, oy, 1.1))
    for i, y in enumerate(years):
        xx = ox + w * i / float(len(years) - 1)
        body.append(line(xx, oy, xx, oy + 5, 0.9))
        body.append(txt(xx, oy + 20, str(y), 11, "middle"))
    dashes = ["", "8 4", "2 4", "10 3 2 3"]
    for k, (nm, vals) in enumerate(series):
        pts = [(ox + w * i / float(len(years) - 1), oy - h * v / ymax)
               for i, v in enumerate(vals)]
        body.append(poly(pts, 2.0, dashes[k % 4]))
        for (x, y) in pts:
            if marks[k % 4] == "o":
                body.append(circle(x, y, 3.4, "#fff", 1.4))
            elif marks[k % 4] == "s":
                body.append(rect(x - 3.2, y - 3.2, 6.4, 6.4, "#fff", 1.4))
            elif marks[k % 4] == "t":
                body.append(poly([(x, y - 4), (x + 3.6, y + 2.6), (x - 3.6, y + 2.6)],
                                 1.3, fill="#fff", close=True))
            else:
                body.append(poly([(x, y - 4), (x + 4, y), (x, y + 4), (x - 4, y)],
                                 1.3, fill="#fff", close=True))
        body.append(txt(pts[-1][0] + 8, pts[-1][1] + 4, nm, 12, "start", "bold"))
    body.append(txt(ox - 40, oy - h - 12, ylab, 11))
    body.append(txt(ox + w / 2, oy + 44, "年", 11, "middle"))
    body.append(txt(20, H - 14, note, 11))
    return svg(W, H, "\n".join(body), title)


# ======================================================================
# 散布図
# ======================================================================
SC_GNI = [("ア", 62000, 3), ("イ", 41000, 4), ("ウ", 28000, 6), ("エ", 14000, 11),
          ("オ", 8600, 18), ("カ", 4200, 29), ("キ", 2100, 44), ("ク", 980, 58),
          ("ケ", 620, 71), ("コ", 34000, 5), ("サ", 1500, 52), ("シ", 21000, 8)]
SC_URB = [("ア", 84, 2), ("イ", 78, 3), ("ウ", 71, 5), ("エ", 64, 9),
          ("オ", 55, 14), ("カ", 46, 22), ("キ", 38, 31), ("ク", 30, 40),
          ("ケ", 24, 52), ("コ", 81, 2), ("サ", 33, 36), ("シ", 60, 11)]


def scatter(data, title, xlab, ylab, note, xmax, ymax, xlog=False, hi=()):
    W, H = 720, 520
    ox, oy = 96.0, 420.0
    w, h = 560.0, 330.0
    body = [txt(20, 26, title, 16, "start", "bold")]

    def X(v):
        if xlog:
            return ox + w * (math.log10(v) - 2.0) / (math.log10(xmax) - 2.0)
        return ox + w * v / xmax

    def Y(v):
        return oy - h * v / ymax

    ticks = [100, 300, 1000, 3000, 10000, 30000, 100000] if xlog else \
            [xmax * i / 5.0 for i in range(6)]
    for t in ticks:
        if t > xmax or (xlog and t < 100):
            continue
        body.append(line(X(t), oy, X(t), oy - h, 0.4, "3 3"))
        body.append(txt(X(t), oy + 20, format(int(t), ","), 11, "middle"))
    for i in range(6):
        v = ymax * i / 5.0
        body.append(line(ox, Y(v), ox + w, Y(v), 0.4, "3 3"))
        body.append(txt(ox - 8, Y(v) + 4, "%g" % v, 11, "end"))
    body.append(line(ox, oy - h, ox, oy, 1.1))
    body.append(line(ox, oy, ox + w, oy, 1.1))
    for (nm, xv, yv) in data:
        px, py = X(xv), Y(yv)
        big = nm in hi
        body.append(circle(px, py, 6.0 if big else 4.2, "#000" if big else "#fff", 1.4))
        body.append(txt(px + 8, py - 6, nm, 11, "start", "bold" if big else "normal"))
    body.append(txt(ox + w / 2, oy + 44, xlab, 12, "middle"))
    body.append(txt(ox - 46, oy - h - 12, ylab, 12))
    body.append(txt(20, H - 14, note, 11))
    return svg(W, H, "\n".join(body), title)


# ======================================================================
# 主題図（階級区分図・図形表現図）
# ======================================================================
# 架空の地域を9つの区に分けた。面積(km2)・人口(千人)・人口密度は下で検算する。
REGIONS = [
    # 区, 中心x, 中心y, 面積km2, 人口千人
    ("ア", 150, 130, 120, 342), ("イ", 320, 120, 260, 338), ("ウ", 500, 140, 380, 190),
    ("エ", 140, 270, 210, 546), ("オ", 320, 270, 150, 900), ("カ", 510, 280, 320, 256),
    ("キ", 160, 400, 340, 204), ("ク", 330, 400, 280, 196), ("ケ", 500, 400, 440, 132),
]
REG_POLY = {
    "ア": [(60, 60), (240, 60), (240, 200), (60, 200)],
    "イ": [(240, 60), (410, 60), (410, 190), (240, 190)],
    "ウ": [(410, 60), (620, 60), (620, 210), (410, 210)],
    "エ": [(60, 200), (240, 200), (235, 340), (60, 340)],
    "オ": [(240, 190), (410, 190), (410, 345), (235, 340)],
    "カ": [(410, 210), (620, 210), (620, 350), (410, 345)],
    "キ": [(60, 340), (235, 340), (240, 470), (60, 470)],
    "ク": [(235, 340), (410, 345), (415, 470), (240, 470)],
    "ケ": [(410, 345), (620, 350), (620, 470), (415, 470)],
}
DENS_CLASS = [(0, 500), (500, 1500), (1500, 3000), (3000, 7000)]
STEP_FILL = ["#fff", "hatch:dotfine", "hatch:diag", "#000"]
STEP_TXT = ["#000", "#000", "#000", "#fff"]


def density(nm):
    for (r, cx, cy, area, pop) in REGIONS:
        if r == nm:
            return pop * 1000.0 / area
    return 0.0


def choropleth():
    W, H = 720, 620
    body = [txt(20, 26, "架空の地域の人口密度（区ごと・階級区分図）", 16, "start", "bold")]
    for (nm, cx, cy, area, pop) in REGIONS:
        d = density(nm)
        k = 0
        for i, (lo, hi) in enumerate(DENS_CLASS):
            if lo <= d < hi:
                k = i
        body.append(poly(REG_POLY[nm], 1.4, fill=STEP_FILL[k], close=True))
        body.append(rect(cx - 15, cy - 13, 30, 22, "#fff", 0))
        body.append(txt(cx, cy + 4, nm, 15, "middle", "bold"))
    ly = 500.0
    body.append(rect(60, ly, 560, 62, "none", 1))
    body.append(txt(72, ly + 20, "凡例　人口密度（人/km²）", 12, "start", "bold"))
    for k, (lo, hi) in enumerate(DENS_CLASS):
        cx = 76.0 + k * 138.0
        body.append(rect(cx, ly + 30, 26, 18, STEP_FILL[k], 1.1))
        body.append(txt(cx + 32, ly + 44,
                        "%s〜%s" % (format(lo, ","), format(hi, ",")), 11))
    body.append(txt(20, H - 12, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(body), "階級区分図")


def propsymbol():
    W, H = 720, 620
    body = [txt(20, 26, "架空の地域の人口（区ごと・図形表現図）", 16, "start", "bold")]
    for nm in REG_POLY:
        body.append(poly(REG_POLY[nm], 1.0, fill="#fff", close=True))
    for (nm, cx, cy, area, pop) in REGIONS:
        r = 6.0 + math.sqrt(pop) * 1.15
        body.append(circle(cx, cy, r, "hatch:dotfine", 1.4))
        body.append(txt(cx, cy + 5, nm, 14, "middle", "bold"))
    ly = 500.0
    body.append(rect(60, ly, 560, 74, "none", 1))
    body.append(txt(72, ly + 20, "凡例　円の面積が人口に比例する（千人）", 12,
                    "start", "bold"))
    for k, v in enumerate((200, 500, 900)):
        cx = 130.0 + k * 170.0
        r = 6.0 + math.sqrt(v) * 1.15
        body.append(circle(cx, ly + 46, r, "hatch:dotfine", 1.2))
        body.append(txt(cx + r + 8, ly + 50, str(v), 11))
    body.append(txt(20, H - 12, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(body), "図形表現図")


# ======================================================================
FIGURES = {
    "B01_climo.svg": lambda: climo(CLIMO1, "架空の4地点ア〜エの雨温図"),
    "B02_climo.svg": lambda: climo(CLIMO2, "架空の4地点オ〜クの雨温図"),
    "B03_hyther.svg": lambda: hyther(CLIMO3, "架空の4地点サ〜セのハイサーグラフ"),
    "B04_pyramid.svg": lambda: pyramids(PYR, "架空の4か国の人口ピラミッド"),
    "B05_pyramid.svg": lambda: pyramids(
        PYR_TIME, "架空のX国の人口ピラミッドの移り変わり", show_ages=True),
    "B06_triangle.svg": lambda: triangle(
        TRI4, "架空の4か国の産業別就業者構成（三角グラフ）", NOTE_FAKE),
    "B07_triangle.svg": lambda: triangle(
        TRI_TIME, "架空のY国の産業別就業者構成の移り変わり（三角グラフ）", NOTE_FAKE),
    "B08_bars.svg": lambda: stackbars(
        BAR_ENERGY2, "架空の4か国の一次エネルギー消費の内訳（％）", NOTE_FAKE),
    "B09_bars.svg": lambda: stackbars(
        BAR_EXPORT, "架空の4か国の輸出品目の内訳（％）", NOTE_FAKE,
        keys=None),
    "B10_line.svg": lambda: linechart(
        TRANS_YEARS, TRANS, "架空のZ国の出生率と死亡率の移り変わり",
        "人口千人あたり（‰）", NOTE_FAKE, 50.0),
    "B11_line.svg": lambda: linechart(
        URBAN_YEARS, URBAN, "架空の4か国の都市人口率の移り変わり",
        "都市人口率（％）", NOTE_FAKE, 100.0),
    "B12_scatter.svg": lambda: scatter(
        SC_GNI, "架空の12か国の一人当たりGNIと乳児死亡率",
        "一人当たりGNI（ドル・対数目盛）", "乳児死亡率（出生千人あたり）",
        NOTE_FAKE, 100000, 80.0, xlog=True),
    "B13_scatter.svg": lambda: scatter(
        SC_URB, "架空の12か国の都市人口率と第一次産業就業者割合",
        "都市人口率（％）", "第一次産業就業者割合（％）", NOTE_FAKE, 100.0, 60.0),
    "B14_choro.svg": choropleth,
    "B15_prop.svg": propsymbol,
}
