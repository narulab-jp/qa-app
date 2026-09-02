# -*- coding: utf-8 -*-
"""利用者バーの「切り替え」ボタンを、指で押せる大きさ（44px以上）にする。"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "app.css")
t = io.open(P, encoding="utf-8-sig").read().replace("\r\n", "\n")

old = """#userBar{
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
}"""
new = """#userBar{
  position:sticky; top:0; z-index:20;
  display:flex; align-items:center; gap:8px;
  background:var(--accent); color:#fff;
  border-radius:0 0 10px 10px; padding:5px 10px; margin:0 0 10px;
  font-size:0.95em;
}
#userBar .ub-name{flex:1 1 auto;font-weight:bold;}
#userBar .ub-btn{
  flex:0 0 auto; min-height:44px; padding:6px 16px;
  border:1.5px solid #fff; border-radius:8px;
  background:transparent; color:#fff; font-size:0.9em; cursor:pointer;
}"""
if old not in t:
    print("★未検出")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="\n").write(t.replace(old, new, 1))
print("利用者バーのボタンを 44px 以上にした")
