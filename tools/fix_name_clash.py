# -*- coding: utf-8 -*-
"""変数名の衝突を解消する。

指示Cで追加した「現在の利用者名」を currentUser という名前にしたが、
既存コードでは currentUser が「利用者が入力した解答の文字列」として
使われていた。既存コードには手を触れず、追加分だけ activeUser に改名する。
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "app.js")
t = io.open(P, encoding="utf-8-sig").read().replace("\r\n", "\n")

before = t.count("currentUser")
t = t.replace("currentUser", "activeUser")

# --- 既存コード（解答の文字列）は currentUser のまま戻す ---
KEEP = [
    ("var current = null, currentItem = null, activeUser = \"\", shownAt = 0, answered = false;",
     "var current = null, currentItem = null, currentUser = \"\", shownAt = 0, answered = false;"),
    ("  current = currentItem.q;\n  activeUser = \"\";",
     "  current = currentItem.q;\n  currentUser = \"\";"),
    ("  if(listening && rec){ try{ rec.stop(); }catch(e){} }\n  activeUser = text || \"\";",
     "  if(listening && rec){ try{ rec.stop(); }catch(e){} }\n  currentUser = text || \"\";"),
    ("  $(\"jUser\").textContent = activeUser ? activeUser : \"（未回答）\";",
     "  $(\"jUser\").textContent = currentUser ? currentUser : \"（未回答）\";"),
    ("  if(self && activeUser){", "  if(self && currentUser){"),
    ("    var ok = activeUser ? judge(activeUser, current) : false;",
     "    var ok = currentUser ? judge(currentUser, current) : false;"),
    ("  quiz.results.push({item:currentItem, user:activeUser, ok:ok});",
     "  quiz.results.push({item:currentItem, user:currentUser, ok:ok});"),
]
ng = []
for old, new in KEEP:
    if old not in t:
        ng.append(old.strip().splitlines()[0][:60])
        continue
    t = t.replace(old, new, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("currentUser の出現 %d 箇所 → 利用者名は activeUser に改名" % before)
print("既存コードへ戻した箇所: %d / %d" % (len(KEEP) - len(ng), len(KEEP)))
if ng:
    print("★戻せなかった箇所:")
    for x in ng:
        print("   " + x)
sys.exit(1 if ng else 0)
