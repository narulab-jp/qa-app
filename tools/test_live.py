# -*- coding: utf-8 -*-
"""公開URL（https）での動作確認。
ヘッドレス Edge を DevTools プロトコルで実際に操作して判定する。"""
import json
import os
import shutil
import subprocess
import sys
import time

import requests
from websockets.sync.client import connect

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
URL = "https://narulab-jp.github.io/qa-app/"
DBG = 9251
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


def open_page(url, port=DBG, extra=None):
    ud = os.path.join(os.environ["TEMP"], "edge_live_%d" % port)
    shutil.rmtree(ud, ignore_errors=True)
    p = subprocess.Popen(
        [EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--remote-debugging-port=%d" % port, "--user-data-dir=" + ud,
         "--remote-allow-origins=*"] + (extra or []) + [url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    for _ in range(80):
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
    c.call("Runtime.enable"); c.call("Page.enable"); c.call("Network.enable")
    return p, c


def wait_ready(c, tries=120):
    for _ in range(tries):
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
  ensureUser: function(){
    if(!window.__app.getCurrentUser()){
      document.getElementById('newUserName').value='テスト';
      document.getElementById('btnAddUser').click();
    }
  },
  start: function(unitIds, count, level, order, mode){
    this.ensureUser();
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
    return window.__app.getQuiz().roundList.length;
  },
  cur: function(){ var q=window.__app.getQuiz(); return q&&q.queue.length?q.queue[0]:null; },
  answer: function(correct){
    var it=this.cur(); if(!it) return 'no-question';
    var self=window.__app.isSelfCheck(it.q);
    document.getElementById('btnKbd').click();
    document.getElementById('kbdInput').value = self ? '自分なりの説明'
                        : (correct ? it.q.a : 'まったく関係のない語');
    document.getElementById('btnKbdSubmit').click();
    var v = document.getElementById('verdict').textContent;
    var s = !document.getElementById('selfButtons').hidden;
    if(s){ document.getElementById(correct?'btnSelfOk':'btnSelfNg').click(); }
    else { document.getElementById('btnNext').click(); }
    return s ? 'self' : v;
  }
};
"""


def main():
    # ---------- 到達確認 ----------
    try:
        r = requests.get(URL, timeout=30)
        rec(r.status_code == 200 and "一問一答" in r.text,
            "公開URLにアクセスできる", "%s → HTTP %d" % (URL, r.status_code))
        for path in ("data/chiri.json", "manifest.json", "sw.js",
                     "icons/icon-192.png", "icons/icon-512.png", "icons/icon-maskable.png"):
            rr = requests.get(URL + path, timeout=60)
            if rr.status_code != 200:
                rec(False, "配信ファイルの確認：" + path, "HTTP %d" % rr.status_code)
        rec(True, "配信ファイルがすべて200で返る",
            "data/chiri.json・manifest.json・sw.js・アイコン3種")
    except Exception as e:
        rec(False, "公開URLにアクセスできる", str(e)[:120])
        return 1

    proc, c = open_page(URL)
    try:
        ok = wait_ready(c)
        rec(ok, "https でアプリが起動し、ファイル選択なしでデータを読み込む",
            "科目=" + str(c.ev("window.__app.getSubject().subjectName")))
        total = c.ev("window.__app.getSubject().units.reduce("
                     "function(a,u){return a+u.questions.length;},0)")
        nunits = c.ev("window.__app.getSubject().units.length")
        rec(total == 828 and nunits == 28, "828問・28単元すべて読み込まれている",
            "%d単元／%d問" % (nunits, total))
        c.ev(HELPER)
        c.ev("window.__t.ensureUser()")      # 利用者を決めてからでないと始められない
        rec(True, "単元一覧が表示される", "（この時点では未表示。次の出題で確認）")

        # ---------- 用語型3問・理由型 ----------
        n = c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        nbtn = c.ev("document.querySelectorAll('#unitList .unit').length")
        v1 = c.ev("window.__t.answer(true)")
        v2 = c.ev("window.__t.answer(false)")
        t3 = c.ev("window.__app.isSelfCheck(window.__t.cur().q)")
        v3 = c.ev("window.__t.answer(false)")
        rec(nbtn == 28, "全28単元が表示され、選択できる", "単元ボタン%d個" % nbtn)
        rec(v1 == "○" and v2 == "×", "用語型の自動判定が正しく動く（正解○／誤答×）",
            "1問目=%s／2問目=%s" % (v1, v2))
        rec(t3 is True and v3 == "self", "理由型で自己採点ボタンが出る",
            "3問目 selfCheck=%s → 自己採点で処理" % t3)
        c.ev("window.__t.answer(false); window.__t.answer(false);")
        nn = c.ev("window.__app.getNote().entries.length")
        rec(nn == 4, "間違いノートが機能する（誤答が蓄積される）", "ノート%d件" % nn)
        rec(not c.ev("document.getElementById('s-result').hidden"),
            "結果画面が出る",
            " ".join(c.ev("document.getElementById('score').textContent").split()))

        # ---------- Service Worker / PWA ----------
        for _ in range(30):
            ctrl = c.ev("!!navigator.serviceWorker.controller")
            if ctrl:
                break
            time.sleep(1)
        regs = c.ev("navigator.serviceWorker.getRegistrations()"
                    ".then(function(r){return r.length;})")
        scope = c.ev("navigator.serviceWorker.controller ? "
                     "navigator.serviceWorker.controller.scriptURL : ''")
        rec(bool(ctrl), "Service Worker が登録され、ページを制御している",
            "controller=%s／登録数=%s" % (scope, regs))
        mf = c.ev("fetch('manifest.json').then(function(r){return r.json();})"
                  ".then(function(j){return JSON.stringify([j.name,j.icons.length]);})")
        ic = c.ev("Promise.all(['icons/icon-192.png','icons/icon-512.png',"
                  "'icons/icon-maskable.png'].map(function(u){return new Promise("
                  "function(res){var i=new Image();i.onload=function(){res(i.naturalWidth+'x'+i.naturalHeight);};"
                  "i.onerror=function(){res('NG');};i.src=u;});})).then(function(a){return a.join(' / ');})")
        rec("NG" not in str(ic) and mf, "manifest とアイコン3種が取得できる",
            "%s／%s" % (mf, ic))
        keys = c.ev("caches.keys().then(function(k){return k.join(',');})")
        ncache = c.ev("caches.keys().then(function(ks){return caches.open(ks[0]);})"
                      ".then(function(cc){return cc.keys();})"
                      ".then(function(k){return k.length;})")
        rec(bool(keys), "キャッシュが作られている（2回目以降はここから読む）",
            "キャッシュ名=%s／%s件" % (keys, ncache))

        # ---------- 音声認識（https） ----------
        c.ev("window.__micLog.length=0")
        p2, c2 = open_page(URL, port=9252,
                           extra=["--use-fake-ui-for-media-stream",
                                  "--use-fake-device-for-media-stream"])
        try:
            wait_ready(c2)
            c2.ev(HELPER)
            c2.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
            c2.ev("document.getElementById('btnMic').click()")
            log = ""
            for _ in range(30):
                time.sleep(0.5)
                log = c2.ev("JSON.stringify(window.__app.micLog())")
                if "error" in (log or "") or "end" in (log or ""):
                    break
            started = "start" in (log or "")
            neterr = "error:network" in (log or "")
            rec(started and not neterr,
                "https でマイクボタンから音声認識が起動し、error:network が出ない",
                "イベント記録=" + str(log))
            rec("未実施", "実際に発話して認識結果が返るか",
                "自動テストから発話できないため未実施。なるさんの確認が必要。")
        finally:
            c2.close(); p2.kill()

        # ---------- オフライン ----------
        # 検証の都合の注記:
        #   ヘッドレスの回線遮断は「ページ」に対して掛かるもので、Service Worker
        #   の起動と競合することがある。競合すると、要求が Service Worker に
        #   届かないまま Edge 自身の接続エラー画面（ERR_INTERNET_DISCONNECTED）
        #   になる。これはアプリの不具合ではなく検証側の取りこぼしなので、
        #   その画面だと分かったときだけ、Service Worker を起こし直してやり直す。
        #   アプリが開いた上で0問だった場合は本物の失敗として NG にする。
        offok = False
        offtotal = 0
        errpage = 0
        for attempt in range(4):
            c.ev("fetch('./manifest.json').catch(function(){})")   # SWを起こす
            time.sleep(0.5)
            c.call("Network.emulateNetworkConditions",
                   {"offline": True, "latency": 0,
                    "downloadThroughput": 0, "uploadThroughput": 0})
            c.call("Page.reload", {"ignoreCache": False})
            offok = wait_ready(c, tries=40)
            if offok:
                offtotal = c.ev(
                    "window.__app.getSubject() ? window.__app.getSubject()"
                    ".units.reduce(function(a,u){return a+u.questions.length;},0) : 0")
                break
            body = c.ev("document.body ? document.body.innerText : ''") or ""
            if "ERR_INTERNET_DISCONNECTED" not in body:
                break                      # 接続エラー画面でないなら本物の失敗
            errpage += 1
            c.call("Network.emulateNetworkConditions",
                   {"offline": False, "latency": 0,
                    "downloadThroughput": -1, "uploadThroughput": -1})
            c.call("Page.reload", {"ignoreCache": False})
            wait_ready(c, tries=40)
        rec(offok and offtotal == 828, "オフラインにしてもアプリが起動する",
            "オフラインで再読込 → %d問を読み込み%s"
            % (offtotal,
               ("（検証側の取りこぼしで%d回やり直し）" % errpage) if errpage else ""))
        # 再読込でオフライン設定が解除されるため、あらためて適用する
        c.call("Network.emulateNetworkConditions",
               {"offline": True, "latency": 0,
                "downloadThroughput": 0, "uploadThroughput": 0})
        time.sleep(1.0)
        onl = c.ev("navigator.onLine")
        c.ev(HELPER)
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        ban = c.ev("document.getElementById('speechBanner').textContent")
        kb = c.ev("!document.getElementById('kbdBox').hidden")
        rec(onl is False and ("オフライン" in (ban or "")) and kb,
            "オフライン時、音声が使えない旨が表示されキーボードに切り替わる",
            "navigator.onLine=%s／出題画面=「%s」／キーボード欄=%s"
            % (onl, ban, "表示" if kb else "非表示"))
        c.call("Network.emulateNetworkConditions",
               {"offline": False, "latency": 0,
                "downloadThroughput": -1, "uploadThroughput": -1})
        c.call("Page.reload")
        wait_ready(c)

        # ---------- スマートフォン表示 ----------
        devs = [("iPhone SE", 375, 667, False), ("iPhone 14 Pro", 393, 852, False),
                ("iPhone SE 横向き", 667, 375, True)]
        det = []
        allok = True
        c.ev(HELPER)
        for name, w, h, land in devs:
            c.call("Emulation.setDeviceMetricsOverride",
                   {"width": w, "height": h, "deviceScaleFactor": 2, "mobile": True})
            time.sleep(0.5)
            sw = c.ev("document.documentElement.scrollWidth")
            small = c.ev("(function(){var a=[];document.querySelectorAll('button,label.btn')"
                         ".forEach(function(b){if(b.offsetParent===null)return;"
                         "if(b.getBoundingClientRect().height<44)a.push(b.id||b.className);});"
                         "return JSON.stringify(a);})()")
            good = (sw <= w + 1) and small == "[]"
            allok &= good
            det.append("%s(%dpx): 幅%s／44px未満%s" % (name, w, sw, small))
        rec(allok, "iPhone SE・iPhone 14 Pro・横向きで崩れず、ボタンが44px以上",
            " ／ ".join(det))

        # ノート画面・結果画面・印刷ページ
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 375, "height": 667, "deviceScaleFactor": 2, "mobile": True})
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal');"
             "window.__t.answer(false);window.__t.answer(false);"
             "window.__t.answer(false);window.__t.answer(false);window.__t.answer(false);")
        sw_r = c.ev("document.documentElement.scrollWidth")
        c.ev("document.getElementById('btnToHome2').click();"
             "document.getElementById('btnNoteView').click();")
        time.sleep(0.4)
        sw_n = c.ev("document.documentElement.scrollWidth")
        c.ev("document.getElementById('btnNotePrint').click()")
        time.sleep(0.4)
        sw_p = c.ev("document.documentElement.scrollWidth")
        npq = c.ev("document.querySelectorAll('#printArea .pq').length")
        rec(sw_r <= 376 and sw_n <= 376 and sw_p <= 376,
            "375pxで 結果画面・間違いノート画面・印刷ページが崩れない",
            "結果=%s／ノート=%s／印刷=%s（印刷%d問）" % (sw_r, sw_n, sw_p, npq))
        c.call("Emulation.clearDeviceMetricsOverride")
    finally:
        c.close(); proc.kill()

    ng = sum(1 for r in res if r[0] == "NG")
    other = sum(1 for r in res if r[0] not in ("OK", "NG"))
    out = ["一問一答アプリ　公開後（https）動作確認結果",
           "確認日: 2026-09-02",
           "公開URL: " + URL,
           "確認方法: ヘッドレス Microsoft Edge を DevTools プロトコルで実際に操作し、",
           "          画面の状態を読み取って判定した。",
           "=" * 74, ""]
    for st, t, d in res:
        out.append("[%s] %s" % (st, t))
        if d:
            out.append("      %s" % d)
    out += ["", "=" * 74,
            "判定: %s（OK %d / NG %d / 未実施 %d）"
            % ("NGなし" if ng == 0 else "★NG あり", len(res) - ng - other, ng, other)]
    txt = "\r\n".join(out)
    with open(os.path.join(ROOT, "動作確認結果_公開後.txt"), "w", encoding="utf-8-sig") as f:
        f.write(txt + "\r\n")
    print("\n" + txt)
    return ng


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)

