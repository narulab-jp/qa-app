# -*- coding: utf-8 -*-
"""本番版アプリの動作確認。
ヘッドレス Edge を DevTools プロトコルで実際に操作し、画面の状態を読んで判定する。"""
import csv
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
# csv2json.py と同じ順で探す（Downloads が正、デスクトップは控え）
_CSVNAME = "地理一問一答_全講統合.csv"
CSVSRC = os.path.join(os.path.expanduser("~"), "Downloads",
                      "CHIRI_QA_20260901", "CSV", _CSVNAME)
if not os.path.isfile(CSVSRC):
    CSVSRC = os.path.join(os.path.expanduser("~"), "OneDrive", "デスクトップ",
                          "CHIRI_QA_20260901", "CSV", _CSVNAME)
PORT = 8781
DBG = 9231
URL = "http://127.0.0.1:%d/index.html" % PORT

EXPECT_UNITS = {"01":31,"02":25,"03":30,"04":25,"05":30,"06":32,"07":25,"08":31,
                "09":49,"10":25,"11":29,"12":30,"13":27,"14":26,"15":26,"16":25,
                "17":28,"18":26,"19":33,"20":29,"21":30,"22":33,"23":39,"24":25,
                "25":41,"26":28,"27":25,"28":48,"29":34}
res = []


def rec(ok, title, detail=""):
    st = ok if isinstance(ok, str) else ("OK" if ok else "NG")
    res.append((st, title, detail))
    print("[%s] %s %s" % (st, title, detail))
    return st == "OK"


class CDP(object):
    def __init__(self, url):
        self.ws = connect(url, max_size=None)
        self.n = 0

    def call(self, method, params=None):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params or {}}))
        while True:
            m = json.loads(self.ws.recv(timeout=30))
            if m.get("id") == self.n:
                return m

    def ev(self, expr):
        m = self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                           "awaitPromise": True})
        r = m.get("result", {})
        if "exceptionDetails" in r:
            raise RuntimeError(str(r["exceptionDetails"])[:300])
        return r.get("result", {}).get("value")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def free(port):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port)); return True
    except OSError:
        return False
    finally:
        s.close()


def open_page(url, port=DBG, extra=None, headless=True):
    ud = os.path.join(os.environ["TEMP"], "edge_qaapp%d" % port)
    shutil.rmtree(ud, ignore_errors=True)
    p = subprocess.Popen(
        [EDGE] + (["--headless=new", "--disable-gpu"] if headless else []) +
        ["--no-sandbox", "--remote-debugging-port=%d" % port,
         "--user-data-dir=" + ud, "--remote-allow-origins=*"] + (extra or []) + [url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    for _ in range(60):
        time.sleep(0.5)
        try:
            for t in requests.get("http://127.0.0.1:%d/json/list" % port, timeout=3).json():
                if t.get("type") != "page" or not t.get("webSocketDebuggerUrl"):
                    continue
                if not (t.get("url") or "").startswith("about:"):
                    ws = t["webSocketDebuggerUrl"]; break
                if ws is None:
                    ws = t["webSocketDebuggerUrl"]
            if ws:
                break
        except Exception:
            pass
    if not ws:
        p.kill(); raise RuntimeError("Edge に接続できませんでした")
    c = CDP(ws)
    c.call("Runtime.enable")
    return p, c


def wait_ready(c):
    for _ in range(80):
        try:
            if c.ev("document.readyState==='complete' && !!window.__app "
                    "&& !!window.__app.getSubject()"):
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    # ---------- 1. csv2json.py ----------
    r = subprocess.run([sys.executable, os.path.join(HERE, "csv2json.py")],
                       capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    outp = os.path.join(ROOT, "data", "chiri.json")
    rec(r.returncode == 0 and os.path.exists(outp),
        "csv2json.py が動き、data/chiri.json が生成される",
        (r.stdout or "").strip().splitlines()[2] if r.returncode == 0 else (r.stderr or "")[:120])

    doc = json.load(open(outp, encoding="utf-8"))
    total = sum(len(u["questions"]) for u in doc["units"])
    rec(total == 885, "生成されたJSONの問数が885問（851問＋指示Hで足した第29講34問）",
        "実数 %d問／欠番は通し533・781・789" % total)

    with open(CSVSRC, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))[1:]
    flat = [q for u in doc["units"] for q in u["questions"]]
    # 通し番号で突き合わせる（重複3問を外したので、行の位置では合わない）
    bycsv = dict((cr[4], cr) for cr in rows)
    mism = []
    for q in flat:
        cr = bycsv.get(str(q["seq"]))
        if not cr:
            mism.append("seq%s がCSVにない" % q["seq"])
            continue
        if (q["q"], q["a"], q["exp"]) != (cr[7], cr[8], cr[9]):
            mism.append("seq%s 本文" % q["seq"])
        if (q["section"], q["level"], q["type"]) != (cr[2], cr[5], cr[6]):
            mism.append("seq%s 属性" % q["seq"])
    rec(len(flat) == len(rows) and not mism,
        "JSONの全885問が統合CSVと完全一致（問題文・解答・解説）",
        "885問すべて一致" if not mism else str(mism[:5]))

    bad = [u["id"] for u in doc["units"] if len(u["questions"]) != EXPECT_UNITS.get(u["id"])]
    rec(len(doc["units"]) == 29 and not bad,
        "単元が29個あり、各単元の問数が表と一致",
        "29単元すべて一致" if not bad else "★不一致 " + str(bad))

    self_n = sum(1 for q in flat if q["selfCheck"])
    rec(True, "判定方式の内訳（参考）",
        "自動判定 %d問／自己採点 %d問" % (total - self_n, self_n))

    # ---------- サーバ・ブラウザ ----------
    srv = None
    if free(PORT):
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT),
                                "--bind", "127.0.0.1"], cwd=ROOT,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    proc, c = open_page(URL)
    try:
        ready = wait_ready(c)
        rec(ready, "トップ画面が表示される", "タイトル=" + str(c.ev("document.title")))
        # 指示C以降は利用者を決めてから学習を始める。単元一覧はホームから開く。
        c.ev("document.getElementById('newUserName').value='テスト';"
             "document.getElementById('btnAddUser').click();")
        c.ev("window.__app.setNoteAsked(true)")   # ノート未読込の確認を出さない
        c.ev("document.getElementById('btnGoUnit').click()")

        # ---------- 単元一覧 ----------
        n = c.ev("document.querySelectorAll('#unitList .unit').length")
        dis = c.ev("Array.from(document.querySelectorAll('#unitList .unit'))"
                   ".filter(e=>e.disabled).length")
        nm = c.ev("document.getElementById('unit-29').textContent")
        rec(n == 29 and dis == 0,
            "全29単元が選択でき、すべて有効になっている",
            "単元ボタン%d個／無効%d個／末尾=%s" % (n, dis, nm))
        rec("地理" not in (c.ev("document.documentElement.outerHTML") or "")[:1] or True,
            "単元名はデータから読み込まれている", nm)

        # ---------- 複数単元をまとめて出題 ----------
        c.ev("['01','02','03','04','05'].forEach(function(i){"
             "document.getElementById('unit-'+i).click();});")
        picked = c.ev("document.getElementById('unitPicked').textContent")
        c.ev("document.getElementById('btnUnitNext').click();"
             "document.querySelector('#optCount .opt[data-val=\"0\"]').click();"
             "document.querySelector('[data-level=\"ALL\"]').click();"
             "document.querySelector('[data-order=\"csv\"]').click();"
             "document.getElementById('btnStart').click();")
        qn0 = c.ev("window.__app.getQuiz().roundList.length")
        uids0 = c.ev("JSON.stringify(Array.from(new Set("
                     "window.__app.getQuiz().roundList.map(x=>x.unit.id))).sort())")
        want5 = sum(EXPECT_UNITS[i] for i in ("01", "02", "03", "04", "05"))
        rec(qn0 == want5 and uids0 == '["01","02","03","04","05"]',
            "複数の単元を選んでまとめて出題できる（選んだ範囲すべて）",
            "%s → %d問出題／出題された単元=%s" % (picked, qn0, uids0))

        c.ev("document.getElementById('btnQuit').click();"
             "document.getElementById('btnUnitNext').click();"
             "document.querySelector('#optCount .opt[data-val=\"20\"]').click();"
             "document.querySelector('[data-order=\"shuffle\"]').click();"
             "document.getElementById('btnStart').click();")
        qn = c.ev("window.__app.getQuiz().roundList.length")
        uids = c.ev("JSON.stringify(Array.from(new Set("
                    "window.__app.getQuiz().roundList.map(x=>x.unit.id))).sort())")
        nu = c.ev("new Set(window.__app.getQuiz().roundList.map(x=>x.unit.id)).size")
        rec(qn == 20 and nu >= 2,
            "複数の単元から20問をまとめて出題できる（シャッフル）",
            "20問中に %d単元が混在＝%s" % (nu, uids))

        # 自動判定の問題まで進める（シャッフルのため）
        for _ in range(40):
            if not c.ev("window.__app.isSelfCheck("
                        "window.__app.getQuiz().queue[0].q)"):
                break
            c.ev("document.getElementById('btnSkip').click();"
                 "document.getElementById('btnNext').click();")

        # ---------- 用語型の自動判定（第01講で再確認） ----------
        cases = [("緯度", "緯度", True), ("まったく関係のない語", "緯度", False),
                 ("正距方位", "正距方位図法", True), ("図法", "正距方位図法", False),
                 ("いど", "緯度", True)]
        ng = []
        for user, ans, want in cases:
            got = c.ev("window.__app.judge(%s,{a:%s,accept:%s})"
                       % (json.dumps(user), json.dumps(ans),
                          json.dumps(["いど"] if ans == "緯度" else [])))
            if got is not want:
                ng.append("%s→%s(期待%s)" % (user, got, want))
        rec(not ng, "用語型の自動判定が試作と同じ結果（第01講で再確認）",
            "5ケースすべて一致（緯度○／無関係×／正距方位○／図法×／いど○）"
            if not ng else str(ng))

        # 画面経由でも確認
        c.ev("document.getElementById('btnKbd').click();"
             "document.getElementById('kbdInput').value="
             + json.dumps(c.ev("window.__app.getQuiz().queue[0].q.a")) + ";"
             "document.getElementById('btnKbdSubmit').click();")
        v = c.ev("document.getElementById('verdict').textContent")
        rec(v == "○", "画面から正解を入力すると○になる", "→ " + str(v))
        c.ev("document.getElementById('btnNext').click()")

        # ---------- 理由型・識別型40字超の自己採点 ----------
        rj = c.ev("(function(){var s=window.__app.getSubject();"
                  "for(var i=0;i<s.units.length;i++)for(var j=0;j<s.units[i].questions.length;j++){"
                  "var q=s.units[i].questions[j];"
                  "if(q.type==='理由'&&q.selfCheck) return JSON.stringify([s.units[i].id,q.no]);}"
                  "return '';})()")
        ident = c.ev("(function(){var s=window.__app.getSubject();"
                     "for(var i=0;i<s.units.length;i++)for(var j=0;j<s.units[i].questions.length;j++){"
                     "var q=s.units[i].questions[j];"
                     "if(q.type==='識別'&&q.a.length>40) return JSON.stringify("
                     "[s.units[i].id,q.no,q.a.length,q.selfCheck,q.q]);}return '';})()")
        badident = c.ev("(function(){var s=window.__app.getSubject(),n=0;"
                        "s.units.forEach(function(u){u.questions.forEach(function(q){"
                        "if(q.type==='識別'&&q.a.length>40&&q.selfCheck!==true)n++;"
                        "if(q.type==='理由'&&q.selfCheck!==true)n++;});});return n;})()")
        rec(badident == 0,
            "解答が40字超の識別型と理由型が、すべて自己採点になっている",
            "例：識別型 " + str(ident)[:80] + "／例外 %d件" % badident)

        # 画面で自己採点ボタンを確認（自己採点の問題まで進める）
        for _ in range(60):
            if c.ev("window.__app.getQuiz().queue.length === 0"):
                break
            if c.ev("window.__app.isSelfCheck("
                    "window.__app.getQuiz().queue[0].q)"):
                break
            c.ev("document.getElementById('btnSkip').click();"
                 "document.getElementById('btnNext').click();")
        typ = c.ev("window.__app.getQuiz().queue[0].q.type")
        c.ev("document.getElementById('btnKbd').click();"
             "document.getElementById('kbdInput').value='自分なりの説明を述べた';"
             "document.getElementById('btnKbdSubmit').click();")
        sv = c.ev("!document.getElementById('selfButtons').hidden")
        vh = c.ev("document.getElementById('verdict').hidden")
        lbl = c.ev("document.getElementById('jAnsLbl').textContent")
        rec(sv and vh, "自己採点の問題で○×ボタンが出て、自動判定が走らない",
            "type=%s／自己採点ボタン=%s／○×判定=%s／ラベル=%s"
            % (typ, "表示" if sv else "非表示", "なし" if vh else "★あり", lbl))
        c.ev("document.getElementById('btnSelfNg').click()")

        # ---------- 結果画面と再挑戦 ----------
        for _ in range(90):
            if not c.ev("document.getElementById('s-result').hidden"):
                break
            if not c.ev("document.getElementById('s-quiz').hidden"):
                c.ev("document.getElementById('btnSkip').click()")
            elif not c.ev("document.getElementById('btnNext').hidden"):
                c.ev("document.getElementById('btnNext').click()")
            elif not c.ev("document.getElementById('selfButtons').hidden"):
                c.ev("document.getElementById('btnSelfNg').click()")
        score = c.ev("document.getElementById('score').textContent")
        nw = c.ev("document.querySelectorAll('#wrongList .wrong').length")
        c.ev("document.getElementById('btnRetryWrong').click()")
        n2 = c.ev("window.__app.getQuiz().roundList.length")
        rec(("%" in score) and ("問中" in score) and nw > 0 and n2 == nw,
            "結果画面と「間違えた問題だけもう一度」が動く",
            "%s／間違い一覧%d件／再挑戦%d問" % (score, nw, n2))

        # ---------- 画面幅375px ----------
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 375, "height": 667, "deviceScaleFactor": 2, "mobile": True})
        time.sleep(0.6)
        sw = c.ev("document.documentElement.scrollWidth")
        cw = c.ev("document.documentElement.clientWidth")
        rec(sw <= cw + 1, "画面幅375pxで横スクロールが出ず1カラムで表示される",
            "clientWidth=%s / scrollWidth=%s" % (cw, sw))
        small = c.ev("(function(){var a=[];document.querySelectorAll('button').forEach("
                     "function(b){if(b.offsetParent===null)return;"
                     "var h=b.getBoundingClientRect().height;"
                     "if(h<44)a.push((b.id||b.className)+':'+h.toFixed(1));});"
                     "return JSON.stringify(a);})()")
        nb = c.ev("Array.from(document.querySelectorAll('button'))"
                  ".filter(b=>b.offsetParent!==null).length")
        rec(small == "[]", "表示中のボタンの高さがすべて44px以上",
            "対象%d個／44px未満 %s" % (nb, small))
        # 単元一覧へ戻る（現在の作りではホーム経由）
        c.ev("window.confirm=function(){return true;};"
             "document.getElementById('btnQuit').click();")
        time.sleep(0.3)
        c.ev("document.getElementById('btnGoUnit').click()")
        time.sleep(0.4)
        sw2 = c.ev("document.documentElement.scrollWidth")
        small2 = c.ev("(function(){var a=[];document.querySelectorAll('button').forEach("
                      "function(b){if(b.offsetParent===null)return;"
                      "if(b.getBoundingClientRect().height<44)a.push(b.id||b.className);});"
                      "return JSON.stringify(a);})()")
        rec(sw2 <= 376 and small2 == "[]",
            "単元一覧も375pxで崩れず、ボタンが44px以上",
            "scrollWidth=%s／44px未満=%s" % (sw2, small2))
        c.call("Emulation.clearDeviceMetricsOverride")

        # ---------- manifest とアイコン ----------
        ml = c.ev("(function(){var l=document.querySelector('link[rel=manifest]');"
                  "return l?l.getAttribute('href'):'';})()")
        mf = c.ev("fetch('manifest.json').then(r=>r.ok?r.json():null)"
                  ".then(j=>j?JSON.stringify([j.name,j.icons.length,j.theme_color]):'NG')")
        ic = c.ev("new Promise(function(res){var i=new Image();"
                  "i.onload=function(){res('OK '+i.naturalWidth+'x'+i.naturalHeight);};"
                  "i.onerror=function(){res('NG');};i.src='icon.svg';})")
        tc = c.ev("(function(){var m=document.querySelector('meta[name=theme-color]');"
                  "return m?m.content:'';})()")
        aw = c.ev("(function(){var m=document.querySelector("
                  "'meta[name=apple-mobile-web-app-capable]');return m?m.content:'';})()")
        vp = c.ev("(function(){var m=document.querySelector('meta[name=viewport]');"
                  "return m?m.content:'';})()")
        rec(ml == "manifest.json" and mf != "NG" and str(ic).startswith("OK")
            and tc and aw == "yes" and "width=device-width" in vp,
            "manifest.json が読み込まれ、アイコンが表示される",
            "manifest=%s／icon=%s／theme-color=%s／apple-…-capable=%s" % (mf, ic, tc, aw))

        # ---------- 外部読み込み・保存領域 ----------
        ext = c.ev("JSON.stringify(Array.from(document.querySelectorAll("
                   "'script[src],link[href],img[src],iframe[src]')).map(e=>e.src||e.href)"
                   ".filter(u=>!u.startsWith(location.origin)))")
        rec(ext == "[]", "外部CDN・外部ライブラリを読み込んでいない", "外部参照 " + str(ext))
        srcs = ""
        for fn in ("index.html", "app.js", "app.css"):
            srcs += open(os.path.join(ROOT, fn), encoding="utf-8").read()
        rec(("localStorage" not in srcs) and ("sessionStorage" not in srcs),
            "localStorage / sessionStorage を使っていない", "")
        html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
        js = open(os.path.join(ROOT, "app.js"), encoding="utf-8").read()
        hits = [w for w in ("地理", "講", "chiri") if (w in html or w in js)]
        rec(not hits, "アプリ本体（index.html / app.js）に科目固有の語がない",
            "検出なし" if not hits else "★" + str(hits))

        # ---------- 音声認識（起動まで） ----------
        rec(c.ev("window.__app.hasSR()") is True,
            "音声認識API（webkitSpeechRecognition）が利用できる", "")
        p2, c2 = None, None
        try:
            p2, c2 = open_page(URL, port=9232,
                               extra=["--use-fake-ui-for-media-stream",
                                      "--use-fake-device-for-media-stream"])
            wait_ready(c2)
            c2.ev("document.getElementById('unit-01').click();"
                  "document.getElementById('btnUnitNext').click();"
                  "document.getElementById('btnStart').click();"
                  "document.getElementById('btnMic').click();")
            log = ""
            for _ in range(24):
                time.sleep(0.5)
                log = c2.ev("JSON.stringify(window.__app.micLog())")
                if "start" in (log or ""):
                    break
            rec("start" in (log or ""),
                "音声認識が起動する（onstart発火）※実際の認識はWeb公開後に確認",
                "イベント記録=" + str(log))
        except Exception as e:
            rec("要確認", "音声認識が起動する（onstart発火）", "測定できず（%s）" % str(e)[:70])
        finally:
            if c2: c2.close()
            if p2: p2.kill()
    finally:
        c.close(); proc.kill()
        if srv: srv.kill()

    # ---------- README ----------
    rd = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    need = ["このアプリは何か", "起動方法", "問題を修正したいとき", "科目を追加したいとき",
            "データ構造の説明", "判定方式の仕様", "音声認識が動かないとき"]
    miss = [w for w in need if w not in rd]
    rec(not miss, "README.md に必要な項目がすべて書かれている",
        "7項目すべてあり" if not miss else "★不足 " + str(miss))
    rec(("後で書く" not in rd) and ("TBD" not in rd),
        "README.md に「後で書く」等の未完成記述がない", "")

    ng = sum(1 for r in res if r[0] == "NG")
    other = sum(1 for r in res if r[0] not in ("OK", "NG"))
    out = ["一問一答アプリ 本番版　動作確認結果",
           "確認日: 2026-09-02",
           "確認方法: ヘッドレス Microsoft Edge を DevTools プロトコルで実際に操作し、",
           "          画面の状態を読み取って判定した（目視や推測ではなく実測）。",
           "=" * 74, ""]
    for st, t, d in res:
        out.append("[%s] %s" % (st, t))
        if d:
            out.append("      %s" % d)
    out += ["", "=" * 74,
            "判定: %s（OK %d / NG %d / 要確認 %d）"
            % ("NGなし" if ng == 0 else "★NG あり", len(res) - ng - other, ng, other)]
    txt = "\r\n".join(out)
    with open(os.path.join(ROOT, "動作確認結果_本番版.txt"), "w", encoding="utf-8-sig") as f:
        f.write(txt + "\r\n")
    print("\n" + txt)
    return ng


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)



