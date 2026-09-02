# -*- coding: utf-8 -*-
"""指示Cの変更（利用者の選択が必須・保存ファイル名に利用者名）に合わせて、
既存の動作確認スクリプトを現在の画面の流れに追随させる。"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ng = []


def patch(name, pairs):
    p = os.path.join(ROOT, "tools", name)
    t = io.open(p, encoding="utf-8-sig").read().replace("\r\n", "\n")
    for old, new, tag in pairs:
        if old not in t:
            ng.append("%s: %s" % (name, tag))
            continue
        t = t.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    print("処理: tools/%s" % name)


# ---------------------------------------------------------------- test_app.py
patch("test_app.py", [
    ("""        rec(wait_ready(c), "トップ画面が表示される",""",
     """        # 指示C以降は利用者を決めてから学習を始める
        c.ev("document.getElementById('newUserName').value='テスト';"
             "document.getElementById('btnAddUser').click();")
        c.ev("document.getElementById('btnGoUnit').click()")
        rec(wait_ready(c), "トップ画面が表示される",""",
     "利用者登録と単元一覧への遷移"),
    ("""        c.ev("document.getElementById('lec-01').click()")""",
     """        c.ev("document.getElementById('btnGoUnit').click()")""",
     "旧ボタン"),
])

# --------------------------------------------------------------- test_app2.py
patch("test_app2.py", [
    ("""        c.ev(HELPER)

        # ---------- 1. ノートが空のとき ----------""",
     """        c.ev(HELPER)
        c.ev("window.__t.ensureUser()")      # 利用者を決めてからでないと始められない

        # ---------- 1. ノートが空のとき ----------""",
     "利用者登録"),
    ("""                if f.endswith("_note.json"):""",
     """                if "_note_" in f and f.endswith(".json"):""",
     "ノートのファイル名"),
    ("""                if f.endswith("_resume.json"):""",
     """                if "_resume_" in f and f.endswith(".json"):""",
     "中断ファイルの名前"),
])

# --------------------------------------------------------------- test_live.py
patch("test_live.py", [
    ("""        nbtn = c.ev("document.querySelectorAll('#unitList .unit').length")
        c.ev(HELPER)
        rec(True, "単元一覧が表示される", "（この時点では未表示。次の出題で確認）")""",
     """        c.ev(HELPER)
        c.ev("window.__t.ensureUser()")      # 利用者を決めてからでないと始められない
        rec(True, "単元一覧が表示される", "（この時点では未表示。次の出題で確認）")""",
     "利用者登録"),
])

print("★未検出: %s" % ng if ng else "すべて適用")
