# -*- coding: utf-8 -*-
"""出題設定の画面を撮る（コア問題の選択肢の見え方を目視で確かめる）。"""
import base64
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
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 8797
DBG = 9277
OUT = os.path.join(os.environ["TEMP"], "qa_shots")


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
    ud = os.path.join(os.environ["TEMP"], "edge_shot_setup")
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
        c = connect(ws, max_size=None)
        n = [0]

        def call(m, pp=None):
            n[0] += 1
            c.send(json.dumps({"id": n[0], "method": m, "params": pp or {}}))
            while True:
                r = json.loads(c.recv(timeout=60))
                if r.get("id") == n[0]:
                    return r

        def ev(e):
            return call("Runtime.evaluate",
                        {"expression": e, "returnByValue": True,
                         "awaitPromise": True})["result"] \
                .get("result", {}).get("value")

        call("Runtime.enable")
        call("Page.enable")
        call("Emulation.setDeviceMetricsOverride",
             {"width": 390, "height": 844, "deviceScaleFactor": 2,
              "mobile": True})
        for _ in range(60):
            if ev("document.readyState==='complete' && !!window.__app"):
                break
            time.sleep(0.5)
        ev("document.getElementById('newUserName').value='テスト';"
           "document.getElementById('btnAddUser').click();"
           "window.__app.setNoteAsked(true);"
           "document.getElementById('btnGoUnit').click();"
           "document.getElementById('btnUnitAll').click();"
           "document.getElementById('btnUnitNext').click();"
           "document.querySelector('[data-level=\"CORE\"]').click();")
        time.sleep(0.8)
        d = call("Page.captureScreenshot",
                 {"format": "png", "captureBeyondViewport": True})
        fp = os.path.join(OUT, "setup_core.png")
        io.open(fp, "wb").write(base64.b64decode(d["result"]["data"]))
        print("  " + fp)
    finally:
        try:
            p.kill()
        except Exception:
            pass
        if srv:
            srv.kill()


if __name__ == "__main__":
    main()
