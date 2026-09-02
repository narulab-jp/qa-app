# -*- coding: utf-8 -*-
"""機能追加版（間違いノート・周回・学習ログ・印刷・PWA）の動作確認。
ヘッドレス Edge を DevTools プロトコルで実際に操作し、画面の状態を読んで判定する。"""
import base64
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
PORT = 8791
DBG = 9241
URL = "http://127.0.0.1:%d/index.html" % PORT
DL = os.path.join(os.environ["TEMP"], "qa_dl")
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
            m = json.loads(self.ws.recv(timeout=60))
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


def open_page(url, port=DBG, extra=None):
    ud = os.path.join(os.environ["TEMP"], "edge_qa2_%d" % port)
    shutil.rmtree(ud, ignore_errors=True)
    p = subprocess.Popen(
        [EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--remote-debugging-port=%d" % port, "--user-data-dir=" + ud,
         "--remote-allow-origins=*"] + (extra or []) + [url],
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
    c.call("Page.enable")
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


HELPER = """
window.__t = {
  start: function(unitIds, count, level, order, mode){
    window.__app.setNoteAsked(true);
    document.getElementById('btnToHome1') && 0;
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
    return window.__app.getQuiz().roundList.length;
  },
  cur: function(){
    var q = window.__app.getQuiz();
    return q && q.queue.length ? q.queue[0] : null;
  },
  answer: function(correct){
    var it = this.cur(); if(!it) return 'no-question';
    var self = window.__app.isSelfCheck(it.q);
    document.getElementById('btnKbd').click();
    document.getElementById('kbdInput').value = self ? '自分なりの説明'
                                : (correct ? it.q.a : 'まったく関係のない語');
    document.getElementById('btnKbdSubmit').click();
    if(self && !document.getElementById('selfButtons').hidden){
      document.getElementById(correct ? 'btnSelfOk' : 'btnSelfNg').click();
    }else{
      document.getElementById('btnNext').click();
    }
    return it.q.seq;
  },
  run: function(pattern, max){
    var out = [], i = 0;
    while(document.getElementById('s-result').hidden && i < (max||200)){
      var c = pattern[i] === undefined ? pattern[pattern.length-1] : pattern[i];
      var r = this.answer(!!c);
      if(r === 'no-question') break;
      out.push(r); i++;
    }
    return out;
  }
};
"""


def main():
    os.makedirs(DL, exist_ok=True)
    for f in os.listdir(DL):
        try:
            os.remove(os.path.join(DL, f))
        except Exception:
            pass

    srv = None
    if free(PORT):
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT),
                                "--bind", "127.0.0.1"], cwd=ROOT,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    proc, c = open_page(URL)
    try:
        wait_ready(c)
        c.call("Browser.setDownloadBehavior",
               {"behavior": "allow", "downloadPath": DL, "eventsEnabled": True})
        c.ev(HELPER)

        # ---------- 1. ノートが空のとき ----------
        rec(c.ev("document.getElementById('btnNoteQuiz').disabled") is True
            and "空" in c.ev("document.getElementById('noteCount').textContent"),
            "間違いノートが空の状態で、出題ボタンが押せない",
            c.ev("document.getElementById('noteCount').textContent"))

        # ---------- 2. 5問中3問間違え → 3件追加 ----------
        n = c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        seqs = c.ev("JSON.stringify(window.__t.run([true,true,false,false,false],10))")
        cnt = c.ev("window.__app.getNote().entries.length")
        rec(n == 5 and cnt == 3, "5問やって3問間違えたとき、ノートに3件追加される",
            "出題%d問 → ノート%d件（解答した通し番号=%s）" % (n, cnt, seqs))

        # ---------- 3. もう一度間違えて wrongCount が 2 ----------
        c.ev("document.getElementById('btnToHome2').click()")
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        c.ev("window.__t.run([true,true,false,false,false],10)")
        wc = c.ev("JSON.stringify(window.__app.getNote().entries"
                  ".map(function(e){return [e.seq,e.wrongCount,e.correctStreak];}))")
        allw2 = c.ev("window.__app.getNote().entries"
                     ".every(function(e){return e.wrongCount===2;})")
        rec(allw2 is True, "同じ問題をもう一度間違えたとき、wrongCount が 2 になる",
            "[seq, wrongCount, correctStreak] = " + str(wc))

        # ---------- 4. 1回正解では卒業せず、2回連続で卒業 ----------
        c.ev("document.getElementById('btnToHome2').click()")
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        c.ev("window.__t.run([true,true,true,true,true],10)")
        after1 = c.ev("window.__app.getNote().entries.length")
        st1 = c.ev("JSON.stringify(window.__app.getNote().entries"
                   ".map(function(e){return e.correctStreak;}))")
        c.ev("document.getElementById('btnToHome2').click()")
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        c.ev("window.__t.run([true,true,true,true,true],10)")
        after2 = c.ev("window.__app.getNote().entries.length")
        rec(after1 == 3 and after2 == 0,
            "1回正解しても卒業せず、2回連続正解で卒業する",
            "1回目の正解後=%d件（連続正解%s）／2回目の正解後=%d件" % (after1, st1, after2))

        # ---------- 5. よく間違える順 ----------
        c.ev("document.getElementById('btnToHome2').click()")
        # seq3 を3回、seq4 を1回間違える状態を作る
        for pat in ("[true,true,false,false,false]", "[true,true,false,false,true]",
                    "[true,true,false,true,true]"):
            c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
            c.ev("window.__t.run(%s,10)" % pat)
            c.ev("document.getElementById('btnToHome2').click()")
        order = c.ev("JSON.stringify(window.__app.noteItems('wrong')"
                     ".map(function(x){return [x.entry.seq,x.entry.wrongCount];}))")
        desc = c.ev("(function(){var a=window.__app.noteItems('wrong');"
                    "for(var i=1;i<a.length;i++)"
                    "if(a[i-1].entry.wrongCount<a[i].entry.wrongCount) return false;"
                    "return true;})()")
        rec(desc is True and "[" in order,
            "「よく間違える順」が wrongCount の降順になっている",
            "[seq, wrongCount] = " + str(order))

        # ---------- 11/12/13. 書き出し・読み込み・照合 ----------
        before = c.ev("JSON.stringify(window.__app.exportNote().entries.length)")
        c.ev("document.getElementById('btnNoteSave').click()")
        path, waited = None, 0
        while waited < 15 and not path:
            time.sleep(0.5); waited += 0.5
            for f in os.listdir(DL):
                if f.endswith("_note.json"):
                    path = os.path.join(DL, f)
        rec(bool(path), "ノートをJSONで書き出せる",
            "保存されたファイル=%s（%s件）" % (os.path.basename(path) if path else "なし", before))
        txt = open(path, encoding="utf-8").read() if path else "{}"
        d = json.loads(txt)
        rec(path is not None and d.get("entries") is not None
            and len(d["entries"]) == int(before),
            "書き出したJSONの中身が正しい",
            "entries=%d件／settings=%s" % (len(d.get("entries", [])), d.get("settings")))

        c.ev("window.__app.getNote().entries = []")   # いったん空にする
        r = c.ev("JSON.stringify(window.__app.importNoteText(%s))" % json.dumps(txt))
        after = c.ev("window.__app.getNote().entries.length")
        rec(after == int(before), "書き出したJSONを読み込んで状態が復元される",
            "読み込み結果=%s／entries=%d件" % (r, after))

        bad = json.loads(txt)
        bad["entries"] = bad["entries"] + [{"seq": 999999, "unitId": "99", "no": 1,
                                            "wrongCount": 1, "correctStreak": 0,
                                            "firstWrong": None, "lastWrong": None,
                                            "lastCorrect": None}]
        r2 = c.ev("JSON.stringify(window.__app.importNoteText(%s))"
                  % json.dumps(json.dumps(bad, ensure_ascii=False)))
        msg = c.ev("document.getElementById('noteLoadMsg').textContent")
        rec(json.loads(r2)["ignored"] == 1,
            "存在しない seq を含むJSONを読み込んでも壊れず、件数が表示される",
            "結果=%s／画面表示=「%s」" % (r2, msg))

        # ---------- 14. 未保存の警告 ----------
        DISPATCH = ("(function(){var e=new Event('beforeunload',{cancelable:true});"
                    "window.dispatchEvent(e);return e.defaultPrevented;})()")
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        c.ev("window.__t.answer(false)")        # 解答してノートを更新＝未保存にする
        dirty_flag = c.ev("window.__app.isDirty()")
        dirty_evt = c.ev(DISPATCH)
        c.ev("document.getElementById('btnQuit').click();"
             "document.getElementById('btnNoteSave').click();")
        time.sleep(1.2)
        clean_flag = c.ev("window.__app.isDirty()")
        clean_evt = c.ev(DISPATCH)
        rec(dirty_flag is True and dirty_evt is True
            and clean_flag is False and clean_evt is False,
            "未保存で画面を離れようとしたとき警告が出る（保存後は出ない）",
            "解答直後: 未保存=%s・警告=%s ／ 保存後: 未保存=%s・警告=%s"
            % (dirty_flag, dirty_evt, clean_flag, clean_evt))

        # ---------- 6. 周回モード ----------
        c.ev("window.__app.getNote().entries = []")
        n = c.ev("window.__t.start(['01'],0,'ALL','csv','round')")
        c.ev("window.__t.run([false],40)")            # 27問すべて間違える
        still = c.ev("document.getElementById('s-result').hidden")
        remain = c.ev("window.__app.getQuiz().queue.length + "
                      "window.__app.getQuiz().wrongPass.length")
        bar = c.ev("document.getElementById('statusBar').textContent")
        rec(n == 27 and still is True and remain == 27,
            "周回モードで、全問正解するまで終わらない",
            "27問すべて誤答 → 結果画面に進まず残り%d問／表示=「%s」" % (remain, bar))

        # ---------- 7. 中断して保存 → 再開 ----------
        c.ev("document.getElementById('btnPause').click()")
        rpath, waited = None, 0
        while waited < 15 and not rpath:
            time.sleep(0.5); waited += 0.5
            for f in os.listdir(DL):
                if f.endswith("_resume.json"):
                    rpath = os.path.join(DL, f)
        rtxt = open(rpath, encoding="utf-8").read() if rpath else "{}"
        rr = c.ev("JSON.stringify(window.__app.importResumeText(%s))" % json.dumps(rtxt))
        rq = c.ev("document.getElementById('s-quiz').hidden")
        bar2 = c.ev("document.getElementById('statusBar').textContent")
        rec(bool(rpath) and rq is False and json.loads(rr)["remain"] == 27,
            "周回モードで「中断して保存」が動き、再開できる",
            "保存=%s／再開結果=%s／再開後の表示=「%s」"
            % (os.path.basename(rpath) if rpath else "なし", rr, bar2))

        # ---------- 8/9/10. 全問正解して完了 → 統計 ----------
        c.ev("window.__t.run([true],40)")
        done = c.ev("document.getElementById('s-result').hidden")
        s = json.loads(c.ev("JSON.stringify(window.__app.getSession())"))
        rec(done is False and s["completed"] is True,
            "周回モードで全問正解すると1周が完了する",
            "%s／解答回数54想定に対し初回対象=%d問" % (c.ev("document.getElementById('resultTitle').textContent"),
                                                s["totalAsked"]))
        rec(s["totalAsked"] == 27 and s["firstTryCorrect"] == 0 and s["firstTryRate"] == 0.0,
            "初回正答率が、再出題を含まずに計算されている",
            "totalAsked=%d（＝出題した実数）／firstTryCorrect=%d／firstTryRate=%s"
            % (s["totalAsked"], s["firstTryCorrect"], s["firstTryRate"]))
        stats = c.ev("document.getElementById('resultStats').textContent")
        rec(len(s["slowest"]) > 0 and "時間がかかった問題 上位5問" in stats,
            "1問ごとの所要時間が記録され、上位5問が結果画面に出る",
            "slowest=%d件／先頭=%s" % (len(s["slowest"]), s["slowest"][0] if s["slowest"] else ""))
        rec("出題タイプ別" in stats and "重要度別" in stats
            and set(s["byType"].keys()) and set(s["byLevel"].keys()),
            "出題タイプ別・重要度別の正答率が出る",
            "byType=%s／byLevel=%s" % (list(s["byType"].keys()), list(s["byLevel"].keys())))
        rec(c.ev("window.__app.getLogs().sessions.length") >= 1,
            "学習ログにセッションが記録される",
            "%d件" % c.ev("window.__app.getLogs().sessions.length"))

        # ---------- 20. 375px でノート画面・結果画面 ----------
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 375, "height": 667, "deviceScaleFactor": 2, "mobile": True})
        time.sleep(0.5)
        sw_r = c.ev("document.documentElement.scrollWidth")
        small_r = c.ev("(function(){var a=[];document.querySelectorAll('button').forEach("
                       "function(b){if(b.offsetParent===null)return;"
                       "if(b.getBoundingClientRect().height<44)a.push(b.id);});"
                       "return JSON.stringify(a);})()")
        c.ev("document.getElementById('btnToHome2').click();"
             "document.getElementById('btnNoteView').click();")
        time.sleep(0.4)
        sw_n = c.ev("document.documentElement.scrollWidth")
        small_n = c.ev("(function(){var a=[];document.querySelectorAll('button,label.btn')"
                       ".forEach(function(b){if(b.offsetParent===null)return;"
                       "if(b.getBoundingClientRect().height<44)a.push(b.id||b.className);});"
                       "return JSON.stringify(a);})()")
        rec(sw_r <= 376 and sw_n <= 376 and small_r == "[]" and small_n == "[]",
            "画面幅375pxで、間違いノート画面と結果画面が崩れない",
            "結果画面 scrollWidth=%s／ノート画面 scrollWidth=%s／44px未満=%s %s"
            % (sw_r, sw_n, small_r, small_n))
        c.call("Emulation.clearDeviceMetricsOverride")

        # ---------- 15/16/17. 印刷 ----------
        c.ev("document.getElementById('btnNotePrint').click()")
        time.sleep(0.4)
        shown = c.ev("!document.getElementById('s-print').hidden")
        title = c.ev("document.querySelector('#printArea .printhead h2').textContent")
        nitems = c.ev("document.querySelectorAll('#printArea .pq').length")
        pdf = c.call("Page.printToPDF", {"printBackground": False,
                                         "preferCSSPageSize": True})
        data = pdf.get("result", {}).get("data")
        pp = os.path.join(DL, "note_print.pdf")
        with open(pp, "wb") as f:
            f.write(base64.b64decode(data))
        import fitz
        doc = fitz.open(pp)
        w, h = doc[0].rect.width, doc[0].rect.height
        a4 = abs(w - 595.276) < 3 and abs(h - 841.89) < 3
        pages = [p.get_text() for p in doc]
        doc.close()
        full = "".join(pages)
        rec(shown and nitems > 0 and a4,
            "印刷ページが表示され、A4縦に収まる",
            "「%s」／%d問／PDF %0.f×%0.f pt（A4=595×842）" % (title, nitems, w, h))
        btns = ["この内容を印刷する", "戻る", "ホームに戻る", "ノートを保存",
                "印刷用の表示にする", "単元を選ぶ"]
        found = [b for b in btns if b in full]
        rec(not found, "印刷時にボタン類が消える",
            "PDF内に検出されたボタン文言=%s" % (found if found else "なし"))

        # 1問が改ページで分断されていないか（問題文と正解が同じページにあるか）
        items = json.loads(c.ev(
            "JSON.stringify(Array.from(document.querySelectorAll('#printArea .pq'))"
            ".map(function(e){return [e.querySelector('.q').textContent,"
            "e.querySelector('.a').textContent];}))"))
        split = []
        for q, a in items:
            qp = [i for i, t in enumerate(pages) if q.replace(" ", "") in t.replace(" ", "").replace("\n", "")]
            ap = [i for i, t in enumerate(pages) if a.replace(" ", "") in t.replace(" ", "").replace("\n", "")]
            if not qp or not ap or not set(qp) & set(ap):
                split.append(q[:20])
        rec(not split, "印刷時に1問が改ページで分断されない",
            "%d問すべて問題文と正解が同一ページ（PDF %d ページ）" % (len(items), len(pages))
            if not split else "★分断 %d件 %s" % (len(split), split[:3]))

        # ---------- 18. manifest とアイコン ----------
        mf = c.ev("fetch('manifest.json').then(function(r){return r.json();})"
                  ".then(function(j){return JSON.stringify("
                  "[j.name,j.icons.map(function(i){return i.src+' '+i.sizes+' '+(i.purpose||'any');})]);})")
        icons = []
        for nm in ("icon-192.png", "icon-512.png", "icon-maskable.png"):
            p = os.path.join(ROOT, "icons", nm)
            icons.append((nm, os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else 0))
        load = c.ev("Promise.all(['icons/icon-192.png','icons/icon-512.png',"
                    "'icons/icon-maskable.png'].map(function(u){return new Promise("
                    "function(res){var i=new Image();i.onload=function(){res(i.naturalWidth+'x'+i.naturalHeight);};"
                    "i.onerror=function(){res('NG');};i.src=u;});})).then(function(a){return a.join(' / ');})")
        rec(all(x[1] for x in icons) and "NG" not in str(load),
            "manifest.json が読み込まれ、アイコンが3種類とも存在する",
            "%s／実サイズ=%s" % (mf, load))

        # ---------- 21. 判定ロジックが変わっていない ----------
        cases = [("緯度", "緯度", ["いど"], True), ("まったく関係のない語", "緯度", [], False),
                 ("正距方位", "正距方位図法", [], True), ("図法", "正距方位図法", [], False),
                 ("いど", "緯度", ["いど"], True)]
        ng = []
        for user, ans, acc, want in cases:
            got = c.ev("window.__app.judge(%s,{a:%s,accept:%s})"
                       % (json.dumps(user), json.dumps(ans), json.dumps(acc)))
            if got is not want:
                ng.append("%s→%s" % (user, got))
        rec(not ng, "既存の判定ロジックが変わっていない（試作と同じ結果）",
            "5ケースすべて一致" if not ng else str(ng))

        # ---------- 設定 ----------
        c.ev("document.getElementById('btnToHome3').click();"
             "document.getElementById('btnSettings').click();")
        c.ev("document.querySelector('#optStreak .opt[data-val=\"3\"]').click()")
        c.ev("document.querySelector('[data-fs=\"large\"]').click()")
        st = c.ev("JSON.stringify(window.__app.getSettings())")
        big = c.ev("document.body.classList.contains('fs-large')")
        c.ev("document.querySelector('[data-fs=\"normal\"]').click()")
        rec(json.loads(st)["graduateStreak"] == 3 and big is True,
            "設定（卒業に必要な連続正解数・文字サイズ等）が画面から変更できる", st)
    finally:
        c.close(); proc.kill()

    # ---------- 19. Service Worker の登録に失敗しても動く ----------
    p2, c2 = open_page("about:blank", port=9242)
    try:
        c2.call("Network.enable")
        c2.call("Network.setBlockedURLs", {"urls": ["*/sw.js"]})
        c2.call("Page.navigate", {"url": URL})
        okr = wait_ready(c2)
        c2.ev(HELPER)
        n = c2.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        c2.ev("window.__t.answer(true)")
        v = c2.ev("document.getElementById('verdict').textContent")
        swreg = c2.ev("navigator.serviceWorker.getRegistrations()"
                      ".then(function(r){return r.length;})")
        rec(okr and n == 5 and v == "○",
            "Service Worker の登録に失敗しても、アプリが正常に動く",
            "sw.js を遮断した状態で起動 → 登録数%s／出題%d問／判定=%s" % (swreg, n, v))
    finally:
        c2.close(); p2.kill()
        if srv: srv.kill()

    ng = sum(1 for r in res if r[0] == "NG")
    other = sum(1 for r in res if r[0] not in ("OK", "NG"))
    out = ["一問一答アプリ 機能追加版　動作確認結果",
           "確認日: 2026-09-02",
           "確認方法: ヘッドレス Microsoft Edge を DevTools プロトコルで実際に操作し、",
           "          画面の状態・保存されたファイル・印刷PDFを読み取って判定した。",
           "=" * 74, ""]
    for st, t, d in res:
        out.append("[%s] %s" % (st, t))
        if d:
            out.append("      %s" % d)
    out += ["", "=" * 74,
            "判定: %s（OK %d / NG %d / 要確認 %d）"
            % ("NGなし" if ng == 0 else "★NG あり", len(res) - ng - other, ng, other),
            "",
            "※ 音声認識は指示A で確認済み（onstart まで動作、実際の認識はWeb公開後）。",
            "※ Service Worker の本来の動作（オフライン利用）は https 配信後に確認する。"]
    txt = "\r\n".join(out)
    with open(os.path.join(ROOT, "動作確認結果_機能追加版.txt"), "w", encoding="utf-8-sig") as f:
        f.write(txt + "\r\n")
    print("\n" + txt)
    return ng


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)

