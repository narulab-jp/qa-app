# -*- coding: utf-8 -*-
"""CDP のオフライン擬似化で navigator.onLine が false になるかを実測する調査用スクリプト。"""
import json
import os
import shutil
import subprocess
import time

import requests
from websockets.sync.client import connect

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
URL = "https://narulab-jp.github.io/qa-app/"
PORT = 9261

ud = os.path.join(os.environ["TEMP"], "edge_onl")
shutil.rmtree(ud, ignore_errors=True)
p = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                      "--remote-debugging-port=%d" % PORT, "--user-data-dir=" + ud,
                      "--remote-allow-origins=*", URL],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ws = None
for _ in range(60):
    time.sleep(0.5)
    try:
        for t in requests.get("http://127.0.0.1:%d/json/list" % PORT, timeout=3).json():
            if t.get("type") == "page" and not (t.get("url") or "").startswith("about:"):
                ws = t["webSocketDebuggerUrl"]
        if ws:
            break
    except Exception:
        pass

c = connect(ws, max_size=None)
n = [0]


def call(m, pa=None):
    n[0] += 1
    c.send(json.dumps({"id": n[0], "method": m, "params": pa or {}}))
    while True:
        r = json.loads(c.recv(timeout=30))
        if r.get("id") == n[0]:
            return r


def ev(e):
    return call("Runtime.evaluate",
                {"expression": e, "returnByValue": True, "awaitPromise": True}) \
        .get("result", {}).get("result", {}).get("value")


call("Runtime.enable")
call("Network.enable")
for _ in range(80):
    if ev("document.readyState==='complete'"):
        break
    time.sleep(0.5)

print("通常時          navigator.onLine =", ev("navigator.onLine"))
call("Network.emulateNetworkConditions",
     {"offline": True, "latency": 0, "downloadThroughput": 0, "uploadThroughput": 0})
time.sleep(2.0)
print("CDPオフライン時 navigator.onLine =", ev("navigator.onLine"))
print("offlineBanner   =", repr(ev("document.getElementById('offlineBanner').textContent")))
call("Page.reload")
for _ in range(60):
    if ev("document.readyState==='complete'"):
        break
    time.sleep(0.5)
time.sleep(1.0)
print("再読込後        navigator.onLine =", ev("navigator.onLine"))
print("offlineBanner   =", repr(ev("document.getElementById('offlineBanner').textContent")))
c.close()
p.kill()
