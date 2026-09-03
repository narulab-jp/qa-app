# -*- coding: utf-8 -*-
"""冊D　地域調査の資料（指示Hで足した分）の図版。

  冊Gの地域調査（盆地の集落／川ぞいの市街地）とは扱う技能を変えてある。
  こちらは「調べる前に資料を選ぶ」「主題図を自分でつくる」
  「集めた数値をまとめて示す」の3つで、図の読み取りそのものよりも
  資料の選び方・つくり方・言えることの限界に寄せている。

    セット1（D-1）調査の下調べ
      資料1 調査計画のメモと、手に入る資料の一覧
      資料2 現在の地形図（模式）
    セット2（D-2）主題図をつくる
      資料1 地区別の統計表
      資料2 同じ数値を2とおりの区切り方でぬり分けた階級区分図
    セット3（D-3）調べた結果をまとめる
      資料1 年次別の統計表と、1990年を100とした折れ線
      資料2 聞き取りの記録

  1セットの資料を2点にそろえ、横長（幅720・高さ340前後）にしてある。
  印刷したとき、資料2点で高さ160mm前後に収まり、同じページに設問が置ける。
  資料3点だと資料だけでページが埋まり、設問が次のページへ押し出されてしまう。

  つくるときの約束（冊Gと同じ）
    ・資料の中に答えを文章で書かない。示すのは事実（記号・位置・数値）だけ。
    ・凡例には区分の数値だけを書く。意味や理由は書かない。
    ・数値・地名はすべて架空で、図の中に明記する。
"""
from figlib import (NOTE_FAKE, NOTE_MAP, circle, line, poly, rect, svg, txt,
                    sym_ta, sym_kouyou, sym_factory, sym_school, sym_torii)

W, H = 720, 340
NOTE_TRAIN = "※ 訓練用に作成したものであり、実在の地域・事例ではない。"

# 4段階の濃さ（薄い→濃い）。色は使わない。
#   点の網かけは点を数千個描くことになりSVGが重くなるので、線だけで作る。
FILLS = ["none", "hatch:diag", "hatch:grid", "#000"]
FG = ["#000", "#000", "#000", "#fff"]


def panel(b, x, y, w, h, title):
    b.append(rect(x, y, w, h, "none", 1))
    b.append(txt(x + 12, y + 22, title, 12.5, "start", "bold"))


def grid_table(b, x, y, widths, rh, head, rows, fs=10.5, hfs=10.5):
    """罫線つきの表を、指定の位置に描く。"""
    cols = [x]
    for wd in widths:
        cols.append(cols[-1] + wd)
    tot = cols[-1] - cols[0]
    b.append(rect(cols[0], y, tot, rh, "none", 1.3))
    for i, hd in enumerate(head):
        b.append(txt((cols[i] + cols[i + 1]) / 2, y + rh / 2 + hfs * 0.36, hd,
                     hfs, "middle", "bold"))
    for k, row in enumerate(rows):
        ry = y + rh + k * rh
        b.append(rect(cols[0], ry, tot, rh, "none", 0.9))
        for i, v in enumerate(row):
            b.append(txt((cols[i] + cols[i + 1]) / 2, ry + rh / 2 + fs * 0.36,
                         v, fs, "middle", "bold" if i == 0 else "normal"))
    for c in cols[1:-1]:
        b.append(line(c, y, c, y + rh * (len(rows) + 1), 0.9))


# ======================================================================
# セット1　調査の下調べ
# ======================================================================
MEMO = [
    ("問い", "この地区で、駅の東側にだけ"),
    ("", "新しい住宅が増えたのはなぜか。"),
    ("", ""),
    ("仮説Ａ", "工場が移り、その跡地が"),
    ("", "住宅になったから。"),
    ("仮説Ｂ", "駅の東側は西側より土地が"),
    ("", "平らで、家を建てやすいから。"),
    ("仮説Ｃ", "駅の東側のほうが、西側より"),
    ("", "家賃が安いから。"),
]
SHIRYO_LIST = [
    ["旧版地形図", "1975年の建物と土地利用"],
    ["現在の地形図", "いまの建物と土地利用"],
    ["土地条件図", "土地の成り立ちの区分"],
    ["国勢調査", "町丁ごとの人口と世帯数"],
    ["市の統計書", "工場の数と働く人の数"],
]


def plan_memo():
    b = [txt(20, 24, "資料1　調査計画のメモと、手に入る資料の一覧", 15,
             "start", "bold")]
    panel(b, 20, 36, 336, 272, "調査計画のメモ")
    y = 76
    for (who, s) in MEMO:
        if who:
            b.append(txt(34, y, who, 11.5, "start", "bold"))
        if s:
            b.append(txt(100, y, s, 11.5))
        y += 25
    panel(b, 368, 36, 332, 272, "手に入る資料の一覧")
    grid_table(b, 380, 68, [138, 170], 30,
               ["資　料　名", "わ か る こ と"], SHIRYO_LIST, 9.5, 9.5)
    b.append(txt(20, H - 10, NOTE_TRAIN, 10))
    return svg(W, H, "\n".join(b), "調査計画のメモと資料の一覧")


# 地形図の骨組み。西が台地、東が低地。崖線が両者を分ける。横長の範囲。
GAKE_D = [(254, 44), (242, 100), (258, 160), (240, 220), (254, 282)]
RAIL_D = [(26, 176), (200, 172), (420, 168), (694, 164)]
IE_E = [(330, 92), (362, 98), (394, 92), (426, 98), (458, 92),
        (340, 124), (372, 130), (404, 124), (436, 130),
        (530, 96), (562, 102), (594, 96),
        (346, 220), (378, 226), (410, 220), (442, 226), (474, 220),
        (356, 252), (388, 258), (420, 252),
        (538, 224), (570, 230), (602, 224)]
IE_W = [(112, 108), (144, 114), (176, 108),
        (118, 240), (150, 246), (182, 240)]


def area_map():
    b = [txt(20, 24, "資料2　現在の地形図（模式）", 15, "start", "bold"),
         rect(20, 36, 680, 250, "none", 1.2)]
    # 西の台地の等高線。高さの数字を入れて、崖の線と見分けがつくようにする。
    for (dx, wdt, hh) in ((0, 1.0, "30"), (-52, 0.8, "40")):
        b.append(poly([(214 + dx, 44), (176 + dx, 106), (196 + dx, 164),
                       (172 + dx, 222), (208 + dx, 282)], wdt))
        b.append(rect(174 + dx, 156, 22, 14, "#fff", 0))
        b.append(txt(185 + dx, 167, hh, 10, "middle"))
    # 崖（ケバは低い側＝東を向く）
    b.append(poly(GAKE_D, 1.4))
    for k in range(9):
        t = k / 8.0
        i = min(int(t * (len(GAKE_D) - 1)), len(GAKE_D) - 2)
        u = t * (len(GAKE_D) - 1) - i
        x = GAKE_D[i][0] + (GAKE_D[i + 1][0] - GAKE_D[i][0]) * u
        y = GAKE_D[i][1] + (GAKE_D[i + 1][1] - GAKE_D[i][1]) * u
        b.append(line(x, y, x + 8, y, 0.9))
    b.append(txt(40, 62, "台地", 11.5))
    b.append(txt(276, 62, "低地", 11.5))
    b.append(txt(262, 116, "崖", 10.5))
    # 鉄道と駅
    b.append(poly(RAIL_D, 1.2))
    for k in range(19):
        t = k / 18.0
        x = 26 + (694 - 26) * t
        y = 176 + (164 - 176) * t
        b.append(line(x, y - 5, x, y + 5, 0.9))
    b.append(txt(34, 162, "鉄道", 10.5))
    b.append(rect(300, 160, 22, 22, "#fff", 1.6))
    b.append(txt(311, 152, "駅", 10.5, "middle"))
    for (x, y) in IE_E + IE_W:
        b.append(rect(x - 4, y - 4, 8, 8, "#000", 0.6))
    # 記号どうし、記号と縮尺・鉄道が重ならない位置に置く
    b.append(sym_factory(622, 238))
    b.append(sym_factory(658, 226))
    b.append(sym_school(496, 138))
    b.append(sym_torii(96, 208))
    for (x, y) in [(560, 56), (614, 62), (666, 56)]:
        b.append(sym_ta(x, y))
    for (x, y) in [(52, 100), (54, 258)]:
        b.append(sym_kouyou(x, y))
    b.append(rect(600, 272, 84, 2, "#000", 0))
    b.append(txt(642, 268, "500m", 10, "middle"))
    b.append(txt(24, 302, "北は図の上。等高線に添えた数字は高さ（m）。", 10))
    # 凡例
    ly = 292.0
    b.append(rect(370, ly, 330, 30, "none", 1))
    x = 384.0
    for (fn, lab) in [(None, "家屋"), (sym_factory, "工場"),
                      (sym_school, "学校"), (sym_torii, "神社"),
                      (sym_ta, "田")]:
        if fn is None:
            b.append(rect(x - 4, ly + 11, 8, 8, "#000", 0.6))
        else:
            b.append(fn(x, ly + 15))
        b.append(txt(x + 11, ly + 19, lab, 10))
        x += 14 + len(lab) * 10.5 + 16
    b.append(txt(20, H - 10, NOTE_MAP, 10))
    return svg(W, H, "\n".join(b), "現在の模式地形図")


# ======================================================================
# セット2　主題図をつくる
# ======================================================================
KU = [
    # 地区, 人口(人), 面積(km2), 65歳以上(人)
    ("ア", 24000, 3.0, 3600),
    ("イ", 9600, 12.0, 2880),
    ("ウ", 15000, 5.0, 3000),
    ("エ", 4200, 21.0, 1680),
    ("オ", 7200, 9.0, 1440),
]
CUT_A = [(0, 10), (10, 20), (20, 30), (30, 100)]
CUT_B = [(0, 20), (20, 25), (25, 35), (35, 100)]
# 5地区の区画（パネルの左上を原点とした相対位置）。2枚で同じ形を使う。
BOX = {"ア": (8, 30, 140, 76), "イ": (156, 30, 76, 76), "ウ": (240, 30, 82, 76),
       "エ": (8, 114, 200, 68), "オ": (216, 114, 106, 68)}


def ritsu(name):
    for (nm, pop, _a, old) in KU:
        if nm == name:
            return 100.0 * old / pop
    raise KeyError(name)


def cls_of(v, cuts):
    for i, (lo, hi) in enumerate(cuts):
        if lo <= v < hi:
            return i
    return len(cuts) - 1


def ku_table():
    b = [txt(20, 24, "資料1　Ｍ市の5つの地区の人口・面積・65歳以上の人数", 15,
             "start", "bold")]
    rows = [[nm, "{:,}".format(pop), ("%g" % ar), "{:,}".format(old)]
            for (nm, pop, ar, old) in KU]
    grid_table(b, 24, 44, [110, 190, 180, 200], 40,
               ["地区", "人口（人）", "面積（km²）", "65歳以上（人）"],
               rows, 12.5, 11.5)
    b.append(txt(24, 296, "いずれも同じ年の値。", 10))
    b.append(txt(20, H - 10, NOTE_FAKE, 10))
    return svg(W, H, "\n".join(b), "地区別の人口・面積・65歳以上の人数")


def _one_choro(b, ox, oy, title, cuts):
    b.append(rect(ox, oy, 342, 264, "none", 1))
    b.append(txt(ox + 12, oy + 20, title, 11.5, "start", "bold"))
    for (nm, (dx, dy, w, h)) in sorted(BOX.items()):
        x, y = ox + dx, oy + dy
        i = cls_of(ritsu(nm), cuts)
        b.append(rect(x, y, w, h, FILLS[i], 1.2))
        if i != 3:
            b.append('<rect x="%.1f" y="%.1f" width="24" height="20" '
                     'fill="#fff" stroke="none"/>'
                     % (x + w / 2 - 12, y + h / 2 - 14))
        b.append(txt(x + w / 2, y + h / 2 + 5, nm, 15, "middle", "bold", FG[i]))
    ly = oy + 186
    b.append(txt(ox + 12, ly + 12, "凡例　65歳以上の割合（％）", 10, "start",
                 "bold"))
    for i, (lo, hi) in enumerate(cuts):
        cx = ox + 12 + (i % 2) * 168
        cy = ly + 22 + (i // 2) * 25
        b.append(rect(cx, cy, 26, 18, FILLS[i], 0.9))
        if i == 0:
            lab = "%d未満" % hi
        elif i == len(cuts) - 1:
            lab = "%d以上" % lo
        else:
            lab = "%d〜%d" % (lo, hi)
        b.append(txt(cx + 32, cy + 14, lab, 10))


def choro_pair():
    b = [txt(20, 24, "資料2　資料1の「65歳以上の割合」を、2とおりの区切り方で"
                     "ぬり分けた階級区分図", 14, "start", "bold")]
    _one_choro(b, 20, 36, "区切り方その1", CUT_A)
    _one_choro(b, 378, 36, "区切り方その2（その1と同じ数値）", CUT_B)
    b.append(txt(20, H - 10, NOTE_FAKE, 10))
    return svg(W, H, "\n".join(b), "2とおりの区切り方の階級区分図")


# ======================================================================
# セット3　調べた結果をまとめる
# ======================================================================
NEN = [
    (1990, 12000, 240, 30),
    (2000, 11400, 180, 27),
    (2010, 10200, 120, 24),
    (2020, 8400, 60, 18),
]
SERIES = [("人口", 1, "", 3.0), ("商店の数", 2, "7 5", 3.0),
          ("工場の数", 3, "2 4", 3.0)]


def _marker(b, x, y, idx, mk):
    if idx == 1:
        b.append(circle(x, y, mk, "#000", 0.8))
    elif idx == 2:
        b.append(rect(x - mk, y - mk, 2 * mk, 2 * mk, "#000", 0.8))
    else:
        b.append(poly([(x, y - mk - 0.8), (x + mk + 0.8, y + mk),
                       (x - mk - 0.8, y + mk)], 0.8, "", "#000", True))


def nen_data():
    b = [txt(20, 24, "資料1　Ｑ町の人口・商店の数・工場の数と、"
                     "1990年を100としたときの値", 14, "start", "bold")]
    rows = [[str(y), "{:,}".format(p), str(s), str(f)] for (y, p, s, f) in NEN]
    grid_table(b, 24, 48, [66, 106, 86, 92], 40,
               ["年", "人口（人）", "商店（店）", "工場（か所）"], rows, 11, 10)
    b.append(txt(24, 296, "左の表の数値を、右の図で1990年＝100に直してある。", 10))

    ax, ay, aw, ah = 440.0, 244.0, 236.0, 186.0
    b.append(txt(396, 52, "1990年を100としたときの値", 11, "start", "bold"))
    b.append(line(ax, ay - ah, ax, ay, 1.0))
    b.append(line(ax, ay, ax + aw, ay, 1.0))
    for v in (0, 25, 50, 75, 100):
        y = ay - ah * v / 110.0
        b.append(line(ax - 4, y, ax, y, 0.8))
        b.append(txt(ax - 8, y + 3.5, str(v), 9.5, "end"))
    for k, row in enumerate(NEN):
        x = ax + aw * k / 3.0
        b.append(line(x, ay, x, ay + 4, 0.8))
        b.append(txt(x, ay + 16, str(row[0]), 9.5, "middle"))
    base = NEN[0]
    for (lab, idx, dash, mk) in SERIES:
        pts = []
        for k, row in enumerate(NEN):
            v = 100.0 * row[idx] / base[idx]
            pts.append((ax + aw * k / 3.0, ay - ah * v / 110.0))
        b.append(poly(pts, 1.5, dash))
        for (x, y) in pts:
            _marker(b, x, y, idx, mk)
    ly = 268.0
    b.append(rect(388, ly, 312, 26, "none", 0.9))
    x = 400.0
    for (lab, idx, dash, mk) in SERIES:
        b.append(line(x, ly + 13, x + 30, ly + 13, 1.5, dash))
        _marker(b, x + 15, ly + 13, idx, mk)
        b.append(txt(x + 35, ly + 17, lab, 9.5))
        x += 36 + len(lab) * 10 + 12
    b.append(txt(20, H - 10, NOTE_FAKE, 10))
    return svg(W, H, "\n".join(b), "年次別の統計と1990年を100とした値")


KIKITORI = [
    ("商店主", "30年前は、買い物といえばこの通りでした。"),
    ("", "いまは車で隣の市の大きな店へ行く人が多いです。"),
    ("町役場", "町の外へ働きに出る人が増えました。"),
    ("", "町内で新しく店を始めた人は、この10年で2人です。"),
    ("高校生", "学校の帰りに寄る店が、駅の近くにありません。"),
    ("", "友だちとは隣の市で待ち合わせます。"),
]


def kikitori():
    b = [txt(20, 24, "資料2　聞き取りの記録（3人に、それぞれ1回）", 15,
             "start", "bold"),
         rect(20, 36, 680, 262, "none", 1)]
    y = 76
    for (who, s) in KIKITORI:
        if who:
            b.append(txt(40, y, who, 12, "start", "bold"))
        b.append(txt(140, y, s, 13.5))
        y += 38
    b.append(txt(20, H - 10, NOTE_TRAIN, 10))
    return svg(W, H, "\n".join(b), "聞き取りの記録")


FIGURES = {
    "D1_plan.svg": plan_memo,
    "D1_map.svg": area_map,
    "D2_table.svg": ku_table,
    "D2_choro.svg": choro_pair,
    "D3_data.svg": nen_data,
    "D3_talk.svg": kikitori,
}
