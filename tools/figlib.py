# -*- coding: utf-8 -*-
"""図版を描くための共通部品。

  ・教科書・資料集・過去問の図は一切写していない。すべてここの計算で描く。
  ・白黒印刷で判別できるよう、色ではなく線種・ハッチング・記号で区別する。
  ・架空の数値を使う図には、図の中に「架空」である旨を必ず書く。

  ★線の太さについて（2026-09-05）
    図は 720 単位の幅で描き、紙の上では 78mm〜169mm と、図によって
    2倍以上の開きがある大きさで置かれる。太さを単位で決めていたため、
    小さく置かれる図では 1.1 単位＝0.12mm しかなく、白黒で印刷すると
    等高線や境界線が消えていた（実測で全体の75%が0.25mm未満）。

    そこで、太さを「単位」ではなく「紙の上の mm」で決める。
      主要な線（等高線・境界線・海岸線・枠・軸）  0.35mm 以上
      補助線・目盛・ハッチング                    0.25mm 以上
    図ごとに「いちばん小さく置かれるときの mm/単位」を set_target() で
    渡し、svg() を組み立てるときに、その図に必要な単位数へ引き上げる。
    もともと太い線はそのまま。細い線だけが下限まで上がる。
"""
import math
import re

# ---- 紙に出たときの太さ（mm） ----
MM_MAIN = 0.35        # ふつうの線（太さ1.1で描いてある線）を、この太さにする
MM_SUB = 0.25         # 何があってもこれより細くしない（補助線・目盛・網かけ）
BASE_UNITS = 1.1      # この教材でいちばん多く使っている「ふつうの線」の太さ
MAX_K = 2.4           # 倍率の上限（際限なく太らせない）

# その図が、いちばん小さく置かれるときの 1単位あたりの mm。
# set_target() で図ごとに入れ替える。既定は安全側（小さめ）の値。
_UNIT_MM = [0.109]


def set_target(unit_mm):
    """この図の「1単位あたり何mmで刷られるか」を設定する。"""
    _UNIT_MM[0] = float(unit_mm) if unit_mm else 0.109


def unit_mm():
    return _UNIT_MM[0]


def k_scale():
    """この図の線を何倍にするか。

      ★一律の下限にしないのは、主曲線と計曲線のように
        「細い線」「太い線」で意味を分けている図があるため。
        下限だけで持ち上げると、両方が同じ太さになって区別が消える。
        倍率でそろえて持ち上げ、そのうえで下限を当てる。
    """
    return min(MAX_K, MM_MAIN / (BASE_UNITS * _UNIT_MM[0]))


def scale_units(old):
    """紙の上で読める太さ（単位）にする。細くはしない。

      小数2桁で書き出すので、切り上げておく。切り捨てると
      0.25mm のつもりが 0.2494mm になり、下限を割ってしまう。
    """
    v = max(old, old * k_scale(), MM_SUB / _UNIT_MM[0])
    return math.ceil(v * 100.0 - 1e-9) / 100.0

FONT = ("'Hiragino Sans','Hiragino Kaku Gothic ProN','Yu Gothic',"
        "'Meiryo',sans-serif")
NOTE_MAP = "※ 訓練用に作成した模式地形図であり、実在の地域ではない。"
NOTE_FAKE = "※ 訓練用に作成した架空の数値であり、実在の地点・国ではない。"

# 白黒で見分けるためのハッチング。色は使わない。
PATTERNS = """<defs>
 <pattern id="pDiag" width="8" height="8" patternUnits="userSpaceOnUse">
  <rect width="8" height="8" fill="#fff"/><path d="M0 8 L8 0" stroke="#000" stroke-width="1.4"/></pattern>
 <pattern id="pDiag2" width="8" height="8" patternUnits="userSpaceOnUse">
  <rect width="8" height="8" fill="#fff"/><path d="M0 0 L8 8" stroke="#000" stroke-width="1.4"/></pattern>
 <pattern id="pDot" width="8" height="8" patternUnits="userSpaceOnUse">
  <rect width="8" height="8" fill="#fff"/><circle cx="2" cy="2" r="1.3" fill="#000"/>
  <circle cx="6" cy="6" r="1.3" fill="#000"/></pattern>
 <pattern id="pDotFine" width="5" height="5" patternUnits="userSpaceOnUse">
  <rect width="5" height="5" fill="#fff"/><circle cx="1.4" cy="1.4" r="0.9" fill="#000"/></pattern>
 <pattern id="pGrid" width="8" height="8" patternUnits="userSpaceOnUse">
  <rect width="8" height="8" fill="#fff"/>
  <path d="M0 4 H8 M4 0 V8" stroke="#000" stroke-width="0.9"/></pattern>
 <pattern id="pWave" width="10" height="8" patternUnits="userSpaceOnUse">
  <rect width="10" height="8" fill="#fff"/>
  <path d="M0 5 q2.5 -3 5 0 t5 0" stroke="#000" stroke-width="0.9" fill="none"/></pattern>
</defs>"""

# 階級区分図で使う濃さの段階（薄い→濃い）。すべて無彩色。
STEPS = ["#FFFFFF", "url(#pDotFine)", "url(#pDiag)", "url(#pGrid)", "#000000"]
STEP_FG = ["#000", "#000", "#000", "#000", "#fff"]


def n(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def txt(x, y, s, size=13, anchor="start", weight="normal", fill="#000", rot=None):
    r = ""
    if rot is not None:
        r = ' transform="rotate(%s %s %s)"' % (n(rot), n(x), n(y))
    return ('<text x="%s" y="%s" font-size="%s" text-anchor="%s" font-weight="%s" '
            'font-family="%s" fill="%s"%s>%s</text>'
            % (n(x), n(y), n(size), anchor, weight, FONT, fill, r, esc(s)))


HATCH_STEP = {"diag": 7.0, "diag2": 7.0, "diagfine": 3.5, "dot": 8.0,
              "dotfine": 5.0, "grid": 8.0, "wave": 10.0}
_cid = [0]


def _hw():
    """網かけの線の太さ。本文の線より細くしておく（0.25mm）。
       太くすると塗りつぶしに見えて、階級の区別がつかなくなる。"""
    return max(1.1, MM_SUB / _UNIT_MM[0])


def _hstep(kind):
    """線を太くしたぶん、間隔も広げる。広げないと塗りつぶしに見えて、
       斜線・格子・点の区別がつかなくなる。"""
    return HATCH_STEP[kind] * _hw() / 1.1


def _hatch_lines(kind, x0, y0, w, h):
    """網かけを線と点で描く。パターン塗りを使うとPDFで画像に変換されて
       ファイルが巨大になるため、はじめから線として描いておく。

       ここで出す線は、太さも間隔もこの関数で決めきる。
       svg() の引き上げが二重にかからないよう data-h="1" を付ける。"""
    out = []
    st = _hstep(kind)
    hw = _hw()
    def hl(x1, y1, x2, y2):
        return ('<path d="M%s %s L%s %s" stroke="#000" stroke-width="%s" '
                'fill="none" data-h="1"/>'
                % (n(x1), n(y1), n(x2), n(y2), n(hw)))

    if kind in ("diag", "diag2", "diagfine"):
        i, m = 0, int((w + h) / st) + 2
        while i < m:
            if kind != "diag2":
                out.append(hl(x0 - h + i * st, y0 + h, x0 + i * st, y0))
            else:
                out.append(hl(x0 + i * st - h, y0, x0 + i * st, y0 + h))
            i += 1
    elif kind in ("dot", "dotfine"):
        # 点は太さではなく大きさ。線と同じだけ大きくして、消えないようにする。
        r = (1.3 if kind == "dot" else 0.85) * hw / 1.1
        yy, k = y0 + st / 2, 0
        while yy < y0 + h + st:
            xx = x0 + (st / 2 if k % 2 else 0)
            while xx < x0 + w + st:
                out.append('<circle cx="%s" cy="%s" r="%s" fill="#000" '
                           'stroke="none" data-h="1"/>' % (n(xx), n(yy), n(r)))
                xx += st
            yy += st
            k += 1
    elif kind == "grid":
        yy = y0 + st / 2
        while yy < y0 + h + st:
            out.append(hl(x0, yy, x0 + w, yy))
            yy += st
        xx = x0 + st / 2
        while xx < x0 + w + st:
            out.append(hl(xx, y0, xx, y0 + h))
            xx += st
    elif kind == "wave":
        yy = y0 + 5
        while yy < y0 + h + st:
            d = ["M%s %s" % (n(x0), n(yy))]
            xx = x0
            while xx < x0 + w:
                d.append("q%s -3 %s 0" % (n(st / 4), n(st / 2)))
                d.append("t%s 0" % n(st / 2))
                xx += st
            out.append('<path d="%s" stroke="#000" stroke-width="%s" '
                       'fill="none" data-h="1"/>' % (" ".join(d), n(hw)))
            yy += st * 0.8
    return "".join(out)


def _hatched(shape, kind, bbox, stroke_w):
    """shape は塗りなしの図形タグ。網かけをクリップして重ねる。"""
    _cid[0] += 1
    cid = "hc%d" % _cid[0]
    x0, y0, w, h = bbox
    return ('<defs><clipPath id="%s">%s</clipPath></defs>'
            '%s<g clip-path="url(#%s)">%s</g>%s'
            % (cid, shape % ('fill="#fff" stroke="none"'),
               shape % ('fill="#fff" stroke="none"'), cid,
               _hatch_lines(kind, x0, y0, w, h),
               shape % ('fill="none" stroke="#000" stroke-width="%s"' % n(stroke_w))))


def poly(pts, width=1.0, dash="", fill="none", close=False):
    d = " ".join("%s,%s" % (n(p[0]), n(p[1])) for p in pts)
    tag = "polygon" if close else "polyline"
    if fill.startswith("hatch:"):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        shape = '<polygon points="' + d + '" %s/>'
        return _hatched(shape, fill[6:],
                        (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)), width)
    return ('<%s points="%s" fill="%s" stroke="#000" stroke-width="%s"%s/>'
            % (tag, d, fill, n(width), (' stroke-dasharray="%s"' % dash) if dash else ""))


def line(x1, y1, x2, y2, width=1.0, dash=""):
    return ('<path d="M%s %s L%s %s" stroke="#000" stroke-width="%s" fill="none"%s/>'
            % (n(x1), n(y1), n(x2), n(y2), n(width),
               (' stroke-dasharray="%s"' % dash) if dash else ""))


def rect(x, y, w, h, fill="none", width=1.0, dash=""):
    if fill.startswith("hatch:"):
        shape = ('<rect x="%s" y="%s" width="%s" height="%s" '
                 % (n(x), n(y), n(w), n(h))) + "%s/>"
        return _hatched(shape, fill[6:], (x, y, w, h), width)
    return ('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="#000" '
            'stroke-width="%s"%s/>' % (n(x), n(y), n(w), n(h), fill, n(width),
                                       (' stroke-dasharray="%s"' % dash) if dash else ""))


def circle(x, y, r, fill="none", width=1.0):
    if fill.startswith("hatch:"):
        shape = ('<circle cx="%s" cy="%s" r="%s" ' % (n(x), n(y), n(r))) + "%s/>"
        return _hatched(shape, fill[6:], (x - r, y - r, 2 * r, 2 * r), width)
    return ('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#000" stroke-width="%s"/>'
            % (n(x), n(y), n(r), fill, n(width)))


RE_TAG_SW = re.compile(r'<[^>]*stroke-width="[\d.]+"[^>]*>')
RE_SW = re.compile(r'stroke-width="([\d.]+)"')


def thicken(body):
    """図の中の線を、紙の上で下限を満たす太さまで引き上げる。

      ・細くはしない。太い線はそのまま
      ・data-h="1"（ハッチング）は、間隔と合わせて決めてあるので触らない
      ・stroke-width="0"（塗りだけの図形）は線ではないので触らない
    """
    def one(m):
        tag = m.group(0)
        if 'data-h="1"' in tag:
            return tag
        def rep(s):
            v = float(s.group(1))
            if v <= 0:
                return s.group(0)
            return 'stroke-width="%s"' % n(scale_units(v))
        return RE_SW.sub(rep, tag)
    return RE_TAG_SW.sub(one, body)


def svg(w, h, body, label):
    # 図の幅（単位）と、紙に置かれる幅から決まる mm/単位 は set_target() で
    # 渡してある。ここで線の太さを紙の上の下限までまとめて引き上げる。
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" '
            'height="%d" role="img" aria-label="%s">%s'
            '<rect width="%d" height="%d" fill="#fff"/>\n%s\n</svg>'
            % (w, h, w, h, esc(label), thicken(PATTERNS), w, h, thicken(body)))


def mark(x, y, lab, r=8.5):
    """P・Q・X・Y などの地点記号"""
    return (circle(x, y, r, "#fff", 1.8) + txt(x, y + 4.5, lab, 12.5, "middle", "bold"))


# ======================================================================
# 等値線（マーチングスクエア法）
# ======================================================================
def marching(fn, x0, x1, y0, y1, step, level):
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
            elif len(cross) == 4:
                segs.append((cross[0], cross[1]))
                segs.append((cross[2], cross[3]))
    return segs


def join(segs):
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
        ln = [segs[idx][0], segs[idx][1]]
        for side in (0, 1):
            while True:
                tip = ln[0] if side == 0 else ln[-1]
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
                    ln.insert(0, p)
                else:
                    ln.append(p)
        out.append(ln)
    return out


def smax(a, b, k):
    """なめらかな max。面の境目に折れ目を作らないため。"""
    m = a if a > b else b
    return m + k * math.log(math.exp((a - m) / k) + math.exp((b - m) / k))


def gauss(v, c, w):
    return math.exp(-((v - c) / w) ** 2)


# ======================================================================
# 地図記号
# ======================================================================
def sym_ta(x, y):
    """田"""
    return ('<path d="M%s %s v7 M%s %s v7" stroke="#000" stroke-width="1.1" fill="none"/>'
            % (n(x - 2.5), n(y - 3.5), n(x + 2.5), n(y - 3.5)))


def sym_hatake(x, y):
    """畑"""
    return ('<path d="M%s %s l3 6 l3 -6" stroke="#000" stroke-width="1.1" fill="none"/>'
            % (n(x - 3), n(y - 3)))


def sym_kaju(x, y):
    """果樹園"""
    return (circle(x, y - 2, 2.6, "none", 1.1) +
            '<path d="M%s %s v3" stroke="#000" stroke-width="1.1"/>' % (n(x), n(y + 0.6)))


def sym_kuwa(x, y):
    """茶畑（三つの点）"""
    return "".join(circle(x + dx, y + dy, 1.1, "#000", 0.6)
                   for (dx, dy) in [(0, -4), (-2.6, 0.6), (2.6, 0.6)])


def sym_shinyou(x, y):
    """針葉樹林"""
    return ('<path d="M%s %s l3.6 7 h-7.2 z" fill="none" stroke="#000" stroke-width="1.2"/>'
            '<path d="M%s %s v3" stroke="#000" stroke-width="1.2"/>'
            % (n(x), n(y - 6.5), n(x), n(y + 0.5)))


def sym_kouyou(x, y):
    """広葉樹林"""
    return (circle(x, y - 3, 3.4, "none", 1.2) +
            '<path d="M%s %s v3.4" stroke="#000" stroke-width="1.2"/>' % (n(x), n(y + 0.4)))


def sym_arechi(x, y):
    """荒地"""
    return ('<path d="M%s %s v5 M%s %s h5" stroke="#000" stroke-width="1" fill="none"/>'
            % (n(x), n(y - 2.5), n(x - 2.5), n(y + 2.5)))


def _glyph(x, y, ch, r=7.0, size=10.0):
    return circle(x, y, r, "#fff", 1.2) + txt(x, y + size * 0.36, ch, size, "middle")


def sym_school(x, y):
    return _glyph(x, y, "文")


def sym_hs(x, y):
    """高等学校"""
    return _glyph(x, y, "⊗", 7.0, 11)


def sym_post(x, y):
    return _glyph(x, y, "〒", 7.0, 9.5)


def sym_hosp(x, y):
    """病院"""
    return _glyph(x, y, "田", 7.0, 9.5)


def sym_koban(x, y):
    """交番"""
    return _glyph(x, y, "X", 6.0, 9)


def sym_city(x, y):
    """市役所"""
    return circle(x, y, 6.5, "#fff", 1.3) + circle(x, y, 3.2, "none", 1.1)


def sym_factory(x, y):
    """工場"""
    return _glyph(x, y, "✿", 7.0, 10)


def sym_torii(x, y):
    """神社"""
    return ('<path d="M%s %s h11 M%s %s h9 M%s %s v8 M%s %s v8" '
            'stroke="#000" stroke-width="1.3" fill="none"/>'
            % (n(x - 5.5), n(y - 4), n(x - 4.5), n(y - 1),
               n(x - 3.5), n(y - 4), n(x + 3.5), n(y - 4)))


def sym_tera(x, y):
    """寺院"""
    return _glyph(x, y, "卍", 7.0, 11)


def sym_sankaku(x, y, h=None):
    """三角点"""
    s = ('<path d="M%s %s l4.5 8 h-9 z" fill="none" stroke="#000" stroke-width="1.2"/>'
         % (n(x), n(y - 5)))
    if h:
        s += txt(x + 7, y + 4, h, 11)
    return s


def sym_suijun(x, y, h=None):
    """水準点"""
    s = rect(x - 4, y - 4, 8, 8, "none", 1.2) + circle(x, y, 1.2, "#000", 0.5)
    if h:
        s += txt(x + 7, y + 4, h, 11)
    return s


def sym_hakubutsu(x, y):
    """博物館"""
    return _glyph(x, y, "血", 7.0, 10)


def sym_roujin(x, y):
    """老人ホーム"""
    return _glyph(x, y, "介", 7.0, 10)


SYMBOLS = [
    ("田", sym_ta), ("畑", sym_hatake), ("果樹園", sym_kaju), ("茶畑", sym_kuwa),
    ("針葉樹林", sym_shinyou), ("広葉樹林", sym_kouyou), ("荒地", sym_arechi),
    ("小・中学校", sym_school), ("高等学校", sym_hs), ("郵便局", sym_post),
    ("病院", sym_hosp), ("交番", sym_koban), ("市役所", sym_city),
    ("工場", sym_factory), ("神社", sym_torii), ("寺院", sym_tera),
    ("三角点", sym_sankaku), ("水準点", sym_suijun),
    ("博物館", sym_hakubutsu), ("老人ホーム", sym_roujin),
]


# ======================================================================
# 目盛のある図の枠
# ======================================================================
def axes(x0, y0, w, h, xlab="", ylab="", ylab2=""):
    s = [line(x0, y0 - h, x0, y0, 1.1), line(x0, y0, x0 + w, y0, 1.1)]
    if xlab:
        s.append(txt(x0 + w / 2, y0 + 30, xlab, 11, "middle"))
    if ylab:
        s.append(txt(x0 - 34, y0 - h - 10, ylab, 11))
    if ylab2:
        s.append(txt(x0 + w + 6, y0 - h - 10, ylab2, 11))
    return "".join(s)


def caption(x, y, s, size=11):
    return txt(x, y, s, size)
