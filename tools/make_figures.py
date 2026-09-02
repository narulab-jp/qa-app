# -*- coding: utf-8 -*-
"""図表編の図版（SVG）を作る。

  ・教科書・資料集・過去問の図は一切写していない。
    地形は下の height() で定義した計算式から等高線を起こしており、
    グラフも下に書いた数値からこのスクリプトが目盛りごと描いている。
  ・白黒印刷で判別できるよう、色ではなく線の太さ・線種・ハッチング・
    記号で区別する。
  ・架空の数値を使う図には、図の中に「架空」である旨を必ず書く。
"""
import io
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures")
FONT = "'Hiragino Sans','Hiragino Kaku Gothic ProN','Yu Gothic','Meiryo',sans-serif"


def n(v):
    """座標を短く丸める（ファイルを小さく保つため）"""
    return ("%.2f" % v).rstrip("0").rstrip(".")


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def txt(x, y, s, size=13, anchor="start", weight="normal", extra=""):
    return ('<text x="%s" y="%s" font-size="%d" text-anchor="%s" '
            'font-weight="%s" font-family="%s" fill="#000"%s>%s</text>'
            % (n(x), n(y), size, anchor, weight, FONT,
               (" " + extra) if extra else "", esc(s)))


# ======================================================================
# 冊A　模式地形図
# ======================================================================
# 図の枠は x 40〜620、y 30〜450。縮尺は 1000m ＝ 145 単位（＝2万5千分の1の
# 地形図で 4cm にあたる）。したがって図全体は東西およそ 4000m を表す。
MX0, MX1, MY0, MY1 = 40.0, 620.0, 30.0, 450.0
UNIT_1000M = 145.0          # 1000m にあたる図上の長さ
APEX = (300.0, 240.0)       # 谷口（扇状地の要）


def smax(a, b, k):
    """なめらかな max。単純な max だと面の境目に折れ目ができるため。"""
    m = a if a > b else b
    return m + k * math.log(math.exp((a - m) / k) + math.exp((b - m) / k))


def height(x, y):
    """訓練用に作った模式的な地形の標高（m）。実在の場所ではない。

    ・西に山地があり、東へ下る
    ・y=240 付近に東西方向の谷、y=120 付近に尾根
    ・谷口(300,240) から東へ扇状地が半円状に広がる
    ・その東は平野
    3つの面（山地・扇状地・平野）をなめらかに重ねて作る。
    """
    plain = 34.0 - 0.010 * max(0.0, x - APEX[0])           # 平野面
    m = (128.0
         - 0.44 * (x - MX0)
         - 52.0 * math.exp(-((y - 240.0) / 62.0) ** 2)     # 谷
         + 32.0 * math.exp(-((y - 120.0) / 55.0) ** 2)     # 尾根
         - 15.0 * math.exp(-((y - 405.0) / 85.0) ** 2))    # 南側の低み
    if x > APEX[0]:
        m *= math.exp(-((x - APEX[0]) / 50.0) ** 2)        # 東へ向けて山地を消す
    mount = plain + m
    dx = (x - APEX[0]) if x >= APEX[0] else (APEX[0] - x) * 3.0   # 西側へは伸びない
    fan = plain + 28.0 - 0.16 * math.hypot(dx, (y - APEX[1]) * 0.95)
    return smax(smax(mount, fan, 5.0), plain, 4.0)


def marching(fn, x0, x1, y0, y1, step, level):
    """等値線を求める（マーチングスクエア法）。線分の並びを返す。"""
    nx = int(round((x1 - x0) / step)) + 1
    ny = int(round((y1 - y0) / step)) + 1
    g = [[fn(x0 + i * step, y0 + j * step) for j in range(ny)] for i in range(nx)]
    segs = []
    for i in range(nx - 1):
        for j in range(ny - 1):
            xa, ya = x0 + i * step, y0 + j * step
            xb, yb = xa + step, ya + step
            v = [g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]]
            pts = [(xa, ya), (xb, ya), (xb, yb), (xa, yb)]
            cross = []
            for k in range(4):
                a, b = v[k], v[(k + 1) % 4]
                if (a - level) * (b - level) < 0:
                    t = (level - a) / (b - a)
                    p, q = pts[k], pts[(k + 1) % 4]
                    cross.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
            if len(cross) == 2:
                segs.append((cross[0], cross[1]))
            elif len(cross) == 4:                 # 鞍部。近い順に2組つなぐ
                segs.append((cross[0], cross[1]))
                segs.append((cross[2], cross[3]))
    return segs


def join(segs):
    """線分をつなげて折れ線にする。"""
    def key(p):
        return (round(p[0], 2), round(p[1], 2))
    ends = {}
    for idx, (a, b) in enumerate(segs):
        ends.setdefault(key(a), []).append((idx, 0))
        ends.setdefault(key(b), []).append((idx, 1))
    used = [False] * len(segs)
    out = []
    for idx in range(len(segs)):
        if used[idx]:
            continue
        used[idx] = True
        line = [segs[idx][0], segs[idx][1]]
        for side in (0, 1):
            while True:
                tip = line[0] if side == 0 else line[-1]
                nxt = None
                for (j, e) in ends.get(key(tip), []):
                    if not used[j]:
                        nxt = (j, e)
                        break
                if not nxt:
                    break
                j, e = nxt
                used[j] = True
                p = segs[j][1 - e]
                if side == 0:
                    line.insert(0, p)
                else:
                    line.append(p)
        out.append(line)
    return out


def poly(line, width, dash=""):
    d = " ".join("%s,%s" % (n(p[0]), n(p[1])) for p in line)
    return ('<polyline points="%s" fill="none" stroke="#000" stroke-width="%s"%s/>'
            % (d, width, (' stroke-dasharray="%s"' % dash) if dash else ""))


def sym_ta(x, y):
    """田（２本の短い縦線）"""
    return ('<path d="M%s %s v7 M%s %s v7" stroke="#000" stroke-width="1.1" fill="none"/>'
            % (n(x - 2.5), n(y - 3.5), n(x + 2.5), n(y - 3.5)))


def sym_hatake(x, y):
    """畑（Ｖ字）"""
    return ('<path d="M%s %s l3 6 l3 -6" stroke="#000" stroke-width="1.1" fill="none"/>'
            % (n(x - 3), n(y - 3)))


def sym_kaju(x, y):
    """果樹園（丸と短い軸）"""
    return ('<circle cx="%s" cy="%s" r="2.6" fill="none" stroke="#000" stroke-width="1.1"/>'
            '<path d="M%s %s v3" stroke="#000" stroke-width="1.1"/>'
            % (n(x), n(y - 2), n(x), n(y + 0.6)))


def sym_shinyou(x, y):
    """針葉樹林（三角の樹冠）。果樹園の丸と紛れないよう、山地はこれで統一する。"""
    return ('<path d="M%s %s l3.6 7 h-7.2 z" fill="none" stroke="#000" stroke-width="1.2"/>'
            '<path d="M%s %s v3" stroke="#000" stroke-width="1.2"/>'
            % (n(x), n(y - 6.5), n(x), n(y + 0.5)))


def sym_school(x, y):
    return ('<circle cx="%s" cy="%s" r="6.5" fill="#fff" stroke="#000" stroke-width="1.2"/>'
            % (n(x), n(y)) + txt(x, y + 4, "文", 10, "middle"))


def sym_post(x, y):
    return ('<circle cx="%s" cy="%s" r="6.5" fill="#fff" stroke="#000" stroke-width="1.2"/>'
            % (n(x), n(y)) + txt(x, y + 4, "〒", 9, "middle"))


def sym_torii(x, y):
    """神社（鳥居）"""
    return ('<path d="M%s %s h11 M%s %s h9 M%s %s v8 M%s %s v8" '
            'stroke="#000" stroke-width="1.3" fill="none"/>'
            % (n(x - 5.5), n(y - 4), n(x - 4.5), n(y - 1),
               n(x - 3.5), n(y - 4), n(x + 3.5), n(y - 4)))


def sym_sankaku(x, y, h):
    """三角点（標高つき）"""
    return ('<path d="M%s %s l4.5 8 h-9 z" fill="none" stroke="#000" stroke-width="1.2"/>'
            % (n(x), n(y - 5)) + txt(x + 7, y + 4, h, 11))


def map_A01():
    W, H = 720, 620
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" '
         'height="%d" role="img" aria-label="訓練用の模式地形図">' % (W, H, W, H)]
    s.append('<rect width="%d" height="%d" fill="#fff"/>' % (W, H))

    # ---- 等高線 ----
    body = []
    labels = []            # 計曲線に入れる標高値の位置
    lv = 40
    while lv <= 190:
        thick = (lv % 50 == 0)
        lines = [ln for ln in join(marching(height, MX0, MX1, MY0, MY1, 4.0, float(lv)))
                 if len(ln) >= 3]
        for line in lines:
            body.append(poly(line, "1.6" if thick else "0.7"))
        if thick and lines:
            # いちばん長い線の上に、実際に線が通る点を選んで標高値を置く
            lines.sort(key=len, reverse=True)
            for ln in lines[:2]:
                for frac in (0.28, 0.72):
                    p = ln[int(len(ln) * frac)]
                    if MX0 + 24 < p[0] < MX1 - 30 and MY0 + 20 < p[1] < MY1 - 16:
                        labels.append((p[0], p[1], str(lv)))
                        break
        lv += 10
    s.append('<g clip-path="url(#frame)">')
    s.extend(body)

    # ---- 河川（二重線。流れる向きの矢印は入れない）----
    riv = [(MX0, 243), (110, 241), (180, 240), (250, 239), (APEX[0], 240),
           (350, 243), (405, 248), (460, 252), (520, 256), (575, 258), (MX1, 259)]
    for off in (-2.2, 2.2):
        s.append(poly([(p[0], p[1] + off) for p in riv], "1.2"))

    # ---- 土地利用の記号 ----
    # 扇状地の上：果樹園と畑
    for i in range(7):
        for j in range(4):
            x = 322 + i * 23
            y = 196 + j * 24
            if math.hypot(x - APEX[0], (y - APEX[1]) * 0.95) > 150:
                continue
            if abs(y - 250) < 12:
                continue                      # 川筋は空ける
            s.append(sym_kaju(x, y) if (i + j) % 2 == 0 else sym_hatake(x, y))
    # 東の平野：水田
    for i in range(4):
        for j in range(5):
            x = 508 + i * 26
            y = 180 + j * 30
            if abs(y - 254) < 14:
                continue
            s.append(sym_ta(x, y))
    for i in range(4):
        for j in range(3):
            s.append(sym_ta(500 + i * 26, 330 + j * 28))
    # 山地：樹林
    for (x, y) in [(70, 90), (110, 66), (152, 100), (95, 150), (140, 168),
                   (75, 200), (120, 212), (188, 88), (218, 130), (188, 175),
                   (80, 300), (125, 322), (170, 302), (215, 332), (95, 382),
                   (150, 396), (205, 382), (246, 200), (252, 330), (60, 288)]:
        s.append(sym_shinyou(x, y))

    # ---- 建物・基準点 ----
    s.append(sym_school(352, 300))
    s.append(sym_torii(430, 196))
    s.append(sym_post(470, 300))
    s.append(sym_sankaku(112, 122, "176"))
    s.append(sym_sankaku(556, 190, "31"))

    # ---- 計曲線の標高値（実際に線が通る点に置く）----
    for (x, y, v) in labels:
        s.append('<rect x="%s" y="%s" width="26" height="14" fill="#fff"/>'
                 % (n(x - 13), n(y - 10)))
        s.append(txt(x, y, v, 11, "middle", "bold"))
    s.append("</g>")

    # ---- 記号 P Q R X Y ----
    def mark(x, y, lab, r=8):
        return ('<circle cx="%s" cy="%s" r="%d" fill="#fff" stroke="#000" '
                'stroke-width="1.8"/>' % (n(x), n(y), r)) + \
               txt(x, y + 4.5, lab, 12, "middle", "bold")
    px, py = 350.0, 330.0
    qx, qy = px + UNIT_1000M, 330.0        # 図上で 1000m ＝ 4cm 分だけ離す
    s.append('<path d="M%s %s L%s %s" stroke="#000" stroke-width="1" '
             'stroke-dasharray="5 3"/>' % (n(px), n(py), n(qx), n(qy)))
    s.append(mark(px, py, "P"))
    s.append(mark(qx, qy, "Q"))
    s.append(mark(395, 175, "R"))
    s.append(mark(170, 240, "X"))
    s.append(mark(170, 120, "Y"))

    # ---- 枠 ----
    s.append('<defs><clipPath id="frame"><rect x="%s" y="%s" width="%s" height="%s"/>'
             "</clipPath></defs>" % (n(MX0), n(MY0), n(MX1 - MX0), n(MY1 - MY0)))
    s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="#000" '
             'stroke-width="1.6"/>' % (n(MX0), n(MY0), n(MX1 - MX0), n(MY1 - MY0)))

    # ---- 方位記号 ----
    s.append('<g><path d="M655 60 L648 100 L655 92 L662 100 Z" fill="#000"/>'
             '<path d="M655 60 v40" stroke="#000" stroke-width="1"/>'
             + txt(655, 52, "N", 14, "middle", "bold") + "</g>")

    # ---- 縮尺バー ----
    bx, by = 430.0, 478.0
    s.append('<rect x="%s" y="%s" width="%s" height="9" fill="#fff" stroke="#000" '
             'stroke-width="1.2"/>' % (n(bx), n(by), n(UNIT_1000M)))
    s.append('<rect x="%s" y="%s" width="%s" height="9" fill="#000"/>'
             % (n(bx), n(by), n(UNIT_1000M / 2)))
    s.append(txt(bx, by + 24, "0", 11, "middle"))
    s.append(txt(bx + UNIT_1000M / 2, by + 24, "500", 11, "middle"))
    s.append(txt(bx + UNIT_1000M, by + 24, "1000m", 11, "middle"))
    s.append(txt(bx, by - 7, "2万5千分の1", 12))

    # ---- 凡例 ----
    lx, ly = 46.0, 474.0
    s.append('<rect x="%s" y="%s" width="330" height="122" fill="none" stroke="#000" '
             'stroke-width="1"/>' % (n(lx), n(ly)))
    s.append(txt(lx + 10, ly + 18, "凡例", 12, "start", "bold"))
    items = [
        ("contour_thin", "主曲線（10mごと）"),
        ("contour_thick", "計曲線（50mごと）"),
        ("river", "河川"),
        ("ta", "田"),
        ("hatake", "畑"),
        ("kaju", "果樹園"),
        ("ki", "針葉樹林"),
        ("bldg", "建物・神社など"),
    ]
    for k, (kind, lab) in enumerate(items):
        cx = lx + 22 + (k % 2) * 165
        cy = ly + 40 + (k // 2) * 21
        if kind == "contour_thin":
            s.append('<path d="M%s %s h22" stroke="#000" stroke-width="0.7"/>'
                     % (n(cx - 11), n(cy - 3)))
        elif kind == "contour_thick":
            s.append('<path d="M%s %s h22" stroke="#000" stroke-width="1.6"/>'
                     % (n(cx - 11), n(cy - 3)))
        elif kind == "river":
            s.append('<path d="M%s %s h22 M%s %s h22" stroke="#000" stroke-width="1.2"/>'
                     % (n(cx - 11), n(cy - 5), n(cx - 11), n(cy - 1)))
        elif kind == "ta":
            s.append(sym_ta(cx, cy - 1))
        elif kind == "hatake":
            s.append(sym_hatake(cx, cy - 1))
        elif kind == "kaju":
            s.append(sym_kaju(cx, cy - 1))
        elif kind == "ki":
            s.append(sym_shinyou(cx, cy - 1))
        else:
            s.append(sym_torii(cx, cy - 1))
        s.append(txt(cx + 18, cy, lab, 11))

    s.append(txt(MX0, 610, "※ 訓練用に作成した模式地形図であり、実在の地域ではない。", 11))
    s.append("</svg>")
    return "\n".join(s)


# ======================================================================
# 冊B　雨温図（架空の4地点）
# ======================================================================
CLIMO = [
    ("ア", [26, 26, 27, 27, 27, 26, 26, 26, 26, 26, 26, 26],
     [230, 220, 240, 250, 230, 180, 160, 170, 190, 220, 240, 250]),
    ("イ", [8, 9, 11, 15, 19, 23, 26, 26, 22, 17, 12, 9],
     [80, 70, 60, 50, 30, 10, 5, 8, 35, 80, 95, 90]),
    ("ウ", [-15, -13, -6, 3, 11, 17, 20, 18, 12, 4, -4, -12],
     [25, 20, 25, 35, 50, 70, 85, 80, 60, 45, 35, 30]),
    ("エ", [25, 25, 23, 19, 15, 12, 12, 14, 17, 20, 22, 24],
     [110, 105, 115, 90, 80, 60, 55, 60, 75, 95, 105, 115]),
]
T_MIN, T_MAX = -20.0, 30.0
P_MAX = 300.0


def climo_panel(ox, oy, w, h, name, temp, prec):
    """雨温図を1枚描く。降水量は棒（左目盛）、気温は折れ線（右目盛）。"""
    s = []
    s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="#000" '
             'stroke-width="1.2"/>' % (n(ox), n(oy), n(w), n(h)))
    s.append(txt(ox + 8, oy + 20, "地点" + name, 15, "start", "bold"))
    s.append(txt(ox + 10, oy + 40, "降水量(mm)", 11))
    s.append(txt(ox + w - 10, oy + 40, "気温(℃)", 11, "end"))
    px0, py0 = ox + 44.0, oy + h - 30.0        # 目盛原点
    pw, ph = w - 88.0, h - 78.0                # 上に見出しの行をあける

    def yp(mm):
        return py0 - ph * (mm / P_MAX)

    def yt(c):
        return py0 - ph * ((c - T_MIN) / (T_MAX - T_MIN))

    # 目盛線（降水量 100mm ごと）
    for mm in (100, 200, 300):
        s.append('<path d="M%s %s h%s" stroke="#000" stroke-width="0.4" '
                 'stroke-dasharray="3 3"/>' % (n(px0), n(yp(mm)), n(pw)))
        s.append(txt(px0 - 6, yp(mm) + 4, str(mm), 10, "end"))
    # 気温の目盛（右）
    for c in (-20, -10, 0, 10, 20, 30):
        s.append(txt(px0 + pw + 6, yt(c) + 4, str(c), 10, "start"))
    s.append('<path d="M%s %s v%s M%s %s v%s M%s %s h%s" stroke="#000" '
             'stroke-width="1.1" fill="none"/>'
             % (n(px0), n(py0 - ph), n(ph), n(px0 + pw), n(py0 - ph), n(ph),
                n(px0), n(py0), n(pw)))
    # 0℃の線
    s.append('<path d="M%s %s h%s" stroke="#000" stroke-width="0.8" '
             'stroke-dasharray="6 3"/>' % (n(px0), n(yt(0)), n(pw)))
    s.append(txt(px0 + pw + 6, yt(0) - 6, "0℃", 9, "start"))
    # 降水量の棒
    bw = pw / 12.0
    for i, mm in enumerate(prec):
        x = px0 + i * bw + bw * 0.18
        s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#000"/>'
                 % (n(x), n(yp(mm)), n(bw * 0.64), n(py0 - yp(mm))))
    # 気温の折れ線
    pts = [(px0 + (i + 0.5) * bw, yt(c)) for i, c in enumerate(temp)]
    s.append(poly(pts, "2"))
    for (x, y) in pts:
        s.append('<circle cx="%s" cy="%s" r="2.6" fill="#fff" stroke="#000" '
                 'stroke-width="1.4"/>' % (n(x), n(y)))
    # 月の目盛
    for i in (0, 3, 6, 9, 11):
        s.append(txt(px0 + (i + 0.5) * bw, py0 + 14, str(i + 1), 10, "middle"))
    s.append(txt(px0 + pw / 2, py0 + 27, "月", 10, "middle"))
    return "\n".join(s)


def climo_B01():
    W, H = 720, 660
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" '
         'height="%d" role="img" aria-label="架空の4地点の雨温図">' % (W, H, W, H)]
    s.append('<rect width="%d" height="%d" fill="#fff"/>' % (W, H))
    s.append(txt(20, 26, "架空の4地点ア〜エの雨温図", 16, "start", "bold"))
    pw, ph = 330.0, 280.0
    for k, (name, t, p) in enumerate(CLIMO):
        ox = 20 + (k % 2) * (pw + 20)
        oy = 44 + (k // 2) * (ph + 24)
        s.append(climo_panel(ox, oy, pw, ph, name, t, p))
    s.append(txt(20, 648,
                 "※ 訓練用に作成した架空の数値であり、実在の観測地点ではない。", 11))
    s.append("</svg>")
    return "\n".join(s)


# ======================================================================
# 冊C　電源構成の帯グラフ ＋ 統計表（架空の4か国）
# ======================================================================
ENERGY = [
    ("A", [("水力", 85), ("火力", 10), ("原子力", 0), ("その他", 5)]),
    ("B", [("水力", 10), ("火力", 20), ("原子力", 65), ("その他", 5)]),
    ("C", [("水力", 0), ("火力", 95), ("原子力", 0), ("その他", 5)]),
    ("D", [("水力", 20), ("火力", 70), ("原子力", 0), ("その他", 10)]),
]
STAT = [
    ("A", "78,000", "2", "起伏が大きく、年降水量が多い"),
    ("B", "42,000", "3", "石炭・石油・天然ガスにとぼしい"),
    ("C", "25,000", "2", "国土の大半が砂漠。原油の輸出が経済の中心"),
    ("D", "2,400", "38", "石炭を産出する。人口の多くが農村部に住む"),
]
FILL = {"水力": "url(#hHydro)", "火力": "#000",
        "原子力": "url(#hNuke)", "その他": "#fff"}


def bars_C01():
    W, H = 720, 400
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" '
         'height="%d" role="img" aria-label="架空の4か国の電源構成">' % (W, H, W, H)]
    s.append("""<defs>
  <pattern id="hHydro" width="8" height="8" patternUnits="userSpaceOnUse">
    <rect width="8" height="8" fill="#fff"/>
    <path d="M0 8 L8 0" stroke="#000" stroke-width="1.4"/>
  </pattern>
  <pattern id="hNuke" width="8" height="8" patternUnits="userSpaceOnUse">
    <rect width="8" height="8" fill="#fff"/>
    <circle cx="2" cy="2" r="1.3" fill="#000"/>
    <circle cx="6" cy="6" r="1.3" fill="#000"/>
  </pattern>
</defs>""")
    s.append('<rect width="%d" height="%d" fill="#fff"/>' % (W, H))
    s.append(txt(20, 26, "資料1　架空の4か国の発電電力量の内訳（％）", 16, "start", "bold"))
    bx, bw = 90.0, 540.0
    for k, (name, parts) in enumerate(ENERGY):
        by = 58.0 + k * 62.0
        s.append(txt(bx - 14, by + 22, name + "国", 14, "end", "bold"))
        x = bx
        for (lab, v) in parts:
            if v <= 0:
                continue
            w = bw * v / 100.0
            s.append('<rect x="%s" y="%s" width="%s" height="32" fill="%s" '
                     'stroke="#000" stroke-width="1.1"/>'
                     % (n(x), n(by), n(w), FILL[lab]))
            if w >= 40:
                s.append('<rect x="%s" y="%s" width="30" height="15" fill="#fff" '
                         'opacity="0.85"/>' % (n(x + w / 2 - 15), n(by + 8)))
                s.append(txt(x + w / 2, by + 20, str(v), 12, "middle", "bold"))
            x += w
        s.append(txt(bx, by + 48, "0", 10, "middle"))
        s.append(txt(bx + bw, by + 48, "100", 10, "middle"))
    # 凡例
    ly = 316.0
    s.append('<rect x="%s" y="%s" width="600" height="42" fill="none" stroke="#000" '
             'stroke-width="1"/>' % (n(60), n(ly)))
    for k, lab in enumerate(["水力", "火力", "原子力", "その他"]):
        cx = 80.0 + k * 150.0
        s.append('<rect x="%s" y="%s" width="26" height="16" fill="%s" stroke="#000" '
                 'stroke-width="1.1"/>' % (n(cx), n(ly + 13), FILL[lab]))
        s.append(txt(cx + 33, ly + 26, lab, 13))
    s.append(txt(20, 386,
                 "※ 訓練用に作成した架空の国と数値であり、実在の国ではない。", 11))
    s.append("</svg>")
    return "\n".join(s)


def table_C01():
    W, H = 720, 320
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" '
         'height="%d" role="img" aria-label="架空の4か国の統計表">' % (W, H, W, H)]
    s.append('<rect width="%d" height="%d" fill="#fff"/>' % (W, H))
    s.append(txt(20, 26, "資料2　架空の4か国の一人当たりGNIと国土のようす", 16,
                 "start", "bold"))
    cols = [20.0, 90.0, 235.0, 385.0, 700.0]
    head = ["国", "一人当たりGNI\n（ドル）", "就業者に占める\n第一次産業の割合(%)",
            "国土や資源のようす"]
    top, rh = 46.0, 46.0
    # 見出し
    s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="#000" '
             'stroke-width="1.4"/>' % (n(cols[0]), n(top), n(cols[4] - cols[0]), n(rh)))
    for i, hd in enumerate(head):
        parts = hd.split("\n")
        for j, p in enumerate(parts):
            y = top + (rh / 2) + (j - (len(parts) - 1) / 2.0) * 15 + 5
            s.append(txt((cols[i] + cols[i + 1]) / 2, y, p, 12, "middle", "bold"))
    for k, row in enumerate(STAT):
        ry = top + rh + k * rh
        s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="#000" '
                 'stroke-width="1"/>' % (n(cols[0]), n(ry), n(cols[4] - cols[0]), n(rh)))
        vals = [row[0] + "国", row[1], row[2], row[3]]
        for i, v in enumerate(vals):
            if i == 3:
                s.append(txt(cols[i] + 12, ry + rh / 2 + 5, v, 12))
            else:
                s.append(txt((cols[i] + cols[i + 1]) / 2, ry + rh / 2 + 5, v, 13,
                             "middle", "bold" if i == 0 else "normal"))
    for c in cols[1:4]:
        s.append('<path d="M%s %s v%s" stroke="#000" stroke-width="1"/>'
                 % (n(c), n(top), n(rh * 5)))
    s.append(txt(20, 302,
                 "※ 訓練用に作成した架空の国と数値であり、実在の国ではない。", 11))
    s.append("</svg>")
    return "\n".join(s)


# ======================================================================
FIGURES = {
    "A01_map.svg": map_A01,
    "B01_climo.svg": climo_B01,
    "C01_energy.svg": bars_C01,
    "C01_table.svg": table_C01,
}


def main():
    if not os.path.isdir(FIG):
        os.makedirs(FIG)
    for name, fn in sorted(FIGURES.items()):
        body = fn()
        p = os.path.join(FIG, name)
        io.open(p, "w", encoding="utf-8", newline="\n").write(body + "\n")
        print("  %-18s %7d bytes" % (name, os.path.getsize(p)))
    print("図版 %d 枚を作成" % len(FIGURES))


if __name__ == "__main__":
    main()
