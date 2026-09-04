# -*- coding: utf-8 -*-
"""公開サイトを実際のブラウザで開いて、第29講が単元一覧に出るかを確かめる。

  ローカルのファイルではなく https://narulab-jp.github.io/qa-app/ を開く。
  まっさらなプロファイルで開くので、古いキャッシュの影響を受けない。
"""
import json
import os
import subprocess
import shutil
import sys
import time

import requests
from websockets.sync.client import connect

URL = "https://narulab-jp.github.io/qa-app/"
DBG = 9341
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


def main():
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    ud = os.path.join(os.environ["TEMP"], "edge_live29")
    shutil.rmtree(ud, ignore_errors=True)      # まっさらな状態で開く
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
    if not ws:
        p.kill()
        raise RuntimeError("Edge に接続できませんでした")
    c = CDP(ws)
    c.call("Runtime.enable")
    try:
        ok = False
        for _ in range(80):
            try:
                if c.ev("document.readyState==='complete' && !!window.__app "
                        "&& !!window.__app.getSubject()"):
                    ok = True
                    break
            except Exception:
                pass
            time.sleep(0.5)
        rec(ok, "公開サイトが開ける", URL)

        # ---- 読みこんだデータ ----
        n = c.ev("window.__app.getSubject().units.length")
        tot = c.ev("window.__app.getSubject().units.reduce("
                   "function(a,u){return a+u.questions.length;},0)")
        src = c.ev("window.__app.getSubject().source")
        rec(n == 29 and tot == 885,
            "アプリが読みこんだのが29単元・885問である",
            "%d単元／%d問／%s" % (n, tot, src))

        # ---- 単元一覧の画面 ----
        c.ev("document.getElementById('newUserName').value='確認';"
             "document.getElementById('btnAddUser').click();")
        c.ev("window.__app.setNoteAsked(true)")
        c.ev("document.getElementById('btnGoUnit').click()")
        time.sleep(0.5)
        nb = c.ev("document.querySelectorAll('#unitList .unit').length")
        dis = c.ev("Array.from(document.querySelectorAll('#unitList .unit'))"
                   ".filter(function(e){return e.disabled;}).length")
        last = c.ev("document.getElementById('unit-29')"
                    " ? document.getElementById('unit-29').textContent : ''")
        vis = c.ev("(function(){var e=document.getElementById('unit-29');"
                   "if(!e) return 'ボタンがない';"
                   "var r=e.getBoundingClientRect();"
                   "return (r.width>0&&r.height>0)?'表示されている':'見えない';})()")
        rec(nb == 29 and dis == 0 and "地域調査" in (last or ""),
            "単元一覧に第29講が出ている",
            "ボタン%d個／無効%d個／29番目=「%s」／%s"
            % (nb, dis, (last or "").strip(), vis))

        # ---- 第29講だけを選んで出題できる ----
        c.ev("document.getElementById('btnUnitNone').click();"
             "document.getElementById('unit-29').click();"
             "document.getElementById('btnUnitNext').click();"
             "document.querySelector('#optCount .opt[data-val=\"0\"]').click();"
             "document.querySelector('[data-level=\"ALL\"]').click();"
             "document.querySelector('[data-order=\"csv\"]').click();"
             "document.getElementById('btnStart').click();")
        qn = c.ev("window.__app.getQuiz().roundList.length")
        uids = c.ev("JSON.stringify(Array.from(new Set("
                    "window.__app.getQuiz().roundList.map("
                    "function(x){return x.unit.id;}))))")
        q1 = c.ev("window.__app.getQuiz().queue[0].q.q")
        rec(qn == 34 and uids == '["29"]',
            "第29講だけを選んで34問出題できる",
            "%d問／単元=%s／1問目=「%s…」" % (qn, uids, (q1 or "")[:28]))

        # ---- 出題順に「優先度の高い順」がある ----
        c.ev("document.getElementById('btnQuit').click();")
        lab = c.ev("JSON.stringify(Array.from("
                   "document.querySelectorAll('[data-order]')).map("
                   "function(e){return e.textContent;}))")
        rec("優先度の高い順" in (lab or ""),
            "出題順に「優先度の高い順」が出ている", lab)

        # ---- Service Worker ----
        # 版数は上げていくので決め打ちしない。
        # 公開されている sw.js の VERSION と、ブラウザに入ったキャッシュ名を突き合わせる。
        import re as _re
        pub = requests.get(URL + "sw.js?nc=1", timeout=30).text
        m = _re.search(r'VERSION\s*=\s*"([^"]+)"', pub)
        want = m.group(1) if m else ""
        sw = c.ev("navigator.serviceWorker.getRegistration().then("
                  "function(r){ return r ? (r.active ? r.active.scriptURL "
                  ": 'installing') : 'なし'; })")
        ck = c.ev("caches.keys().then(function(k){return JSON.stringify(k);})")
        rec(bool(want) and want in (ck or ""),
            "ブラウザに入るキャッシュが、公開中の版と同じ（%s）" % want,
            "%s／SW=%s" % (ck, sw))
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
