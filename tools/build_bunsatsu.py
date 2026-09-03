# -*- coding: utf-8 -*-
"""指示H Phase D：優先順位版の分冊PDFを作る。

  講の順ではなく、出題頻度×配点で決めた優先度の順に並べ替えた冊子である。
  既存のPDF（講別28冊・図表編4冊・本番形式編4冊）は消さない。
  出力先は CHIRI_QA_20260901\\PDF\\優先順位版\\ で、別の場所に作る。

  組版は既存の冊子と同じにそろえてある。
    A4縦／余白 上下15mm・左右13mm／綴じ代15mm（左）／全ページにページ番号
    白黒（色は使わない）／図は必ず設問と同じページ／解答は別のページ
    一問一答にはチェック欄□□□（3周分）／コアには◎

  1冊の並び
    表紙（この分冊で何をカバーするか）
    → 分野ごとに［扉ページ → 一問一答 → 図表編 → 本番形式編］
    → 解答・解説（分野ごとにまとめて、末尾に）
"""
import base64
import collections
import io
import json
import os
import shutil
import subprocess
import sys
import time

import requests
from websockets.sync.client import connect

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fieldtag                       # noqa: E402
import yomimono                       # noqa: E402

# 指示I：読み物を、それを使う分冊の冒頭に入れる。
#   r29  … A5（地域調査）を解くための読み物 → 第1分冊
#   rfmt … 本番形式編の答え方 → 冊D・冊Fの問が最初に出てくる第2分冊
READ_AT = {1: "r29", 2: "rfmt"}

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, "Downloads", "CHIRI_QA_20260901")
PDF_DIR = os.path.join(BASE, "PDF", "優先順位版")
HTML_DIR = os.path.join(BASE, "HTML", "優先順位版")
PLAN = os.path.join(BASE, "分析", "bunsatsu_plan.json")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DBG = 9311

PW, PH = 210.0, 297.0
M_TOP, M_BOT, M_R, M_L = 15.0, 15.0, 13.0, 28.0      # 左＝13mm＋綴じ代15mm
CW = PW - M_L - M_R
CH = PH - M_TOP - M_BOT
HEAD_H, FOOT_H = 8.0, 8.0
BODY_H = CH - HEAD_H - FOOT_H
SAFE_H = BODY_H - 10.0   # 実測とのずれで最後の行が切れないよう余裕を持たせる

MARK = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨"]
IMP = {"S": "★S", "A": "◆A", "B": "▽B"}

NOTICE = (
    "本冊子は共通テストの練習用に独自に作成した問題です。"
    "教科書・資料集・過去問の文章や図を転載または模写したものではありません。"
    "図はすべてこの冊子のために作図したもので、地形図は訓練用の模式図であり"
    "実在の地域ではありません。雨温図・統計は架空の地点および架空の国の数値です。"
    "実在の統計を判断の根拠にしないでください。"
)

# 分野の扉ページに書く「この分野で問われること」
ABOUT = {
    "A5": "調査の問いと仮説の立て方、資料の選び方、指標のつくり方、"
          "資料から言えることの限界まで。本番では大問1つを占める。",
    "A1": "地図の図法、GIS、地形図の読図。単独で問われることは少ないが、"
          "地域調査や自然環境の大問の中で道具として使う。",
    "A2": "衣食住・言語・宗教など生活文化の地域差と、"
          "その背景にある自然環境と歴史。",
    "A3": "地球温暖化・砂漠化などの環境問題、食料・人口・格差といった"
          "地球的課題と、その解決に向けた国際協力。",
    "A4": "地震・火山・風水害などの自然災害と、地形条件・ハザードマップ・"
          "避難のしくみ。",
    "B1": "プレート運動がつくる大地形と、河川・海岸・氷河などがつくる小地形。"
          "地形図での見分け方まで。",
    "B2": "気温と降水の分布を決めるしくみ、気候区分、"
          "それに対応する植生と土壌。",
    "B3": "陸水と海洋の分布、海流、水資源の偏りと利用。",
    "B4": "エネルギー資源と鉱産資源の分布・産出・貿易、"
          "発電の構成の国ごとの違い。",
    "B5": "農業の地域類型、主要作物の生産と貿易、林業と水産業。",
    "B6": "工業の立地条件、工業地域の形成と移り変わり、主要国の産業構造。",
    "B7": "商業の立地、観光の地域差、第三次産業の比重。",
    "B8": "交通機関の特色と使い分け、通信網の広がりと情報の格差。",
    "B9": "貿易の構造と相手先、資本の移動、経済統合。",
    "B10": "人口の分布と増減、人口転換、人口ピラミッド、移動と都市への集中。",
    "B11": "村落の立地と形態、都市の内部構造と都市圏、都市問題。",
    "B12": "国家の領域と国境、民族と言語の分布、地域紛争と国際機構。",
    "B13": "各地域の自然・産業・人口・都市を、地域ごとにまとめて確かめる。",
}
PREREQ_ABOUT = (
    "縮尺・等高線・尾根と谷・地図記号・主題図の読み方。"
    "この分野は単独ではほとんど出題されないが、"
    "この分冊のA5（地域調査）を解くための道具になるので、ここに置いてある。"
    "分野としての優先度は「余力」のままで、第5分冊にも同じ分野の問がある。"
)

CSS = """
@page { size: A4 portrait; margin: %(MT)smm %(MR)smm %(MB)smm %(ML)smm; }
* { box-sizing: border-box; }
html, body { margin:0; padding:0; }
body { font-family:"Yu Gothic UI","Meiryo","Hiragino Sans","MS PGothic",sans-serif;
       color:#000; -webkit-print-color-adjust:exact; }
.page { position:relative; height:%(CH)smm; width:100%%;
        page-break-after:always; overflow:hidden; }
.page:last-child { page-break-after:auto; }
.phead { height:%(HH)smm; font-size:8.5pt; border-bottom:1.2pt solid #000;
         display:flex; justify-content:space-between; align-items:flex-end;
         padding-bottom:1mm; }
.pbody { height:%(BH)smm; overflow:hidden; padding-top:3mm; }
.pfoot { position:absolute; bottom:0; left:0; right:0; height:%(FH)smm;
         font-size:8.5pt; text-align:center; border-top:0.5pt solid #000;
         padding-top:1mm; }
h1.bt { font-size:17pt; margin:16mm 0 2mm; }
h2.bs { font-size:11pt; margin:0 0 6mm; font-weight:normal; }
.lead { font-size:10pt; line-height:1.7; margin:0 0 5mm; }
.notice { border:0.8pt solid #000; padding:3.5mm; font-size:8.5pt;
          line-height:1.6; margin-top:5mm; }
.howto { font-size:9.5pt; line-height:1.75; margin-top:5mm; }
.sumtbl { width:100%%; border-collapse:collapse; margin:0 0 5mm; }
.sumtbl th, .sumtbl td { border:0.6pt solid #000; padding:1.6mm 1.6mm;
                         font-size:9.5pt; }
.sumtbl th { background:#e8e8e8; font-weight:normal; text-align:center; }
.sumtbl td.c { text-align:center; }
/* 分野の扉 */
.door { margin-top:26mm; }
.door .dn { font-size:9.5pt; }
.door .dt { font-size:20pt; font-weight:bold; margin:2mm 0 5mm; }
.door .dd { font-size:10.5pt; line-height:1.8; margin-bottom:6mm; }
/* 一問一答 */
.ihead, .irow { display:flex; width:100%%; }
.ihead > div, .irow > div { border:0.5pt solid #000; border-left:none;
                            padding:1.3mm 1.4mm; }
.ihead > div:first-child, .irow > div:first-child { border-left:0.5pt solid #000; }
.irow > div { border-top:none; }
.ihead > div { background:#e8e8e8; font-size:8.5pt; text-align:center; }
.irow > div { font-size:10pt; line-height:1.5; }
/* 幅の決まった列は縮ませない。縮ませると、問題文の長さによって
   列の位置が行ごとにずれ、「理由」が「理／由」と折り返してしまう。 */
.w1 { flex:0 0 10mm; text-align:center; font-size:9pt; }
.w2 { flex:0 0 16mm; text-align:center; font-size:9pt; white-space:nowrap; }
.w3 { flex:0 0 13mm; text-align:center; font-size:9pt; white-space:nowrap; }
.w4 { flex:1 1 0; min-width:0; }
.w5 { flex:0 0 17mm; text-align:center; font-size:12pt; letter-spacing:0.5mm;
      white-space:nowrap; }
.aw3 { flex:0 0 62mm; }
.aw4 { flex:1 1 0; min-width:0; }
.secline { font-size:9.5pt; font-weight:bold; background:#d4d4d4;
           border:0.5pt solid #000; border-top:none; padding:1.3mm 2mm; }
.kindline { font-size:10pt; font-weight:bold; margin:0 0 2.5mm;
            border-left:3pt solid #000; padding-left:2.5mm; }
/* 図表編・本番形式編 */
.figwrap { margin:0 0 3mm; text-align:center; }
.figwrap img { display:block; margin:0 auto; border:0.5pt solid #000; }
.figcap { font-size:8.5pt; margin:1mm 0 0; text-align:left; }
.qb { margin:0 0 4mm; }
.qb .qh { font-size:9pt; margin:0 0 1mm; }
.qb .qt { font-size:10.5pt; line-height:1.6; margin:0 0 1.5mm; }
.qb .ch { font-size:10pt; line-height:1.55; margin:0 0 0.6mm; padding-left:6mm;
          text-indent:-6mm; }
.qb .mark { font-size:9pt; margin-top:1mm; }
.qb .mark b { font-weight:normal; border:0.6pt solid #000; padding:0 4mm;
              margin-left:2mm; }
/* 読み物（分冊の冒頭に入れる解説） */
.rtx { font-size:10.5pt; line-height:1.8; margin:0 0 3.5mm; text-align:justify; }
.rsub { font-size:11pt; font-weight:bold; margin:3mm 0 1.5mm; }
.rli { font-size:10.5pt; line-height:1.75; margin:0 0 3.5mm; padding-left:6mm; }
.rli li { margin:0 0 1mm; }
.rbox { border:0.9pt solid #000; padding:3mm 4mm; margin:0 0 4mm;
        font-size:10pt; line-height:1.7; }
.rbox ul { margin:1.5mm 0 0; padding-left:5mm; }
.ab { margin:0 0 3.5mm; font-size:9.5pt; line-height:1.6; }
.ab .ah { font-weight:bold; }
.ab .ag { font-size:9pt; }
"""


class C(object):
    def __init__(self, ws):
        self.ws = ws
        self.i = 0

    def call(self, m, p=None):
        self.i += 1
        self.ws.send(json.dumps({"id": self.i, "method": m, "params": p or {}}))
        while True:
            d = json.loads(self.ws.recv())
            if d.get("id") == self.i:
                if "error" in d:
                    raise RuntimeError(d["error"])
                return d.get("result", {})

    def ev(self, e):
        r = self.call("Runtime.evaluate",
                      {"expression": e, "awaitPromise": True,
                       "returnByValue": True})
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"],
                                          ensure_ascii=False)[:300])
        return r.get("result", {}).get("value")


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def sub_of(book):
    """表示用の副題。ファイル名では＿でつないでいる区切りを、全角空白に戻す。"""
    return (book["sub"] or "").replace("_", "　")


def split_note(sec):
    if not sec.get("split"):
        return ""
    return ("　なお、この分野は1冊に収まらないため2冊に分けており、"
            "配点とスコアは実測値を問数の比で割った値である。")


def css():
    return CSS % dict(MT=M_TOP, MB=M_BOT, ML=M_L, MR=M_R, CH=CH,
                      HH=HEAD_H, FH=FOOT_H, BH=BODY_H)


# ----------------------------------------------------------------------
# 部品
# ----------------------------------------------------------------------
IHEAD = ('<div class="ihead"><div class="w1">通し</div><div class="w2">重要度</div>'
         '<div class="w3">種別</div><div class="w4">問　題</div>'
         '<div class="w5">チェック</div></div>')
AHEAD = ('<div class="ihead"><div class="w1">通し</div><div class="w2">重要度</div>'
         '<div class="aw3">解　答</div><div class="aw4">解　説</div></div>')


def i_row(q):
    return ('<div class="irow"><div class="w1">%d</div><div class="w2">%s</div>'
            '<div class="w3">%s</div><div class="w4">%s</div>'
            '<div class="w5">□□□</div></div>'
            % (q["seq"], ("◎" if q.get("core") else "") + IMP[q["level"]],
               q["type"], esc(q["q"])))


def i_arow(q):
    return ('<div class="irow"><div class="w1">%d</div><div class="w2">%s</div>'
            '<div class="aw3">%s</div><div class="aw4">%s</div></div>'
            % (q["seq"], ("◎" if q.get("core") else "") + IMP[q["level"]],
               esc(q["a"]), esc(q.get("exp", ""))))


def fig_size(path, single, scale=1.0):
    t = io.open(os.path.join(ROOT, path.replace("/", os.sep)),
                encoding="utf-8").read()
    vb = t.split('viewBox="')[1].split('"')[0].split()
    w, h = float(vb[2]), float(vb[3])
    mw = min(CW, (150.0 if single else 78.0) * w / h) * scale
    return mw, mw * h / w


def fig_block(figs, scale=1.0):
    single = (len(figs) == 1)
    s = ['<div class="figwrap">']
    for f in figs:
        mw, mh = fig_size(f, single, scale)
        s.append('<img src="%s" style="width:%.1fmm;height:%.1fmm">'
                 % ("file:///" + os.path.join(ROOT, f.replace("/", os.sep))
                    .replace("\\", "/"), mw, mh))
    s.append('<p class="figcap">※ この冊子のために作図した図です。'
             '実在の地域・地点・国ではありません。</p></div>')
    return "\n".join(s)


def q_block(q):
    # 通し番号は科目ごとの番号なので、一問一答の番号と見分けがつくよう
    # 「図表編 通し126」のように種別を添える。番号自体は振り直していない。
    s = ['<div class="qb">']
    s.append('<div class="qh">%s 通し%d　［%s］　重要度 %s</div>'
             % (q["_kind"], q["seq"], esc(q.get("skill", "")), q["level"]))
    s.append('<div class="qt">%s</div>' % esc(q["q"]))
    for i, ch in enumerate(q["choices"]):
        s.append('<div class="ch">%s　%s</div>' % (MARK[i], esc(ch)))
    s.append('<div class="mark">解答欄<b>　</b></div></div>')
    return "\n".join(s)


def a_block(q):
    g = "".join("<div class='ag'>・%s</div>" % esc(x)
                for x in (q.get("grounds") or []))
    return ('<div class="ab"><span class="ah">%s 通し%d　正解 %s</span>'
            '<div>%s</div>%s%s</div>'
            % (q["_kind"], q["seq"], MARK[q["answer"]], esc(q["exp"]),
               "<div class='ag'>根拠</div>" if g else "", g))


# ----------------------------------------------------------------------
def measure(c, blocks):
    # display:flow-root を付けておかないと、段落の下マージンが
    # 外側の div の外へ抜けてしまい、高さを実際より小さく測ってしまう。
    # そのまま詰めると、ページの最後の行が紙面からはみ出して切れる。
    body = ('<div style="width:%.2fmm">' % CW +
            "".join('<div id="b%d" style="display:flow-root">%s</div>' % (i, b)
                    for i, b in enumerate(blocks)) +
            '</div><div id="cal" style="height:100mm"></div>')
    html = ("<!doctype html><meta charset='utf-8'><style>%s</style><body>%s</body>"
            % (css(), body))
    p = os.path.join(HTML_DIR, "_measure.html")
    io.open(p, "w", encoding="utf-8", newline="\n").write(html)
    c.call("Page.navigate", {"url": "file:///" + p.replace("\\", "/")})
    time.sleep(1.4)
    for _ in range(40):
        if c.ev("document.readyState==='complete' && "
                "Array.prototype.every.call(document.images,function(i){"
                "return i.complete && i.naturalWidth>0;})"):
            break
        time.sleep(0.4)
    px = c.ev("document.getElementById('cal').getBoundingClientRect().height") / 100.0
    return [c.ev("document.getElementById('b%d').getBoundingClientRect().height" % i) / px
            for i in range(len(blocks))]


def pack(items, heads=None):
    """(html, 高さ) の並びをページに詰める。heads があれば各ページの先頭に置く。"""
    pages, cur, used = [], [], 0.0
    hh = heads[1] if heads else 0.0
    for (b, h) in items:
        if used + h > SAFE_H and cur:
            pages.append("".join(cur))
            cur, used = [], 0.0
        if not cur and heads:
            cur.append(heads[0])
            used += hh
        cur.append(b)
        used += h
    if cur:
        pages.append("".join(cur))
    return pages


# ----------------------------------------------------------------------
def door(sec, book):
    pre = sec.get("prereq")
    return ('<div class="door">'
            '<div class="dn">第%d分冊　%s%s</div>'
            '<div class="dt">%s　%s</div>'
            '<div class="dd">%s</div>'
            '<table class="sumtbl">'
            '<tr><th>問数</th><th>一問一答</th><th>図表編</th><th>本番形式編</th>'
            '<th>1回あたり配点</th><th>優先度スコア</th><th>1周の目安</th></tr>'
            '<tr><td class="c">%d問</td><td class="c">%d</td><td class="c">%d</td>'
            '<td class="c">%d</td><td class="c">%s</td><td class="c">%s</td>'
            '<td class="c">約%d分</td></tr></table>'
            '<div class="lead">%s</div>'
            '</div>'
            % (book["no"], book["name"],
               ("　" + sub_of(book)) if book["sub"] else "",
               sec["field"], esc(sec["name"]),
               esc(PREREQ_ABOUT if pre else ABOUT[sec["field"]]),
               sec["n"], sec["ichimon"], sec["zuhyo"], sec["honban"],
               "—" if pre else "%.1f点" % sec["haiten"],
               "—" if pre else "%.1f" % sec["score"],
               sec["minutes"],
               "この分野は単独では出題実績がほとんどない。"
               "点をとるための分野ではなく、前の分野を解くための道具として通す。"
               if pre else
               "「1回あたり配点」は、新課程の本試験・追試験4回で"
               "この分野が1回あたり平均何点を占めていたかの実測値である。"
               "この分冊で何点とれるかを示すものではない。" + split_note(sec)))


def front(book):
    rows = ""
    for s in book["sections"]:
        rows += ('<tr><td>%s %s%s%s</td><td class="c">%d</td>'
                 '<td class="c">%s</td><td class="c">%s</td>'
                 '<td class="c">約%d分</td></tr>'
                 % (s["field"], esc(s["name"]),
                    "（前提技能）" if s.get("prereq") else "",
                    "※" if s.get("split") else "",
                    s["n"], "—" if s.get("prereq") else "%.1f点" % s["haiten"],
                    "—" if s.get("prereq") else "%.1f" % s["score"],
                    s["minutes"]))
    return ('<h1 class="bt">共通テスト地理　優先順位版　第%d分冊</h1>'
            '<h2 class="bs">%s%s　（優先度：%s）</h2>'
            '<p class="lead">この冊子は、教科書の講の順ではなく、'
            '<b>出題される見こみ×配点</b>の順に並べ替えたものです。'
            '2024年度の地理B（本試・追試）と2025・2026年度の地理総合／地理探究'
            '（本試・追試）の計6回・180マーク・600点を1マークずつ数え、'
            'そこから決めた順に並べてあります。'
            '前から順にやってください。時間が足りずに最後まで行けなかったとき、'
            '残るのが<b>いちばん出にくいところ</b>になるように組んであります。</p>'
            '<table class="sumtbl">'
            '<tr><th>分　野</th><th>問数</th><th>1回あたり配点</th>'
            '<th>優先度スコア</th><th>1周の目安</th></tr>%s'
            '<tr><th>合　計</th><th>%d問</th><th>%.1f点分</th><th>%.1f</th>'
            '<th>約%.1f時間</th></tr></table>'
            '<div class="lead">この分冊は、本番100点のうち'
            '<b>%.1f点分の範囲をカバーします</b>。'
            'これは「%.1f点とれる」という意味ではありません。'
            'この分冊に入っている分野が、本番で平均して%.1f点ぶん出題されている、'
            'という実測値です。%s</div>'
            '<div class="howto">'
            'チェック欄□□□は3周分です。1周目＝解けたか仕分ける／'
            '2周目＝空欄の残ったものだけ／3周目＝最後まで残ったものだけ。<br>'
            '重要度は記号で示しています（★S＝中核／◆A＝標準／▽B＝余力）。'
            '<b>◎</b>はコア問題で、2025・2026年度の本試験で実際に必要とされた'
            '知識にだけ付けてあります。<br>'
            '解答・解説は冊子の末尾にまとめてあります。'
            '</div>'
            '<div class="notice">%s</div>'
            % (book["no"], book["name"],
               ("　" + sub_of(book)) if book["sub"] else "",
               book["band"], rows, book["n"], book["haiten"], book["score"],
               book["minutes"] / 60.0,
               book["haiten"], book["haiten"], book["haiten"],
               ("　※の分野は1冊に収まらないため2冊に分けており、"
                "配点とスコアは実測値を問数の比で割った値です。"
                if any(s.get("split") for s in book["sections"]) else ""),
               esc(NOTICE)))


# ----------------------------------------------------------------------
def reading_blocks(rid):
    """読み物の本文を、分冊の冒頭に入れるための部品にする。
       本文そのものは yomimono.py にあり、紙の解説PDFと同じものを使う。"""
    doc = [d for d in yomimono.READINGS if d["id"] == rid][0]
    out = ['<div class="door"><div class="dn">この分冊を始める前に読む</div>'
           '<div class="dt">%s</div><div class="dd">%s</div>'
           '<div class="lead">%s</div>'
           '<div class="lead">読むのにかかる時間の目安は約%d分です。'
           '同じものは PDF＼地理解説_… と、アプリの「読む」にもあります。</div>'
           '</div>'
           % (esc(doc["title"]), esc(doc["sub"]), esc(doc["lead"]),
              doc["minutes"])]
    for (title, items) in doc["sections"]:
        out.append('<div class="kindline">%s</div>' % esc(title))
        for it in items:
            if it[0] == "p":
                out.append('<p class="rtx">%s</p>' % rich(it[1]))
            elif it[0] == "h":
                out.append('<div class="rsub">%s</div>' % esc(it[1]))
            elif it[0] == "ul":
                out.append('<ul class="rli">%s</ul>'
                           % "".join("<li>%s</li>" % rich(x) for x in it[1]))
            elif it[0] == "box":
                out.append('<div class="rbox"><b>%s</b><ul>%s</ul></div>'
                           % (esc(it[1]),
                              "".join("<li>%s</li>" % rich(x) for x in it[2])))
            elif it[0] == "fig":
                mw, mh = fig_size(it[1], True, 0.62)
                out.append('<div class="figwrap"><img src="%s" '
                           'style="width:%.1fmm;height:%.1fmm"></div>'
                           % ("file:///" + os.path.join(
                               ROOT, it[1].replace("/", os.sep)).replace("\\", "/"),
                              mw, mh))
    return out


def rich(s):
    """**ここ** を太字にする。"""
    out, bold = [], False
    for part in esc(s).split("**"):
        out.append(("<b>%s</b>" % part) if bold and part else part)
        bold = not bold
    return "".join(out)


def build_book(c, book, qmap):
    body = [front(book)]
    ans = []

    # 指示I：読む材料がある分冊は、問題より先に読み物を置く
    rid = READ_AT.get(book["no"])
    if rid:
        blocks = reading_blocks(rid)
        hs = measure(c, blocks)
        body += pack(list(zip(blocks, hs)))

    for sec in book["sections"]:
        # どの問を入れるかは bunsatsu_plan.json が持っている。
        # ここで決め直すと、割り当ての規則が2か所に散らばるため。
        want = set((k, s) for (k, s) in sec["items"])
        mine = [q for q in qmap if (q["_kind"], q["seq"]) in want]
        assert len(mine) == len(want), (book["no"], sec["field"],
                                        len(mine), len(want))
        body.append(door(sec, book))

        # ---- 一問一答 ----
        ich = sorted([q for q in mine if q["_kind"] == "一問一答"],
                     key=lambda x: x["seq"])
        if ich:
            blocks = [i_row(q) for q in ich]
            hs = measure(c, [IHEAD] + blocks)
            head = ('<div class="kindline">一問一答（%d問）</div>' % len(ich)) + IHEAD
            pgs = pack(list(zip(blocks, hs[1:])), (IHEAD, hs[0]))
            pgs[0] = ('<div class="kindline">一問一答（%d問）</div>' % len(ich)) + pgs[0]
            body += pgs
            ablocks = [i_arow(q) for q in ich]
            ahs = measure(c, [AHEAD] + ablocks)
            apgs = pack(list(zip(ablocks, ahs[1:])), (AHEAD, ahs[0]))
            apgs[0] = ('<div class="kindline">%s %s　一問一答（%d問）の解答</div>'
                       % (sec["field"], esc(sec["name"]), len(ich))) + apgs[0]
            ans += apgs
            del head

        # ---- 図表編・本番形式編 ----
        for kind in ("図表編", "本番形式編"):
            arr = sorted([q for q in mine if q["_kind"] == kind],
                         key=lambda x: x["seq"])
            if not arr:
                continue
            sets = []
            for q in arr:
                if not sets or sets[-1][0] != q["setId"]:
                    sets.append((q["setId"], q["figures"], []))
                sets[-1][2].append(q)
            blocks, tag = [], []
            for (sid, figs, qs) in sets:
                blocks.append(fig_block(figs))
                tag.append(("fig", sid))
                for q in qs:
                    blocks.append(q_block(q))
                    tag.append(("q", sid))
            hs = measure(c, blocks)
            pages = []
            i = 0
            while i < len(blocks):
                kd, sid = tag[i]
                if kd != "fig":
                    i += 1
                    continue
                fig_html, fig_h = blocks[i], hs[i]
                qidx = [j for j in range(i + 1, len(blocks))
                        if tag[j][0] == "q" and tag[j][1] == sid]
                need = max([hs[j] for j in qidx]) if qidx else 0.0
                if fig_h + need > SAFE_H:
                    figs = [f for (s2, f, _q) in sets if s2 == sid][0]
                    sc = min(1.0, (SAFE_H - 6.0) / fig_h)
                    pages.append(fig_block(figs, sc))
                    note = ('<p class="figcap" style="margin:0 0 3mm">'
                            '※ 資料は前のページにあります。</p>')
                    cur, used = [], 0.0
                    for j in qidx:
                        if used + hs[j] > SAFE_H and cur:
                            pages.append("".join(cur))
                            cur, used = [], 0.0
                        if not cur:
                            cur.append(note)
                            used += 6.0
                        cur.append(blocks[j])
                        used += hs[j]
                    if cur:
                        pages.append("".join(cur))
                    i = (qidx[-1] + 1) if qidx else (i + 1)
                    continue
                j = i + 1
                cur, used = [fig_html], fig_h
                while j < len(blocks) and tag[j][0] == "q" and tag[j][1] == sid:
                    if used + hs[j] > SAFE_H and len(cur) > 1:
                        pages.append("".join(cur))
                        cur, used = [fig_html], fig_h
                    cur.append(blocks[j])
                    used += hs[j]
                    j += 1
                pages.append("".join(cur))
                i = j
            pages[0] = ('<div class="kindline">%s（%d問）</div>' % (kind, len(arr))) + pages[0]
            body += pages

            ablocks = [a_block(q) for q in arr]
            ahs = measure(c, ablocks)
            apgs = pack(list(zip(ablocks, ahs)))
            apgs[0] = ('<div class="kindline">%s %s　%s（%d問）の解答</div>'
                       % (sec["field"], esc(sec["name"]), kind, len(arr))) + apgs[0]
            ans += apgs

    head = ('<h2 style="font-size:13pt;margin:0 0 5mm">解答・解説</h2>'
            '<p class="lead">分野ごと、種別ごとに、冊子に出てきた順で並べてあります。'
            '番号は問の通し番号です。</p>')
    body += [head] + ans

    n = len(body)
    title = "第%d分冊　%s%s" % (book["no"], book["name"],
                                ("　" + sub_of(book)) if book["sub"] else "")
    out = []
    for k, b in enumerate(body):
        out.append('<div class="page">'
                   '<div class="phead"><span>共通テスト地理　優先順位版</span>'
                   '<span>%s（%s）</span></div>'
                   '<div class="pbody">%s</div>'
                   '<div class="pfoot">%s　%d/%d</div></div>'
                   % (title, book["band"], b, title, k + 1, n))
    html = ("<!doctype html><meta charset='utf-8'><title>%s</title>"
            "<style>%s</style><body>%s</body>" % (title, css(), "".join(out)))
    hp = os.path.join(HTML_DIR, book["filename"] + ".html")
    io.open(hp, "w", encoding="utf-8", newline="\n").write(html)

    c.call("Page.navigate", {"url": "file:///" + hp.replace("\\", "/")})
    time.sleep(2.0)
    for _ in range(60):
        if c.ev("document.readyState==='complete' && "
                "Array.prototype.every.call(document.images,function(i){"
                "return i.complete && i.naturalWidth>0;})"):
            break
        time.sleep(0.5)
    d = c.call("Page.printToPDF", {
        "printBackground": True, "preferCSSPageSize": True,
        "paperWidth": 8.27, "paperHeight": 11.69,
        "marginTop": 0, "marginBottom": 0, "marginLeft": 0, "marginRight": 0,
        "displayHeaderFooter": False})
    pp = os.path.join(PDF_DIR, book["filename"] + ".pdf")
    io.open(pp, "wb").write(base64.b64decode(d["data"]))
    return pp, n


def load_all():
    out = []
    for sid, kind, fn in (("chiri", "一問一答", "chiri.json"),
                          ("chiri-zuhyo", "図表編", "chiri-zuhyo.json"),
                          ("chiri-honban", "本番形式編", "chiri-honban.json")):
        d = json.loads(io.open(os.path.join(ROOT, "data", fn),
                               encoding="utf-8").read())
        for u in d["units"]:
            for q in u["questions"]:
                q["_kind"] = kind
                q["_unit"] = u["id"]
                out.append(q)
    return out


def main():
    for d in (PDF_DIR, HTML_DIR):
        if not os.path.isdir(d):
            os.makedirs(d)
    plan = json.loads(io.open(PLAN, encoding="utf-8").read())
    qs = load_all()
    # 割り当ては計画側が持っている一覧のとおり。抜けと重複だけ先に見る。
    seen = collections.Counter()
    for b in plan["books"]:
        n = 0
        for sec in b["sections"]:
            for (k, s) in sec["items"]:
                seen[(k, s)] += 1
                n += 1
        assert n == b["n"], (b["no"], n, b["n"])
    have = set((q["_kind"], q["seq"]) for q in qs)
    assert set(seen) == have, ("計画と教材が合わない",
                               sorted(have - set(seen))[:5],
                               sorted(set(seen) - have)[:5])
    dup = [k for k, v in seen.items() if v > 1]
    assert not dup, ("2冊に入っている問がある", dup[:5])

    ud = os.path.join(os.environ["TEMP"], "edge_bunsatsu")
    shutil.rmtree(ud, ignore_errors=True)
    p = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu",
                          "--remote-debugging-port=%d" % DBG,
                          "--user-data-dir=" + ud, "--no-first-run",
                          "--allow-file-access-from-files",
                          "--run-all-compositor-stages-before-draw",
                          "about:blank"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws = None
        for _ in range(80):
            time.sleep(0.5)
            try:
                for t in requests.get("http://127.0.0.1:%d/json/list" % DBG,
                                      timeout=2).json():
                    if t["type"] == "page":
                        ws = t["webSocketDebuggerUrl"]
                if ws:
                    break
            except Exception:
                pass
        c = C(connect(ws, max_size=None))
        c.call("Page.enable")
        c.call("Runtime.enable")
        c.call("Emulation.setEmulatedMedia", {"media": "print"})
        only = sys.argv[1:]
        for b in plan["books"]:
            if only and str(b["no"]) not in only:
                continue
            pp, n = build_book(c, b, qs)
            print("  %-44s %3dページ %8d bytes"
                  % (os.path.basename(pp), n, os.path.getsize(pp)))
    finally:
        try:
            p.kill()
        except Exception:
            pass
        mp = os.path.join(HTML_DIR, "_measure.html")
        if os.path.isfile(mp):
            os.remove(mp)
    print("PDF を %s に出力した" % PDF_DIR)


if __name__ == "__main__":
    main()
