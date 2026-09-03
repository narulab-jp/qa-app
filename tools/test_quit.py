# -*- coding: utf-8 -*-
"""出題の途中でやめられるかを確かめる。

  確かめること
    1. 出題の画面と答え合わせの画面の両方に「やめる」がある
    2. 押すと「ここまでの結果を見て終わりますか」と確認が出る
    3. 「いいえ」なら出題に戻る（進み具合が変わらない）
    4. 「はい」ならそこまでの結果画面が出る
    5. 結果画面からホームに戻れる
    6. 途中までの間違いノートの記録が残っている
    7. まだ1問も答えていないときは、結果を出さずにホームへ戻る
    8. 自己採点の問題（「次へ」が隠れる場面）でも「やめる」が押せる
"""
import json
import os
import socket
import subprocess
import sys
import time

import requests
from websockets.sync.client import connect

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT = 8791
DBG = 9247
# 引数にURLを渡すと、そのアドレス（公開サイトなど）を確かめる。
# 何も渡さなければ、手元のファイルを簡易サーバで出して確かめる。
LIVE = sys.argv[1] if len(sys.argv) > 1 else ""
URL = LIVE or ("http://127.0.0.1:%d/index.html" % PORT)
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


def free(port):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def open_page(url):
    import shutil
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    ud = os.path.join(os.environ["TEMP"], "edge_quit_test")
    shutil.rmtree(ud, ignore_errors=True)      # 古いキャッシュを持ちこまない
    p = subprocess.Popen([edge, "--headless=new", "--disable-gpu",
                          "--remote-debugging-port=%d" % DBG,
                          "--user-data-dir=" + ud, "--no-first-run", url],
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
    return p, c


def shown(c, sid):
    return c.ev("!document.getElementById('%s').hidden" % sid)


def visible(c, bid):
    return c.ev("(function(){var e=document.getElementById('%s');"
                "if(!e||e.hidden) return false;"
                "var r=e.getBoundingClientRect();"
                "return r.width>0 && r.height>0;})()" % bid)


def start(c, units=("29",), order="csv", count="0"):
    c.ev("document.getElementById('btnGoUnit').click()")
    c.ev("document.getElementById('btnUnitNone').click();"
         + "".join("document.getElementById('unit-%s').click();" % u
                   for u in units))
    c.ev("document.getElementById('btnUnitNext').click();"
         "document.querySelector('#optCount .opt[data-val=\"%s\"]').click();"
         "document.querySelector('[data-level=\"ALL\"]').click();"
         "document.querySelector('[data-order=\"%s\"]').click();"
         "document.getElementById('btnStart').click();" % (count, order))


def answer_one(c, correct):
    """自動判定の問題まで進めて、1問答える。"""
    for _ in range(60):
        if not c.ev("window.__app.isSelfCheck(window.__app.getQuiz().queue[0].q)"):
            break
        c.ev("document.getElementById('btnSkip').click();"
             "document.getElementById('btnNext').click();")
    a = c.ev("window.__app.getQuiz().queue[0].q.a")
    txt = a if correct else "まったく関係のない語"
    c.ev("document.getElementById('btnKbd').click();"
         "document.getElementById('kbdInput').value=" + json.dumps(txt) +
         ";document.getElementById('btnKbdSubmit').click();")
    return c.ev("document.getElementById('verdict').textContent")


def main():
    srv = None
    if not LIVE and free(PORT):
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT),
                                "--bind", "127.0.0.1"], cwd=ROOT,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    proc, c = open_page(URL)
    try:
        for _ in range(80):
            if c.ev("document.readyState==='complete' && !!window.__app "
                    "&& !!window.__app.getSubject()"):
                break
            time.sleep(0.5)
        c.ev("document.getElementById('newUserName').value='やめる確認';"
             "document.getElementById('btnAddUser').click();")
        c.ev("window.__app.setNoteAsked(true)")

        # ---------- 1. ボタンがあるか ----------
        start(c)
        vq = visible(c, "btnQuit")
        lq = c.ev("document.getElementById('btnQuit').textContent")
        rec(vq, "出題の画面に「やめる」がある", "「%s」" % (lq or "").strip())

        v1 = answer_one(c, True)
        vj = visible(c, "btnQuitJudge")
        lj = c.ev("document.getElementById('btnQuitJudge').textContent")
        rec(vj and v1 == "○", "答え合わせの画面に「やめる」がある",
            "「%s」／1問目の判定=%s" % ((lj or "").strip(), v1))
        c.ev("document.getElementById('btnNext').click()")
        v2 = answer_one(c, False)      # 2問目はわざと間違える
        wrong_seq = c.ev("window.__app.getQuiz().results.slice(-1)[0].item.q.seq")

        # ---------- 2〜3. 確認して「いいえ」 ----------
        done_before = c.ev("window.__app.getQuiz().done")
        c.ev("document.getElementById('btnQuitJudge').click()")
        time.sleep(0.3)
        msg = c.ev("document.getElementById('confirmMsg').textContent")
        openq = c.ev("!document.getElementById('confirmWrap').hidden")
        rec(openq and "ここまでの結果を見て終わりますか" in (msg or ""),
            "「やめる」を押すと確認が出る", "「%s」" % msg)
        c.ev("document.getElementById('confirmNo').click()")
        time.sleep(0.3)
        rec(shown(c, "s-judge")
            and c.ev("window.__app.getQuiz().done") == done_before,
            "「いいえ」なら出題に戻り、進み具合も変わらない",
            "答え合わせの画面のまま／解答済み%d問" % done_before)

        # ---------- 4. 「はい」で結果画面 ----------
        c.ev("document.getElementById('btnQuitJudge').click()")
        time.sleep(0.3)
        c.ev("document.getElementById('confirmYes').click()")
        time.sleep(0.5)
        title = c.ev("document.getElementById('resultTitle').textContent")
        sub = c.ev("document.getElementById('scoreSub').textContent")
        stats = c.ev("document.getElementById('resultStats').textContent")
        nr = c.ev("document.getElementById('btnNextRound').hidden")
        rec(shown(c, "s-result") and title == "途中までの結果" and nr,
            "「はい」でそこまでの結果画面が出る",
            "見出し=「%s」／%s" % (title, sub))
        rec("途中でやめました" in (stats or "") and "残りは" in (stats or ""),
            "結果画面に、途中でやめたことと残りの問数が出る",
            (stats or "").split("。")[0][:60] + "。")

        # ---------- 6. 間違いノートが残っているか ----------
        inNote = c.ev("JSON.stringify(window.__app.getNote().entries"
                      ".map(function(e){return e.seq;}))")
        rec(str(wrong_seq) in (inNote or ""),
            "途中までの間違いノートの記録が残っている",
            "通し%s が入っている（ノート%d件）／2問目の判定=%s"
            % (wrong_seq, len(json.loads(inNote)), v2))

        # ---------- 5. ホームに戻れる ----------
        c.ev("document.getElementById('btnToHome2').click()")
        time.sleep(0.3)
        rec(shown(c, "s-home"), "結果画面からホームに戻れる", "")

        # ---------- 7. 1問も答えていないとき ----------
        start(c)
        c.ev("document.getElementById('btnQuit').click()")
        time.sleep(0.3)
        msg2 = c.ev("document.getElementById('confirmMsg').textContent")
        c.ev("document.getElementById('confirmYes').click()")
        time.sleep(0.4)
        nlog = c.ev("window.__app.getLogs() ? "
                    "window.__app.getLogs().sessions.length : -1")
        rec(shown(c, "s-home") and "まだ1問も答えていません" in (msg2 or ""),
            "1問も答えていないときは結果を出さずにホームへ戻る",
            "「%s」／学習ログの件数=%s（空の記録は足していない）" % (msg2, nlog))

        # ---------- 8. 自己採点の場面でも押せる ----------
        start(c)
        okself = False
        for _ in range(60):
            if c.ev("window.__app.isSelfCheck("
                    "window.__app.getQuiz().queue[0].q)"):
                c.ev("document.getElementById('btnKbd').click();"
                     "document.getElementById('kbdInput').value='ためし';"
                     "document.getElementById('btnKbdSubmit').click();")
                if shown(c, "s-judge"):
                    okself = True
                break
            c.ev("document.getElementById('btnSkip').click();"
                 "document.getElementById('btnNext').click();")
        hidden_next = c.ev("document.getElementById('btnNext').hidden")
        selfb = c.ev("!document.getElementById('selfButtons').hidden")
        vj2 = visible(c, "btnQuitJudge")
        rec(okself and hidden_next and selfb and vj2,
            "自己採点の問題（「次へ」が隠れる場面）でも「やめる」が押せる",
            "次へ=隠れている／○×ボタン=出ている／やめる=押せる")
    finally:
        try:
            proc.kill()
        except Exception:
            pass
        if srv:
            srv.kill()

    ng = [r for r in res if r[0] == "NG"]
    print("=" * 64)
    print("判定: %s（OK %d / NG %d）"
          % ("NGなし" if not ng else "★NGあり", len(res) - len(ng), len(ng)))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
