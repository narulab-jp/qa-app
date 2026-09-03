# -*- coding: utf-8 -*-
"""公開URLで、図表・読図編がオフラインでも開けるかを確かめる。
   図（SVG）と問題データがキャッシュから読めることを、実際に表示させて確認する。"""
import json
import os
import shutil
import subprocess
import sys
import time

import requests
from websockets.sync.client import connect

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
URL = "https://narulab-jp.github.io/qa-app/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DBG = 9311
res = []


def rec(ok, title, detail=""):
    st = "OK" if ok else "NG"
    res.append((st, title, detail))
    print("[%s] %s %s" % (st, title, detail))


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
        if "exceptionDetails" in r:
            return None
        return r.get("result", {}).get("value")


def ready(c, tries=80):
    for _ in range(tries):
        try:
            if c.ev("document.readyState==='complete' && !!window.__app "
                    "&& !!window.__app.getSubject()"):
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    ud = os.path.join(os.environ["TEMP"], "edge_zoff")
    shutil.rmtree(ud, ignore_errors=True)
    p = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--remote-debugging-port=%d" % DBG, "--user-data-dir=" + ud,
                          "--remote-allow-origins=*", URL],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws = None
        for _ in range(80):
            time.sleep(0.5)
            try:
                for t in requests.get("http://127.0.0.1:%d/json/list" % DBG,
                                      timeout=2).json():
                    if t["type"] == "page" and t["url"].startswith("http"):
                        ws = t["webSocketDebuggerUrl"]
                if ws:
                    break
            except Exception:
                pass
        c = C(connect(ws, max_size=None))
        c.call("Page.enable")
        c.call("Runtime.enable")
        c.call("Network.enable")
        if not ready(c):
            rec(False, "公開サイトが開く", "開かなかった")
            return 1
        for _ in range(60):
            if c.ev("!!navigator.serviceWorker.controller"):
                break
            time.sleep(1)
        keys = c.ev("caches.keys().then(function(ks){return caches.open(ks[0]);})"
                    ".then(function(cc){return cc.keys();})"
                    ".then(function(k){return k.map(function(r){"
                    "return r.url.split('/qa-app/')[1]||'/';}).join(', ');})")
        figs = [x for x in (keys or "").split(", ") if x.startswith("figures/")]
        nfig = len([x for x in os.listdir(os.path.join(ROOT, "figures"))
                    if x.endswith(".svg")])
        dat = [d for d in ("data/chiri-zuhyo.json", "data/chiri-honban.json")
               if d in (keys or "")]
        rec(len(figs) == nfig and len(dat) == 2,
            "図（SVG）と図表編・本番形式編のデータがキャッシュに入っている",
            "図 %d枚（figures/ の%d枚すべて）／データ %s／骨組みも含めて全%d件"
            % (len(figs), nfig, "・".join(dat), len((keys or "").split(", "))))

        # オフラインにして開き直す（Service Worker を起こしてから遮断する）
        ok = False
        for _ in range(4):
            c.ev("fetch('./manifest.json').catch(function(){})")
            time.sleep(0.5)
            c.call("Network.emulateNetworkConditions",
                   {"offline": True, "latency": 0,
                    "downloadThroughput": 0, "uploadThroughput": 0})
            c.call("Page.reload", {"ignoreCache": False})
            ok = ready(c, 40)
            if ok:
                break
            body = c.ev("document.body ? document.body.innerText : ''") or ""
            if "ERR_INTERNET_DISCONNECTED" not in body:
                break
            c.call("Network.emulateNetworkConditions",
                   {"offline": False, "latency": 0,
                    "downloadThroughput": -1, "uploadThroughput": -1})
            c.call("Page.reload", {"ignoreCache": False})
            ready(c, 40)
        if not ok:
            rec(False, "オフラインでアプリが起動する", "起動しなかった")
            return 1

        c.ev("(function(){if(!window.__app.getCurrentUser()){"
             "document.getElementById('newUserName').value='テスト';"
             "document.getElementById('btnAddUser').click();}"
             "window.__app.setNoteAsked(true);})()")
        c.ev("window.__app.openSubjectById('chiri-zuhyo')")
        # 科目の読み込みは非同期なので、切りかわるまで待つ
        sid = None
        for _ in range(40):
            time.sleep(0.5)
            sid = c.ev("window.__app.getSubject() ? "
                       "window.__app.getSubject().subjectId : ''")
            if sid == "chiri-zuhyo":
                break
        nq = c.ev("window.__app.getSubject().units.reduce(function(a,u){"
                  "return a+u.questions.length;},0)")
        rec(sid == "chiri-zuhyo" and nq == 159,
            "オフラインでも図表編の問題が読み込める",
            "科目=%s／%d問" % (sid, nq))

        c.ev("(function(){document.getElementById('btnGoUnit').click();"
             "document.getElementById('btnUnitNone').click();"
             "document.getElementById('unit-A').click();"
             "document.getElementById('btnUnitNext').click();"
             "document.querySelector('[data-level=\"ALL\"]').click();"
             "document.querySelector('[data-order=\"csv\"]').click();"
             "document.getElementById('btnStart').click();})()")
        time.sleep(1.5)
        got = c.ev("(function(){var i=document.querySelector('#figBox img');"
                   "return i? (i.complete? i.naturalWidth+'x'+i.naturalHeight : 'まだ')"
                   " : 'なし';})()")
        rec(got not in ("なし", "まだ", "0x0"),
            "オフラインでも図がキャッシュから表示される", "図の実寸=%s" % got)
    finally:
        try:
            p.kill()
        except Exception:
            pass
    ng = [r for r in res if r[0] == "NG"]
    print("-" * 68)
    print("オフラインの確認: %s（OK %d / NG %d）"
          % ("NGなし" if not ng else "★NG あり",
             len([r for r in res if r[0] == "OK"]), len(ng)))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
