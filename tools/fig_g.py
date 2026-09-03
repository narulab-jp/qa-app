# -*- coding: utf-8 -*-
"""冊E（通し演習）専用の資料。第1問・第2問・第6問のぶんを新しく作る。

  作る理由
    通し演習は「初見の資料を60分で読む」訓練である。図表編で見慣れた図を
    使い回すと、その訓練にならない。そこで、本番と同じ形式の資料を
    この冊子のためだけに新しく起こした。

  作るときの約束（第三者レビューの指摘による）
    ・資料の中に答えを文章で書かない。
      資料が示すのは事実（数値・記号・位置・形）だけで、
      「〜だから〜である」という判断は書かない。
    ・凡例に答えを書かない。凡例は区分の名まえだけを示し、
      その意味や理由の説明は入れない。
    ・気候区や地形の名まえも資料には書かない。
      名まえを書けば、読み取らずに答えられてしまう。

  数値・地名はすべて架空で、図の中に明記する。写真は使わない。
"""
import math

from figlib import (NOTE_FAKE, NOTE_MAP, circle, line, poly, rect, svg, txt,
                    sym_ta, sym_hatake, sym_kaju, sym_kuwa,
                    sym_school, sym_city)

W = 720
NOTE_TRAIN = "※ 訓練用に作成したものであり、実在の地域・事例ではない。"


def _tbl(title, headers, rows, widths, note=NOTE_FAKE, w=W, rh=40.0):
    """数値だけを並べる表。説明の文は入れない。"""
    h = int(46 + rh * (len(rows) + 1) + 40)
    cols = [20.0]
    for wd in widths:
        cols.append(cols[-1] + wd)
    b = [txt(20, 28, title, 16, "start", "bold"),
         rect(cols[0], 46.0, cols[-1] - cols[0], rh, "none", 1.4)]
    for i, hd in enumerate(headers):
        parts = hd.split("\n")
        for j, p in enumerate(parts):
            y = 46.0 + rh / 2 + (j - (len(parts) - 1) / 2.0) * 15 + 5
            b.append(txt((cols[i] + cols[i + 1]) / 2, y, p, 12, "middle", "bold"))
    for k, row in enumerate(rows):
        ry = 46.0 + rh + k * rh
        b.append(rect(cols[0], ry, cols[-1] - cols[0], rh, "none", 1))
        for i, v in enumerate(row):
            b.append(txt((cols[i] + cols[i + 1]) / 2, ry + rh / 2 + 5, v, 13,
                         "middle", "bold" if i == 0 else "normal"))
    for c in cols[1:-1]:
        b.append(line(c, 46.0, c, 46.0 + rh * (len(rows) + 1), 1))
    b.append(txt(20, h - 14, note, 11))
    return svg(w, h, "\n".join(b), title)


# ======================================================================
# 第1問　生活文化
# ======================================================================
# 資料1：架空大陸。緯線と地点の位置だけを示す。
#        気候帯の名まえも境の帯も書かない（書くと資料2を読まずに答えられる）。
G_ARC = [(130, 90), (310, 62), (500, 96), (585, 175), (610, 290),
         (560, 385), (440, 455), (300, 486), (175, 440), (108, 330),
         (100, 190)]
#  (ラベル, y)
G_LAT = [("北緯40度", 150), ("北緯20度", 208), ("赤道（0度）", 268),
         ("南緯20度", 330), ("南緯40度", 392)]
# 地点（記号, x, y）。雨温図のある4地点は緯度と矛盾しない位置に置く。
G_PT = [("ア", 330, 268),      # 赤道上
        ("イ", 215, 330),
        ("ウ", 470, 300),
        ("エ", 255, 165),
        ("オ", 420, 205),      # 北緯20度あたり
        ("カ", 350, 105),      # 高緯度の内陸
        ("キ", 140, 142),      # 高緯度の西岸
        ("ク", 400, 400)]


def zone():
    H = 560
    b = [txt(20, 30, "資料1　架空大陸における地点の位置", 16, "start", "bold"),
         poly(G_ARC, 1.6, "", "none", True)]
    for (lab, y) in G_LAT:
        b.append(line(96, y, 640, y, 0.8, "6,5"))
        b.append(txt(648, y + 4, lab, 11))
    b.append(txt(66, 96, "北", 13, "start", "bold"))
    b.append(txt(66, 470, "南", 13, "start", "bold"))
    b.append(txt(150, 500, "西", 12, "middle"))
    b.append(txt(560, 500, "東", 12, "middle"))
    for (lab, x, y) in G_PT:
        b.append(circle(x, y, 11, "#fff", 1.6))
        b.append(txt(x, y + 5, lab, 13, "middle", "bold"))
    b.append(txt(20, 528, "破線は緯線。図の左が大陸の西岸、右が東岸にあたる。", 12))
    b.append(txt(20, H - 12, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(b), "架空大陸における地点の位置")


# 資料2：雨温図。数値だけを描き、気候区の名まえは書かない。
#   Ｐ＝ア（赤道の多雨）／Ｑ＝オ（少雨・高温）／
#   Ｒ＝カ（年較差が大きい内陸）／Ｓ＝キ（年中湿潤で冷涼）
#   どの地点かは図に書かない。資料1の緯度と資料2の数値から考えさせる。
G_CLIMO = {
    "Ｐ": ([26.4, 26.6, 26.8, 26.9, 26.7, 26.4, 26.1, 26.2, 26.4, 26.5,
            26.4, 26.3],
           [262, 244, 279, 291, 256, 190, 171, 168, 186, 224, 253, 268]),
    "Ｑ": ([12.1, 15.3, 20.4, 26.2, 31.0, 34.2, 35.1, 34.6, 31.2, 25.4,
            18.3, 13.2],
           [2, 1, 1, 0, 0, 0, 1, 2, 1, 1, 2, 3]),
    "Ｒ": ([-3.8, -1.6, 4.2, 12.1, 18.4, 23.2, 25.6, 24.4, 18.2, 11.0,
            3.6, -1.9],
           [12, 10, 16, 24, 41, 58, 46, 34, 26, 20, 15, 11]),
    "Ｓ": ([4.2, 4.6, 6.4, 9.1, 12.3, 15.2, 17.1, 16.8, 14.2, 10.8,
            7.2, 5.1],
           [78, 62, 58, 54, 56, 51, 48, 55, 63, 82, 88, 84]),
}
G_ORDER = ["Ｐ", "Ｑ", "Ｒ", "Ｓ"]


def _deg(v):
    """負の記号は全角のマイナスにそろえる"""
    return ("%.1f" % v).replace("-", "−")


def climo():
    cw, ch = 152.0, 176.0
    H = 360
    b = [txt(20, 28, "資料2　4地点の気温と降水量（Ｐ〜Ｓ）", 16,
             "start", "bold"),
         txt(20, 52, "折れ線＝気温（−10〜40℃）　棒＝降水量（0〜300mm）　"
                     "月は左から1月〜12月", 12)]
    for k, name in enumerate(G_ORDER):
        temp, rain = G_CLIMO[name]
        ox = 26 + k * (cw + 14)
        oy = 88.0
        b.append(rect(ox, oy, cw, ch, "none", 1.1))
        b.append(txt(ox + cw / 2, oy - 8, name, 15, "middle", "bold"))
        for m in range(12):
            bw = cw / 12.0 * 0.72
            bx = ox + cw / 12.0 * (m + 0.14)
            bh = ch * (min(rain[m], 300) / 300.0) * 0.86
            if bh > 0.4:
                b.append(rect(bx, oy + ch - bh, bw, bh, "hatch:diag", 0.7))
        pts = []
        for m in range(12):
            px = ox + cw / 12.0 * (m + 0.5)
            py = oy + ch - ch * ((temp[m] + 10.0) / 50.0) * 0.86
            pts.append((px, py))
        b.append(poly(pts, 1.5))
        for (px, py) in pts:
            b.append(circle(px, py, 1.8, "#000", 0.6))
        b.append(txt(ox + 2, oy + ch + 18, "年降水量 %dmm" % sum(rain), 11))
        b.append(txt(ox + 2, oy + ch + 34,
                     "最暖月 %s℃／最寒月 %s℃"
                     % (_deg(max(temp)), _deg(min(temp))), 11))
    b.append(txt(20, H - 12, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(b), "4地点の雨温図")


# 資料3：地点ごとの暮らしのようす。事実だけを並べ、理由は書かない。
# Ｋ＝キ、Ｌ＝ア、Ｍ＝オ、Ｎ＝カ。並びは雨温図とわざとずらしてある。
G_LIFE = [
    ("Ｋ", "牧草・ばれいしょ", "石を積んだ厚い壁の家", "鉄道"),
    ("Ｌ", "天然ゴム・油やし", "高床で壁の少ない木の家", "川舟"),
    ("Ｍ", "なつめやし", "日干しれんがの厚い壁の家", "らくだ"),
    ("Ｎ", "小麦・牧草", "土と草でつくった移動式の家", "馬"),
]


def life():
    return _tbl("資料3　4つの地域の作物・住居・おもな移動手段（Ｋ〜Ｎ）",
                ["地域", "おもな作物", "住居のつくり", "移動手段"],
                [list(r) for r in G_LIFE], [70, 170, 250, 130],
                NOTE_TRAIN)


# ======================================================================
# 第2問　地域調査
# ======================================================================
# 資料1：模式地形図。地形の名まえは書かない。等高線・標高点・記号だけ。
APEX = (230.0, 300.0)          # 谷口
FAN_R = [(90, 60), (150, 50), (210, 40), (266, 30)]   # 半径と標高
FAN_HALF = 44.0                # 等高線が枠からはみ出さない開き


def _arc(cx, cy, r, half=FAN_HALF, n=36):
    pts = []
    for k in range(n + 1):
        a = math.radians(-half + 2 * half * k / float(n))
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def chiiki_map():
    H = 620
    b = [txt(20, 30, "資料1　ミナトさんたちが調べた地域の地形図", 16,
             "start", "bold"),
         rect(30, 48, 660, 490, "none", 1.2)]
    # 山地（左側）。等高線を密に置くだけで、地形の名まえは書かない。
    for k in range(4):
        x = 52 + k * 28
        b.append(poly([(x, 140), (x + 12, 220), (x + 4, 300),
                       (x + 14, 380), (x + 2, 460)], 0.9))
    b.append(txt(58, 122, "山地", 12))
    # 扇状地の等高線（谷口を頂点に東へ開く）
    for (r, v) in FAN_R:
        pts = _arc(APEX[0], APEX[1], r)
        b.append(poly(pts, 1.3 if v % 20 == 0 else 0.8))
        b.append(txt(pts[0][0] + 6, pts[0][1] - 6, "%dm" % v, 11))
    # 川（山地から谷口を通り、東へ）
    b.append(poly([(60, 152), (140, 224), (196, 268), (230, 300),
                   (330, 324), (470, 314), (600, 322), (688, 316)], 2.2))
    b.append(txt(250, 344, "川", 12))
    # 地図記号（扇状地の上＝果樹園・畑・桑畑、東の平野＝田）
    for (fn, x, y) in [(sym_kaju, 322, 224), (sym_kaju, 300, 356),
                       (sym_kaju, 372, 372), (sym_hatake, 372, 210),
                       (sym_hatake, 420, 234), (sym_hatake, 340, 392),
                       (sym_kuwa, 296, 246), (sym_hatake, 430, 358)]:
        b.append(fn(x, y))
    for (fn, x, y) in [(sym_ta, 566, 148), (sym_ta, 616, 186),
                       (sym_ta, 562, 224), (sym_ta, 618, 356),
                       (sym_ta, 570, 392), (sym_ta, 622, 430),
                       (sym_ta, 566, 466), (sym_ta, 630, 250)]:
        b.append(fn(x, y))
    b.append(sym_city(506, 168))
    b.append(sym_school(500, 442))
    # 標高点（数値だけ）。等高線どうしの間に置き、値と矛盾しないようにする。
    for (x, y, v) in [(348, 280, "58.4"), (410, 288, "41.2"),
                      (468, 286, "34.6"), (560, 288, "12.3")]:
        b.append(txt(x, y, "・", 15, "middle"))
        b.append(txt(x + 6, y - 6, v, 11))
    b.append(txt(30, 562, "等高線は10mごと。数字は標高点（m）。"
                          "記号は 果樹園・畑・桑畑・田・市役所・小学校。", 12))
    b.append(txt(20, H - 12, NOTE_MAP, 11))
    return svg(W, H, "\n".join(b), "地域調査の模式地形図")


# 資料2：地区別の土地利用（数値だけ）
def chiiki_table():
    return _tbl("資料2　3つの地区の土地利用（％）",
                ["地区", "田", "畑・果樹園", "森林", "宅地・その他"],
                [["Ｐ地区", "2", "58", "31", "9"],
                 ["Ｑ地区", "18", "34", "12", "36"],
                 ["Ｒ地区", "71", "6", "3", "20"]],
                [92, 130, 160, 130, 148])


# 資料3：会話文。答えそのものは言わず、空欄と手がかりだけを置く。
G_TALK = [
    ("ミナト", "この地形図、川が山から出たところを頂点にして、"),
    ("", "東へ半円のように等高線が開いているね。"),
    ("セリ", "標高点をたどると58.4m、41.2m、28.6m、12.3mと"),
    ("", "東へ行くほど下がっている。"),
    ("ミナト", "記号を見ると、頂点に近いほうは（　カ　）が多くて、"),
    ("", "東のほうは田ばかりだ。"),
    ("先生", "土地をつくる粒の大きさがちがうのです。頂点に近いところは"),
    ("", "粒があらく、東へ行くほど細かくなります。"),
    ("セリ", "粒があらいと、水は（　キ　）ということですね。"),
    ("ミナト", "資料2の3つの地区も、同じ順に並べられそうだ。"),
]


def chiiki_talk():
    H = 92 + len(G_TALK) * 30 + 40
    b = [txt(20, 30, "資料3　地域調査での会話", 16, "start", "bold"),
         rect(20, 46, W - 40, H - 96, "none", 1)]
    y = 78
    for (who, s) in G_TALK:
        if who:
            b.append(txt(40, y, who, 13, "start", "bold"))
        b.append(txt(118, y, s, 14))
        y += 30
    b.append(txt(20, H - 14, NOTE_TRAIN, 11))
    return svg(W, int(H), "\n".join(b), "地域調査の会話文")


# ======================================================================
# 第6問　地誌
# ======================================================================
# 資料1：4か国の統計（数値と品目だけ）
def kuni_table():
    return _tbl("資料1　4か国のようす",
                ["国", "一人当たり\nGNI（ドル）", "人口\n（万人）",
                 "輸出額1位の品目", "その品目が\n輸出額に占める割合"],
                [["Ｓ国", "1,150", "3,400", "カカオ豆", "58％"],
                 ["Ｔ国", "6,900", "9,200", "衣類", "31％"],
                 ["Ｕ国", "23,800", "2,100", "原油", "74％"],
                 ["Ｖ国", "41,200", "1,600", "機械類", "22％"]],
                [80, 150, 110, 180, 160])


# 資料2：三角グラフ（産業別人口構成）。国の記号だけを打つ。
#   S 第一次64 第二次12 第三次24 ／ T 22/38/40 ／ U 8/46/46 ／ V 3/21/76
# ア＝Ｓ国、イ＝Ｔ国、ウ＝Ｕ国、エ＝Ｖ国。図には国名を書かない。
G_TRI = [("ア", 64, 12, 24), ("イ", 22, 38, 40),
         ("ウ", 8, 46, 46), ("エ", 3, 21, 76)]


def kuni_triangle():
    H = 600
    S = 430.0
    A = (145.0, 520.0)                       # 第一次100％の頂点
    B = (145.0 + S, 520.0)                   # 第二次100％の頂点
    C = (145.0 + S / 2, 520.0 - S * math.sqrt(3) / 2)   # 第三次100％の頂点

    def pt(w1, w2, w3):
        return (A[0] * w1 + B[0] * w2 + C[0] * w3,
                A[1] * w1 + B[1] * w2 + C[1] * w3)

    b = [txt(20, 30, "資料2　4か国の産業別人口構成（ア〜エ）", 16, "start", "bold"),
         poly([A, B, C], 1.6, "", "none", True)]
    for v in range(20, 100, 20):
        f = v / 100.0
        # 第三次が一定（横の線）
        p1, p2 = pt(1 - f, 0, f), pt(0, 1 - f, f)
        b.append(line(p1[0], p1[1], p2[0], p2[1], 0.5, "3,4"))
        b.append(txt(p2[0] + 12, p2[1] + 4, str(v), 11))          # 右＝第三次
        # 第二次が一定
        q1, q2 = pt(1 - f, f, 0), pt(0, f, 1 - f)
        b.append(line(q1[0], q1[1], q2[0], q2[1], 0.5, "3,4"))
        b.append(txt(q1[0], q1[1] + 20, str(v), 11, "middle"))
        # 第一次が一定
        r1, r2 = pt(f, 1 - f, 0), pt(f, 0, 1 - f)
        b.append(line(r1[0], r1[1], r2[0], r2[1], 0.5, "3,4"))
        b.append(txt(r2[0] - 12, r2[1] + 4, str(v), 11, "end"))    # 左＝第一次
    for (nm, p1, p2, p3) in G_TRI:
        x, y = pt(p1 / 100.0, p2 / 100.0, p3 / 100.0)
        b.append(circle(x, y, 12, "#fff", 1.7))
        b.append(txt(x, y + 5, nm, 13, "middle", "bold"))
    b.append(txt(A[0] + S / 2, 566, "第二次産業（％）→", 12, "middle"))
    b.append(txt(66, 300, "第一次産業（％）", 12, "middle", "normal", "#000", -90))
    b.append(txt(664, 300, "第三次産業（％）", 12, "middle", "normal",
                 "#000", 90))
    b.append(txt(20, H - 12, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(b), "4か国の産業別人口構成")


# 資料3：内陸国の地図。位置関係と交通の記号だけ。説明の文は入れない。
def inland():
    H = 560
    b = [txt(20, 30, "資料3　Ｗ国とそのまわり", 16, "start", "bold"),
         rect(30, 48, 660, 420, "none", 1.2)]
    # 海（右下。枠の内側におさめる）
    b.append(poly([(474, 466), (688, 466), (688, 302), (600, 340),
                   (520, 410)], 1.0, "", "hatch:wave", True))
    b.append(txt(624, 436, "海", 14, "middle", "bold"))
    # 4つの国
    b.append(poly([(180, 110), (400, 100), (420, 250), (200, 268)],
                  1.4, "", "none", True))
    b.append(txt(300, 190, "Ｗ国", 16, "middle", "bold"))
    b.append(poly([(62, 120), (180, 110), (200, 268), (72, 280)],
                  1.2, "", "none", True))
    b.append(txt(130, 200, "Ｘ国", 14, "middle", "bold"))
    b.append(poly([(400, 100), (620, 120), (600, 340), (420, 250)],
                  1.2, "", "none", True))
    b.append(txt(508, 190, "Ｙ国", 14, "middle", "bold"))
    b.append(poly([(200, 268), (420, 250), (520, 410), (240, 430)],
                  1.2, "", "none", True))
    b.append(txt(336, 348, "Ｚ国", 14, "middle", "bold"))
    # 山脈（Ｗ国とＺ国の境）
    for x in range(228, 400, 34):
        b.append(poly([(x, 262), (x + 16, 238), (x + 32, 262)], 1.2,
                      "", "none", True))
    # 鉄道（Ｗ国 → Ｙ国 → 海）
    rail = [(330, 190), (430, 205), (540, 260), (610, 330)]
    b.append(poly(rail, 1.6, "9,5"))
    for k in range(9):
        x = 330 + (610 - 330) * k / 8.0
        y = 190 + (330 - 190) * k / 8.0
        b.append(line(x, y - 6, x, y + 6, 1.0))
    # 道路（Ｗ国 → Ｘ国）
    b.append(poly([(280, 190), (200, 196), (122, 200)], 1.0, "3,5"))
    # 凡例（区分の名まえだけ）
    b.append(rect(30, 484, 660, 46, "none", 1))
    b.append(txt(44, 512, "凡例", 12, "start", "bold"))
    b.append(poly([(100, 506), (150, 506)], 1.6, "9,5"))
    b.append(txt(158, 512, "鉄道", 12))
    b.append(poly([(230, 506), (280, 506)], 1.0, "3,5"))
    b.append(txt(288, 512, "道路", 12))
    b.append(poly([(360, 514), (376, 494), (392, 514)], 1.2, "", "none", True))
    b.append(txt(400, 512, "山脈", 12))
    b.append(rect(470, 498, 26, 16, "hatch:wave", 1))
    b.append(txt(504, 512, "海", 12))
    b.append(txt(20, H - 12, NOTE_MAP, 11))
    return svg(W, H, "\n".join(b), "内陸国とそのまわりの地図")


# 資料4：Ｗ国の輸出額の内訳と、その品目の国際価格の推移（数値だけ）
G_EXP = [("銅", 71), ("コバルト", 12), ("木材", 7), ("その他", 10)]
G_PRICE = [(2016, 62), (2018, 88), (2020, 71), (2022, 104), (2024, 58)]


def inland_data():
    H = 520
    b = [txt(20, 30, "資料4　Ｗ国の輸出額の内訳と、銅の国際価格の動き", 16,
             "start", "bold"),
         txt(20, 74, "輸出額の内訳（％）", 13, "start", "bold")]
    x0, y0, bw, bh = 30.0, 86.0, 640.0, 46.0
    b.append(rect(x0, y0, bw, bh, "none", 1.4))
    x = x0
    for k, (nm, v) in enumerate(G_EXP):
        w = bw * v / 100.0
        b.append(rect(x, y0, w, bh, ["hatch:diag", "hatch:dot",
                                     "hatch:grid", "none"][k], 1))
        # ラベルが重ならないよう、細い区間は上下にずらす
        ly = y0 + bh + (20 if k % 2 == 0 else 38)
        b.append(txt(x + w / 2, ly, "%s %d％" % (nm, v), 12, "middle"))
        if k % 2 == 1:
            b.append(line(x + w / 2, y0 + bh + 2, x + w / 2, ly - 11, 0.6))
        x += w
    b.append(txt(20, 208, "銅の国際価格（2016年を100とした指数）", 13,
                 "start", "bold"))
    ax, ay, aw, ah = 96.0, 430.0, 552.0, 180.0
    b.append(line(ax, ay - ah, ax, ay, 1.1))
    b.append(line(ax, ay, ax + aw, ay, 1.1))
    for v in (50, 75, 100, 125):
        y = ay - ah * (v - 40) / 100.0
        b.append(line(ax - 5, y, ax, y, 0.8))
        b.append(txt(ax - 10, y + 4, str(v), 11, "end"))
    pts = []
    for k, (yr, v) in enumerate(G_PRICE):
        px = ax + aw * k / (len(G_PRICE) - 1.0)
        py = ay - ah * (v - 40) / 100.0
        pts.append((px, py))
        b.append(txt(px, ay + 20, str(yr), 11, "middle"))
        b.append(txt(px + (14 if k == 0 else 0), py - 12, str(v), 11, "middle"))
    b.append(poly(pts, 1.6))
    for (px, py) in pts:
        b.append(circle(px, py, 3.0, "#000", 0.8))
    b.append(txt(20, H - 12, NOTE_FAKE, 11))
    return svg(W, H, "\n".join(b), "内陸国の輸出と価格の資料")


FIGURES = {
    "G1_zone.svg": zone,
    "G1_climo.svg": climo,
    "G1_life.svg": life,
    "G2_map.svg": chiiki_map,
    "G2_table.svg": chiiki_table,
    "G2_talk.svg": chiiki_talk,
    "G6_table.svg": kuni_table,
    "G6_triangle.svg": kuni_triangle,
    "G6_map.svg": inland,
    "G6_data.svg": inland_data,
}
