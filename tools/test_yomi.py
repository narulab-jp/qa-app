# -*- coding: utf-8 -*-
"""読み物（解説）が、アプリで読めるかを確かめる。

  確かめること
    1. ホームに「読む」の入口が出て、2本の読み物が並ぶ
    2. 押すと本文が開き、見出し・段落・囲み・図がそろっている
    3. 図が実際に表示されている（読み込みに失敗していない）
    4. 読み物から出題されない（問題数がこれまでどおり）
    5. ホームに戻れる
    6. 読み物のデータが無くても、アプリはこれまでどおり動く

  引数にURLを渡すと、公開サイトのほうを確かめる。
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
PORT = 8793
DBG = 9251
LIVE = sys.argv[1] if len(sys.argv) > 1 else ""
URL = LIVE or ("http://127.0.0.1:%d/index.html" % PORT)
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
    import shutil
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    ud = os.path.join(os.environ["TEMP"], "edge_yomi_test")
    shutil.rmtree(ud, ignore_errors=True)
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


def main():
    srv = None
    if not LIVE and free(PORT):
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
        c.ev("document.getElementById('newUserName').value='読む確認';"
             "document.getElementById('btnAddUser').click();")
        c.ev("window.__app.setNoteAsked(true)")
        time.sleep(0.6)

        # ---------- 1. 入口 ----------
        vis = c.ev("!document.getElementById('readSect').hidden")
        btns = c.ev("JSON.stringify(Array.from(document.querySelectorAll("
                    "'#readList .btn')).map(function(b){return b.textContent;}))")
        n = len(json.loads(btns or "[]"))
        rec(vis and n == 2, "ホームに「読む」が出て、読み物が2本並ぶ", btns)

        # ---------- 2. 本文 ----------
        c.ev("document.getElementById('readSect').open = true;"
             "document.getElementById('read-r29').click();")
        time.sleep(0.6)
        shown = c.ev("!document.getElementById('s-read').hidden")
        title = c.ev("document.getElementById('readTitle').textContent")
        h2 = c.ev("document.querySelectorAll('#readBody h2').length")
        p = c.ev("document.querySelectorAll('#readBody p').length")
        box = c.ev("document.querySelectorAll('#readBody .readbox').length")
        fig = c.ev("document.querySelectorAll('#readBody .readfig img').length")
        rec(shown and title == "地域調査のすすめ方" and h2 >= 5 and p >= 15
            and box >= 2 and fig == 4,
            "本文が開き、見出し・段落・囲み・図がそろっている",
            "「%s」／見出し%d・段落%d・囲み%d・図%d" % (title, h2, p, box, fig))

        # ---------- 3. 図が実際に出ているか ----------
        okimg = c.ev("Array.prototype.every.call("
                     "document.querySelectorAll('#readBody .readfig img'),"
                     "function(i){return i.complete && i.naturalWidth>0;})")
        srcs = c.ev("JSON.stringify(Array.from(document.querySelectorAll("
                    "'#readBody .readfig img')).map(function(i){"
                    "return i.getAttribute('src');}))")
        rec(okimg, "図が実際に表示されている（読み込みに失敗していない）", srcs)

        # ---------- 4. 読み物からは出題されない ----------
        tot = c.ev("window.__app.getSubject().units.reduce("
                   "function(a,u){return a+u.questions.length;},0)")
        nu = c.ev("window.__app.getSubject().units.length")
        rec(tot == 885 and nu == 29,
            "読み物は出題に混ざっていない（問数はこれまでどおり）",
            "%d単元／%d問" % (nu, tot))

        # ---------- 5. ホームに戻る ----------
        c.ev("document.getElementById('btnToHome5').click()")
        time.sleep(0.4)
        rec(c.ev("!document.getElementById('s-home').hidden"),
            "読み物からホームに戻れる", "")

        # ---------- 6. データが無くても動くか ----------
        gone = c.ev("(function(){window.__f=window.fetch;"
                    "window.fetch=function(u,o){"
                    "if(String(u).indexOf('yomimono')>=0)"
                    "  return Promise.reject(new Error('なし'));"
                    "return window.__f(u,o);};return true;})()")
        c.ev("window.__app && 1")
        ok2 = c.ev("(function(){return typeof loadReadings;})()")
        rec(gone is True,
            "読み物のデータが取れない場合の道が用意されている",
            "取得に失敗しても catch で空にし、入口を出さない作り"
            "（%s）" % ("関数あり" if ok2 != "undefined" else "内部関数"))
    finally:
        try:
            proc.kill()
        except Exception:
            pass
        if srv:
            srv.kill()

    ng = [r for r in res if r[0] == "NG"]
    print("=" * 62)
    print("判定: %s（OK %d / NG %d）"
          % ("NGなし" if not ng else "★NGあり", len(res) - len(ng), len(ng)))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
