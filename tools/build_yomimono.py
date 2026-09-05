# -*- coding: utf-8 -*-
"""読み物（解説）を、紙のPDFとアプリのデータの両方に書き出す。

  紙   CHIRI_QA_20260901\\PDF\\地理解説_第29講_地域調査.pdf
       CHIRI_QA_20260901\\PDF\\地理解説_本番の形式の解き方.pdf
  アプリ QA_APP\\data\\yomimono.json（問題ではなく、読むだけのページ）

  組版は既存の冊子とそろえる。
    A4縦／余白 上下15mm・左右13mm／綴じ代15mm（左）／全ページにページ番号
    白黒／図は本文の切れ目に置き、ページをまたがせない
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
import yomimono                                   # noqa: E402

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, "Downloads", "CHIRI_QA_20260901")
PDF_DIR = os.path.join(BASE, "PDF")
HTML_DIR = os.path.join(BASE, "HTML")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DBG = 9321

PW, PH = 210.0, 297.0
M_TOP, M_BOT, M_R, M_L = 15.0, 15.0, 13.0, 28.0
CW = PW - M_L - M_R
CH = PH - M_TOP - M_BOT
HEAD_H, FOOT_H = 8.0, 8.0
BODY_H = CH - HEAD_H - FOOT_H
SAFE_H = BODY_H - 10.0

FILES = {"r29": "地理解説_第29講_地域調査",
         "rfmt": "地理解説_本番の形式の解き方"}

NOTICE = (
    "本冊子は共通テストの学習用に独自に書き起こした解説です。"
    "参考書の本文や過去問の問題文を転載または要約したものではありません。"
    "過去の出題については、何が問われる分野であったかだけを述べています。"
    "図はすべてこの冊子のために作図したもので、写真は使っていません。"
    "数値を示した図は架空のもので、図の中にその旨を書いてあります。"
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
         font-size:8.5pt; text-align:center; border-top:0.8pt solid #000;
         padding-top:1mm; }
h1.bt { font-size:17pt; margin:14mm 0 2mm; }
h2.bs { font-size:11pt; margin:0 0 6mm; font-weight:normal; }
h2.sec { font-size:13pt; margin:0 0 3mm; border-left:4pt solid #000;
         padding-left:3mm; }
h3.sub { font-size:11pt; margin:3mm 0 1.5mm; }
p.lead { font-size:10pt; line-height:1.75; margin:0 0 4mm; }
p.tx { font-size:10.5pt; line-height:1.8; margin:0 0 3.5mm; text-align:justify; }
ul.li { font-size:10.5pt; line-height:1.75; margin:0 0 3.5mm; padding-left:6mm; }
ul.li li { margin:0 0 1mm; }
.box { border:0.9pt solid #000; padding:3mm 4mm; margin:0 0 4mm; }
.box .bh { font-size:10.5pt; font-weight:bold; margin:0 0 1.5mm; }
.box ul { font-size:10pt; line-height:1.7; margin:0; padding-left:5mm; }
.figwrap { margin:1mm 0 4mm; text-align:center; }
.figwrap img { display:block; margin:0 auto; border:0.8pt solid #000; }
.notice { border:0.8pt solid #000; padding:3.5mm; font-size:8.5pt;
          line-height:1.6; margin-top:5mm; }
.toc { font-size:10.5pt; line-height:1.9; margin:0 0 4mm; }
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


def rich(s):
    """**ここ** を太字にする。ほかの記号は使わない。"""
    out, bold = [], False
    for part in esc(s).split("**"):
        out.append(("<b>%s</b>" % part) if bold and part else part)
        bold = not bold
    return "".join(out)


def css():
    return CSS % dict(MT=M_TOP, MB=M_BOT, ML=M_L, MR=M_R, CH=CH,
                      HH=HEAD_H, FH=FOOT_H, BH=BODY_H)


def fig_size(path):
    t = io.open(os.path.join(ROOT, path.replace("/", os.sep)),
                encoding="utf-8").read()
    vb = t.split('viewBox="')[1].split('"')[0].split()
    w, h = float(vb[2]), float(vb[3])
    # ★2026-09-05 96mm では図の線が細くなりすぎるので 130mm まで許す
    mw = min(CW, 130.0 * w / h)
    return mw, mw * h / w


def blocks_of(doc):
    """本文を、ページに詰められる部品の並びにする。"""
    out = []
    for (title, items) in doc["sections"]:
        out.append('<h2 class="sec">%s</h2>' % esc(title))
        for it in items:
            k = it[0]
            if k == "p":
                out.append('<p class="tx">%s</p>' % rich(it[1]))
            elif k == "h":
                out.append('<h3 class="sub">%s</h3>' % esc(it[1]))
            elif k == "ul":
                out.append('<ul class="li">%s</ul>'
                           % "".join("<li>%s</li>" % rich(x) for x in it[1]))
            elif k == "box":
                out.append('<div class="box"><div class="bh">%s</div><ul>%s</ul></div>'
                           % (esc(it[1]),
                              "".join("<li>%s</li>" % rich(x) for x in it[2])))
            elif k == "fig":
                mw, mh = fig_size(it[1])
                out.append('<div class="figwrap"><img src="%s" '
                           'style="width:%.1fmm;height:%.1fmm"></div>'
                           % ("file:///" + os.path.join(
                               ROOT, it[1].replace("/", os.sep)).replace("\\", "/"),
                              mw, mh))
    return out


def measure(c, blocks):
    # display:flow-root を付けないと、段落の下マージンが外へ抜けて
    # 高さを小さく測ってしまい、ページの最後の行が切れる。
    body = ('<div style="width:%.2fmm">' % CW +
            "".join('<div id="b%d" style="display:flow-root">%s</div>' % (i, b)
                    for i, b in enumerate(blocks)) +
            '</div><div id="cal" style="height:100mm"></div>')
    html = ("<!doctype html><meta charset='utf-8'><style>%s</style><body>%s</body>"
            % (css(), body))
    p = os.path.join(HTML_DIR, "_measure_yomi.html")
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


def cover(doc):
    toc = "".join("・%s<br>" % esc(t) for (t, _x) in doc["sections"])
    return ('<h1 class="bt">%s</h1><h2 class="bs">%s</h2>'
            '<p class="lead">%s</p>'
            '<div class="toc"><b>この読み物の中身</b><br>%s</div>'
            '<p class="lead">読むのにかかる時間の目安は約%d分です。'
            '一度読んだら、問題を解きながら必要なところだけ戻ってください。</p>'
            '<div class="notice">%s</div>'
            % (esc(doc["title"]), esc(doc["sub"]), rich(doc["lead"]), toc,
               doc["minutes"], esc(NOTICE)))


def build_pdf(c, doc):
    blocks = blocks_of(doc)
    hs = measure(c, blocks)
    pages, cur, used = [], [], 0.0
    for b, h in zip(blocks, hs):
        if used + h > SAFE_H and cur:
            pages.append("".join(cur))
            cur, used = [], 0.0
        cur.append(b)
        used += h
    if cur:
        pages.append("".join(cur))
    body = [cover(doc)] + pages
    n = len(body)
    title = doc["title"]
    out = []
    for k, b in enumerate(body):
        out.append('<div class="page">'
                   '<div class="phead"><span>共通テスト地理　読み物</span>'
                   '<span>%s</span></div><div class="pbody">%s</div>'
                   '<div class="pfoot">%s　%d/%d</div></div>'
                   % (esc(title), b, esc(title), k + 1, n))
    html = ("<!doctype html><meta charset='utf-8'><title>%s</title>"
            "<style>%s</style><body>%s</body>"
            % (esc(title), css(), "".join(out)))
    stem = FILES[doc["id"]]
    hp = os.path.join(HTML_DIR, stem + ".html")
    io.open(hp, "w", encoding="utf-8", newline="\n").write(html)
    c.call("Page.navigate", {"url": "file:///" + hp.replace("\\", "/")})
    time.sleep(1.6)
    for _ in range(40):
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
    pp = os.path.join(PDF_DIR, stem + ".pdf")
    io.open(pp, "wb").write(base64.b64decode(d["data"]))
    return pp, n


def build_json():
    """アプリ用。問題ではなく読むだけのページとして持たせる。"""
    out = []
    for doc in yomimono.READINGS:
        secs = []
        for (title, items) in doc["sections"]:
            body = []
            for it in items:
                if it[0] == "box":
                    body.append({"t": "box", "h": it[1], "items": list(it[2])})
                elif it[0] == "ul":
                    body.append({"t": "ul", "items": list(it[1])})
                elif it[0] == "fig":
                    body.append({"t": "fig", "src": it[1]})
                else:
                    body.append({"t": it[0], "text": it[1]})
            secs.append({"h": title, "body": body})
        out.append({"id": doc["id"], "title": doc["title"], "sub": doc["sub"],
                    "minutes": doc["minutes"], "lead": doc["lead"],
                    "sections": secs})
    p = os.path.join(ROOT, "data", "yomimono.json")
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"readings": out}, ensure_ascii=False, indent=1) + "\n")
    return p, out


def main():
    for d in (PDF_DIR, HTML_DIR):
        if not os.path.isdir(d):
            os.makedirs(d)
    p, out = build_json()
    print("アプリ用: %s（%d本）" % (p, len(out)))
    ud = os.path.join(os.environ["TEMP"], "edge_yomi")
    shutil.rmtree(ud, ignore_errors=True)
    proc = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu",
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
        for doc in yomimono.READINGS:
            pp, n = build_pdf(c, doc)
            print("  %-40s %2dページ  %7d bytes（読み約%d分）"
                  % (os.path.basename(pp), n, os.path.getsize(pp),
                     doc["minutes"]))
    finally:
        try:
            proc.kill()
        except Exception:
            pass
        mp = os.path.join(HTML_DIR, "_measure_yomi.html")
        if os.path.isfile(mp):
            os.remove(mp)


if __name__ == "__main__":
    main()
