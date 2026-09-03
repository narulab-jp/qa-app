# -*- coding: utf-8 -*-
"""本番形式編（冊D・冊E）の動作確認。
   ヘッドレス Edge を DevTools プロトコルで実際に操作して確かめる。
   目視や推測ではなく、画面の状態と計算された値を読み取って判定する。"""
import base64
import io
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
PORT, DBG = 8793, 9293
SHOT = os.path.join(os.environ["TEMP"], "qa_honban")
res = []
ACCENT = "rgb(27, 58, 92)"


def rec(ok, title, detail=""):
    st = ok if isinstance(ok, str) else ("OK" if ok else "NG")
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
            raise RuntimeError(json.dumps(r["exceptionDetails"], ensure_ascii=False)[:300])
        return r.get("result", {}).get("value")

    def css(self, sel, prop):
        return self.ev("(function(){var e=document.querySelector(%s);"
                       "return e?getComputedStyle(e).getPropertyValue(%s):'no-element';})()"
                       % (json.dumps(sel), json.dumps(prop)))

    def shot(self, name):
        if not os.path.isdir(SHOT):
            os.makedirs(SHOT)
        d = self.call("Page.captureScreenshot",
                      {"format": "png", "captureBeyondViewport": True})
        io.open(os.path.join(SHOT, name + ".png"), "wb").write(
            base64.b64decode(d["data"]))
        return name + ".png"


HELPER = """
window.__h = {
  user: function(){
    if(!window.__app.getCurrentUser()){
      document.getElementById('newUserName').value='テスト';
      document.getElementById('btnAddUser').click();
    }
    window.__app.setNoteAsked(true);
  },
  start: function(unitIds, count){
    this.user();
    document.getElementById('btnGoUnit').click();
    document.getElementById('btnUnitNone').click();
    unitIds.forEach(function(i){ document.getElementById('unit-'+i).click(); });
    document.getElementById('btnUnitNext').click();
    document.querySelector('[data-mode="normal"]').click();
    document.querySelector('[data-level="ALL"]').click();
    document.querySelector('[data-order="csv"]').click();
    var b = document.querySelector('#optCount .opt[data-val="'+count+'"]');
    if(b) b.click();
    document.getElementById('btnStart').click();
    return window.__app.getQuiz().roundList.length;
  },
  cur: function(){ var q=window.__app.getQuiz(); return q.queue[0].q; },
  pick: function(correct){
    var q = this.cur();
    var n = q.choices.length;
    var i = correct ? q.answer : ((q.answer + 1) % n);
    document.getElementById('ch-'+i).click();
    return i;
  },
  seekChoices: function(n){
    /* 毎回はじめから出題し直して、n択の問題までスキップで進む */
    this.start(['D'],0);
    for(var k=0;k<60;k++){
      var q=window.__app.getQuiz();
      if(!q || !q.queue.length) return false;
      if(q.queue[0].q.choices.length === n) return true;
      document.getElementById('btnSkip').click();
      document.getElementById('btnNext').click();
    }
    return false;
  },
  small: function(){
    var a=[];
    document.querySelectorAll('button,label.btn,summary').forEach(function(b){
      if(b.offsetParent===null) return;
      var h=b.getBoundingClientRect().height;
      if(h<44) a.push((b.id||b.className||b.tagName)+':'+h.toFixed(1));
    });
    return JSON.stringify(a);
  }
};
"""


def serve():
    return subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)],
                            cwd=ROOT, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def open_page(url, port=DBG):
    ud = os.path.join(os.environ["TEMP"], "edge_honban_%d" % port)
    shutil.rmtree(ud, ignore_errors=True)
    p = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--remote-debugging-port=%d" % port,
                          "--user-data-dir=" + ud, "--remote-allow-origins=*", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    for _ in range(80):
        time.sleep(0.5)
        try:
            for t in requests.get("http://127.0.0.1:%d/json/list" % port,
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


def main():
    srv = serve()
    time.sleep(1.2)
    p, c = open_page("http://127.0.0.1:%d/index.html" % PORT)
    shots = []
    try:
        if not wait_ready(c):
            rec(False, "アプリが起動する", "起動しなかった")
            return 1
        c.ev(HELPER)
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
        time.sleep(0.4)

        subs = c.ev("JSON.stringify(window.__app.getSubjects().map("
                    "function(s){return s.id;}))")
        c.ev("window.__h.user()")
        c.ev("window.__app.openSubjectById('chiri-honban')")
        time.sleep(1.0)
        sid = c.ev("window.__app.getSubject().subjectId")
        units = c.ev("JSON.stringify(window.__app.getSubject().units.map("
                     "function(u){return [u.id,u.name,u.questions.length];}))")
        rec(sid == "chiri-honban" and "D" in units and "E" in units,
            "アプリで本番形式編を科目として選べる",
            "科目=%s／%s" % (subs, units))

        # ---------- 冊D：組合せ形式が正しく出るか ----------
        c.ev("window.__h.start(['D'],0)")
        time.sleep(0.8)
        n = c.ev("window.__app.getQuiz().roundList.length")
        nch = c.ev("document.querySelectorAll('#choiceBox .ch').length")
        marks = c.ev("(function(){var a=[];"
                     "document.querySelectorAll('#choiceBox .ch .mk').forEach("
                     "function(m){a.push(m.textContent);});return a.join('');})()")
        txt0 = c.ev("document.querySelector('#choiceBox .ch').textContent")
        rec(n == 48 and nch >= 4 and "＝" in txt0.replace("=", "＝"),
            "冊Dの48問が出題され、選択肢が組合せの形になっている",
            "%d問／選択肢%d個／記号=%s／先頭の選択肢=「%s」"
            % (n, nch, marks, txt0.strip()[:34]))
        shots.append(c.shot("H1_kumiawase"))

        # 6択・8択・9択が画面に出せるか
        for want in (6, 8, 9):
            ok = c.ev("window.__h.seekChoices(%d)" % want)
            time.sleep(0.4)
            got = c.ev("document.querySelectorAll('#choiceBox .ch').length")
            mk = c.ev("(function(){var a=[];"
                      "document.querySelectorAll('#choiceBox .ch .mk').forEach("
                      "function(m){a.push(m.textContent);});return a.join('');})()")
            small = c.ev("window.__h.small()")
            rec(ok is True and got == want and small == "[]",
                "%d択の問題が画面にそのまま出せる（ボタンは44px以上）" % want,
                "選択肢%d個／記号=%s／44px未満=%s" % (got, mk, small))
            if want == 9:
                shots.append(c.shot("H2_9taku"))

        # ---------- 判定 ----------
        c.ev("window.__h.pick(false)")
        time.sleep(0.4)
        v = c.ev("(function(){var s=getComputedStyle("
                 "document.getElementById('verdict'),'::before');return s.content;})()")
        ju = c.ev("document.getElementById('jUser').textContent")
        ja = c.ev("document.getElementById('jAns').textContent")
        jg = c.ev("document.querySelectorAll('#jGrounds li').length")
        rec("不正解" in str(v) and jg >= 2 and ju != ja,
            "組合せ形式でも判定・解説・根拠が正しく出る",
            "判定=%s／あなたの解答=%s／正解=%s／根拠%d件"
            % (v, ju.strip()[:20], ja.strip()[:20], jg))
        c.ev("document.getElementById('btnNext').click()")
        time.sleep(0.3)
        c.ev("window.__h.pick(true)")
        time.sleep(0.4)
        v2 = c.ev("(function(){var s=getComputedStyle("
                  "document.getElementById('verdict'),'::before');return s.content;})()")
        rec("正解" in str(v2) and str(v2).find("不") < 0,
            "正しい組合せを選べば正解になる", "判定=%s" % v2)

        # ---------- 冊E：通し演習 ----------
        c.ev("window.confirm=function(){return true;};"
             "document.getElementById('btnQuit').click()")
        time.sleep(0.3)
        c.ev("window.__h.start(['E'],0)")
        time.sleep(0.8)
        ne = c.ev("window.__app.getQuiz().roundList.length")
        pt = c.ev("window.__app.getQuiz().roundList.reduce("
                  "function(a,x){return a+(x.q.haiten||0);},0)")
        fig = c.ev("(function(){var a=[];document.querySelectorAll('#figBox img')"
                   ".forEach(function(i){a.push(i.naturalWidth+'x'+i.naturalHeight);});"
                   "return JSON.stringify(a);})()")
        rec(ne == 30 and pt == 100 and "0x0" not in fig,
            "冊Eが30マーク・配点100点で出題され、資料も表示される",
            "%dマーク／配点合計%d点／資料=%s" % (ne, pt, fig))
        shots.append(c.shot("H3_moshi"))

        # ---------- 375px ----------
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 375, "height": 667, "deviceScaleFactor": 2, "mobile": True})
        time.sleep(0.5)
        sw = c.ev("document.documentElement.scrollWidth")
        cw = c.ev("document.documentElement.clientWidth")
        small = c.ev("window.__h.small()")
        qfs = c.ev("parseFloat(getComputedStyle("
                   "document.getElementById('qText')).fontSize)")
        chc = c.css("#choiceBox .ch", "border-top-color")
        rec(sw <= cw + 1 and small == "[]" and qfs >= 20 and chc == ACCENT,
            "375pxで崩れず、指示Dのデザイン規則を守っている",
            "clientWidth=%s/scrollWidth=%s／44px未満=%s／問題文%.0fpx／枠=%s"
            % (cw, sw, small, qfs, chc))
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})

        # ---------- 間違いノートが科目別か ----------
        c.ev("window.__h.pick(false)")
        time.sleep(0.4)
        nf = c.ev("window.__app.noteFileName()")
        ne2 = c.ev("window.__app.getNote().entries.length")
        rec(nf == "chiri-honban_note_テスト.json" and ne2 >= 1,
            "間違いノートが本番形式編だけのファイルに分かれている",
            "%s／登録%d問" % (nf, ne2))

        # ---------- 既存科目が壊れていないか ----------
        c.ev("document.getElementById('btnNext').click()")
        c.ev("document.getElementById('btnQuit').click()")
        time.sleep(0.3)
        c.ev("window.__app.openSubjectById('chiri')")
        time.sleep(1.5)
        n1 = c.ev("window.__app.getSubject().units.reduce("
                  "function(a,u){return a+u.questions.length;},0)")
        rec(n1 == 849, "一問一答が849問（重複3問を外し、知識の穴24問を足した数）になっている",
            "%d問／欠番は通し533・781・789" % n1)
        cases = [("緯度", "緯度", ["いど"], True),
                 ("まったく関係のない語", "緯度", [], False),
                 ("正距方位", "正距方位図法", [], True),
                 ("図法", "正距方位図法", [], False),
                 ("いど", "緯度", ["いど"], True)]
        ng = []
        for (u, a, acc, want) in cases:
            got = c.ev("window.__app.judge(%s,{a:%s,accept:%s})"
                       % (json.dumps(u), json.dumps(a), json.dumps(acc)))
            if got is not want:
                ng.append("%s→%s" % (u, got))
        rec(not ng, "一問一答の判定ロジックが変わっていない（5ケース確認）",
            "5ケースすべて一致" if not ng else str(ng))
        c.ev("window.__app.openSubjectById('chiri-zuhyo')")
        time.sleep(1.2)
        n2 = c.ev("window.__app.getSubject().units.reduce("
                  "function(a,u){return a+u.questions.length;},0)")
        rec(n2 == 159, "図表編159問が従来どおり読める", "%d問" % n2)

        # ---------- Service Worker ----------
        sw_js = io.open(os.path.join(ROOT, "sw.js"), encoding="utf-8").read()
        ver = sw_js.split('VERSION = "')[1].split('"')[0]
        rec(ver.startswith("v") and ver[1:].isdigit() and int(ver[1:]) >= 9,
        "Service Worker のキャッシュ版数を上げてある",
            "バージョン=%s" % ver)
    finally:
        try:
            c.call("Emulation.clearDeviceMetricsOverride")
            p.kill()
        except Exception:
            pass
        srv.kill()

    ng = [r for r in res if r[0] == "NG"]
    out = os.path.join(ROOT, "動作確認結果_本番形式編.txt")
    L = ["一問一答アプリ　本番形式編（冊D 組合せ形式48問／冊E 通し演習30マーク）",
         "　　　　　　　　動作確認結果", "",
         "確認日: " + time.strftime("%Y-%m-%d"),
         "確認方法: ヘッドレス Microsoft Edge を DevTools プロトコルで操作し、",
         "          画面の状態と計算された値を読み取って判定した。",
         "=" * 74, ""]
    for (st, t, d) in res:
        L.append("[%s] %s" % (st, t))
        if d:
            L.append("      " + d)
        L.append("")
    L.append("撮影した画面:")
    for s in shots:
        L.append("  " + s)
    L.append("")
    L.append("=" * 74)
    L.append("判定: %s（OK %d / NG %d）"
             % ("NGなし" if not ng else "★NG あり",
                len([r for r in res if r[0] == "OK"]), len(ng)))
    io.open(out, "w", encoding="utf-8", newline="\r\n").write("\n".join(L) + "\n")
    print("-" * 70)
    print(L[-1])
    return 1 if ng else 0


sys.exit(main())
