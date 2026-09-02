# -*- coding: utf-8 -*-
"""指示C（複数利用者対応）のためのパッチ。index.html / app.css / sw.js を書き換える。"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(p):
    t = io.open(os.path.join(ROOT, p), encoding="utf-8-sig").read()
    return t.replace("\r\n", "\n")


def write(p, t):
    io.open(os.path.join(ROOT, p), "w", encoding="utf-8", newline="\n").write(t)


def sub(t, old, new, tag):
    if old not in t:
        print("★未検出: %s" % tag)
        return t, False
    return t.replace(old, new, 1), True


ok = True

# ------------------------------------------------------------------ index.html
t = read("index.html")
t, r = sub(t, """<body>
<div id="app">

  <!-- ============ ホーム ============ -->""",
"""<body>
<div id="app">

  <!-- ============ 現在の利用者（常に表示） ============ -->
  <div id="userBar" hidden>
    <span class="ub-name" id="userBarName"></span>
    <button class="ub-btn" id="btnSwitchUser">切り替え</button>
  </div>

  <!-- ============ 利用者の選択・登録 ============ -->
  <section id="s-user" hidden>
    <h1>一問一答</h1>
    <p class="lead" id="userLead">誰が使いますか。</p>
    <div id="userList"></div>
    <div class="panel">
      <div class="lbl2">新しく追加する</div>
      <input id="newUserName" type="text" autocomplete="off"
             placeholder="名前を入れてください（例：たろう）">
      <button class="btn primary" id="btnAddUser">＋ 新しく追加</button>
      <p class="small" id="userMsg"></p>
    </div>
    <div class="panel">
      <div class="lbl2">保存したファイルから始める</div>
      <label class="btn center sub" for="userNotePick">保存したノートを読み込む</label>
      <input id="userNotePick" type="file" accept=".json,application/json" class="hidden-file">
      <p class="small">前に保存したノートを選ぶと、利用者の一覧もいっしょに戻ります。</p>
    </div>
  </section>

  <!-- ============ ホーム ============ -->""", "index.html: userBar と s-user")
ok &= r
write("index.html", t)

# -------------------------------------------------------------------- app.css
t = read("app.css")
t, r = sub(t, "[hidden]{display:none !important;}",
"""/* 現在の利用者を常に表示する帯 */
#userBar{
  position:sticky; top:0; z-index:20;
  display:flex; align-items:center; gap:8px;
  background:var(--accent); color:#fff;
  border-radius:0 0 10px 10px; padding:7px 12px; margin:0 0 10px;
  font-size:0.95em;
}
#userBar .ub-name{flex:1 1 auto;font-weight:bold;}
#userBar .ub-btn{
  flex:0 0 auto; min-height:34px; padding:4px 12px;
  border:1.5px solid #fff; border-radius:8px;
  background:transparent; color:#fff; font-size:0.9em; cursor:pointer;
}
#userBar .ub-btn:hover{background:rgba(255,255,255,.18);}

/* 利用者の一覧 */
.userrow{display:flex;gap:6px;margin:8px 0;}
.userrow .nmbtn{
  flex:1 1 auto; min-height:var(--tap); padding:10px 13px;
  border:2px solid #bbb; border-radius:10px; background:#fff;
  font-size:1em; text-align:left; cursor:pointer;
}
.userrow .nmbtn[aria-pressed="true"]{border-color:var(--accent);background:#e8effa;font-weight:bold;}
.userrow .icobtn{
  flex:0 0 auto; width:56px; min-height:var(--tap);
  border:2px solid #bbb; border-radius:10px; background:#fff;
  font-size:0.85em; cursor:pointer;
}
.userrow .icobtn:hover{background:#eef2f8;}
#newUserName, .renameInput{
  width:100%; min-height:var(--tap); font-size:1.05em; padding:10px 12px;
  border:2px solid var(--line); border-radius:10px; margin:0 0 8px;
}

[hidden]{display:none !important;}""", "app.css: userBar と利用者一覧")
ok &= r
t, r = sub(t, """  button, label.btn, .noprint, .row, fieldset, .statusbar, .meta,
  #s-home, #s-unit, #s-setup, #s-quiz, #s-judge, #s-result, #s-note,
  #s-settings, #confirmWrap { display:none !important; }""",
"""  button, label.btn, .noprint, .row, fieldset, .statusbar, .meta,
  #s-home, #s-unit, #s-setup, #s-quiz, #s-judge, #s-result, #s-note,
  #s-settings, #s-user, #userBar, #confirmWrap { display:none !important; }""",
        "app.css: 印刷時に利用者バーを隠す")
ok &= r
write("app.css", t)

# --------------------------------------------------------------------- sw.js
t = read("sw.js")
t, r = sub(t, 'var VERSION = "v2";', 'var VERSION = "v3";', "sw.js: バージョン")
ok &= r
write("sw.js", t)

print("パッチ適用: %s" % ("すべて成功" if ok else "★未検出あり"))
sys.exit(0 if ok else 1)
