# -*- coding: utf-8 -*-
"""図版を実際にブラウザで描かせて PNG にする（目で見て確かめるため）。
   白黒印刷の確認用に、グレースケール相当（filter: grayscale）でも撮る。"""
import base64
import io
import json
import os
import subprocess
import sys
import time

import requests
from websockets.sync.client import connect

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG = os.path.join(ROOT, "figures")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(os.environ["TEMP"], "qa_figs")
DBG = 9281


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
        return r.get("result", {}).get("value")


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    names = sorted(os.listdir(FIG))
    if len(sys.argv) > 1:      # 名前の一部を渡すと、その図だけを書き出す
        names = [x for x in names if any(a in x for a in sys.argv[1:])]
    ud = os.path.join(os.environ["TEMP"], "edge_figs")
    p = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu",
                          "--remote-debugging-port=%d" % DBG,
                          "--user-data-dir=" + ud, "--no-first-run",
                          "about:blank"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws = None
        for _ in range(60):
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
        for nm in names:
            hp = os.path.join(OUT, "_view.html")
            io.open(hp, "w", encoding="utf-8", newline="\n").write(
                "<meta charset='utf-8'>"
                "<body style='margin:0;background:white'>"
                "<img id='i' style='display:block;filter:grayscale(1)' src='"
                + os.path.join(FIG, nm).replace("\\", "/") + "'>")
            c.call("Page.navigate", {"url": "file:///" + hp.replace("\\", "/")})
            time.sleep(1.2)
            w = c.ev("document.getElementById('i').naturalWidth")
            h = c.ev("document.getElementById('i').naturalHeight")
            c.call("Emulation.setDeviceMetricsOverride",
                   {"width": int(w or 720), "height": int(h or 600),
                    "deviceScaleFactor": 2, "mobile": False})
            time.sleep(0.4)
            d = c.call("Page.captureScreenshot", {"format": "png"})
            out = os.path.join(OUT, nm.replace(".svg", ".png"))
            io.open(out, "wb").write(base64.b64decode(d["data"]))
            print("  %-18s %sx%s -> %s" % (nm, w, h, out))
    finally:
        try:
            p.kill()
        except Exception:
            pass


main()
