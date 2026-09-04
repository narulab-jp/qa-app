# -*- coding: utf-8 -*-
"""新しい版への入れ替えが働くかを、実際に版を差し替えて確かめる。

  手順
    1. いまの sw.js で1回開き、Service Worker を入れる
    2. sw.js の版数を書き換えて（＝新しい版を公開したことにして）
    3. 同じブラウザで開き直し、画面に知らせが出るかを見る
    4. 「今すぐ更新」を押して、新しい版に入れ替わるかを見る
    5. 終わったら sw.js を元に戻す

  確かめること
    ・アプリ本体（index.html / app.js / app.css）が通信優先になっていること
    ・新しい版があるとき、画面に知らせが出ること
    ・押すと入れ替わり、版数が上がること
    ・設定に、いまの版が出ること
"""
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import time

import requests
from websockets.sync.client import connect

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SW = os.path.join(ROOT, "sw.js")
PORT = 8795
DBG = 9255
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


def wait_ready(c):
    for _ in range(80):
        try:
            if c.ev("document.readyState==='complete' && !!window.__app"):
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    orig = io.open(SW, encoding="utf-8").read()
    srv = None
    if free(PORT):
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT),
                                "--bind", "127.0.0.1"], cwd=ROOT,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    ud = os.path.join(os.environ["TEMP"], "edge_upd_test")
    shutil.rmtree(ud, ignore_errors=True)
    proc = subprocess.Popen([edge, "--headless=new", "--disable-gpu",
                             "--remote-debugging-port=%d" % DBG,
                             "--user-data-dir=" + ud, "--no-first-run", URL],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
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
        c = CDP(ws)
        c.call("Runtime.enable")
        c.call("Page.enable")
        wait_ready(c)

        # ---------- 1. まず Service Worker が入るまで待つ ----------
        got = False
        for _ in range(40):
            if c.ev("!!navigator.serviceWorker.controller"):
                got = True
                break
            time.sleep(0.5)
        v1 = c.ev("(function(){return new Promise(function(ok){"
                  "if(!navigator.serviceWorker.controller) return ok('');"
                  "var ch=new MessageChannel();"
                  "ch.port1.onmessage=function(e){ok(e.data&&e.data.version||'');};"
                  "navigator.serviceWorker.controller.postMessage("
                  "{type:'GET_VERSION'},[ch.port2]);"
                  "setTimeout(function(){ok('');},2000);});})()")
        rec(got and bool(v1), "Service Worker が入り、版数を答える",
            "いまの版=%s" % v1)

        # ---------- 2. アプリ本体が通信優先になっているか ----------
        shell = c.ev("(function(){return fetch('app.js?probe='+Date.now())"
                     ".then(function(r){return r.ok;}).catch(function(){return false;});})()")
        rec(shell is True, "アプリ本体を通信で取りに行ける（通信優先になっている）",
            "app.js を取り直せた")

        # ---------- 3. 新しい版を公開したことにする ----------
        io.open(SW, "w", encoding="utf-8", newline="").write(
            orig.replace('var VERSION = "', 'var VERSION = "TEST-', 1))
        time.sleep(0.5)
        c.ev("(function(){return navigator.serviceWorker.getRegistration()"
             ".then(function(r){return r.update();});})()")
        shown = False
        for _ in range(40):
            if c.ev("!document.getElementById('updBar').hidden"):
                shown = True
                break
            time.sleep(0.5)
        msg = c.ev("document.getElementById('updMsg').textContent")
        btn = c.ev("document.getElementById('btnUpdate').textContent")
        rec(shown, "新しい版があるとき、画面に知らせが出る",
            "「%s」／ボタン=「%s」" % (msg, btn))

        # ---------- 4. 押すと入れ替わる ----------
        c.ev("document.getElementById('btnUpdate').click()")
        time.sleep(3.0)
        wait_ready(c)
        for _ in range(40):
            if c.ev("!!navigator.serviceWorker.controller"):
                break
            time.sleep(0.5)
        v2 = c.ev("(function(){return new Promise(function(ok){"
                  "if(!navigator.serviceWorker.controller) return ok('');"
                  "var ch=new MessageChannel();"
                  "ch.port1.onmessage=function(e){ok(e.data&&e.data.version||'');};"
                  "navigator.serviceWorker.controller.postMessage("
                  "{type:'GET_VERSION'},[ch.port2]);"
                  "setTimeout(function(){ok('');},2000);});})()")
        rec(v2.startswith("TEST-") and v2 != v1,
            "「今すぐ更新」を押すと、新しい版に入れ替わる",
            "%s → %s" % (v1, v2))

        # ---------- 5. 設定に版が出る ----------
        c.ev("document.getElementById('newUserName').value='版の確認';"
             "document.getElementById('btnAddUser').click();")
        c.ev("window.__app.setNoteAsked(true)")
        c.ev("document.getElementById('btnSettings').click()")
        time.sleep(1.2)
        sv = c.ev("document.getElementById('swVersion').textContent")
        rec("いまの版：" in (sv or ""), "設定に、いまの版が出る", sv)

        # ---------- 6. 「あとで」で閉じられる ----------
        c.ev("document.getElementById('updBar').hidden=false;"
             "document.getElementById('btnUpdLater').click();")
        rec(c.ev("document.getElementById('updBar').hidden"),
            "知らせは「×」で閉じられる（次に開いたらまた出る）", "")
    finally:
        io.open(SW, "w", encoding="utf-8", newline="").write(orig)
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
