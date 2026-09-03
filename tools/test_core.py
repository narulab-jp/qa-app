# -*- coding: utf-8 -*-
"""Phase 4 で足した「コア問題」の動作確認。
   ヘッドレス Edge を DevTools プロトコルで操作し、画面の状態を読んで判定する。"""
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
PORT = 8795
DBG = 9275
URL = "http://127.0.0.1:%d/index.html" % PORT
res = []


def rec(ok, title, detail=""):
    st = ok if isinstance(ok, str) else ("OK" if ok else "NG")
    res.append((st, title, detail))
    print("[%s] %s %s" % (st, title, detail))
    return st == "OK"


class C(object):
    def __init__(self, url):
        self.ws = connect(url, max_size=None)
        self.n = 0

    def call(self, m, p=None):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": m, "params": p or {}}))
        while True:
            r = json.loads(self.ws.recv(timeout=60))
            if r.get("id") == self.n:
                return r

    def ev(self, e):
        r = self.call("Runtime.evaluate",
                      {"expression": e, "returnByValue": True,
                       "awaitPromise": True}).get("result", {})
        if "exceptionDetails" in r:
            raise RuntimeError(str(r["exceptionDetails"])[:250])
        return r.get("result", {}).get("value")


def main():
    # ---------- データ側 ----------
    doc = json.loads(io.open(os.path.join(ROOT, "data", "chiri.json"),
                             encoding="utf-8").read())
    qs = [q for u in doc["units"] for q in u["questions"]]
    core = [q for q in qs if q.get("core")]
    lv = {}
    for q in qs:
        lv[q["level"]] = lv.get(q["level"], 0) + 1
    rec(len(core) > 0 and len(core) < len(qs) / 2,
        "コア問題が全体の一部として付いている",
        "%d問中 %d問（%.0f%%）" % (len(qs), len(core),
                                100.0 * len(core) / len(qs)))
    imp = json.loads(io.open(os.path.join(
        os.path.expanduser("~"), "Downloads", "CHIRI_QA_20260901", "src",
        "imp_map.json"), encoding="utf-8").read())
    bad = [q["seq"] for q in qs if imp.get(str(q["seq"])) != q["level"]]
    rec(not bad, "重要度が振り直しの表どおりに入っている",
        "S %d／A %d／B %d問" % (lv.get("S", 0), lv.get("A", 0), lv.get("B", 0))
        if not bad else str(bad[:5]))
    cl = set(json.loads(io.open(os.path.join(
        os.path.expanduser("~"), "Downloads", "CHIRI_QA_20260901", "src",
        "core_list.json"), encoding="utf-8").read()))
    bad = [q["seq"] for q in qs if bool(q.get("core")) != (q["seq"] in cl)]
    rec(not bad, "コアの印が表どおりに入っている", "%d問すべて一致" % len(qs)
        if not bad else str(bad[:5]))
    ncore_S = len([q for q in core if q["level"] != "S"])
    rec(ncore_S == 0, "コア問題はすべて重要度Sになっている",
        "コア%d問すべてS" % len(core) if not ncore_S else "S以外が%d問" % ncore_S)

    # 図表編・本番形式編にはコアを付けていない（役割が違う）
    for name in ("chiri-zuhyo.json", "chiri-honban.json"):
        d2 = json.loads(io.open(os.path.join(ROOT, "data", name),
                                encoding="utf-8").read())
        n = len([q for u in d2["units"] for q in u["questions"]
                 if q.get("core")])
        rec(n == 0, "%s にはコアの印を付けていない" % name, "コア %d問" % n)

    # ---------- 画面 ----------
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
    ud = os.path.join(os.environ["TEMP"], "edge_core")
    shutil.rmtree(ud, ignore_errors=True)
    p = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--remote-debugging-port=%d" % DBG,
                          "--user-data-dir=" + ud, "--remote-allow-origins=*",
                          URL],
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
        for _ in range(80):
            if c.ev("document.readyState==='complete' && !!window.__app "
                    "&& !!window.__app.getSubject()"):
                break
            time.sleep(0.5)
        c.ev("document.getElementById('newUserName').value='テスト';"
             "document.getElementById('btnAddUser').click();"
             "window.__app.setNoteAsked(true);")

        # 全単元を選んで「コア問題だけ」にする
        c.ev("document.getElementById('btnGoUnit').click();"
             "document.getElementById('btnUnitAll').click();"
             "document.getElementById('btnUnitNext').click();"
             "document.querySelector('[data-level=\"CORE\"]').click();"
             "document.querySelector('#optCount .opt[data-val=\"0\"]').click();")
        txt = c.ev("document.getElementById('setupCount').textContent")
        hid = c.ev("document.querySelector('[data-level=\"CORE\"]').hidden")
        rec((str(len(core)) + "問中") in txt and hid is False,
            "「コア問題だけ」を選ぶと、その問数だけが対象になる",
            "表示=「%s」" % txt.strip())

        c.ev("document.querySelector('[data-order=\"csv\"]').click();"
             "document.getElementById('btnStart').click();")
        n = c.ev("window.__app.getQuiz().roundList.length")
        allcore = c.ev("window.__app.getQuiz().roundList"
                       ".every(function(x){return !!x.q.core;})")
        rec(n == len(core) and allcore is True,
            "出題されたのがすべてコア問題である",
            "%d問出題／すべてコア=%s" % (n, allcore))

        # 答え合わせの画面に ◎コア が出る
        c.ev("document.getElementById('btnKbd').click();"
             "document.getElementById('kbdInput').value='まったく関係のない語';"
             "document.getElementById('btnKbdSubmit').click();")
        jl = c.ev("document.getElementById('jLevel').textContent")
        rec("◎コア" in (jl or ""),
            "答え合わせの画面でコア問題だと分かる", "表示=「%s」" % jl)
        vis = c.ev("getComputedStyle(document.getElementById('mLevel')).display")
        rec(vis == "none", "出題中は重要度・コアを出していない（指示Dのまま）",
            "#mLevel の display=%s" % vis)

        # 図表編ではコアの選択肢を出さない
        c.ev("document.getElementById('btnQuit').click()")
        c.ev("window.__app.openSubjectById('chiri-zuhyo')")
        for _ in range(40):
            time.sleep(0.3)
            if c.ev("window.__app.getSubject().subjectId") == "chiri-zuhyo":
                break
        c.ev("document.getElementById('btnGoUnit').click();"
             "document.getElementById('btnUnitAll').click();"
             "document.getElementById('btnUnitNext').click();")
        hid = c.ev("document.querySelector('[data-level=\"CORE\"]').hidden")
        lvl = c.ev("window.__app.getCfg().level")
        st = c.ev("document.getElementById('btnStart').disabled")
        rec(hid is True and lvl != "CORE" and st is False,
            "図表編ではコアの選択肢を出さず、行き止まりにならない",
            "選択肢hidden=%s／level=%s／はじめるボタン=%s"
            % (hid, lvl, "押せる" if st is False else "押せない"))

        # 間違いノートは通し番号で問を指したまま
        nn = c.ev("window.__app.getNote().entries.length")
        seq = c.ev("window.__app.getNote().entries.length ? "
                   "window.__app.getNote().entries[0].seq : -1")
        rec(nn > 0 and seq > 0,
            "間違いノートが通し番号で記録されている（振り直しの影響なし）",
            "ノート%d件／先頭 seq=%s" % (nn, seq))
    finally:
        try:
            p.kill()
        except Exception:
            pass
        if srv:
            srv.kill()

    ng = [r for r in res if r[0] == "NG"]
    print("-" * 68)
    print("判定: %s（OK %d / NG %d）"
          % ("NGなし" if not ng else "★NG あり",
             len([r for r in res if r[0] == "OK"]), len(ng)))
    out = os.path.join(ROOT, "動作確認結果_コア問題.txt")
    io.open(out, "w", encoding="utf-8-sig", newline="\r\n").write(
        "コア問題と重要度の振り直しの動作確認\n"
        + "=" * 60 + "\n\n"
        + "\n\n".join("[%s] %s\n      %s" % r for r in res)
        + "\n\n" + "=" * 60 + "\n判定: %s（OK %d / NG %d）\n"
        % ("NGなし" if not ng else "★NG あり",
           len([r for r in res if r[0] == "OK"]), len(ng)))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
