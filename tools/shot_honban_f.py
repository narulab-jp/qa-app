# -*- coding: utf-8 -*-
"""冊Fの問題が、実際の画面でどう見えるかを撮る（目視確認用）。"""
import base64
import io
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
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 8793
DBG = 9273
OUT = os.path.join(os.environ["TEMP"], "qa_shots")
TARGETS = [1, 5, 9, 12]      # 6択の対応型・GIS・下線部・会話文


class C(object):
    def __init__(self, url):
        self.ws = connect(url, max_size=None)
        self.n = 0

    def call(self, m, p=None):
        self.n += 1
        self.ws.send(__import__("json").dumps(
            {"id": self.n, "method": m, "params": p or {}}))
        while True:
            r = __import__("json").loads(self.ws.recv(timeout=60))
            if r.get("id") == self.n:
                return r

    def ev(self, e):
        r = self.call("Runtime.evaluate",
                      {"expression": e, "returnByValue": True,
                       "awaitPromise": True}).get("result", {})
        if "exceptionDetails" in r:
            raise RuntimeError(str(r["exceptionDetails"])[:200])
        return r.get("result", {}).get("value")


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", PORT))
        free = True
    except OSError:
        free = False
    finally:
        s.close()
    srv = None
    if free:
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT),
                                "--bind", "127.0.0.1"], cwd=ROOT,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    ud = os.path.join(os.environ["TEMP"], "edge_shot_f")
    shutil.rmtree(ud, ignore_errors=True)
    p = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu",
                          "--remote-debugging-port=%d" % DBG,
                          "--user-data-dir=" + ud, "--remote-allow-origins=*",
                          "http://127.0.0.1:%d/index.html" % PORT],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws = None
        for _ in range(80):
            time.sleep(0.5)
            try:
                for t in requests.get("http://127.0.0.1:%d/json/list" % DBG,
                                      timeout=3).json():
                    if t.get("type") == "page" and \
                            not (t.get("url") or "").startswith("about:"):
                        ws = t["webSocketDebuggerUrl"]
                if ws:
                    break
            except Exception:
                pass
        c = C(ws)
        c.call("Runtime.enable")
        c.call("Page.enable")
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 390, "height": 844, "deviceScaleFactor": 2,
                "mobile": True})
        for _ in range(60):
            if c.ev("document.readyState==='complete' && !!window.__app"):
                break
            time.sleep(0.5)
        c.ev("document.getElementById('newUserName').value='テスト';"
             "document.getElementById('btnAddUser').click();"
             "window.__app.setNoteAsked(true);")
        c.ev("window.__app.openSubjectById('chiri-honban')")
        for _ in range(40):
            time.sleep(0.5)
            if c.ev("window.__app.getSubject().subjectId") == "chiri-honban":
                break
        for no in TARGETS:
            c.ev("(function(){"
                 "var q=window.__app.getQuiz();"
                 "if(!q||!q.queue.length){"
                 "document.getElementById('btnGoUnit').click();"
                 "document.getElementById('btnUnitNone').click();"
                 "document.getElementById('unit-F').click();"
                 "document.getElementById('btnUnitNext').click();"
                 "document.querySelector('[data-level=\"ALL\"]').click();"
                 "document.querySelector('[data-order=\"csv\"]').click();"
                 "var b=document.querySelector('#optCount .opt[data-val=\"0\"]');"
                 "if(b)b.click();"
                 "document.getElementById('btnStart').click();}"
                 "})()")
            # 目的の問まで、選択肢を押して進める
            for _ in range(80):
                cur = c.ev("(function(){var q=window.__app.getQuiz();"
                           "return q&&q.queue.length?q.queue[0].q.no:-1;})()")
                if cur == no or cur == -1:
                    break
                c.ev("(function(){"
                     "var b=document.querySelector('#choiceBox .ch');"
                     "if(b)b.click();"
                     "var n=document.getElementById('btnNext');"
                     "if(n&&!n.hidden)n.click();})()")
                time.sleep(0.25)
            time.sleep(0.8)
            d = c.call("Page.captureScreenshot",
                       {"format": "png", "captureBeyondViewport": True})
            fp = os.path.join(OUT, "F_%02d.png" % no)
            io.open(fp, "wb").write(base64.b64decode(d["result"]["data"]))
            print("  冊F 問%d → %s" % (no, fp))
    finally:
        try:
            p.kill()
        except Exception:
            pass
        if srv:
            srv.kill()


if __name__ == "__main__":
    main()
