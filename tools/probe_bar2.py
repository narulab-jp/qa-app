# -*- coding: utf-8 -*-
"""利用者バーが出題中に消える原因を、テストと同じ手順で追う調査用スクリプト。"""
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
PORT, DBG = 8803, 9273
URL = "http://127.0.0.1:%d/index.html" % PORT

s = socket.socket()
try:
    s.bind(("127.0.0.1", PORT)); s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                           cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except OSError:
    s.close(); srv = None
time.sleep(1.5)

ud = os.path.join(os.environ["TEMP"], "edge_probe_bar2")
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
        return "EXC: " + str(r["exceptionDetails"].get("exception", {})
                            .get("description", ""))[:200]
    return r.get("result", {}).get("value")


def state(tag):
    scr = ev("['s-user','s-home','s-unit','s-setup','s-quiz','s-judge','s-result']"
             ".filter(function(s){return !document.getElementById(s).hidden;}).join(',')")
    bar = ev("document.getElementById('userBar').hidden")
    nm = ev("document.getElementById('userBarName').textContent")
    print("  %-14s 画面=%-8s userBar.hidden=%-6s 表示=%r" % (tag, scr, bar, nm))


call("Runtime.enable")
for _ in range(80):
    if ev("document.readyState==='complete' && !!window.__app && !!window.__app.getSubject()"):
        break
    time.sleep(0.5)

HELPER = """
window.__t = {
  start: function(unitIds, count, level, order, mode){
    window.__app.setNoteAsked(true);
    document.getElementById('btnGoUnit').click();
    document.getElementById('btnUnitNone').click();
    unitIds.forEach(function(i){ document.getElementById('unit-'+i).click(); });
    document.getElementById('btnUnitNext').click();
    document.querySelector('[data-mode="'+mode+'"]').click();
    document.querySelector('[data-level="'+level+'"]').click();
    document.querySelector('[data-order="'+order+'"]').click();
    var b = document.querySelector('#optCount .opt[data-val="'+count+'"]');
    if(b) b.click();
    document.getElementById('btnStart').click();
    return window.__app.getQuiz() ? window.__app.getQuiz().roundList.length : 'no-quiz';
  },
  answer: function(correct){
    var q = window.__app.getQuiz(); var it = q && q.queue.length ? q.queue[0] : null;
    if(!it) return 'no-question';
    var self = window.__app.isSelfCheck(it.q);
    document.getElementById('btnKbd').click();
    document.getElementById('kbdInput').value = self ? '説明' : (correct ? it.q.a : '違う語');
    document.getElementById('btnKbdSubmit').click();
    var s = !document.getElementById('selfButtons').hidden;
    if(s){ document.getElementById(correct?'btnSelfOk':'btnSelfNg').click(); }
    else { document.getElementById('btnNext').click(); }
    return it.q.seq;
  }
};
"""
ev(HELPER)

print("--- 利用者を4人登録 ---")
for nm in ["長男", "次男", "三男 / テスト", "よつば"]:
    ev("document.getElementById('newUserName').value=%s;"
       "document.getElementById('btnAddUser').click();" % json.dumps(nm))
    ev("document.getElementById('btnSwitchUser').click()")
print("  users =", ev("JSON.stringify(window.__app.getUsers())"))
state("登録直後")

print("--- 長男を選ぶ ---")
ev("document.getElementById('user-長男').click()")
print("  currentUser =", ev("window.__app.getCurrentUser()"))
state("選択後")

print("--- 出題する ---")
print("  start ->", ev("window.__t.start(['01'],5,'ALL','csv','normal')"))
state("出題中")
print("  answer ->", ev("window.__t.answer(false)"))
state("解答後")

c.close(); p.kill()
if srv:
    srv.kill()
