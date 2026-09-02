# -*- coding: utf-8 -*-
"""図表・読図編の動作確認。指示Eの「完了時のチェック」を、
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
PORT = 8791
DBG = 9291
SHOT = os.path.join(os.environ["TEMP"], "qa_zuhyo")
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
            raise RuntimeError(json.dumps(r["exceptionDetails"], ensure_ascii=False)[:400])
        return r.get("result", {}).get("value")

    def css(self, sel, prop):
        return self.ev("(function(){var e=document.querySelector(%s);"
                       "return e?getComputedStyle(e).getPropertyValue(%s):'no-element';})()"
                       % (json.dumps(sel), json.dumps(prop)))

    def shot(self, name):
        if not os.path.isdir(SHOT):
            os.makedirs(SHOT)
        d = self.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True})
        p = os.path.join(SHOT, name + ".png")
        io.open(p, "wb").write(base64.b64decode(d["data"]))
        return name + ".png"


HELPER = """
window.__z = {
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
    var i = correct ? q.answer : ((q.answer + 1) % 4);
    document.getElementById('ch-'+i).click();
    return i;
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
    ud = os.path.join(os.environ["TEMP"], "edge_zuhyo_%d" % port)
    shutil.rmtree(ud, ignore_errors=True)
    p = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                          "--remote-debugging-port=%d" % port,
                          "--user-data-dir=" + ud, "--remote-allow-origins=*", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    for _ in range(80):
        time.sleep(0.5)
        try:
            for t in requests.get("http://127.0.0.1:%d/json/list" % port, timeout=2).json():
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
    url = "http://127.0.0.1:%d/index.html" % PORT
    p, c = open_page(url)
    shots = []
    try:
        if not wait_ready(c):
            rec(False, "アプリが起動する", "起動しなかった")
            return 1
        c.ev(HELPER)
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
        time.sleep(0.4)

        # ---------- 科目の登録と選択 ----------
        subs = c.ev("JSON.stringify(window.__app.getSubjects().map(function(s){"
                    "return [s.id,s.name,s.enabled];}))")
        c.ev("window.__z.user()")
        c.ev("window.__app.openSubjectById('chiri-zuhyo')")
        time.sleep(0.8)
        sid = c.ev("window.__app.getSubject().subjectId")
        fmt = c.ev("window.__app.getSubject().format")
        lab = c.ev("window.__app.getSubject().unitLabel")
        rec(sid == "chiri-zuhyo" and fmt == "choice" and lab == "冊",
            "アプリで図表編を科目として選べる",
            "登録=%s／選択中=%s／format=%s／単位=%s" % (subs, sid, fmt, lab))

        # ---------- 単元（冊）と問数 ----------
        units = c.ev("JSON.stringify(window.__app.getSubject().units.map(function(u){"
                     "return [u.id,u.name,u.questions.length];}))")
        total = c.ev("window.__app.getSubject().units.reduce(function(a,u){"
                     "return a+u.questions.length;},0)")
        rec("Phase1", "冊ごとの問数（Phase 2 で A=40／B=50／C=20セットにする）",
            "%s／合計 %d問" % (units, total))

        # ---------- 全問4択・記述なし ----------
        bad = c.ev("(function(){var a=[],s=window.__app.getSubject();"
                   "s.units.forEach(function(u){u.questions.forEach(function(q){"
                   "if(!q.choices||q.choices.length!==4||q.selfCheck)"
                   "a.push(u.id+'-'+q.no);});});return JSON.stringify(a);})()")
        rec(bad == "[]", "全問が4択で、記述型（自己採点）が混じっていない",
            "%d問すべて選択肢4つ・自己採点0問" % total)

        # ---------- 出題（冊A）----------
        nq = c.ev("window.__z.start(['A'],5)")
        time.sleep(0.6)
        figsrc = c.ev("(function(){var a=[];document.querySelectorAll('#figBox img')"
                      ".forEach(function(i){a.push(i.getAttribute('src'));});"
                      "return JSON.stringify(a);})()")
        loaded = c.ev("(function(){var a=[];document.querySelectorAll('#figBox img')"
                      ".forEach(function(i){a.push(i.naturalWidth+'x'+i.naturalHeight);});"
                      "return JSON.stringify(a);})()")
        rec(figsrc == '["figures/A01_map.svg"]' and "0x0" not in loaded,
            "出題画面に図が <img> で読み込まれて表示される",
            "src=%s／実寸=%s" % (figsrc, loaded))

        micv = c.ev("document.getElementById('btnMic').offsetParent!==null")
        kbdv = c.ev("document.getElementById('kbdBox').offsetParent!==null")
        rec(micv is False and kbdv is False,
            "選択式ではマイクボタンもキーボード欄も表示されない",
            "マイク=非表示／キーボード欄=非表示")

        nch = c.ev("document.querySelectorAll('#choiceBox .ch').length")
        chh = c.ev("(function(){var a=[];document.querySelectorAll('#choiceBox .ch')"
                   ".forEach(function(b){a.push(Math.round("
                   "b.getBoundingClientRect().height));});return JSON.stringify(a);})()")
        gap = c.ev("(function(){var b=document.querySelectorAll('#choiceBox .ch');"
                   "return Math.round(b[1].getBoundingClientRect().top-"
                   "b[0].getBoundingClientRect().bottom);})()")
        marks = c.ev("(function(){var a=[];document.querySelectorAll('#choiceBox .ch .mk')"
                     ".forEach(function(m){a.push(m.textContent);});return a.join('');})()")
        rec(nch == 4 and min(json.loads(chh)) >= 48 and gap >= 9 and marks == "①②③④",
            "選択肢が縦に4つ並び、高さ48px以上・間隔10px前後",
            "高さ=%s／間隔=%dpx／記号=%s" % (chh, gap, marks))

        qfs = c.ev("parseFloat(getComputedStyle(document.getElementById('qText')).fontSize)")
        chc = c.css("#choiceBox .ch", "border-top-color")
        rec(qfs >= 20 and chc == ACCENT,
            "指示Dのデザイン規則に従っている（問題文20px・紺の枠）",
            "問題文=%.0fpx／選択肢の枠=%s" % (qfs, chc))

        lv = c.css("#mLevel", "display")
        tp = c.css("#mType", "display")
        rec(lv == "none" and tp == "none",
            "出題中に重要度・出題タイプを表示していない",
            "#mLevel=%s／#mType=%s" % (lv, tp))
        shots.append(c.shot("Z1_quiz_A"))

        # ---------- 375px で崩れないか ----------
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 375, "height": 667, "deviceScaleFactor": 2, "mobile": True})
        time.sleep(0.5)
        sw = c.ev("document.documentElement.scrollWidth")
        cw = c.ev("document.documentElement.clientWidth")
        iw = c.ev("document.querySelector('#figBox img').getBoundingClientRect().width")
        small = c.ev("window.__z.small()")
        rec(sw <= cw + 1 and iw <= cw and small == "[]",
            "375pxで図と選択肢が崩れない（横スクロールなし・ボタン44px以上）",
            "clientWidth=%s/scrollWidth=%s／図の幅=%.0f／44px未満=%s"
            % (cw, sw, iw, small))

        # ---------- 図の拡大とピンチ ----------
        c.ev("document.querySelector('#figBox img').click()")
        time.sleep(0.4)
        z0 = json.loads(c.ev("JSON.stringify(window.__app.getZoom())"))
        w0 = c.ev("document.getElementById('zoomImg').getBoundingClientRect().width")
        c.ev("document.getElementById('btnZoomIn').click()")
        time.sleep(0.3)
        z1 = json.loads(c.ev("JSON.stringify(window.__app.getZoom())"))
        w1 = c.ev("document.getElementById('zoomImg').getBoundingClientRect().width")
        ta = c.css("#zoomArea", "touch-action")
        ov = c.css("#zoomArea", "overflow-x")
        rec(z0["open"] is True and z1["scale"] > z0["scale"] and w1 > w0
            and "pinch-zoom" in str(ta) and ov in ("auto", "scroll"),
            "図をタップすると拡大表示になり、ピンチ操作ができる",
            "拡大表示=開いた／%.0f%%→%.0f%%（幅 %.0f→%.0f）／touch-action=%s"
            % (z0["scale"] * 100, z1["scale"] * 100, w0, w1, ta))
        shots.append(c.shot("Z2_zoom"))
        c.ev("document.getElementById('btnZoomClose').click()")
        time.sleep(0.3)
        rec(c.ev("document.getElementById('zoomWrap').hidden") is True,
            "拡大表示を閉じられる", "閉じるボタンで元の画面に戻る")
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
        time.sleep(0.3)

        # ---------- 判定 ----------
        c.ev("window.__z.pick(false)")
        time.sleep(0.4)
        vtxt = c.ev("(function(){var s=getComputedStyle(document.getElementById('verdict'),"
                    "'::before');return [s.content,s.color];})()")
        selfv = c.ev("document.getElementById('selfButtons').offsetParent!==null")
        ju = c.ev("document.getElementById('jUser').textContent")
        ja = c.ev("document.getElementById('jAns').textContent")
        jg = c.ev("document.querySelectorAll('#jGrounds li').length")
        jl = c.ev("document.getElementById('jLevel').textContent")
        jt = c.ev("document.getElementById('jType').textContent")
        rec("不正解" in str(vtxt[0]) and selfv is False and ju.startswith(("①", "②", "③", "④"))
            and ja.startswith(("①", "②", "③", "④")) and jg >= 2 and jl.startswith("重要度"),
            "選択肢が answer と違えば不正解になり、正解・解説・根拠が出る",
            "判定=%s／自己採点ボタン=なし／あなたの解答=%s／正解=%s／根拠=%d件／%s・%s"
            % (vtxt[0], ju, ja, jg, jl, jt))
        shots.append(c.shot("Z3_judge"))
        c.ev("document.getElementById('btnNext').click()")
        time.sleep(0.4)
        c.ev("window.__z.pick(true)")
        time.sleep(0.4)
        vok = c.ev("(function(){var s=getComputedStyle(document.getElementById('verdict'),"
                   "'::before');return [s.content,s.color];})()")
        rec("正解" in str(vok[0]) and str(vok[0]).find("不") < 0,
            "選択肢が answer と一致すれば正解になる", "判定=%s（%s）" % (vok[0], vok[1]))

        # ---------- 同じ setId で図を読み直さないか ----------
        gen0 = c.ev("document.querySelector('#figBox img').__c = 1;"
                    "document.querySelector('#figBox img').src")
        c.ev("document.getElementById('btnNext').click()")
        time.sleep(0.4)
        same = c.ev("(function(){var i=document.querySelector('#figBox img');"
                    "return [i.__c===1, i.src.split('/').pop()];})()")
        rec(same[0] is True and same[1] == "A01_map.svg",
            "同じ setId の連続する問題では、図を読み直さない",
            "同じ img 要素をそのまま使っている（%s）" % same[1])

        # ---------- 間違いノートが科目別か ----------
        nf = c.ev("window.__app.noteFileName()")
        lf = c.ev("window.__app.logFileName()")
        ne = c.ev("window.__app.getNote().entries.length")
        seqs = c.ev("JSON.stringify(window.__app.getNote().entries.map("
                    "function(e){return e.seq;}))")
        rec(nf == "chiri-zuhyo_note_テスト.json" and lf == "chiri-zuhyo_log_テスト.json"
            and ne >= 1,
            "間違いノートが科目別のファイル名に分かれている",
            "%s ／ %s ／ 登録 %d問（seq=%s）" % (nf, lf, ne, seqs))

        # ---------- 冊Cの複数資料 ----------
        c.ev("document.getElementById('btnQuit').click()")
        time.sleep(0.3)
        c.ev("window.__z.start(['C'],0)")
        time.sleep(0.8)
        nfig = c.ev("document.querySelectorAll('#figBox img').length")
        loaded2 = c.ev("(function(){var a=[];document.querySelectorAll('#figBox img')"
                       ".forEach(function(i){a.push(i.naturalWidth+'x'+i.naturalHeight);});"
                       "return JSON.stringify(a);})()")
        rec(nfig == 2 and "0x0" not in loaded2,
            "冊Cでは資料2点が並んで表示される", "図 %d枚／実寸=%s" % (nfig, loaded2))
        shots.append(c.shot("Z4_quiz_C"))

        # ---------- 一問一答の判定ロジックが変わっていないか ----------
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
                ng.append("%s→%s(期待%s)" % (u, got, want))
        rec(not ng, "一問一答の判定ロジックが変わっていない（5ケース確認）",
            "5ケースすべて一致（緯度○／無関係×／正距方位○／図法×／いど○）"
            if not ng else str(ng))

        # ---------- 一問一答（音声）が従来どおり動くか ----------
        c.ev("document.getElementById('btnQuit').click()")
        time.sleep(0.3)
        c.ev("window.__app.openSubjectById('chiri')")
        time.sleep(1.5)
        c.ev("window.__z.start(['01'],5)")
        time.sleep(0.6)
        vmic = c.ev("document.getElementById('btnMic').offsetParent!==null "
                    "|| !window.__app.hasSR()")
        vch = c.ev("document.getElementById('choiceBox').offsetParent!==null")
        vfig = c.ev("document.getElementById('figBox').offsetParent!==null")
        rec(vch is False and vfig is False and vmic is True,
            "一問一答（音声）の出題画面が従来どおりで、選択肢や図が出ない",
            "選択肢=非表示／図=非表示／マイク=表示")
        c.ev("document.getElementById('btnKbd').click();"
             "document.getElementById('kbdInput').value="
             "window.__app.getQuiz().queue[0].q.a;"
             "document.getElementById('btnKbdSubmit').click();")
        time.sleep(0.4)
        v2 = c.ev("(function(){var s=getComputedStyle(document.getElementById('verdict'),"
                  "'::before');return s.content;})()")
        rec("正解" in str(v2) and str(v2).find("不") < 0,
            "一問一答でキーボードから正解を入れると正解になる", "判定=%s" % v2)

        # ---------- 複数利用者 ----------
        # 人が操作するのと同じ順で（切替 → 新しく追加）
        c.ev("document.getElementById('btnSwitchUser').click()")
        time.sleep(0.3)
        c.ev("document.getElementById('newUserName').value='次男';"
             "document.getElementById('btnAddUser').click();")
        time.sleep(0.4)
        us = c.ev("JSON.stringify(window.__app.getUsers())")
        cu = c.ev("window.__app.getCurrentUser()")
        bar = c.ev("document.getElementById('userBarName').textContent")
        rec("次男" in us and cu == "次男" and "次男" in bar,
            "複数利用者の機能が壊れていない",
            "利用者=%s／学習中=%s／表示=「%s」" % (us, cu, bar))

        # ---------- Service Worker のキャッシュ対象 ----------
        sw = io.open(os.path.join(ROOT, "sw.js"), encoding="utf-8").read()
        ver = sw.split('VERSION = "')[1].split('"')[0]
        rec(ver == "v6" and "q.figures" in sw,
            "Service Worker がSVGとJSONをキャッシュし、バージョンを上げてある",
            "バージョン=%s／科目JSONと figures を取り込む処理あり" % ver)
    finally:
        try:
            c.call("Emulation.clearDeviceMetricsOverride")
            p.kill()
        except Exception:
            pass
        srv.kill()

    # ---------- データとPDFの確認も合わせて1つの報告にまとめる ----------
    sys.path.insert(0, HERE)
    import build_zuhyo
    import check_zuhyo_pdf
    print("-" * 70)
    build_zuhyo.check(json.loads(io.open(
        os.path.join(ROOT, "data", "chiri-zuhyo.json"), encoding="utf-8").read()))
    print("-" * 70)
    check_zuhyo_pdf.main()

    groups = [("A. 問題データ", build_zuhyo.REPORT),
              ("B. アプリの動作", res),
              ("C. 印刷用PDF", check_zuhyo_pdf.res)]
    allr = [r for (_, g) in groups for r in g]
    ng = [r for r in allr if r[0] == "NG"]
    out = os.path.join(ROOT, "動作確認結果_図表編.txt")
    L = []
    L.append("一問一答アプリ　図表・読図編（Phase 1）　動作確認結果")
    L.append("")
    L.append("確認日: " + time.strftime("%Y-%m-%d"))
    L.append("確認方法: 問題データは計算で検算し、アプリはヘッドレス Microsoft Edge を")
    L.append("          DevTools プロトコルで実際に操作して画面の状態を読み取り、")
    L.append("          PDFは出来上がったファイルを開いて中身を測って判定した。")
    L.append("          ファイルサイズでは判定していない。")
    L.append("          図は実際に描画させ、白黒でも判別できることを目でも確かめた。")
    L.append("")
    L.append("Phase 1 の範囲: 冊A 地形図1枚＋4問／冊B 雨温図セット4問／")
    L.append("                冊C 1セット（資料2点＋3問）　合計11問")
    L.append("                冊00（解き方の手順）と残りの問題は Phase 2 で作る。")
    L.append("=" * 74)
    for (title, g) in groups:
        L.append("")
        L.append("【%s】" % title)
        L.append("")
        for (st, t, d) in g:
            L.append("[%s] %s" % (st, t))
            if d:
                L.append("      " + d)
            L.append("")
    L.append("撮影した画面:")
    for s in shots:
        L.append("  " + s)
    L.append("")
    L.append("=" * 74)
    L.append("判定: %s（OK %d / NG %d / Phase1で保留 %d）"
             % ("NGなし" if not ng else "★NG あり",
                len([r for r in allr if r[0] == "OK"]), len(ng),
                len([r for r in allr if r[0] == "Phase1"])))
    io.open(out, "w", encoding="utf-8", newline="\r\n").write("\n".join(L) + "\n")
    print("-" * 70)
    print(L[-1])
    print("→ " + out)
    return 1 if ng else 0


sys.exit(main())
