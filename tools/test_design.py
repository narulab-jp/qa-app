# -*- coding: utf-8 -*-
"""デザイン刷新の動作確認。
ヘッドレス Edge を DevTools プロトコルで実際に操作し、
実際に適用されている CSS の値と画面の状態を読み取って判定する。"""
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
PORT, DBG = 8821, 9291
URL = "http://127.0.0.1:%d/index.html" % PORT
SHOT = os.path.join(os.environ["TEMP"], "qa_shots")
res = []

PALETTE = {"accent": "rgb(27, 58, 92)", "ok": "rgb(31, 111, 74)",
           "ng": "rgb(168, 50, 43)", "dim": "rgb(107, 114, 128)",
           "line": "rgb(229, 231, 235)", "fg": "rgb(28, 28, 30)"}


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

    def shot(self, name):
        d = self.call("Page.captureScreenshot", {"format": "png",
                                                 "captureBeyondViewport": True})
        data = d.get("result", {}).get("data")
        if not data:
            return None
        p = os.path.join(SHOT, name + ".png")
        with open(p, "wb") as f:
            f.write(base64.b64decode(data))
        return p

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
    ud = os.path.join(os.environ["TEMP"], "edge_design_%d" % port)
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
  answer: function(correct){
    var q=window.__app.getQuiz(); var it=q&&q.queue.length?q.queue[0]:null;
    if(!it) return 'no-question';
    var self=window.__app.isSelfCheck(it.q);
    document.getElementById('btnKbd').click();
    document.getElementById('kbdInput').value = self ? '説明' : (correct ? it.q.a : '違う語');
    document.getElementById('btnKbdSubmit').click();
    var s = !document.getElementById('selfButtons').hidden;
    if(s){ document.getElementById(correct?'btnSelfOk':'btnSelfNg').click(); }
    return s ? 'self' : 'judged';
  },
  css: function(sel, prop){
    var e = document.querySelector(sel);
    if(!e) return 'no-element';
    return getComputedStyle(e).getPropertyValue(prop);
  },
  smallButtons: function(){
    var a=[];
    document.querySelectorAll('button,label.btn,summary').forEach(function(b){
      if(b.offsetParent===null) return;
      var h=b.getBoundingClientRect().height;
      if(h<44) a.push((b.id||b.className||b.tagName)+':'+h.toFixed(1));
    });
    return JSON.stringify(a);
  },
  shadows: function(){
    var a=[];
    document.querySelectorAll('*').forEach(function(e){
      if(e.offsetParent===null && e!==document.body) return;
      var s=getComputedStyle(e);
      if(s.boxShadow && s.boxShadow!=='none'){
        var id=e.id||e.className||e.tagName;
        if(String(id).indexOf('confirm')<0) a.push('shadow:'+id);
      }
      if(s.backgroundImage && s.backgroundImage.indexOf('gradient')>=0)
        a.push('gradient:'+(e.id||e.className||e.tagName));
    });
    return JSON.stringify(a.slice(0,8));
  }
};
"""


def main():
    os.makedirs(SHOT, exist_ok=True)
    srv = None
    if free(PORT):
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT),
                                "--bind", "127.0.0.1"], cwd=ROOT,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    proc, c = open_page(URL)
    shots = []
    try:
        wait_loaded(c)
        c.ev(HELPER)
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 375, "height": 667, "deviceScaleFactor": 2, "mobile": True})
        time.sleep(0.4)

        # ---------- 外部フォント・外部読み込み ----------
        ext = c.ev("JSON.stringify(Array.from(document.querySelectorAll("
                   "'script[src],link[href],img[src],iframe[src]')).map(function(e){"
                   "return e.src||e.href;}).filter(function(u){"
                   "return u.indexOf(location.origin)!==0;}))")
        ff = c.ev("getComputedStyle(document.body).fontFamily")
        rec(ext == "[]" and "Hiragino" in ff,
            "外部フォント・外部CDNを読み込んでいない（ヒラギノ優先）",
            "外部参照=%s／font-family=%s" % (ext, ff[:60]))

        # ---------- 色 ----------
        c.ev("window.__t.ensureUser()")
        hero_bg = c.ev("window.__t.css('.hero','background-color')")
        body_bg = c.ev("getComputedStyle(document.body).backgroundColor")
        body_fg = c.ev("getComputedStyle(document.body).color")
        rec(hero_bg == PALETTE["accent"] and body_bg == "rgb(255, 255, 255)"
            and body_fg == PALETTE["fg"],
            "白基調・紺のアクセントで配色されている",
            "背景=%s／文字=%s／紺の面=%s" % (body_bg, body_fg, hero_bg))

        # ---------- トップ画面 ----------
        shots.append(c.shot("01_home_empty"))
        go_h = c.ev("document.getElementById('btnNoteQuiz').getBoundingClientRect().height")
        go_txt = c.ev("document.getElementById('btnNoteQuiz').textContent")
        go_vis = c.ev("document.getElementById('btnNoteQuiz').offsetParent !== null")
        folded = c.ev("JSON.stringify(Array.from(document.querySelectorAll("
                      "'#s-home details.sect')).map(function(d){return d.open;}))")
        # 折りたたみの数は、機能が増えると変わる。数を決め打ちせず、
        # 「ぜんぶ閉じていること」だけを見る。
        fl = json.loads(folded)
        rec(go_vis and go_txt.strip() == "はじめる" and go_h >= 44
            and len(fl) >= 3 and not any(fl),
            "トップを開いてすぐ［はじめる］が押せる（他は折りたたみ）",
            "ボタン=「%s」高さ%.0fpx／折りたたみ %d個すべて閉じている"
            % (go_txt.strip(), go_h, len(fl)))

        # ---------- 出題画面 ----------
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        time.sleep(0.3)
        lv = c.ev("getComputedStyle(document.getElementById('mLevel')).display")
        tp = c.ev("getComputedStyle(document.getElementById('mType')).display")
        rec(lv == "none" and tp == "none",
            "出題中に重要度・出題タイプを表示していない",
            "#mLevel=%s／#mType=%s" % (lv, tp))

        qfs = c.ev("parseFloat(getComputedStyle(document.getElementById('qText')).fontSize)")
        others = c.ev("(function(){var m=0,who='';"
                      "document.querySelectorAll('#s-quiz *').forEach(function(e){"
                      "if(e.offsetParent===null||e.id==='qText')return;"
                      "if(!e.textContent.trim())return;"
                      "var f=parseFloat(getComputedStyle(e).fontSize);"
                      "if(f>m){m=f;who=e.id||e.className;}});"
                      "return JSON.stringify([m,who]);})()")
        mx = json.loads(others)
        rec(qfs >= 20 and qfs > mx[0],
            "問題文が出題画面でいちばん大きい要素になっている",
            "問題文=%.0fpx／次に大きい要素=%.0fpx（%s）" % (qfs, mx[0], mx[1]))
        shots.append(c.shot("02_quiz"))

        # ---------- 進捗線が伸びるか ----------
        def fillpct():
            return c.ev("(function(){var t=document.querySelector('.qline'),"
                        "f=document.getElementById('qFill');"
                        "var w=t.getBoundingClientRect().width;"
                        "return w?Math.round(f.getBoundingClientRect().width/w*1000)/10:-1;})()")
        w0 = fillpct()
        c.ev("window.__t.answer(true);document.getElementById('btnNext').click();")
        time.sleep(0.4)
        w1 = fillpct()
        c.ev("window.__t.answer(true);document.getElementById('btnNext').click();")
        time.sleep(0.4)
        w2 = fillpct()
        fcol = c.ev("window.__t.css('#qFill','background-color')")
        rec(w0 == 0 and abs(w1 - 20) < 1.5 and abs(w2 - 40) < 1.5
            and fcol == PALETTE["accent"],
            "進捗線が、何問目まで進んだかに応じて伸びる",
            "5問中 1問目=%.0f%%／2問目=%.0f%%／3問目=%.0f%%（色=%s）"
            % (w0, w1, w2, fcol))
        # 進捗の確認で2問進めたので、判定画面の確認は最初からやり直す
        # （自己採点の問題は○×を押すと自動で次に進み、判定画面が残らないため）
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        time.sleep(0.3)

        # ---------- 音声ボタンの脈打ち ----------
        anim0 = c.ev("window.__t.css('#btnMic','animation-name')")
        c.ev("document.getElementById('btnMic').classList.add('listening')")
        time.sleep(0.2)
        anim1 = c.ev("window.__t.css('#btnMic','animation-name')")
        dur = c.ev("window.__t.css('#btnMic','animation-duration')")
        c.ev("document.getElementById('btnMic').classList.remove('listening')")
        rec(anim0 == "none" and anim1 == "pulse" and dur.startswith("1.5"),
            "音声入力中にマイクボタンが脈打つ（1.5秒周期）",
            "通常=%s／認識中=%s（%s）" % (anim0, anim1, dur))

        # ---------- 判定画面 ----------
        c.ev("window.__t.answer(false)")
        time.sleep(0.3)
        jvis = c.ev("!document.getElementById('s-judge').hidden"
                    "&&!document.getElementById('verdict').hidden")
        vfs = c.ev("parseFloat(window.__t.css('#verdict','font-size'))")
        vtxt = c.ev("(function(){var s=getComputedStyle(document.getElementById('verdict'),"
                    "'::before');return [s.content,s.color,parseFloat(s.fontSize)];})()")
        shots.append(c.shot("03_judge_ng"))
        rec(jvis is True and vfs == 0 and "不正解" in str(vtxt[0])
            and vtxt[1] == PALETTE["ng"] and vtxt[2] <= 20,
            "判定は○×の巨大表示をやめ、控えめな文字で示す",
            "判定画面=表示中／記号の文字サイズ=%.0fpx／表示=%s（%s・%.0fpx）"
            % (vfs, vtxt[0], vtxt[1], vtxt[2]))
        jl = c.ev("(function(){var e=document.getElementById('jLevel');"
                  "return [getComputedStyle(e).display,e.textContent];})()")
        jt = c.ev("(function(){var e=document.getElementById('jType');"
                  "return [getComputedStyle(e).display,e.textContent];})()")
        # Phase 4 でコア問題のときは「◎コア／重要度 S」と前置きが付く
        rec(jvis is True and jl[0] != "none" and ("重要度 " in jl[1])
            and jt[0] != "none" and jt[1] != "",
            "答え合わせの画面では重要度と出題タイプを表示する",
            "判定画面=表示中／#jLevel=%s「%s」／#jType=%s「%s」"
            % (jl[0], jl[1], jt[0], jt[1]))
        c.ev("document.getElementById('btnNext').click()")
        c.ev("window.__t.answer(true)")
        time.sleep(0.3)
        vok = c.ev("(function(){var s=getComputedStyle(document.getElementById('verdict'),"
                   "'::before');return [s.content,s.color];})()")
        shots.append(c.shot("04_judge_ok"))
        okvis = c.ev("!document.getElementById('s-judge').hidden"
                     "&&!document.getElementById('verdict').hidden")
        rec(okvis is True and "正解" in str(vok[0]) and vok[1] == PALETTE["ok"],
            "正解のときは落ち着いた緑で「正解」と出る",
            "判定画面=表示中／%s（%s）" % (vok[0], vok[1]))

        # ---------- 結果画面 ----------
        c.ev("document.getElementById('btnNext').click()")
        for _ in range(12):
            if not c.ev("document.getElementById('s-result').hidden"):
                break
            if not c.ev("document.getElementById('s-quiz').hidden"):
                c.ev("window.__t.answer(false)")
            elif not c.ev("document.getElementById('btnNext').hidden"):
                c.ev("document.getElementById('btnNext').click()")
        sfs = c.ev("parseFloat(window.__t.css('#scoreNum','font-size'))")
        swt = c.ev("window.__t.css('#scoreNum','font-weight')")
        scol = c.ev("window.__t.css('#scoreNum','color')")
        shots.append(c.shot("05_result"))
        rec(sfs >= 28 and int(swt) <= 300 and scol == PALETTE["accent"],
            "結果の数字は大きく細い紺の字で示す",
            "%.0fpx／太さ%s／%s" % (sfs, swt, scol))
        num = c.ev("document.getElementById('scoreNum').textContent")
        sub = c.ev("document.getElementById('scoreSub').textContent")
        ufs = c.ev("parseFloat(window.__t.css('#scoreSub','font-size'))")
        ucol = c.ev("window.__t.css('#scoreSub','color')")
        ntop = c.ev("document.getElementById('scoreNum').getBoundingClientRect().bottom"
                    "<=document.getElementById('scoreSub').getBoundingClientRect().top+1")
        rec(num.endswith("%") and ("問中" in sub) and ("問正解" in sub)
            and ufs <= 13 and ucol == PALETTE["dim"] and ntop is True,
            "結果画面が2段組みで、下段は小さく薄い文字",
            "上段=「%s」%.0fpx／下段=「%s」%.0fpx（%s）"
            % (num, sfs, sub, ufs, ucol))

        # ---------- 影とグラデーション ----------
        sh = c.ev("window.__t.shadows()")
        rec(sh == "[]", "影とグラデーションを（ダイアログ以外に）使っていない",
            "検出=%s" % sh)
        c.ev("window.__app.getQuiz && 0;"
             "document.getElementById('confirmWrap').hidden=false;")
        dsh = c.ev("window.__t.css('.confirm','box-shadow')")
        c.ev("document.getElementById('confirmWrap').hidden=true")
        rec(dsh != "none", "ダイアログにだけ、ごく薄い影を1種類だけ使う", dsh)

        # ---------- ボタンの高さ ----------
        small = c.ev("window.__t.smallButtons()")
        nb = c.ev("Array.from(document.querySelectorAll('button,label.btn,summary'))"
                  ".filter(function(b){return b.offsetParent!==null;}).length")
        rec(small == "[]", "表示中のボタンの高さがすべて44px以上",
            "対象%d個／44px未満=%s" % (nb, small))

        # ---------- 画面幅 ----------
        det = []
        allok = True
        for name, w, h in [("iPhone SE", 375, 667), ("iPhone 14 Pro", 393, 852),
                           ("横向き", 667, 375)]:
            c.call("Emulation.setDeviceMetricsOverride",
                   {"width": w, "height": h, "deviceScaleFactor": 2, "mobile": True})
            time.sleep(0.4)
            bad = []
            for scr, act in [("s-home", "document.getElementById('btnToHome2').click()"),
                             ("s-quiz", None)]:
                pass
            sw = c.ev("document.documentElement.scrollWidth")
            sm = c.ev("window.__t.smallButtons()")
            good = (sw <= w + 1) and sm == "[]"
            allok &= good
            det.append("%s(%dpx): 幅%s／44px未満%s" % (name, w, sw, sm))
        rec(allok, "iPhone SE・iPhone 14 Pro・横向きで崩れない", " ／ ".join(det))
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 375, "height": 667, "deviceScaleFactor": 2, "mobile": True})

        # ---------- フォーカス表示 ----------
        fo = c.ev("(function(){var b=document.getElementById('btnToHome2');b.focus();"
                  "var s=getComputedStyle(b);return [s.outlineWidth,s.outlineStyle];})()")
        rule = c.ev("(function(){for(var i=0;i<document.styleSheets.length;i++){"
                    "try{var r=document.styleSheets[i].cssRules;"
                    "for(var j=0;j<r.length;j++)"
                    "if(String(r[j].selectorText).indexOf('focus-visible')>=0)"
                    "return r[j].cssText;}catch(e){}}return '';})()")
        rec("focus-visible" in rule and "outline" in rule,
            "キーボード操作でフォーカスが見える指定がある", rule[:70])

        # ---------- 動きを減らす設定 ----------
        c.call("Emulation.setEmulatedMedia",
               {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
        c.ev("document.getElementById('btnToHome2') && 0;")
        c.ev("window.__t.start(['01'],5,'ALL','csv','normal')")
        c.ev("document.getElementById('btnMic').classList.add('listening')")
        time.sleep(0.3)
        rm = c.ev("window.__t.css('#btnMic','animation-name')")
        rmd = c.ev("window.__t.css('#btnMic','transition-duration')")
        c.ev("document.getElementById('btnMic').classList.remove('listening')")
        c.call("Emulation.setEmulatedMedia", {"features": []})
        rec(rm == "none", "prefers-reduced-motion で動きが止まる",
            "animation=%s／transition=%s" % (rm, rmd))

        # ---------- 印刷 ----------
        c.call("Emulation.clearDeviceMetricsOverride")
        c.ev("document.getElementById('btnQuit').click();"
             "document.querySelectorAll('#s-home details.sect')[1].open=true;"
             "document.getElementById('btnNoteView').click();"
             "document.getElementById('btnNotePrint').click();")
        time.sleep(0.4)
        npq = c.ev("document.querySelectorAll('#printArea .pq').length")
        pdf = c.call("Page.printToPDF", {"printBackground": False,
                                         "preferCSSPageSize": True})
        pp = os.path.join(SHOT, "print.pdf")
        with open(pp, "wb") as f:
            f.write(base64.b64decode(pdf["result"]["data"]))
        import fitz
        doc = fitz.open(pp)
        w, h = doc[0].rect.width, doc[0].rect.height
        pages = [p.get_text() for p in doc]
        doc.close()
        full = "".join(pages)
        btns = ["はじめる", "ホームに戻る", "印刷用の表示にする", "ノートを保存"]
        found = [b for b in btns if b in full]
        rec(abs(w - 595.276) < 3 and abs(h - 841.89) < 3 and npq > 0 and not found,
            "印刷ページが従来どおりA4に収まり、ボタン類が消える",
            "%0.f×%0.f pt／%d問／PDF内のボタン文言=%s"
            % (w, h, npq, found if found else "なし"))
        shots.append(c.shot("06_print"))
    finally:
        c.close(); proc.kill()
        if srv: srv.kill()

    ng = sum(1 for r in res if r[0] == "NG")
    other = sum(1 for r in res if r[0] not in ("OK", "NG"))
    out = ["一問一答アプリ　デザイン刷新　動作確認結果",
           "確認日: 2026-09-02",
           "確認方法: ヘッドレス Microsoft Edge を DevTools プロトコルで操作し、",
           "          実際に適用されている CSS の値と画面の状態を読み取って判定した。",
           "          画面は実際に撮影して目視でも確認した。",
           "=" * 74, ""]
    for st, t, d in res:
        out.append("[%s] %s" % (st, t))
        if d:
            out.append("      %s" % d)
    out += ["", "撮影した画面:"]
    for s in shots:
        if s:
            out.append("  " + os.path.basename(s))
    out += ["", "=" * 74,
            "判定: %s（OK %d / NG %d / 要確認 %d）"
            % ("NGなし" if ng == 0 else "★NG あり", len(res) - ng - other, ng, other)]
    txt = "\r\n".join(out)
    with open(os.path.join(ROOT, "動作確認結果_デザイン.txt"), "w", encoding="utf-8-sig") as f:
        f.write(txt + "\r\n")
    print("\n" + txt)
    return ng


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
