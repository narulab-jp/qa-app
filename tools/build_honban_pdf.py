# -*- coding: utf-8 -*-
"""本番形式編のPDF（紙で解く版）を作る。

  組版のしくみは図表編と同じものを使う（A4縦・図は設問と同じページ・
  解答は別ページ・全ページにページ番号）。
  冊Eは通し演習なので、表紙に時間と配点の目安を入れる。
"""
import base64
import io
import os
import shutil
import subprocess
import sys
import time

import requests
from websockets.sync.client import connect

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_zuhyo_pdf as Z          # noqa: E402
import honban_d                      # noqa: E402
import honban_e                      # noqa: E402
import honban_f                      # noqa: E402
import honban_g                      # noqa: E402

EDGE = Z.EDGE
DBG = 9302
NOTICE_D = (
    "本冊子は共通テストと同じ組合せ形式に慣れるための練習用に、"
    "独自に作成した問題です。教科書・資料集・過去問の図を転載または"
    "模写したものではありません。図はすべてこの教材のために作図したもので、"
    "地形図は訓練用の模式図、雨温図・統計は架空の地点および架空の国の"
    "数値です。実在の統計を判断の根拠にしないでください。"
)
UNITS = [
    {"id": "D", "name": "組合せ形式", "questions": honban_d.QUESTIONS,
     "lead": "全48問。本番の組合せ形式は3つの型しかありません。"
             "対応型（記号と説明を結ぶ）・2軸型（2つの軸を掛け合わせる）・"
             "正誤の組合せ型の3つを、分野を変えながらくり返し解いてください。"
             "1問1分30秒を目安に、48問で約70分です。"},
    {"id": "E", "name": "通し演習 第1回", "questions": honban_e.QUESTIONS,
     "lead": "全30マーク・100点・制限時間60分。本番と同じ大問構成・配点です。"
             "第1問13点／第2問12点／第3問21点／第4問17点／第5問20点／第6問17点。"
             "時間を計って、途中で止めずに最後まで解いてください。"},
    {"id": "F", "name": "残りの技能・形式", "questions": honban_f.QUESTIONS,
     "lead": "全13問。本試験2年分を1マークずつ調べ、"
             "冊D・冊Eを解いてもなお練習できないまま残った技能・形式だけを"
             "集めました。主題図3枚の同時比較・土壌の分布図・"
             "海面水温の平年差・GISの重ね合わせとバッファ・"
             "下線部の正誤・会話文の空欄の6種類です。"
             "1問2分を目安に、13問で約26分です。"},
    {"id": "G", "name": "地域調査", "questions": honban_g.QUESTIONS,
     "lead": "1つの地域を最後まで調べるセットです。"
             "資料5点で、何が変わったか→どこが変わったか→"
             "なぜ変わったか→これからどうなるか、の順に問います。"
             "資料を読む時間を入れて、1セット20分を目安にしてください。"},
]


def cover(u):
    nq = len(u["questions"])
    return ('<h1 class="bt">共通テスト地理　本番形式　冊%s　%s</h1>'
            '<p class="lead">%s</p>'
            '<div class="notice">%s</div>'
            '<ul class="howto">'
            '<li>組合せの選択肢は、まず1つの軸だけを決める。</li>'
            '<li>決まった軸で選択肢を半分に減らしてから、もう一方を見る。</li>'
            '<li>正誤の組合せは、確実に判断できる文から先に決める。</li>'
            '<li>「必ず」「すべて」を含む文は、反例を1つ探すと消せる。</li>'
            '<li>資料にないことを述べた文は、それだけで誤りである。</li>'
            '</ul>' % (u["id"], Z.esc(u["name"]), Z.esc(u["lead"]),
                       Z.esc(NOTICE_D)))


def build_book(c, u):
    body_pages = [cover(u)] + Z.paginate(c, u) + Z.answer_pages(c, u)
    n = len(body_pages)
    title = "冊%s %s" % (u["id"], u["name"])
    out = []
    for k, b in enumerate(body_pages):
        out.append('<div class="page">'
                   '<div class="phead"><span>共通テスト地理　本番形式</span>'
                   '<span>%s</span></div>'
                   '<div class="pbody">%s</div>'
                   '<div class="pfoot">冊%s　%d/%d</div></div>'
                   % (title, b, u["id"], k + 1, n))
    html = ("<!doctype html><meta charset='utf-8'><title>%s</title>"
            "<style>%s</style><body>%s</body>"
            % (title, Z.CSS % dict(MT=Z.M_TOP, MB=Z.M_BOT, ML=Z.M_L, MR=Z.M_R,
                                   CH=Z.CH, HH=Z.HEAD_H, FH=Z.FOOT_H,
                                   BH=Z.BODY_H), "".join(out)))
    hp = os.path.join(Z.HTML_DIR, "地理本番_%s_%s.html" % (u["id"], u["name"]))
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
    pp = os.path.join(Z.PDF_DIR, "地理本番_%s_%s.pdf" % (u["id"], u["name"]))
    io.open(pp, "wb").write(base64.b64decode(d["data"]))
    return pp, n


def main():
    for d in (Z.PDF_DIR, Z.HTML_DIR):
        if not os.path.isdir(d):
            os.makedirs(d)
    ud = os.path.join(os.environ["TEMP"], "edge_honban_pdf")
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
        c = Z.C(connect(ws, max_size=None))
        c.call("Page.enable")
        c.call("Runtime.enable")
        c.call("Emulation.setEmulatedMedia", {"media": "print"})
        for u in UNITS:
            pp, n = build_book(c, u)
            print("  %-40s %2dページ  %7d bytes"
                  % (os.path.basename(pp), n, os.path.getsize(pp)))
    finally:
        try:
            p.kill()
        except Exception:
            pass
        mp = os.path.join(Z.HTML_DIR, "_measure.html")
        if os.path.isfile(mp):
            os.remove(mp)
    print("PDF を %s に出力した" % Z.PDF_DIR)


if __name__ == "__main__":
    main()
