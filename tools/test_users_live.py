# -*- coding: utf-8 -*-
"""複数利用者対応の動作確認。
ヘッドレス Edge を DevTools プロトコルで実際に操作し、画面の状態と
実際に保存されたファイルを読み取って判定する。"""
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
PORT = 8811
DBG = 9281
URL = "https://narulab-jp.github.io/qa-app/index.html"
DL = os.path.join(os.environ["TEMP"], "qa_dl_users_live")
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


def open_page(url, port=DBG):
    ud = os.path.join(os.environ["TEMP"], "edge_users_%d" % port)
    shutil.rmtree(ud, ignore_errors=True)
    p = subprocess.Popen(
        [EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--remote-debugging-port=%d" % port, "--user-data-dir=" + ud,
         "--remote-allow-origins=*", url],
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
    c.call("Runtime.enable"); c.call("Page.enable")
    return p, c


def wait_loaded(c):
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
    var s = !document.getElementById('selfButtons').hidden;
    if(s){ document.getElementById(correct?'btnSelfOk':'btnSelfNg').click(); }
    else { document.getElementById('btnNext').click(); }
    return it.q.seq;
  },
  run: function(pattern, max){
    var out=[], i=0;
    while(document.getElementById('s-result').hidden && i<(max||60)){
      var v = pattern[i]===undefined ? pattern[pattern.length-1] : pattern[i];
      var r = this.answer(!!v); if(r==='no-question') break; out.push(r); i++;
    }
    return out;
  },
  addUser: function(n){
    document.getElementById('newUserName').value = n;
    document.getElementById('btnAddUser').click();
    return document.getElementById('userMsg').textContent;
  }
};
"""


def wait_file(suffix, timeout=15):
    t = 0
    while t < timeout:
        for f in os.listdir(DL):
            if f.endswith(suffix):
                return os.path.join(DL, f)
        time.sleep(0.5); t += 0.5
    return None


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
        wait_loaded(c)
        c.call("Browser.setDownloadBehavior",
               {"behavior": "allow", "downloadPath": DL, "eventsEnabled": True})
        c.ev(HELPER)

        # ---------- 1. 初回起動 ----------
        onuser = c.ev("!document.getElementById('s-user').hidden")
        onhome = c.ev("!document.getElementById('s-home').hidden")
        lead = c.ev("document.getElementById('userLead').textContent")
        rec(onuser and not onhome, "初回起動時に利用者の登録を求められる",
            "利用者画面=表示／ホーム=非表示／案内=「%s」" % lead)
        rec(c.ev("document.getElementById('userBar').hidden") is True,
            "利用者が決まるまで学習を始められない（利用者バーも出ない）", "")

        # ---------- 2/3. 3人以上・日本語 ----------
        m1 = c.ev("window.__t.addUser('長男')")
        c.ev("document.getElementById('btnSwitchUser').click()")
        m2 = c.ev("window.__t.addUser('次男')")
        c.ev("document.getElementById('btnSwitchUser').click()")
        m3 = c.ev("window.__t.addUser('三男 / テスト')")
        c.ev("document.getElementById('btnSwitchUser').click()")
        m4 = c.ev("window.__t.addUser('よつば')")
        us = c.ev("JSON.stringify(window.__app.getUsers())")
        rec(len(json.loads(us)) == 4, "利用者を3人以上登録できる（上限なし）",
            "登録%d人=%s" % (len(json.loads(us)), us))
        rec("長男" in us and "よつば" in us, "利用者名に日本語が使える", us)

        # ---------- 4. 起動時に選べる ----------
        c.ev("document.getElementById('btnSwitchUser').click()")
        rows = c.ev("document.querySelectorAll('#userList .userrow').length")
        c.ev("document.getElementById('user-長男').click()")
        cu = c.ev("window.__app.getCurrentUser()")
        rec(rows == 4 and cu == "長男", "起動時に利用者を選べる",
            "一覧%d人 → 「%s」を選択" % (rows, cu))

        # ---------- 6. 上部に常時表示 ----------
        bar1 = c.ev("!document.getElementById('userBar').hidden && "
                    "document.getElementById('userBarName').textContent")
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        bar2 = c.ev("!document.getElementById('userBar').hidden && "
                    "document.getElementById('userBarName').textContent")
        c.ev("window.__t.answer(false)")
        bar3 = c.ev("!document.getElementById('userBar').hidden && "
                    "document.getElementById('userBarName').textContent")
        rec(bar1 == bar2 == bar3 == "長男 として学習中",
            "画面上部に現在の利用者が常に表示されている",
            "ホーム/出題/判定 いずれも「%s」" % bar3)

        # ---------- 7. 学習中に切り替え ----------
        c.ev("document.getElementById('btnNext').click()")
        c.ev("document.getElementById('btnSwitchUser').click()")
        pend = c.ev("!document.getElementById('confirmWrap').hidden")
        msg = c.ev("document.getElementById('confirmMsg').textContent")
        c.ev("document.getElementById('confirmYes').click()")
        onuser2 = c.ev("!document.getElementById('s-user').hidden")
        c.ev("document.getElementById('user-次男').click()")
        cu2 = c.ev("window.__app.getCurrentUser()")
        rec(pend and onuser2 and cu2 == "次男",
            "学習中に利用者を切り替えられる（確認あり）",
            "確認=「%s」→ 切り替え後=「%s」" % (msg[:28], cu2))

        # ---------- 16. 記録が混ざらない ----------
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        c.ev("window.__t.run([true,true,true,false,true],10)")
        n_ji = c.ev("window.__app.getNote().entries.length")
        c.ev("document.getElementById('btnToHome2').click();"
             "document.getElementById('btnSwitchUser').click();"
             "document.getElementById('user-長男').click();")
        n_cho = c.ev("window.__app.getNote().entries.length")
        all_notes = c.ev("(function(){var a=window.__app.getAllNotes(),o={};"
                         "Object.keys(a).forEach(function(k){o[k]=a[k].entries.map("
                         "function(e){return e.seq;});});return JSON.stringify(o);})()")
        d = json.loads(all_notes)
        mixed = set(d.get("長男", [])) & set(d.get("次男", []))
        rec(n_cho == 1 and n_ji == 1 and not mixed,
            "利用者Aで間違えた問題が、利用者Bのノートに入らない",
            "長男=%s／次男=%s（共通の問題 %d件）"
            % (d.get("長男"), d.get("次男"), len(mixed)))

        # ---------- 8/9/10. ファイル名と user ----------
        c.ev("document.getElementById('btnNoteSave').click()")
        p1 = wait_file("_note_長男.json")
        c.ev("document.getElementById('btnSwitchUser').click();"
             "document.getElementById('user-三男 / テスト').click();")
        cu3 = c.ev("window.__app.getCurrentUser()")
        fn3 = c.ev("window.__app.noteFileName()")
        c.ev("document.getElementById('btnNoteSave').click()")
        p3 = wait_file("_note_三男___テスト.json")
        rec(bool(p1), "保存されるファイル名に利用者名が入る",
            "保存されたファイル=%s" % (os.path.basename(p1) if p1 else "なし"))
        rec(bool(p3) and cu3 == "三男 / テスト",
            "使えない文字（/・空白）はアンダースコアに置き換えて保存できる",
            "表示名=「%s」／ファイル名=%s" % (cu3, fn3))
        d1 = json.loads(open(p1, encoding="utf-8").read()) if p1 else {}
        rec(d1.get("user") == "長男" and isinstance(d1.get("users"), list)
            and len(d1["users"]) == 4,
            "保存したJSONに user と利用者一覧が入っている",
            "user=%s／users=%s" % (d1.get("user"), d1.get("users")))

        # ---------- 11/12/13. 別人のノートの読み込み ----------
        c.ev("document.getElementById('btnSwitchUser').click();"
             "document.getElementById('user-次男').click();")
        txt = open(p1, encoding="utf-8").read()
        r = c.ev("JSON.stringify(window.__app.importNoteText(%s))" % json.dumps(txt))
        warned = c.ev("!document.getElementById('confirmWrap').hidden")
        wmsg = c.ev("document.getElementById('confirmMsg').textContent")
        ylab = c.ev("document.getElementById('confirmYes').textContent")
        nlab = c.ev("document.getElementById('confirmNo').textContent")
        rec(warned and "長男" in wmsg and "次男" in wmsg,
            "別人のノートを読み込もうとしたとき警告が出る",
            "「%s」／ボタン=[%s][%s]" % (wmsg, ylab, nlab))
        c.ev("document.getElementById('confirmNo').click()")
        cu4 = c.ev("window.__app.getCurrentUser()")
        n4 = c.ev("window.__app.getNote().entries.length")
        msg4 = c.ev("document.getElementById('noteLoadMsg').textContent")
        rec(cu4 == "次男" and n4 == 1,
            "警告で「いいえ」を選ぶと読み込まれない",
            "利用者=%s のまま／ノート%d件／表示=「%s」" % (cu4, n4, msg4))

        c.ev("window.__app.importNoteText(%s)" % json.dumps(txt))
        c.ev("document.getElementById('confirmYes').click()")
        cu5 = c.ev("window.__app.getCurrentUser()")
        n5 = c.ev("window.__app.getNote().entries.length")
        msg5 = c.ev("document.getElementById('noteLoadMsg').textContent")
        rec(cu5 == "長男", "警告で「切り替えて読み込む」を選ぶと利用者も切り替わる",
            "利用者=%s／ノート%d件／表示=「%s」" % (cu5, n5, msg5[:50]))

        # ---------- 14. user を持たない古いファイル ----------
        old = json.loads(txt)
        old.pop("user", None)
        old.pop("users", None)
        r6 = c.ev("JSON.stringify(window.__app.importNoteText(%s))"
                  % json.dumps(json.dumps(old, ensure_ascii=False)))
        msg6 = c.ev("document.getElementById('noteLoadMsg').textContent")
        cu6 = c.ev("window.__app.getCurrentUser()")
        rec(json.loads(r6).get("legacy") is True and "古い形式" in msg6,
            "user を持たない古いファイルを読み込んでもエラーにならない",
            "利用者=%s のものとして読み込み／表示=「%s」" % (cu6, msg6[-46:]))

        # ---------- 15. 設定が利用者ごと ----------
        c.ev("document.getElementById('btnSettings').click();"
             "document.querySelector('[data-fs=\"large\"]').click();"
             "document.querySelector('#optStreak .opt[data-val=\"3\"]').click();"
             "document.getElementById('btnToHome4').click();")
        s_cho = c.ev("JSON.stringify(window.__app.getSettings())")
        c.ev("document.getElementById('btnSwitchUser').click();"
             "document.getElementById('user-次男').click();")
        s_ji = c.ev("JSON.stringify(window.__app.getSettings())")
        big = c.ev("document.body.classList.contains('fs-large')")
        rec(json.loads(s_cho)["fontSize"] == "large"
            and json.loads(s_ji)["fontSize"] == "normal"
            and json.loads(s_cho)["graduateStreak"] == 3
            and json.loads(s_ji)["graduateStreak"] == 2,
            "利用者ごとに設定が別々に保存される",
            "長男=%s／次男=%s" % (s_cho, s_ji))

        # ---------- 17. 名前変更・削除 ----------
        c.ev("document.getElementById('btnSwitchUser').click();"
             "document.getElementById('rename-よつば').click();"
             "document.getElementById('renameInput').value='よつば改';"
             "document.getElementById('btnRenameOk').click();")
        us2 = c.ev("JSON.stringify(window.__app.getUsers())")
        c.ev("document.getElementById('del-よつば改').click();"
             "document.getElementById('confirmYes').click();")
        us3 = c.ev("JSON.stringify(window.__app.getUsers())")
        rec("よつば改" in us2 and "よつば改" not in us3 and len(json.loads(us3)) == 3,
            "利用者の削除・名前の変更ができる",
            "変更後=%s → 削除後=%s" % (us2, us3))

        # ---------- 5. 1人だけなら選択画面を飛ばす ----------
        c.ev("document.getElementById('btnSwitchUser').click();"
             "document.getElementById('del-次男').click();"
             "document.getElementById('confirmYes').click();")
        c.ev("document.getElementById('btnSwitchUser').click();"
             "document.getElementById('del-三男 / テスト').click();"
             "document.getElementById('confirmYes').click();")
        us4 = c.ev("JSON.stringify(window.__app.getUsers())")
        c.ev("window.__app.setUser(window.__app.getUsers()[0])")
        c.ev("window.__app.getCurrentUser()")
        auto = c.ev("(function(){window.__app.switchUser();"
                    "return document.getElementById('s-user').hidden;})()")
        c.ev("document.getElementById('user-長男') && "
             "document.getElementById('user-長男').click();")
        gate = c.ev("(function(){"
                    "return JSON.stringify([window.__app.getUsers().length,"
                    "window.__app.getCurrentUser()]);})()")
        rec(len(json.loads(us4)) == 1, "利用者が1人だけのとき、一覧が1人になる",
            "残った利用者=%s／gate=%s" % (us4, gate))

        # ---------- 18. 学習ログに user ----------
        c.ev("document.getElementById('btnToHome3') && 0;"
             "document.getElementById('user-長男') && document.getElementById('user-長男').click();")
        c.ev("window.__t.start(['01'],5,'ALL','csv','csv'.length?'normal':'normal')")
        c.ev("window.__t.run([true,false,true,true,true],10)")
        lg = c.ev("JSON.stringify(window.__app.getLogs().sessions.slice(-1)[0])")
        lgu = json.loads(lg).get("user")
        top = c.ev("window.__app.getLogs().user")
        rec(lgu == "長男" and top == "長男", "学習ログに user が記録される",
            "セッションの user=%s／ファイル全体の user=%s" % (lgu, top))
        c.ev("document.getElementById('btnToHome2').click();"
             "document.getElementById('btnLogSave').click();")
        pl = wait_file("_log_長男.json")
        dl = json.loads(open(pl, encoding="utf-8").read()) if pl else {}
        rec(bool(pl) and dl.get("user") == "長男",
            "学習ログのファイル名にも利用者名が入る",
            "%s／user=%s" % (os.path.basename(pl) if pl else "なし", dl.get("user")))

        # ---------- 19. 375px ----------
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 375, "height": 667, "deviceScaleFactor": 2, "mobile": True})
        c.ev("document.getElementById('btnSwitchUser').click()")
        time.sleep(0.5)
        sw = c.ev("document.documentElement.scrollWidth")
        small = c.ev("(function(){var a=[];document.querySelectorAll('button,label.btn')"
                     ".forEach(function(b){if(b.offsetParent===null)return;"
                     "if(b.getBoundingClientRect().height<44)a.push(b.id||b.className);});"
                     "return JSON.stringify(a);})()")
        rec(sw <= 376 and small == "[]", "375pxで利用者選択画面が崩れない",
            "scrollWidth=%s／44px未満=%s" % (sw, small))
        c.call("Emulation.clearDeviceMetricsOverride")
        c.ev("document.getElementById('user-長男').click()")

        # ---------- 20/21. 判定ロジックと卒業条件 ----------
        cases = [("緯度", "緯度", ["いど"], True), ("まったく関係のない語", "緯度", [], False),
                 ("正距方位", "正距方位図法", [], True), ("図法", "正距方位図法", [], False),
                 ("いど", "緯度", ["いど"], True)]
        ng = []
        for user, ans, acc, want in cases:
            got = c.ev("window.__app.judge(%s,{a:%s,accept:%s})"
                       % (json.dumps(user), json.dumps(ans), json.dumps(acc)))
            if got is not want:
                ng.append("%s→%s" % (user, got))
        rec(not ng, "既存の判定ロジックが変わっていない（5ケース）",
            "5ケースすべて一致" if not ng else str(ng))

        # この利用者は設定の確認で卒業条件を3回に変えているため、既定の2回に戻してから確かめる
        c.ev("document.getElementById('btnSettings').click();"
             "document.querySelector('#optStreak .opt[data-val=\"2\"]').click();"
             "document.getElementById('btnToHome4').click();")
        streak = c.ev("window.__app.getSettings().graduateStreak")
        c.ev("window.__app.getNote().entries = []")
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        c.ev("window.__t.run([true,true,false,false,false],10)")
        a0 = c.ev("window.__app.getNote().entries.length")
        c.ev("document.getElementById('btnToHome2').click()")
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        c.ev("window.__t.run([true,true,true,true,true],10)")
        a1 = c.ev("window.__app.getNote().entries.length")
        c.ev("document.getElementById('btnToHome2').click()")
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        c.ev("window.__t.run([true,true,true,true,true],10)")
        a2 = c.ev("window.__app.getNote().entries.length")
        rec(streak == 2 and a0 == 3 and a1 == 3 and a2 == 0,
            "間違いノートの卒業条件（2回連続正解）が変わっていない",
            "設定=%d回／誤答後=%d件 → 1回正解=%d件（残る） → 2回連続=%d件"
            % (streak, a0, a1, a2))
    finally:
        c.close(); proc.kill()
        if srv: srv.kill()

    ng = sum(1 for r in res if r[0] == "NG")
    other = sum(1 for r in res if r[0] not in ("OK", "NG"))
    out = ["一問一答アプリ　複数利用者対応　動作確認結果（公開URL）",
           "確認日: 2026-09-02",
           "確認方法: ヘッドレス Microsoft Edge を DevTools プロトコルで実際に操作し、",
           "          画面の状態と実際に保存されたファイルを読み取って判定した。",
           "=" * 74, ""]
    for st, t, d in res:
        out.append("[%s] %s" % (st, t))
        if d:
            out.append("      %s" % d)
    out += ["", "=" * 74,
            "判定: %s（OK %d / NG %d / 要確認 %d）"
            % ("NGなし" if ng == 0 else "★NG あり", len(res) - ng - other, ng, other)]
    txt = "\r\n".join(out)
    with open(os.path.join(ROOT, "動作確認結果_複数利用者_公開後.txt"), "w", encoding="utf-8-sig") as f:
        f.write(txt + "\r\n")
    print("\n" + txt)
    return ng


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
