# -*- coding: utf-8 -*-
"""利用者バーが表示されない原因を調べる調査用スクリプト。"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time

import requests
from websockets.sync.client import connect

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT, DBG = 8802, 9272
URL = "http://127.0.0.1:%d/index.html" % PORT

s = socket.socket()
try:
    s.bind(("127.0.0.1", PORT)); s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT),
                            "--bind", "127.0.0.1"], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except OSError:
    s.close(); srv = None
time.sleep(1.5)

ud = os.path.join(os.environ["TEMP"], "edge_probe_bar")
shutil.rmtree(ud, ignore_errors=True)
p = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                      "--remote-debugging-port=%d" % DBG, "--user-data-dir=" + ud,
                      "--remote-allow-origins=*", URL],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ws = None
for _ in range(60):
    time.sleep(0.5)
    try:
        for t in requests.get("http://127.0.0.1:%d/json/list" % DBG, timeout=3).json():
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
    r = call("Runtime.evaluate", {"expression": e, "returnByValue": True,
                                  "awaitPromise": True}).get("result", {})
    if "exceptionDetails" in r:
        return "EXC: " + str(r["exceptionDetails"].get("exception", {}).get("description", ""))[:160]
    return r.get("result", {}).get("value")


call("Runtime.enable")
for _ in range(80):
    if ev("document.readyState==='complete' && !!window.__app"):
        break
    time.sleep(0.5)

print("s-user 表示 :", ev("!document.getElementById('s-user').hidden"))
ev("document.getElementById('newUserName').value='長男';"
   "document.getElementById('btnAddUser').click();")
time.sleep(0.5)
print("currentUser :", ev("window.__app.getCurrentUser()"))
print("s-home 表示 :", ev("!document.getElementById('s-home').hidden"))
print("userBar.hidden        :", ev("document.getElementById('userBar').hidden"))
print("userBar 属性          :", ev("document.getElementById('userBar').getAttribute('hidden')"))
print("userBarName textContent:", repr(ev("document.getElementById('userBarName').textContent")))
print("renderUserBar 型      :", ev("typeof renderUserBar"))
print("手動で呼ぶ            :", ev("(function(){renderUserBar('s-home');"
                                    "return [document.getElementById('userBar').hidden,"
                                    "document.getElementById('userBarName').textContent];})()"))
print("show 関数の中身       :", ev("String(show).slice(0,220)"))
c.close(); p.kill()
if srv:
    srv.kill()
