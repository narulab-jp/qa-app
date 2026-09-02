# -*- coding: utf-8 -*-
"""tools/test_app.py を現在のアプリの作りに合わせる。

このスクリプトは指示Aの時点で書いたもので、その後の変更
（指示A-2で出題の進行が roundList / queue になった、
  出題数の選択肢が data-val になった）に追随できていなかった。
判定内容は変えず、要素の指定だけを現在の作りに直す。"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "tools", "test_app.py")
t = io.open(P, encoding="utf-8-sig").read().replace("\r\n", "\n")
before = t

# 出題数の選択肢は renderOptRow が data-val で作る
t = t.replace("""document.querySelector('[data-count=\\"0\\"]').click();""",
              """document.querySelector('#optCount .opt[data-val=\\"0\\"]').click();""")
t = t.replace("""document.querySelector('[data-count=\\"20\\"]').click();""",
              """document.querySelector('#optCount .opt[data-val=\\"20\\"]').click();""")

# 出題の進行は quiz.list ではなく quiz.roundList / quiz.queue
t = t.replace("window.__app.getQuiz().list[window.__app.getQuiz().idx]",
              "window.__app.getQuiz().queue[0]")
t = t.replace("window.__app.getQuiz().idx >= window.__app.getQuiz().list.length",
              "window.__app.getQuiz().queue.length === 0")
t = t.replace("window.__app.getQuiz().list.length", "window.__app.getQuiz().roundList.length")
t = t.replace("window.__app.getQuiz().list.map", "window.__app.getQuiz().roundList.map")

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
n = len(re.findall(r"getQuiz\(\)\.list\b", t))
print("test_app.py を更新（旧仕様の残り %d 箇所）" % n)
