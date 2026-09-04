# -*- coding: utf-8 -*-
"""図表・読図編のPDF（紙で解く版）を作る。

  ・PDFの部品は使わない。HTMLを組んで Edge のヘッドレス印刷で出す。
  ・A4縦／余白 上下15mm・左右13mm／綴じ代15mm（左）／全ページにページ番号。
  ・図は必ず設問と同じページに置く。1ページに入りきらないときは、
    次のページに同じ図をもう一度置く（ページをまたぐと解けないため）。
  ・解答・解説は別のページにまとめる。
  ・組み上げる前に、ブラウザで各部品の高さを実測してページに詰める。
"""
import base64
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
import zuhyo_bank as bank        # noqa: E402

HOME = os.path.expanduser("~")          # 公開前にユーザー名を除去
BASE = os.path.join(HOME, "Downloads", "CHIRI_QA_20260901")
PDF_DIR = os.path.join(BASE, "PDF")
HTML_DIR = os.path.join(BASE, "HTML")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DBG = 9301

# 組版（mm）
PW, PH = 210.0, 297.0
M_TOP, M_BOT, M_R, M_L = 15.0, 15.0, 13.0, 28.0      # 左＝13mm＋綴じ代15mm
CW = PW - M_L - M_R                                   # 本文の幅 169mm
CH = PH - M_TOP - M_BOT                               # 本文の高さ 267mm
HEAD_H, FOOT_H = 8.0, 8.0
BODY_H = CH - HEAD_H - FOOT_H                         # 詰められる高さ
# 実測した高さと実際の描画には少しずれが出る。ぎりぎりで詰めると
# 最後の1行が紙面からはみ出して消えるので、安全のぶんを引いておく。
SAFE_H = BODY_H - 10.0   # 実測とのずれで最後の行が切れないよう余裕を持たせる

NOTICE = (
    "本冊子は共通テストと同じマーク式の練習用に、独自に作成した図表・読図問題です。"
    "教科書・資料集・過去問の図を転載または模写したものではありません。"
    "図はすべてこの冊子のために作図したものです。"
    "地形図は訓練用の模式図であり、実在の地域ではありません。"
    "雨温図・統計は架空の地点および架空の国の数値であり、実在の地点・国ではありません。"
    "実在の統計を判断の根拠にしないでください。"
)
MARK = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨"]

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
h1.bt { font-size:16pt; margin:24mm 0 6mm; }
.lead { font-size:10pt; line-height:1.7; margin:0 0 6mm; }
.notice { border:0.8pt solid #000; padding:4mm; font-size:9pt; line-height:1.65; }
.howto { font-size:10pt; line-height:1.8; margin-top:8mm; }
.howto li { margin:0 0 2mm; }
.figwrap { margin:0 0 3mm; text-align:center; }
.figwrap img { display:block; margin:0 auto; border:0.5pt solid #000; }
.figcap { font-size:8.5pt; margin:1mm 0 0; text-align:left; }
.qb { margin:0 0 4mm; break-inside:avoid; }
.qb .qh { font-size:9pt; margin:0 0 1mm; }
.qb .qt { font-size:10.5pt; line-height:1.6; margin:0 0 1.5mm; }
.qb .ch { font-size:10pt; line-height:1.55; margin:0 0 0.6mm; padding-left:6mm;
          text-indent:-6mm; }
.qb .mark { font-size:9pt; margin-top:1mm; }
.qb .mark b { font-weight:normal; border:0.6pt solid #000; padding:0 4mm; margin-left:2mm; }
.ab { margin:0 0 3.5mm; break-inside:avoid; font-size:9.5pt; line-height:1.6; }
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
                      {"expression": e, "awaitPromise": True, "returnByValue": True})
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"], ensure_ascii=False)[:300])
        return r.get("result", {}).get("value")


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def fig_size(path, single, scale=1.0):
    """SVG の viewBox から、印刷したときの大きさ（mm）を決める。"""
    t = io.open(os.path.join(ROOT, path.replace("/", os.sep)), encoding="utf-8").read()
    vb = t.split('viewBox="')[1].split('"')[0].split()
    w, h = float(vb[2]), float(vb[3])
    maxw = CW
    maxh = 150.0 if single else 78.0
    mw = min(maxw, maxh * w / h) * scale
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
             '実在の地域・地点・国ではありません。</p>')
    s.append("</div>")
    return "\n".join(s)


def q_block(u, q):
    s = ['<div class="qb">']
    s.append('<div class="qh">%s−%d　［%s］　重要度 %s</div>'
             % (u["id"], q["no"], esc(q["skill"]), q["level"]))
    s.append('<div class="qt">%s</div>' % esc(q["q"]))
    for i, ch in enumerate(q["choices"]):
        s.append('<div class="ch">%s　%s</div>' % (MARK[i], esc(ch)))
    s.append('<div class="mark">解答欄<b>　</b></div>')
    s.append("</div>")
    return "\n".join(s)


def a_block(u, q):
    g = "".join("<div class='ag'>・%s</div>" % esc(x) for x in q["grounds"])
    return ('<div class="ab"><span class="ah">%s−%d　正解 %s</span>'
            '<div>%s</div><div class="ag">根拠</div>%s</div>'
            % (u["id"], q["no"], MARK[q["answer"]], esc(q["exp"]), g))


def measure(c, blocks):
    """各部品の高さ（mm）をブラウザで実測する。"""
    body = ('<div style="width:%.2fmm">' % CW +
            # display:flow-root を付けないと、中の段落の下マージンが
            # この div の外へ抜けてしまい、高さを実際より小さく測る。
            # そのまま詰めると、ページの最後の行が紙面からはみ出して切れる。
            "".join('<div id="b%d" style="display:flow-root">%s</div>'
                    % (i, b) for i, b in enumerate(blocks)) +
            '</div><div id="cal" style="height:100mm"></div>')
    html = ("<!doctype html><meta charset='utf-8'><style>%s</style><body>%s</body>"
            % (CSS % dict(MT=M_TOP, MB=M_BOT, ML=M_L, MR=M_R, CH=CH,
                          HH=HEAD_H, FH=FOOT_H, BH=BODY_H), body))
    p = os.path.join(HTML_DIR, "_measure.html")
    io.open(p, "w", encoding="utf-8", newline="\n").write(html)
    c.call("Page.navigate", {"url": "file:///" + p.replace("\\", "/")})
    time.sleep(1.6)
    for _ in range(30):
        if c.ev("document.readyState==='complete' && "
                "Array.prototype.every.call(document.images,function(i){"
                "return i.complete && i.naturalWidth>0;})"):
            break
        time.sleep(0.4)
    px = c.ev("document.getElementById('cal').getBoundingClientRect().height") / 100.0
    return [c.ev("document.getElementById('b%d').getBoundingClientRect().height" % i) / px
            for i in range(len(blocks))]


def paginate(c, unit):
    """設問を、図と同じページになるように詰める。戻り値は各ページのHTML本文。"""
    sets = []
    for q in unit["questions"]:
        if not sets or sets[-1][0] != q["setId"]:
            sets.append((q["setId"], q["figures"], []))
        sets[-1][2].append(q)

    blocks, tag = [], []
    for (sid, figs, qs) in sets:
        blocks.append(fig_block(figs))
        tag.append(("fig", sid))
        for q in qs:
            blocks.append(q_block(unit, q))
            tag.append(("q", sid))
    hs = measure(c, blocks)

    pages, cur, used = [], [], 0.0
    i = 0
    while i < len(blocks):
        kind, sid = tag[i]
        if kind == "fig":
            fig_html, fig_h = blocks[i], hs[i]
            qidx = [j for j in range(i + 1, len(blocks))
                    if tag[j][0] == "q" and tag[j][1] == sid]
            need = max([hs[j] for j in qidx]) if qidx else 0.0
            if fig_h + need > SAFE_H:
                # 資料が大きくて、同じページに設問が入らない。
                #   そのまま詰めると設問が紙面からはみ出して消えるので、
                #   資料だけのページを1枚立て、設問は次のページから並べる。
                figs = [q["figures"] for q in unit["questions"]
                        if q["setId"] == sid][0]
                sc = min(1.0, (SAFE_H - 6.0) / fig_h)
                pages.append(fig_block(figs, sc))
                cur, used = [], 0.0
                note = ('<p class="figcap" style="margin:0 0 3mm">'
                        '※ 資料は前のページにあります。</p>')
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
                    pages.append("".join(cur))          # 図をもう一度置いて続ける
                    cur, used = [fig_html], fig_h
                cur.append(blocks[j])
                used += hs[j]
                j += 1
            pages.append("".join(cur))
            i = j
        else:
            i += 1
    return pages


def answer_pages(c, unit):
    blocks = [a_block(unit, q) for q in unit["questions"]]
    hs = measure(c, blocks)
    head = '<h2 style="font-size:12pt;margin:0 0 4mm">解答・解説</h2>'
    pages, cur, used = [], [head], 12.0
    for b, h in zip(blocks, hs):
        if used + h > SAFE_H and len(cur) > 1:
            pages.append("".join(cur))
            cur, used = [], 0.0
        cur.append(b)
        used += h
    if cur:
        pages.append("".join(cur))
    return pages


HOWTO = [
    ("1. 地形図を見たときの手順",
     ["① 縮尺を見る（2万5千分の1なら1cm＝250m、5万分の1なら1cm＝500m）。",
      "② 方位記号を見る。ふつうは上が北だが、必ず確かめる。",
      "③ 計曲線（太線）に書かれた標高を1つ読み、そこを基準にする。",
      "④ 主曲線が何mごとかを確かめる（2万5千分の1なら10mごと）。",
      "⑤ 河川をたどり、どちらへ流れているか（低いほう）を決める。",
      "⑥ 地図記号を見て、田・畑・果樹園・樹林の分布をつかむ。",
      "⑦ そのうえで設問を読む。"]),
    ("2. 雨温図の判定手順",
     ["① 気温の折れ線の山が7〜8月なら北半球、1〜2月なら南半球。",
      "② 最も寒い月の平均気温を読む。",
      "　　18℃以上＝熱帯／−3〜18℃＝温帯／−3℃未満で最暖月10℃超＝亜寒帯。",
      "③ 年降水量を合計し、少なければ乾燥帯（砂漠かステップか）を疑う。",
      "④ 乾季があるか、あるとすれば夏か冬かを見る。",
      "　　夏に乾燥＝地中海性／冬に乾燥＝温暖冬季少雨／乾季なし＝温暖湿潤・西岸海洋性。",
      "⑤ 最後に気候区の名前を決める。名前から入らず、数値から入る。"]),
    ("3. 人口ピラミッドの判定手順",
     ["① いちばん下（0〜4歳）の棒の長さを見る。長ければ富士山型を疑う。",
      "② 上のほう（65歳以上）の厚みを見る。厚ければつぼ型を疑う。",
      "③ 上下の長さがそろっていればつりがね型。",
      "④ 途中の年齢だけがくびれていればひょうたん型（若い世代の流出）。",
      "⑤ 型が決まったら、出生率・死亡率のどの段階かを言葉にする。",
      "　　富士山型＝両方高い／つりがね型＝両方低い／つぼ型＝出生率がさらに低い。"]),
    ("4. 三角グラフの読み方",
     ["① 3つの割合の合計が100％になる図であることを確かめる。",
      "② 底辺の目盛が第一次産業、右の辺が第二次産業、左の辺が第三次産業。",
      "③ 1つの軸だけを先に読む。3つ同時に読もうとしない。",
      "④ 読んだ値を足して100になるか確かめる（読みまちがいの検算になる）。",
      "⑤ 点が第一次産業の頂点に近いほど発展段階が早い。",
      "⑥ 複数の年の点があれば、動いた向きを見る（第一次→第二次→第三次）。"]),
    ("5. 散布図で「相関」と「因果」を取りちがえない",
     ["・散布図が示すのは、2つの値が一緒に動く傾向（相関）だけである。",
      "・「Aが高い国はBが低い」は読み取れる。",
      "・「Aを上げればBが下がる」は読み取れない（因果は別の話）。",
      "・「必ず」「すべて」「〜だから」という言い方の選択肢は、まず疑う。",
      "・傾向から外れた点（例外の国）がないかを探すと、言いすぎの選択肢を消せる。",
      "・軸にない情報（人口の総数、品質、将来の予測）は読み取れない。"]),
    ("6. 複数資料問題の処理順序",
     ["① 設問を先に読む。何を聞かれているかを決めてから資料を見る。",
      "② その設問に必要な資料だけを見る。全部の資料を読み込まない。",
      "③ 「資料1と資料2から」とあれば、両方に根拠がある選択肢を選ぶ。",
      "④ 片方の資料だけで消せる選択肢は、先に消す。",
      "⑤ どの資料にも書かれていないことを述べた選択肢は、必ず誤り。",
      "⑥ 迷ったら、選んだ選択肢の根拠を資料のどこかで指させるか確かめる。"]),
    ("7. 選択肢の切り方",
     ["・数値の断定　「〜は必ず〜である」「すべての国が〜」→ 例外を1つ探す。",
      "・全称表現　　「いつも」「どの年も」→ 1か所でも外れれば誤り。",
      "・因果の飛躍　「〜だから〜になった」→ 資料に原因が書いてあるか確かめる。",
      "・単位の取りちがえ　％と実数、面積あたりと総数を見分ける。",
      "・年次の取りちがえ　どの年の資料かを確かめる。",
      "・全体と一部の取りちがえ　1つの区分の値を全体の値と読まない。"]),
    ("8. 時間配分の目安",
     ["・地形図の読図　1枚の図につき、図を見るのに1分、設問1問あたり1分。",
      "・統計の判読　　1問あたり1分〜1分30秒。",
      "・複数資料　　　1セット（3〜4問）で6〜8分。設問を先に読む分、後半が速くなる。",
      "・見直しの時間を5分残す。特に「必ず」「すべて」を含む選択肢を見直す。",
      "・分からない問題は印をつけて飛ばす。1問に3分以上かけない。"]),
]


def howto_pages(c):
    blocks = []
    for (title, lines) in HOWTO:
        s = ['<div class="qb">']
        s.append('<div class="qt" style="font-weight:bold;margin-bottom:2mm">%s</div>'
                 % esc(title))
        for ln in lines:
            s.append('<div class="ch" style="text-indent:0;padding-left:4mm">%s</div>'
                     % esc(ln))
        s.append("</div>")
        blocks.append("".join(s))
    return blocks          # 1つの手順につき1ページ。あとで見返しやすくする


def build_howto(c):
    body = ['<h1 class="bt">共通テスト地理　図表・読図　冊00　解き方の手順</h1>'
            '<p class="lead">これは覚えるためのものではありません。'
            '図表の問題を解くとき、毎回この順でやるための手順表です。'
            '解く前に1ページ目を見て、解いたあとに見直してください。</p>'
            '<div class="notice">%s</div>' % esc(NOTICE)]
    body += howto_pages(c)
    n = len(body)
    out = []
    for k, b in enumerate(body):
        out.append('<div class="page">'
                   '<div class="phead"><span>共通テスト地理　図表・読図</span>'
                   '<span>冊00 解き方の手順</span></div>'
                   '<div class="pbody">%s</div>'
                   '<div class="pfoot">冊00　%d/%d</div></div>' % (b, k + 1, n))
    html = ("<!doctype html><meta charset='utf-8'><title>冊00 解き方の手順</title>"
            "<style>%s</style><body>%s</body>"
            % (CSS % dict(MT=M_TOP, MB=M_BOT, ML=M_L, MR=M_R, CH=CH,
                          HH=HEAD_H, FH=FOOT_H, BH=BODY_H), "".join(out)))
    hp = os.path.join(HTML_DIR, "地理図表_00_解き方の手順.html")
    io.open(hp, "w", encoding="utf-8", newline="\n").write(html)
    c.call("Page.navigate", {"url": "file:///" + hp.replace("\\", "/")})
    time.sleep(1.4)
    d = c.call("Page.printToPDF", {
        "printBackground": True, "preferCSSPageSize": True,
        "paperWidth": 8.27, "paperHeight": 11.69,
        "marginTop": 0, "marginBottom": 0, "marginLeft": 0, "marginRight": 0,
        "displayHeaderFooter": False})
    pp = os.path.join(PDF_DIR, "地理図表_00_解き方の手順.pdf")
    io.open(pp, "wb").write(base64.b64decode(d["data"]))
    return pp, n


def cover(unit, nq):
    return ('<h1 class="bt">共通テスト地理　図表・読図　冊%s　%s</h1>'
            '<p class="lead">全%d問　すべて4択のマーク式です。'
            '答えは解答欄の□に番号を書き、最後の「解答・解説」で答え合わせをしてください。</p>'
            '<div class="notice">%s</div>'
            '<ul class="howto">'
            '<li>図はまず全体を見て、方位・縮尺・凡例（何の記号か）を確かめる。</li>'
            '<li>設問を先に読み、その設問に必要な部分だけを図から探す。</li>'
            '<li>選択肢は「言い切りすぎ」「単位の取りちがえ」「因果の飛躍」を疑う。</li>'
            '<li>迷ったら、確実に誤りといえる選択肢から消す。</li>'
            '</ul>' % (unit["id"], esc(unit["name"]), nq, esc(NOTICE)))


def build_book(c, unit):
    nq = len(unit["questions"])
    body_pages = [cover(unit, nq)] + paginate(c, unit) + answer_pages(c, unit)
    n = len(body_pages)
    title = "冊%s %s" % (unit["id"], unit["name"])
    out = []
    for k, b in enumerate(body_pages):
        out.append('<div class="page">'
                   '<div class="phead"><span>共通テスト地理　図表・読図</span>'
                   '<span>%s</span></div>'
                   '<div class="pbody">%s</div>'
                   '<div class="pfoot">冊%s　%d/%d</div></div>'
                   % (title, b, unit["id"], k + 1, n))
    html = ("<!doctype html><meta charset='utf-8'><title>%s</title>"
            "<style>%s</style><body>%s</body>"
            % (title, CSS % dict(MT=M_TOP, MB=M_BOT, ML=M_L, MR=M_R, CH=CH,
                                 HH=HEAD_H, FH=FOOT_H, BH=BODY_H),
               "".join(out)))
    hp = os.path.join(HTML_DIR, "地理図表_%s_%s.html" % (unit["id"], unit["name"]))
    io.open(hp, "w", encoding="utf-8", newline="\n").write(html)

    c.call("Page.navigate", {"url": "file:///" + hp.replace("\\", "/")})
    time.sleep(1.8)
    for _ in range(30):
        if c.ev("document.readyState==='complete' && "
                "Array.prototype.every.call(document.images,function(i){"
                "return i.complete && i.naturalWidth>0;})"):
            break
        time.sleep(0.4)
    d = c.call("Page.printToPDF", {
        "printBackground": True, "preferCSSPageSize": True,
        "paperWidth": 8.27, "paperHeight": 11.69,
        "marginTop": 0, "marginBottom": 0, "marginLeft": 0, "marginRight": 0,
        "displayHeaderFooter": False})
    pp = os.path.join(PDF_DIR, "地理図表_%s_%s.pdf" % (unit["id"], unit["name"]))
    io.open(pp, "wb").write(base64.b64decode(d["data"]))
    return pp, n


def main():
    for d in (PDF_DIR, HTML_DIR):
        if not os.path.isdir(d):
            os.makedirs(d)
    ud = os.path.join(os.environ["TEMP"], "edge_zuhyo_pdf")
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
        # 引数に冊のidを渡すと、その冊だけを作り直す。
        # すでにある冊子を作り直さずに済ませるため（指示Hで冊Dを足したときに使った）。
        only = [x.upper() for x in sys.argv[1:]]
        if not only:
            pp, n = build_howto(c)
            print("  %-40s %2dページ  %7d bytes"
                  % (os.path.basename(pp), n, os.path.getsize(pp)))
        for u in [x for x in bank.UNITS if not only or x["id"] in only]:
            pp, n = build_book(c, u)
            print("  %-40s %2dページ  %7d bytes"
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
