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

NOTICE = (
    "本冊子は共通テストと同じマーク式の練習用に、独自に作成した図表・読図問題です。"
    "教科書・資料集・過去問の図を転載または模写したものではありません。"
    "図はすべてこの冊子のために作図したものです。"
    "地形図は訓練用の模式図であり、実在の地域ではありません。"
    "雨温図・統計は架空の地点および架空の国の数値であり、実在の地点・国ではありません。"
    "実在の統計を判断の根拠にしないでください。"
)
MARK = ["①", "②", "③", "④"]

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


def fig_size(path, single):
    """SVG の viewBox から、印刷したときの大きさ（mm）を決める。"""
    t = io.open(os.path.join(ROOT, path.replace("/", os.sep)), encoding="utf-8").read()
    vb = t.split('viewBox="')[1].split('"')[0].split()
    w, h = float(vb[2]), float(vb[3])
    maxw = CW
    maxh = 150.0 if single else 78.0
    mw = min(maxw, maxh * w / h)
    return mw, mw * h / w


def fig_block(figs):
    single = (len(figs) == 1)
    s = ['<div class="figwrap">']
    for f in figs:
        mw, mh = fig_size(f, single)
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
            "".join('<div id="b%d">%s</div>' % (i, b) for i, b in enumerate(blocks)) +
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
            j = i + 1
            cur, used = [fig_html], fig_h
            while j < len(blocks) and tag[j][0] == "q" and tag[j][1] == sid:
                if used + hs[j] > BODY_H and len(cur) > 1:
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
        if used + h > BODY_H and len(cur) > 1:
            pages.append("".join(cur))
            cur, used = [], 0.0
        cur.append(b)
        used += h
    if cur:
        pages.append("".join(cur))
    return pages


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
        for u in bank.UNITS:
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


main()
