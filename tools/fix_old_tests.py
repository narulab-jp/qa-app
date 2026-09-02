# -*- coding: utf-8 -*-
"""指示C以降は利用者を決めないと学習を始められないため、
既存の動作確認スクリプトのヘルパーに利用者の登録を足す。"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = ("  start: function(unitIds, count, level, order, mode){\n"
       "    window.__app.setNoteAsked(true);")
NEW = ("  ensureUser: function(){\n"
       "    if(!window.__app.getCurrentUser()){\n"
       "      document.getElementById('newUserName').value='テスト';\n"
       "      document.getElementById('btnAddUser').click();\n"
       "    }\n"
       "  },\n"
       "  start: function(unitIds, count, level, order, mode){\n"
       "    this.ensureUser();\n"
       "    window.__app.setNoteAsked(true);")

for name in ("test_app.py", "test_app2.py", "test_live.py"):
    p = os.path.join(ROOT, "tools", name)
    t = io.open(p, encoding="utf-8-sig").read().replace("\r\n", "\n")
    if OLD in t:
        io.open(p, "w", encoding="utf-8", newline="\n").write(t.replace(OLD, NEW, 1))
        print("更新: tools/%s" % name)
    else:
        print("★未検出: tools/%s" % name)
