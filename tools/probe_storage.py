# -*- coding: utf-8 -*-
"""公開サイトで、localStorage と IndexedDB が実際に使えるかを試す。

  「使っていない」ことは分かっているが「使えない」かどうかは未確認なので、
  実物のページ（https の公開サイト）で書いて・読んで・消してみる。
  模試の途中経過を置く先を決めるための実験。
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
DBG = 9363
res = []


def rec(ok, title, detail=""):
    res.append(("OK" if ok else "NG", title, detail))
    print("[%s] %s %s" % ("OK" if ok else "NG", title, detail))


class C(object):
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
            return {"error": json.dumps(r["exceptionDetails"],
                                        ensure_ascii=False)[:200]}
        return r.get("result", {}).get("value")


def main():
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    ud = os.path.join(os.environ["TEMP"], "edge_storage")
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
                if t["type"] == "page" and not (t.get("url") or "").startswith("about:"):
                    ws = t["webSocketDebuggerUrl"]
            if ws:
                break
        except Exception:
            pass
    c = C(ws)
    c.call("Runtime.enable")
    try:
        for _ in range(80):
            if c.ev("document.readyState==='complete'") is True:
                break
            time.sleep(0.5)

        # ---- どこを開いているか（origin が違うと結果が変わる）----
        info = c.ev("JSON.stringify({origin:location.origin,"
                    "proto:location.protocol,"
                    "cookie:navigator.cookieEnabled,"
                    "secure:window.isSecureContext})")
        rec(True, "いま開いている場所", str(info))

        # ---- localStorage ----
        r = c.ev("(function(){try{"
                 "localStorage.setItem('__probe','あ'.repeat(10));"
                 "var v=localStorage.getItem('__probe');"
                 "localStorage.removeItem('__probe');"
                 "return v && v.length===10 ? 'ok' : 'よみ違い';"
                 "}catch(e){return 'NG:'+e.name+' '+e.message;}})()")
        rec(r == "ok", "localStorage に書いて読んで消せる", str(r))

        # ---- 模試1回ぶんくらいの大きさを置けるか ----
        r2 = c.ev("(function(){try{"
                  "var big=JSON.stringify({a:new Array(2000).fill('x'.repeat(50))});"
                  "localStorage.setItem('__big',big);"
                  "var n=localStorage.getItem('__big').length;"
                  "localStorage.removeItem('__big');"
                  "return n;}catch(e){return 'NG:'+e.name;}})()")
        rec(isinstance(r2, (int, float)) and r2 > 100000,
            "模試1回ぶんくらいの大きさ（約100KB）を置ける",
            "%s 文字を書いて読み戻せた" % r2)

        # ---- 再読み込みしても残るか ----
        c.ev("localStorage.setItem('__keep','のこる')")
        c.call("Page.navigate", {"url": URL})
        time.sleep(2.5)
        for _ in range(40):
            if c.ev("document.readyState==='complete'") is True:
                break
            time.sleep(0.4)
        r3 = c.ev("localStorage.getItem('__keep')")
        c.ev("localStorage.removeItem('__keep')")
        rec(r3 == "のこる", "ページを読み込み直しても残っている", str(r3))

        # ---- IndexedDB ----
        r4 = c.ev("""(function(){return new Promise(function(ok){
          try{
            var q=indexedDB.open('__probe_db',1);
            q.onupgradeneeded=function(e){ e.target.result.createObjectStore('s'); };
            q.onerror=function(){ ok('NG:open'); };
            q.onsuccess=function(e){
              var db=e.target.result;
              var tx=db.transaction('s','readwrite');
              tx.objectStore('s').put({t:'あ'.repeat(100)},'k');
              tx.oncomplete=function(){
                var tx2=db.transaction('s','readonly');
                var g=tx2.objectStore('s').get('k');
                g.onsuccess=function(){
                  var v=g.result && g.result.t.length;
                  db.close(); indexedDB.deleteDatabase('__probe_db');
                  ok(v===100 ? 'ok' : 'よみ違い');
                };
              };
              tx.onerror=function(){ ok('NG:tx'); };
            };
          }catch(e){ ok('NG:'+e.name); }
          setTimeout(function(){ ok('NG:時間切れ'); }, 6000);
        });})()""")
        rec(r4 == "ok", "IndexedDB に書いて読んで消せる", str(r4))

        # ---- 使える容量の見積り ----
        r5 = c.ev("(function(){return (navigator.storage && navigator.storage.estimate)"
                  " ? navigator.storage.estimate().then(function(e){"
                  "return JSON.stringify({quota:e.quota, usage:e.usage});})"
                  " : Promise.resolve('この端末では分からない');})()")
        try:
            q = json.loads(r5)
            rec(True, "使える容量の見積り",
                "上限 %.0f MB／いま %.1f MB"
                % (q["quota"] / 1048576.0, q["usage"] / 1048576.0))
        except Exception:
            rec(True, "使える容量の見積り", str(r5))

        # ---- Service Worker と同時に使えるか（干渉しないか）----
        r6 = c.ev("(function(){return navigator.serviceWorker.getRegistration()"
                  ".then(function(r){"
                  "localStorage.setItem('__sw','1');"
                  "var v=localStorage.getItem('__sw');"
                  "localStorage.removeItem('__sw');"
                  "return (r?'SWあり':'SWなし')+'／localStorage '+(v==='1'?'使える':'だめ');"
                  "});})()")
        rec("使える" in str(r6), "Service Worker が動いていても使える", str(r6))
    finally:
        try:
            p.kill()
        except Exception:
            pass
    ng = [x for x in res if x[0] == "NG"]
    print("=" * 60)
    print("判定: %s（OK %d / NG %d）"
          % ("NGなし" if not ng else "★NGあり", len(res) - len(ng), len(ng)))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
