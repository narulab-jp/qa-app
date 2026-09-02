# -*- coding: utf-8 -*-
"""test_users.py を公開URL向けに写して、実際に公開されたアプリで確認できるようにする。"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(ROOT, "tools", "test_users.py")
dst = os.path.join(ROOT, "tools", "test_users_live.py")

t = io.open(src, encoding="utf-8-sig").read().replace("\r\n", "\n")
t = t.replace('URL = "http://127.0.0.1:%d/index.html" % PORT',
              'URL = "https://narulab-jp.github.io/qa-app/index.html"')
t = t.replace("動作確認結果_複数利用者.txt", "動作確認結果_複数利用者_公開後.txt")
t = t.replace("一問一答アプリ　複数利用者対応　動作確認結果",
              "一問一答アプリ　複数利用者対応　動作確認結果（公開URL）")
t = t.replace("PORT = 8801", "PORT = 8811")
t = t.replace("DBG = 9271", "DBG = 9281")
t = t.replace('DL = os.path.join(os.environ["TEMP"], "qa_dl_users")',
              'DL = os.path.join(os.environ["TEMP"], "qa_dl_users_live")')
io.open(dst, "w", encoding="utf-8", newline="\n").write(t)
print("作成: tools/test_users_live.py")
