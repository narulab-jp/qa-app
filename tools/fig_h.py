# -*- coding: utf-8 -*-
"""冊G　地域調査（本格版）の資料。セット1「人口が減る盆地の集落」。

  1つの地域を、時間の変化・空間の変化・調査の過程・地域課題まで
  たどれるだけの資料をそろえる。資料は5点。

    資料1 1970年ごろの地形図（模式）
    資料2 現在の地形図（模式・資料1と同じ範囲）
    資料3 人口と年齢構成の移り変わり
    資料4 土地利用の移り変わり
    資料5 調査の会話（仮説を立てる場面）

  作るときの約束（指示Gで確認した規則）
    ・資料の中に答えを文章で書かない。示すのは事実（記号・位置・数値）だけ。
    ・凡例には区分の名まえだけを書く。意味や理由は書かない。
    ・「過疎」「廃校」「高齢化」のような、答えになることばは図に出さない。
    ・写真は使わない。数値・地名はすべて架空で、図の中に明記する。
"""
import math

from figlib import (NOTE_FAKE, NOTE_MAP, circle, line, poly, rect, svg, txt,
                    sym_ta, sym_kuwa, sym_kaju, sym_hatake, sym_arechi,
                    sym_school, sym_post, sym_roujin, sym_shinyou,
                    sym_torii)

W = 720
NOTE_TRAIN = "※ 訓練用に作成したものであり、実在の地域・事例ではない。"

# 盆地の輪郭（山地に囲まれた低地）。2枚の地形図で同じものを使う。
#   川は盆地の中ほど、鉄道はその北側を通す。重ならないように離してある。
BASIN = [(150, 132), (330, 112), (500, 126), (596, 186), (612, 300),
         (556, 384), (410, 424), (250, 412), (158, 330), (136, 226)]
RIVER = [(108, 296), (240, 314), (400, 324), (546, 336), (682, 348)]
RAIL = [(114, 232), (300, 240), (480, 246), (684, 258)]
# 集落（家の並び）。1970年は密、現在はまばら。鉄道の南に並ぶ。
IE_OLD = [(226, 262), (242, 270), (258, 262), (274, 270), (290, 262),
          (234, 280), (250, 288), (266, 280), (282, 288),
          (416, 266), (432, 274), (448, 266), (464, 274),
          (424, 284), (440, 292), (456, 284)]
IE_NEW = [(226, 262), (258, 262), (290, 262),
          (250, 288), (282, 288),
          (416, 266), (448, 266),
          (440, 292)]


def _frame(title, note=NOTE_MAP, H=560):
    return ([txt(20, 30, title, 16, "start", "bold"),
             rect(30, 48, 660, 424, "none", 1.2)], H)


def _mountains(b):
    """まわりの山地。等高線を2本置くだけで、地形の名まえは書かない。"""
    for k, s in enumerate((1.00, 1.10)):
        pts = []
        for (x, y) in BASIN:
            pts.append((372 + (x - 372) * s, 268 + (y - 268) * s))
        b.append(poly(pts, 0.9 if k == 0 else 0.7, "", "none", True))
    for (x, y) in [(72, 108), (664, 104), (74, 432), (662, 436)]:
        b.append(sym_shinyou(x, y))
    b.append(txt(52, 86, "山地", 12))
    b.append(txt(668, 462, "山地", 12, "end"))


def _river(b):
    b.append(poly(RIVER, 2.8))
    b.append(txt(152, 276, "川", 12))


def _rail(b):
    b.append(poly(RAIL, 1.2))
    for k in range(15):
        t = k / 14.0
        x = 114 + (684 - 114) * t
        y = 232 + (258 - 232) * t
        b.append(line(x, y - 5, x, y + 5, 0.9))
    b.append(txt(126, 218, "鉄道", 11))
    b.append(rect(295, 235, 11, 11, "#fff", 1.5))
    b.append(txt(310, 228, "駅", 11))


def _houses(b, pts):
    for (x, y) in pts:
        b.append(rect(x - 4, y - 4, 8, 8, "#000", 0.6))


def _legend(b, items, y=486):
    b.append(rect(30, y, 660, 40, "none", 1))
    b.append(txt(44, y + 25, "凡例", 12, "start", "bold"))
    x = 98.0
    for (fn, lab) in items:
        if fn is None:
            b.append(rect(x - 4, y + 16, 8, 8, "#000", 0.6))
        else:
            b.append(fn(x, y + 20))
        b.append(txt(x + 13, y + 25, lab, 11))
        x += 20 + len(lab) * 11.5 + 20


# 川に近い低いところ（2枚とも田のまま）
TA_NEAR = [(240, 292), (300, 300), (360, 306), (420, 312), (480, 318),
           (256, 342), (316, 348), (376, 352), (436, 356), (494, 360)]
# 川から離れたところ（1970年は田、現在は荒地）。南のはしにまとめてある
TA_FAR = [(222, 388), (272, 394), (322, 398), (372, 400),
          (422, 398), (472, 392), (518, 384)]
# 山ろくの斜面（1970年は桑畑、現在は果樹園）
KUWA = [(196, 178), (250, 164), (312, 156), (376, 154), (438, 160),
        (496, 172), (546, 196)]


def old_map():
    b, H = _frame("資料1　1970年ごろの地形図")
    _mountains(b)
    _river(b)
    _rail(b)
    for (x, y) in TA_NEAR + TA_FAR:
        b.append(sym_ta(x, y))
    for (x, y) in KUWA:
        b.append(sym_kuwa(x, y))
    _houses(b, IE_OLD)
    b.append(sym_school(214, 224))
    b.append(sym_school(478, 226))
    b.append(sym_post(346, 268))
    _legend(b, [(sym_ta, "田"), (sym_kuwa, "桑畑"), (None, "家屋"),
                (sym_school, "小学校"), (sym_post, "郵便局")])
    b.append(txt(20, H - 12, NOTE_MAP, 11))
    return svg(W, H, "\n".join(b), "1970年ごろの模式地形図")


def new_map():
    b, H = _frame("資料2　現在の地形図（資料1と同じ範囲）")
    _mountains(b)
    _river(b)
    _rail(b)
    for (x, y) in TA_NEAR:
        b.append(sym_ta(x, y))
    for (x, y) in TA_FAR:                    # 川から離れた田は荒地になった
        b.append(sym_arechi(x, y))
    for (x, y) in KUWA:                      # 桑畑は果樹園になった
        b.append(sym_kaju(x, y))
    _houses(b, IE_NEW)
    b.append(sym_roujin(214, 224))           # 小学校のうち1つは老人ホームに
    b.append(sym_school(478, 226))
    b.append(sym_post(346, 268))
    # 盆地の南を通る道路が新しくできた
    b.append(poly([(120, 434), (250, 442), (420, 436), (580, 440),
                   (676, 444)], 2.6))
    b.append(txt(134, 458, "道路", 11))
    _legend(b, [(sym_ta, "田"), (sym_arechi, "荒地"), (sym_kaju, "果樹園"),
                (None, "家屋"), (sym_school, "小学校"),
                (sym_roujin, "老人ホーム")])
    b.append(txt(20, H - 12, NOTE_MAP, 11))
    return svg(W, H, "\n".join(b), "現在の模式地形図")


# 資料3　人口と年齢構成（数値だけ。「高齢化」などのことばは書かない）
POP = [(1970, 8200, 26, 62, 12), (1990, 6900, 18, 63, 19),
       (2010, 4800, 11, 57, 32), (2025, 3400, 8, 50, 42)]


def pop_chart():
    H = 590
    b = [txt(20, 30, "資料3　この地域の人口と年齢構成の移り変わり", 16,
             "start", "bold"),
         txt(20, 60, "棒＝総人口（人・左目盛）　"
                     "帯＝年齢構成の割合（％）", 12)]
    ax, ay, aw, ah = 90.0, 296.0, 560.0, 196.0
    b.append(line(ax, ay - ah, ax, ay, 1.1))
    b.append(line(ax, ay, ax + aw, ay, 1.1))
    for v in (0, 2000, 4000, 6000, 8000):
        y = ay - ah * v / 9000.0
        b.append(line(ax - 5, y, ax, y, 0.8))
        b.append(txt(ax - 10, y + 4, "{:,}".format(v), 11, "end"))
    bw = 74.0
    for k, (yr, tot, a, b2, c) in enumerate(POP):
        x = ax + 40 + k * 132
        h = ah * tot / 9000.0
        b.append(rect(x, ay - h, bw, h, "hatch:diag", 1.0))
        b.append(txt(x + bw / 2, ay - h - 8, "{:,}".format(tot), 11, "middle"))
        b.append(txt(x + bw / 2, ay + 20, str(yr), 12, "middle"))
    # 年齢構成は、年ごとに横1本の帯にする。棒と同じ幅だと数字が入らない。
    b.append(txt(20, 348, "年齢構成の割合（％）", 12, "start", "bold"))
    ox, ow, bh = 118.0, 452.0, 26.0
    for k, (yr, tot, a, b2, c) in enumerate(POP):
        by = 360.0 + k * (bh + 6)
        b.append(txt(ox - 10, by + bh / 2 + 5, str(yr), 11, "end"))
        xx = ox
        for (v, fill) in ((a, "hatch:dot"), (b2, "none"), (c, "hatch:grid")):
            ww = ow * v / 100.0
            b.append(rect(xx, by, ww, bh, fill, 0.9))
            # 数字がハッチにまぎれないよう、下地を白でぬく
            b.append('<rect x="%.1f" y="%.1f" width="24" height="16" '
                     'fill="#fff" stroke="none"/>'
                     % (xx + ww / 2 - 12, by + bh / 2 - 8))
            b.append(txt(xx + ww / 2, by + bh / 2 + 5, str(v), 11, "middle"))
            xx += ww
    ly = 490.0
    b.append(rect(30, ly, 660, 44, "none", 1))
    b.append(txt(44, ly + 27, "凡例", 12, "start", "bold"))
    for k, (fill, lab) in enumerate((("hatch:dot", "15歳未満"),
                                     ("none", "15〜64歳"),
                                     ("hatch:grid", "65歳以上"))):
        x = 110 + k * 190
        b.append(rect(x, ly + 14, 26, 18, fill, 1))
        b.append(txt(x + 34, ly + 27, lab, 11))
    b.append(txt(20, H - 12, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(b), "人口と年齢構成の移り変わり")


# 資料4　土地利用の移り変わり（数値だけ）
def land_table():
    rows = [["田", "612", "540", "388", "246"],
            ["桑畑", "184", "96", "12", "0"],
            ["果樹園", "8", "62", "138", "165"],
            ["荒地", "6", "48", "196", "352"],
            ["宅地", "74", "80", "72", "63"]]
    head = ["地目", "1970年", "1990年", "2010年", "2025年"]
    widths = [120, 130, 130, 130, 130]
    rh = 42.0
    h = int(46 + rh * (len(rows) + 1) + 56)
    cols = [20.0]
    for wd in widths:
        cols.append(cols[-1] + wd)
    b = [txt(20, 28, "資料4　この地域の土地利用の移り変わり（ha）", 16,
             "start", "bold"),
         rect(cols[0], 46.0, cols[-1] - cols[0], rh, "none", 1.4)]
    for i, hd in enumerate(head):
        b.append(txt((cols[i] + cols[i + 1]) / 2, 46.0 + rh / 2 + 5, hd, 12,
                     "middle", "bold"))
    for k, row in enumerate(rows):
        ry = 46.0 + rh + k * rh
        b.append(rect(cols[0], ry, cols[-1] - cols[0], rh, "none", 1))
        for i, v in enumerate(row):
            b.append(txt((cols[i] + cols[i + 1]) / 2, ry + rh / 2 + 5, v, 13,
                         "middle", "bold" if i == 0 else "normal"))
    for c in cols[1:-1]:
        b.append(line(c, 46.0, c, 46.0 + rh * (len(rows) + 1), 1))
    b.append(txt(20, h - 30, "haはヘクタール。1ha＝10,000m²。", 11))
    b.append(txt(20, h - 12, NOTE_FAKE, 11))
    return svg(W, h, "\n".join(b), "土地利用の移り変わり")


# 資料5　調査の会話（仮説を立てる場面。答えは言わない）
TALK = [
    ("先生", "2枚の地形図を見比べて、気づいたことを出してみましょう。"),
    ("ソラ", "山ろく側にあった桑畑の記号が、いまは果樹園に変わっている。"),
    ("", "それと、田だったところの一部が荒地になっているね。"),
    ("ミオ", "家の記号も減っている。小学校の記号は1つになって、"),
    ("", "もう1つあった場所には別の記号がついている。"),
    ("ソラ", "荒地になったのは、川から遠いほうが多い気がする。"),
    ("ミオ", "わたしの仮説Ａは「働く人が減ったことが、田を手放した理由だ」。"),
    ("ソラ", "ぼくの仮説Ｂは「桑の値段が下がったことが、果樹に変えた理由だ」。"),
    ("ミオ", "もう一つ、仮説Ｃ「道路ができたことで人が増えた」もある。"),
    ("先生", "その3つのうち、いまある資料で確かめられるのはどれでしょう。"),
]


def talk():
    H = 92 + len(TALK) * 30 + 40
    b = [txt(20, 30, "資料5　地域調査での会話", 16, "start", "bold"),
         rect(20, 46, W - 40, H - 96, "none", 1)]
    y = 78
    for (who, s) in TALK:
        if who:
            b.append(txt(40, y, who, 13, "start", "bold"))
        b.append(txt(112, y, s, 14))
        y += 30
    b.append(txt(20, H - 14, NOTE_TRAIN, 11))
    return svg(W, int(H), "\n".join(b), "地域調査の会話文")


# ======================================================================
# セット2「川ぞいの市街地と水害」
#   3枚の地図はすべて同じ範囲。川と崖線を同じ座標で描いて、
#   同じ場所どうしを見比べられるようにしてある。
# ======================================================================
RIVER2 = [(196, 56), (250, 150), (300, 250), (352, 348), (410, 448)]
GAKE = [(150, 56), (128, 150), (146, 250), (120, 350), (140, 464)]
# 自然堤防（川ぞいの細長い高まり）に沿う点
TEIBO = [(232, 112), (256, 176), (280, 240), (306, 306), (334, 372),
         (206, 128), (232, 192), (256, 256), (282, 322), (310, 388)]
# 低地（自然堤防の外側）。明治期は田、現在は住宅地
TEICHI = [(400, 110), (470, 140), (540, 118), (610, 150),
          (420, 200), (492, 226), (562, 204), (628, 234),
          (444, 288), (514, 312), (584, 292), (646, 320),
          (466, 374), (536, 396), (604, 378),
          (486, 448), (556, 452)]
# 台地の上（崖線より西）
DAICHI = [(70, 110), (78, 200), (66, 292), (82, 382), (70, 442),
          (108, 156), (100, 248), (112, 336), (98, 424),
          (60, 154), (92, 118), (86, 336), (60, 386)]


def _base2(b):
    """3枚の地図に共通の骨組み（川・崖線）。
       崖はケバ付きの実線にして、台地と低地の境をはっきりさせる。"""
    b.append(poly(RIVER2, 3.0))
    b.append(txt(222, 96, "川", 12))
    b.append(poly(GAKE, 1.4))
    for k in range(11):
        t = k / 10.0
        i = min(int(t * (len(GAKE) - 1)), len(GAKE) - 2)
        u = t * (len(GAKE) - 1) - i
        x = GAKE[i][0] + (GAKE[i + 1][0] - GAKE[i][0]) * u
        y = GAKE[i][1] + (GAKE[i + 1][1] - GAKE[i][1]) * u
        b.append(line(x, y, x + 9, y, 0.9))      # 崖のケバ（低い側を向く）
    b.append(txt(56, 82, "台地", 12))
    b.append(txt(160, 92, "崖", 11))


def old_map2():
    b, H = _frame("資料1　明治時代の地形図")
    _base2(b)
    for (x, y) in TEIBO:
        b.append(rect(x - 4, y - 4, 8, 8, "#000", 0.6))
    for (x, y) in TEICHI:
        b.append(sym_ta(x, y))
    for (x, y) in DAICHI:
        b.append(sym_kuwa(x, y))
    b.append(sym_torii(268, 148))
    _legend(b, [(None, "家屋"), (sym_ta, "田"), (sym_kuwa, "桑畑"),
                (sym_torii, "神社")])
    b.append(txt(20, H - 12, NOTE_MAP, 11))
    return svg(W, H, "\n".join(b), "明治時代の模式地形図")


def new_map2():
    b, H = _frame("資料2　現在の地形図（資料1と同じ範囲）")
    _base2(b)
    # 自然堤防の上・低地・台地の上、いずれにも住宅が並ぶ
    for (x, y) in TEIBO:
        b.append(rect(x - 4, y - 4, 8, 8, "#000", 0.6))
    for (x, y) in TEICHI:
        b.append(rect(x - 4, y - 4, 8, 8, "#000", 0.6))
        b.append(rect(x + 12, y + 10, 8, 8, "#000", 0.6))
    for (x, y) in DAICHI:
        b.append(rect(x - 4, y - 4, 8, 8, "#000", 0.6))
    # 田はわずかに残る
    for (x, y) in [(650, 404), (664, 448)]:
        b.append(sym_ta(x, y))
    b.append(sym_torii(268, 148))
    b.append(sym_school(560, 160))
    # 鉄道と駅（東西に横切る）
    b.append(poly([(40, 268), (200, 262), (380, 258), (560, 254),
                   (686, 250)], 1.2))
    for k in range(14):
        t = k / 13.0
        x = 40 + (686 - 40) * t
        y = 268 + (250 - 268) * t
        b.append(line(x, y - 5, x, y + 5, 0.9))
    b.append(txt(52, 250, "鉄道", 11))
    b.append(rect(474, 251, 11, 11, "#fff", 1.5))
    b.append(txt(490, 244, "駅", 11))
    _legend(b, [(None, "家屋"), (sym_ta, "田"), (sym_torii, "神社"),
                (sym_school, "小学校")])
    b.append(txt(20, H - 12, NOTE_MAP, 11))
    return svg(W, H, "\n".join(b), "現在の模式地形図")


def flood_map():
    b, H = _frame("資料3　浸水が想定される深さ（資料1・資料2と同じ範囲）")
    # 低地（川の東側）は深い
    b.append(poly([(370, 56), (686, 56), (686, 464), (390, 464),
                   (330, 300), (300, 170)], 1.0, "", "hatch:diag", True))
    # 自然堤防の帯は浅い
    b.append(poly([(196, 56), (300, 170), (390, 464), (330, 464),
                   (250, 200), (150, 60)], 1.0, "", "hatch:dotfine", True))
    _base2(b)
    b.append(txt(540, 380, "Ｘ", 20, "middle", "bold"))
    b.append(circle(540, 374, 15, "none", 1.4))
    b.append(txt(268, 300, "Ｙ", 20, "middle", "bold"))
    b.append(circle(268, 294, 15, "none", 1.4))
    b.append(txt(86, 300, "Ｚ", 20, "middle", "bold"))
    b.append(circle(86, 294, 15, "none", 1.4))
    ly = 486.0
    b.append(rect(30, ly, 660, 40, "none", 1))
    b.append(txt(44, ly + 25, "凡例", 12, "start", "bold"))
    b.append(rect(98, ly + 11, 26, 18, "hatch:diag", 1))
    b.append(txt(132, ly + 25, "2〜3m", 11))
    b.append(rect(224, ly + 11, 26, 18, "hatch:dotfine", 1))
    b.append(txt(258, ly + 25, "0.5m未満", 11))
    b.append(rect(360, ly + 11, 26, 18, "none", 1))
    b.append(txt(394, ly + 25, "想定なし", 11))
    b.append(txt(470, ly + 25, "Ｘ・Ｙ・Ｚは地点を表す", 11))
    b.append(txt(20, H - 12, NOTE_MAP, 11))
    return svg(W, H, "\n".join(b), "浸水が想定される深さの図")


def house_table():
    rows = [["低地（川の東側）", "12", "1,860", "4,300"],
            ["川ぞいの高まりの上", "140", "520", "1,200"],
            ["台地の上", "30", "1,240", "2,900"]]
    head = ["場所", "明治時代の\n住宅数（戸）", "現在の\n住宅数（戸）",
            "現在の人口（人）"]
    widths = [200, 140, 140, 160]
    rh = 46.0
    h = int(46 + rh * (len(rows) + 1) + 40)
    cols = [20.0]
    for wd in widths:
        cols.append(cols[-1] + wd)
    b = [txt(20, 28, "資料4　場所ごとの住宅数と人口", 16, "start", "bold"),
         rect(cols[0], 46.0, cols[-1] - cols[0], rh, "none", 1.4)]
    for i, hd in enumerate(head):
        parts = hd.split("\n")
        for j, p in enumerate(parts):
            y = 46.0 + rh / 2 + (j - (len(parts) - 1) / 2.0) * 15 + 5
            b.append(txt((cols[i] + cols[i + 1]) / 2, y, p, 12, "middle",
                         "bold"))
    for k, row in enumerate(rows):
        ry = 46.0 + rh + k * rh
        b.append(rect(cols[0], ry, cols[-1] - cols[0], rh, "none", 1))
        for i, v in enumerate(row):
            b.append(txt((cols[i] + cols[i + 1]) / 2, ry + rh / 2 + 5, v, 13,
                         "middle", "bold" if i == 0 else "normal"))
    for c in cols[1:-1]:
        b.append(line(c, 46.0, c, 46.0 + rh * (len(rows) + 1), 1))
    b.append(txt(20, h - 12, NOTE_FAKE, 11))
    return svg(W, h, "\n".join(b), "場所ごとの住宅数と人口")


TALK2 = [
    ("ハルカ", "この町でいちばん古くからある家は、どのあたりですか。"),
    ("住民Ａ", "祖父の代までは、家は川ぞいの少し高いところだけでした。"),
    ("", "東の低いところは、ずっと田んぼでしたよ。"),
    ("住民Ｂ", "うちは30年前に建てました。まわりの家もだいたい同じころです。"),
    ("ハルカ", "駅ができたのは、それより前ですか。"),
    ("住民Ａ", "駅のほうが先です。それから東側が開けていきました。"),
    ("リク", "仮説Ａ「駅ができたことが、低いところに家が増えた理由だ」。"),
    ("ハルカ", "仮説Ｂ「土地の値段が安かったことが、その理由だ」も考えられる。"),
    ("リク", "仮説Ｃ「堤防ができた今は、もう浸水することはない」はどうかな。"),
    ("先生", "3つの仮説を、いまある資料で分けてみましょう。"),
]


def talk2():
    H = 92 + len(TALK2) * 30 + 40
    b = [txt(20, 30, "資料5　住民への聞き取りと、そのあとの話し合い", 16,
             "start", "bold"),
         rect(20, 46, W - 40, H - 96, "none", 1)]
    y = 78
    for (who, s) in TALK2:
        if who:
            b.append(txt(40, y, who, 13, "start", "bold"))
        b.append(txt(126, y, s, 14))
        y += 30
    b.append(txt(20, H - 14, NOTE_TRAIN, 11))
    return svg(W, int(H), "\n".join(b), "住民への聞き取りの会話")


FIGURES = {
    "H1_old.svg": old_map,
    "H1_new.svg": new_map,
    "H1_pop.svg": pop_chart,
    "H1_land.svg": land_table,
    "H1_talk.svg": talk,
    "H2_old.svg": old_map2,
    "H2_new.svg": new_map2,
    "H2_flood.svg": flood_map,
    "H2_table.svg": house_table,
    "H2_talk.svg": talk2,
}
