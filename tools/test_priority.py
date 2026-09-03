# -*- coding: utf-8 -*-
"""指示H Phase E の動作確認：出題順に「優先度の高い順」を足した分だけを見る。

  確かめること
    1. 出題順のボタンが3つになり、「優先度の高い順」が選べる
    2. 選ぶと、実際に prank の小さい順（＝出題の見こみ×配点の高い順）に並ぶ
    3. 既存の「シャッフル」「もとの順」の動きが変わっていない
    4. 判定ロジック（自動判定の○×）が今までどおり動く
    5. 間違いノートに、今までどおり記録される
    6. 利用者を切りかえても、それぞれのノートが混ざらない
"""
import json
import os
import socket
import subprocess
import sys
import time

import requests
from websockets.sync.client import connect

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT = 8787
DBG = 9237
URL = "http://127.0.0.1:%d/index.html" % PORT
res = []


def rec(ok, title, detail=""):
    st = "OK" if ok else "NG"
    res.append((st, title, detail))
    print("[%s] %s %s" % (st, title, detail))


class CDP(object):
    def __init__(self, ws):
        self.ws = connect(ws, max_size=None)
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
                                          ensure_ascii=False)[:200])
        return r.get("result", {}).get("value")


def free(port):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def open_page(url):
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    ud = os.path.join(os.environ["TEMP"], "edge_prio_test")
    p = subprocess.Popen([edge, "--headless=new", "--disable-gpu",
                          "--remote-debugging-port=%d" % DBG,
                          "--user-data-dir=" + ud, "--no-first-run", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    for _ in range(80):
        time.sleep(0.5)
        try:
            for t in requests.get("http://127.0.0.1:%d/json/list" % DBG,
                                  timeout=2).json():
                if t["type"] != "page":
                    continue
                if not (t.get("url") or "").startswith("about:"):
                    ws = t["webSocketDebuggerUrl"]
                    break
                if ws is None:
                    ws = t["webSocketDebuggerUrl"]
            if ws:
                break
        except Exception:
            pass
    if not ws:
        p.kill()
        raise RuntimeError("Edge に接続できませんでした")
    c = CDP(ws)
    c.call("Runtime.enable")
    return p, c


def setup(c, order, count="0", level="ALL", units=("01", "02", "29")):
    c.ev("document.getElementById('btnQuit') && "
         "document.getElementById('btnQuit').click();")
    c.ev("document.getElementById('btnGoUnit').click()")
    c.ev("document.getElementById('btnUnitNone').click();"
         + "".join("document.getElementById('unit-%s').click();" % u for u in units))
    c.ev("document.getElementById('btnUnitNext').click();"
         "document.querySelector('#optCount .opt[data-val=\"%s\"]').click();"
         "document.querySelector('[data-level=\"%s\"]').click();"
         "document.querySelector('[data-order=\"%s\"]').click();"
         "document.getElementById('btnStart').click();" % (count, level, order))
    return c.ev("JSON.stringify(window.__app.getQuiz().roundList"
                ".map(function(x){return [x.q.seq, x.q.prank];}))")


def main():
    srv = None
    if free(PORT):
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT),
                                "--bind", "127.0.0.1"], cwd=ROOT,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    proc, c = open_page(URL)
    try:
        for _ in range(80):
            if c.ev("document.readyState==='complete' && !!window.__app "
                    "&& !!window.__app.getSubject()"):
                break
            time.sleep(0.5)

        # ---------- 1. ボタンがある ----------
        n = c.ev("document.querySelectorAll('[data-order]').length")
        labels = c.ev("JSON.stringify(Array.from("
                      "document.querySelectorAll('[data-order]')).map("
                      "function(e){return e.dataset.order+':'+e.textContent;}))")
        rec(n == 3 and "priority" in labels,
            "出題順の選択肢が3つになり、優先度の高い順が選べる", labels)

        c.ev("document.getElementById('newUserName').value='テストＡ';"
             "document.getElementById('btnAddUser').click();")
        c.ev("window.__app.setNoteAsked(true)")

        # ---------- 2. 優先度の高い順に並ぶ ----------
        got = json.loads(setup(c, "priority"))
        pranks = [x[1] for x in got]
        rec(all(isinstance(x, int) for x in pranks)
            and pranks == sorted(pranks),
            "優先度の高い順にすると、prank の小さい順に並ぶ",
            "%d問／prank %s … %s" % (len(got), pranks[:6], pranks[-3:]))
        # 同じ prank の中では通し番号の順
        ok = True
        for i in range(1, len(got)):
            if got[i][1] == got[i - 1][1] and got[i][0] < got[i - 1][0]:
                ok = False
                break
        rec(ok, "同じ優先度の中では、もとの通し番号の順のまま", "並べ替えは分野の間だけ")

        # ---------- 3. 既存の順が変わっていない ----------
        setup(c, "csv")
        key = json.loads(c.ev(
            "JSON.stringify(window.__app.getQuiz().roundList.map("
            "function(x){return [x.unit.id, x.q.no];}))"))
        rec(key == sorted(key), "「もとの順」は今までどおり単元→問番号の順",
            "先頭 %s／末尾 %s" % (key[:3], key[-2:]))
        sh = json.loads(setup(c, "shuffle", count="20"))
        rec(len(sh) == 20 and [x[0] for x in sh] != sorted(x[0] for x in sh),
            "「シャッフル」は今までどおりばらばらに並ぶ", "%d問" % len(sh))

        # ---------- 4. 判定ロジック ----------
        setup(c, "priority", count="0", level="ALL", units=("29",))
        for _ in range(40):
            if not c.ev("window.__app.isSelfCheck("
                        "window.__app.getQuiz().queue[0].q)"):
                break
            c.ev("document.getElementById('btnSkip').click();"
                 "document.getElementById('btnNext').click();")
        ans = c.ev("window.__app.getQuiz().queue[0].q.a")
        c.ev("document.getElementById('btnKbd').click();"
             "document.getElementById('kbdInput').value=" + json.dumps(ans) +
             ";document.getElementById('btnKbdSubmit').click();")
        mk1 = c.ev("document.getElementById('verdict').textContent")
        c.ev("document.getElementById('btnNext').click();")
        for _ in range(40):
            if not c.ev("window.__app.isSelfCheck("
                        "window.__app.getQuiz().queue[0].q)"):
                break
            c.ev("document.getElementById('btnSkip').click();"
                 "document.getElementById('btnNext').click();")
        wrong_seq = c.ev("window.__app.getQuiz().queue[0].q.seq")
        c.ev("document.getElementById('btnKbd').click();"
             "document.getElementById('kbdInput').value='まったく関係のない語';"
             "document.getElementById('btnKbdSubmit').click();")
        mk2 = c.ev("document.getElementById('verdict').textContent")
        rec(mk1 == "○" and mk2 == "×",
            "優先度の高い順でも、自動判定が今までどおり動く",
            "正答=%s／誤答=%s" % (mk1, mk2))

        # ---------- 5. 間違いノート ----------
        c.ev("document.getElementById('btnNext').click();"
             "document.getElementById('btnQuit').click();")
        inNote = c.ev("JSON.stringify(window.__app.getNote().entries"
                      ".map(function(e){return e.seq;}))")
        rec(str(wrong_seq) in inNote,
            "間違えた問が、今までどおり間違いノートに入る",
            "通し%s が入っている（ノート %d件）"
            % (wrong_seq, len(json.loads(inNote))))

        # ---------- 6. 利用者ごとに分かれている ----------
        c.ev("document.getElementById('newUserName').value='テストＢ';"
             "document.getElementById('btnAddUser').click();")
        c.ev("window.__app.setNoteAsked(true)")
        nB = len(json.loads(c.ev("JSON.stringify(window.__app.getNote()"
                                 ".entries.map(function(e){return e.seq;}))")))
        rec(nB == 0, "利用者を変えると、その人のノートは空のまま",
            "テストＢのノート %d件（テストＡの記録は混ざっていない）" % nB)
    finally:
        try:
            proc.kill()
        except Exception:
            pass
        if srv:
            srv.kill()

    ng = [r for r in res if r[0] == "NG"]
    print("=" * 66)
    print("判定: %s（OK %d / NG %d）"
          % ("NGなし" if not ng else "★NGあり", len(res) - len(ng), len(ng)))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
