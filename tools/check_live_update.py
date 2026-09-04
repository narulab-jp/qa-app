# -*- coding: utf-8 -*-
"""公開サイトで、版の確認まわりが働いているかを見る。

  版を差し替える試験（tools\\test_update.py）は手元でしかできないので、
  公開サイトでは「入っている版が分かること」「確かめるボタンが動くこと」
  「アプリ本体を通信で取りに行けること」を確かめる。
"""
import json
import os
import shutil
import subprocess
import sys
import time

import requests
from websockets.sync.client import connect

URL = sys.argv[1] if len(sys.argv) > 1 else "https://narulab-jp.github.io/qa-app/"
DBG = 9257
res = []


def rec(ok, title, detail=""):
    res.append(("OK" if ok else "NG", title, detail))
    print("[%s] %s %s" % ("OK" if ok else "NG", title, detail))


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


def main():
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    ud = os.path.join(os.environ["TEMP"], "edge_updlive")
    shutil.rmtree(ud, ignore_errors=True)
    p = subprocess.Popen([edge, "--headless=new", "--disable-gpu",
                          "--remote-debugging-port=%d" % DBG,
                          "--user-data-dir=" + ud, "--no-first-run", URL],
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
    c = CDP(ws)
    c.call("Runtime.enable")
    try:
        for _ in range(80):
            if c.ev("document.readyState==='complete' && !!window.__app "
                    "&& !!window.__app.getSubject()"):
                break
            time.sleep(0.5)
        for _ in range(40):
            if c.ev("!!navigator.serviceWorker.controller"):
                break
            time.sleep(0.5)
        v = c.ev("(function(){return new Promise(function(ok){"
                 "if(!navigator.serviceWorker.controller) return ok('');"
                 "var ch=new MessageChannel();"
                 "ch.port1.onmessage=function(e){ok(e.data&&e.data.version||'');};"
                 "navigator.serviceWorker.controller.postMessage("
                 "{type:'GET_VERSION'},[ch.port2]);"
                 "setTimeout(function(){ok('');},2500);});})()")
        rec(bool(v), "公開サイトで Service Worker が入り、版数を答える",
            "いまの版=%s" % v)

        reg = c.ev("(function(){return navigator.serviceWorker.getRegistration()"
                   ".then(function(r){return r ? String(r.updateViaCache) : '';});})()")
        rec(reg == "none",
            "sw.js を必ず通信で取りに行く設定になっている（updateViaCache）",
            "updateViaCache=%s" % reg)

        ok = c.ev("(function(){return fetch('app.js?probe='+Date.now())"
                  ".then(function(r){return r.ok;}).catch(function(){return false;});})()")
        rec(ok is True, "アプリ本体を通信で取りに行ける（通信優先）", "app.js を取り直せた")

        c.ev("document.getElementById('newUserName').value='版の確認';"
             "document.getElementById('btnAddUser').click();")
        c.ev("window.__app.setNoteAsked(true)")
        c.ev("document.getElementById('btnSettings').click()")
        time.sleep(1.4)
        sv = c.ev("document.getElementById('swVersion').textContent")
        rec("いまの版：" in (sv or ""), "設定に、いまの版が出る", sv)

        c.ev("document.getElementById('btnCheckUpd').click()")
        time.sleep(2.5)
        m = c.ev("document.getElementById('updMsg2').textContent")
        rec("いまが最新です" in (m or "") or "新しい版があります" in (m or ""),
            "「新しい版があるか確かめる」が動く", "「%s」" % m)

        bar = c.ev("!!document.getElementById('updBar')")
        btn = c.ev("document.getElementById('btnUpdate')"
                   " ? document.getElementById('btnUpdate').textContent : ''")
        rec(bar and btn.strip() == "今すぐ更新",
            "知らせの部品が画面にある（新しい版が出たときに表示される）",
            "ボタン=「%s」" % btn.strip())
    finally:
        try:
            p.kill()
        except Exception:
            pass
    ng = [r for r in res if r[0] == "NG"]
    print("=" * 62)
    print("判定: %s（OK %d / NG %d）"
          % ("NGなし" if not ng else "★NGあり", len(res) - len(ng), len(ng)))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
