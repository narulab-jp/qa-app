# -*- coding: utf-8 -*-
"""読み物（解説）に使う図版。

  ・写真は使わない。すべてここの計算で描く。
  ・白黒印刷で読めるように、色ではなく線種と網かけで区別する。
  ・数値を出す図には、架空である旨を図の中に書く。
"""
from figlib import NOTE_FAKE, line, poly, rect, svg, txt

W = 720


def _arrow(x1, y1, x2, y2, w=1.4):
    """右向きの矢印。折れ線と三角の頭で描く。"""
    s = [line(x1, y1, x2 - 8, y2, w)]
    s.append(poly([(x2, y2), (x2 - 10, y2 - 5), (x2 - 10, y2 + 5)],
                  0.8, "", "#000", True))
    return "".join(s)


def _box(x, y, w, h, lines, fs=12.5, fill="none"):
    s = [rect(x, y, w, h, fill, 1.2)]
    n = len(lines)
    for i, t in enumerate(lines):
        s.append(txt(x + w / 2, y + h / 2 + (i - (n - 1) / 2.0) * (fs + 5)
                     + fs * 0.36, t, fs, "middle"))
    return "".join(s)


# ======================================================================
# 図1　調査の流れ
# ======================================================================
def flow():
    H = 300
    b = [txt(20, 26, "図1　地域調査の流れ", 15, "start", "bold")]
    # 箱の中に収まる長さにしてある（幅126・字送り11で11字まで）
    steps = [("問いを決める", "何を知りたいか"),
             ("仮説を立てる", "たぶんこうだ"),
             ("資料を集める", "室内が先、現地は後"),
             ("読み取る", "数と図から事実を"),
             ("まとめる", "事実と考えを分ける")]
    x, y, bw, bh, gap = 24.0, 70.0, 126.0, 74.0, 12.0
    for i, (a, c) in enumerate(steps):
        bx = x + i * (bw + gap)
        b.append(_box(bx, y, bw, bh, [a, c], 11.0))
        if i < len(steps) - 1:
            b.append(_arrow(bx + bw, y + bh / 2, bx + bw + gap, y + bh / 2))
    # 仮説が合わなかったときに戻る道
    x0 = x + 3 * (bw + gap) + bw / 2
    x1 = x + 1 * (bw + gap) + bw / 2
    b.append(line(x0, y + bh, x0, y + bh + 40, 1.2, "6 4"))
    b.append(line(x0, y + bh + 40, x1, y + bh + 40, 1.2, "6 4"))
    b.append(line(x1, y + bh + 40, x1, y + bh + 6, 1.2, "6 4"))
    b.append(poly([(x1, y + bh), (x1 - 5, y + bh + 10), (x1 + 5, y + bh + 10)],
                  0.8, "", "#000", True))
    b.append(txt((x0 + x1) / 2, y + bh + 56,
                 "資料と合わなければ、仮説を立て直してもう一度", 12, "middle"))
    b.append(txt(24, 258, "合わなかったことも結果である。"
                          "そのまま書き残しておく。", 12))
    b.append(txt(20, H - 10,
                 "※ この冊子のために作図した図です。", 10))
    return svg(W, H, "\n".join(b), "地域調査の流れ")


# ======================================================================
# 図2　知りたいことと、見る資料
# ======================================================================
SHIRABE = [
    ["昔と今で何が変わったか", "旧版地形図と現在の地形図を同じ範囲で見比べる"],
    ["土地の成り立ち、水害の起こりやすさ", "土地条件図・治水地形分類図・ハザードマップ"],
    ["どこに何人住んでいるか", "国勢調査（e-Stat で町丁ごとに取れる）"],
    ["何をつくり、どこへ売っているか", "市町村の統計書・農林業センサス・貿易統計"],
    ["いつ、なぜそうしたのか", "その場にいた人への聞き取り"],
]


def shirabe():
    rh, y0 = 44.0, 62.0
    H = int(y0 + rh * (len(SHIRABE) + 1) + 54)
    b = [txt(20, 26, "図2　知りたいことと、見る資料", 15, "start", "bold")]
    cols = [24.0, 300.0, 696.0]
    b.append(rect(cols[0], y0, cols[-1] - cols[0], rh, "none", 1.3))
    b.append(txt((cols[0] + cols[1]) / 2, y0 + rh / 2 + 5, "知りたいこと", 12.5,
                 "middle", "bold"))
    b.append(txt((cols[1] + cols[2]) / 2, y0 + rh / 2 + 5, "見る資料", 12.5,
                 "middle", "bold"))
    for k, row in enumerate(SHIRABE):
        ry = y0 + rh + k * rh
        b.append(rect(cols[0], ry, cols[-1] - cols[0], rh, "none", 0.9))
        b.append(txt(cols[0] + 14, ry + rh / 2 + 5, row[0], 12.5))
        b.append(txt(cols[1] + 14, ry + rh / 2 + 5, row[1], 12.5))
    b.append(line(cols[1], y0, cols[1], y0 + rh * (len(SHIRABE) + 1), 0.9))
    b.append(txt(24, H - 30, "上の4つは室内で手に入る。"
                             "いちばん下だけは、現地に行かないと取れない。", 12))
    b.append(txt(20, H - 10, "※ この冊子のために作図した図です。", 10))
    return svg(W, int(H), "\n".join(b), "知りたいことと見る資料")


# ======================================================================
# 図3　同じ数値でも、実数と割合では見え方が変わる
# ======================================================================
#   架空のＭ市。人口・面積・65歳以上の人数から、密度と割合を出している。
KU = [("ア", 24000, 3.0, 3600), ("イ", 9600, 12.0, 2880),
      ("ウ", 15000, 5.0, 3000), ("エ", 4200, 21.0, 1680),
      ("オ", 7200, 9.0, 1440)]


def jissu():
    # 目盛・棒・注記が重ならないよう、縦を広めに取ってある
    H = 352
    b = [txt(20, 26, "図3　同じ数値でも、実数で見るか割合で見るかで順位が変わる",
             15, "start", "bold"),
         txt(20, 50, "架空のＭ市。左は65歳以上の「人数」、右は「割合」。"
                     "いちばん大きい地区が入れかわる。", 12)]
    # 左：人数の棒
    ax, ay, aw, ah = 70.0, 252.0, 250.0, 150.0
    b.append(txt(24, 84, "65歳以上の人数（人）", 12.5, "start", "bold"))
    b.append(line(ax, ay - ah, ax, ay, 1.0))
    b.append(line(ax, ay, ax + aw, ay, 1.0))
    mx = 4000.0
    for i, (nm, pop, ar, old) in enumerate(KU):
        bx = ax + 14 + i * 46
        h = ah * old / mx
        b.append(rect(bx, ay - h, 30, h, "hatch:diag", 1.0))
        b.append(txt(bx + 15, ay - h - 6, "{:,}".format(old), 10, "middle"))
        b.append(txt(bx + 15, ay + 16, nm, 12, "middle"))
    b.append(txt(ax + 14, ay + 44, "いちばん多いのは ア", 12.5, "start", "bold"))
    # 右：割合の棒
    bx0 = 400.0
    b.append(txt(bx0 - 46, 84, "65歳以上の割合（％）", 12.5, "start", "bold"))
    b.append(line(bx0, ay - ah, bx0, ay, 1.0))
    b.append(line(bx0, ay, bx0 + aw, ay, 1.0))
    for i, (nm, pop, ar, old) in enumerate(KU):
        r = 100.0 * old / pop
        xx = bx0 + 14 + i * 46
        h = ah * r / 50.0
        b.append(rect(xx, ay - h, 30, h, "hatch:grid", 1.0))
        b.append(txt(xx + 15, ay - h - 6, "%.0f" % r, 10, "middle"))
        b.append(txt(xx + 15, ay + 16, nm, 12, "middle"))
    b.append(txt(bx0 + 14, ay + 44, "いちばん高いのは エ", 12.5, "start", "bold"))
    b.append(txt(24, 322, "エは人数では少ないほうだが、人口そのものが少ないので、"
                          "割合では最も高くなる。", 12))
    b.append(txt(20, H - 10, NOTE_FAKE, 10))
    return svg(W, H, "\n".join(b), "実数と割合で順位が変わる")


# ======================================================================
# 図4　資料から言えること・言えないこと
# ======================================================================
IERU = [
    ("言える", "資料に数や記号で示してあることを、そのまま読んだこと",
     "資料2で荒地の記号が増えている"),
    ("言える", "示された数どうしを計算して出したこと",
     "人口は8,200人から3,400人へ、約59％減った"),
    ("言えない", "資料に出てこない数量を持ち出したこと",
     "出荷にかかる時間が短くなった（時間の資料がない）"),
    ("言えない", "一方がもう一方の原因だと決めたこと",
     "人口が減ったから田を手放した（順序を示す資料がない）"),
    ("言えない", "一人の話を地域全体の傾向にしたこと",
     "住民はみな不便だと思っている（聞いたのは3人）"),
]


def ieru():
    rh, y0 = 46.0, 68.0
    H = int(y0 + rh * (len(IERU) + 1) + 56)
    b = [txt(20, 26, "図4　資料から言えること・言えないこと", 15, "start", "bold"),
         txt(20, 50, "選択肢を切るときは、この表のどれに当たるかを見る。", 12)]
    cols = [24.0, 118.0, 400.0, 696.0]
    b.append(rect(cols[0], y0, cols[-1] - cols[0], rh, "none", 1.3))
    for i, hd in enumerate(("", "どういう言い方か", "例")):
        if i == 0:
            continue
        b.append(txt((cols[i] + cols[i + 1]) / 2, y0 + rh / 2 + 5, hd, 12.5,
                     "middle", "bold"))
    b.append(txt((cols[0] + cols[1]) / 2, y0 + rh / 2 + 5, "判定", 12.5,
                 "middle", "bold"))
    for k, (v, how, ex) in enumerate(IERU):
        ry = y0 + rh + k * rh
        b.append(rect(cols[0], ry, cols[-1] - cols[0], rh, "none", 0.9))
        b.append(txt((cols[0] + cols[1]) / 2, ry + rh / 2 + 5, v, 12.5,
                     "middle", "bold"))
        b.append(txt(cols[1] + 12, ry + rh / 2 + 5, how, 12))
        b.append(txt(cols[2] + 12, ry + rh / 2 + 5, ex, 11.5))
    for c in cols[1:-1]:
        b.append(line(c, y0, c, y0 + rh * (len(IERU) + 1), 0.9))
    b.append(txt(24, H - 30, "「言えない」の3つは、選択肢の誤りとして"
                             "そのまま出てくる。", 12))
    b.append(txt(20, H - 10, "※ この冊子のために作図した図です。", 10))
    return svg(W, int(H), "\n".join(b), "言えることと言えないこと")


# ======================================================================
# 図5　組合せ形式の絞り方（本番の形式の解き方で使う）
# ======================================================================
def kumi():
    # 表の下端は 74+42*4=242。説明はその下から書く
    H = 340
    b = [txt(20, 26, "図5　組合せ形式は、決まるところから決める", 15,
             "start", "bold"),
         txt(20, 50, "ア〜ウと品目を結ぶ形。3つを同時に考えない。", 12)]
    # 4列（記号＋選択肢3つ）。枠は右端の696まで引く
    cols = [24.0, 200.0, 365.0, 530.0, 696.0]
    rh, y0 = 42.0, 74.0
    head = ["", "選択肢①", "選択肢②", "選択肢③"]
    rows = [["ア", "米", "米", "野菜"],
            ["イ", "野菜", "果実", "米"],
            ["ウ", "果実", "野菜", "果実"]]
    b.append(rect(cols[0], y0, cols[-1] - cols[0], rh, "none", 1.3))
    for i, hd in enumerate(head):
        b.append(txt((cols[i] + cols[i + 1]) / 2, y0 + rh / 2 + 5, hd, 12.5,
                     "middle", "bold"))
    for k, row in enumerate(rows):
        ry = y0 + rh + k * rh
        b.append(rect(cols[0], ry, cols[-1] - cols[0], rh, "none", 0.9))
        for i, v in enumerate(row):
            b.append(txt((cols[i] + cols[i + 1]) / 2, ry + rh / 2 + 5, v, 12.5,
                         "middle", "bold" if i == 0 else "normal"))
    for c in cols[1:-1]:
        b.append(line(c, y0, c, y0 + rh * (len(rows) + 1), 0.9))
    # 「アが米だと分かれば③が消える」の説明
    b.append(txt(24, 270, "「アは米だ」と1つ決まるだけで、③は消える。", 13,
                 "start", "bold"))
    b.append(txt(24, 294, "残るのは①と②。あとは「イが野菜か果実か」だけを"
                          "見ればよい。", 12.5))
    b.append(txt(24, 316, "3つ全部を当てにいかない。"
                          "いちばん自信のある1つから当てる。", 12.5))
    b.append(txt(20, H - 10, "※ この冊子のために作図した図です。", 10))
    return svg(W, H, "\n".join(b), "組合せ形式の絞り方")


FIGURES = {
    "R1_flow.svg": flow,
    "R2_shirabe.svg": shirabe,
    "R3_jissu.svg": jissu,
    "R4_ieru.svg": ieru,
    "R5_kumi.svg": kumi,
}
