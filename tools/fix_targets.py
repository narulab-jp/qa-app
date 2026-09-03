# -*- coding: utf-8 -*-
"""honban_d.py の対応型・2軸型で、正解の位置を直に書いていたところを
   配り役（P）の呼び出しに置きかえる。1回だけ実行する。"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "honban_d.py")
t = io.open(P, encoding="utf-8").read()

# taiou_at({...}, N)  →  taiou_at({...}, P(6))
n1 = 0


def r1(m):
    global n1
    n1 += 1
    return m.group(1) + "P(6))"


t2 = re.sub(r"(taiou_at\((?:[^()]|\([^()]*\))*?,\s*)\d+\)", r1, t, flags=re.S)

# nijiku_at(..., N)  →  nijiku_at(..., P(4))
n2 = 0


def r2(m):
    global n2
    n2 += 1
    return m.group(1) + "P(4))"


t2 = re.sub(r"(nijiku_at\((?:[^()]|\([^()]*\))*?,\s*)\d+\)", r2, t2, flags=re.S)

io.open(P, "w", encoding="utf-8", newline="\n").write(t2)
print("taiou_at %d件／nijiku_at %d件 を P() に置きかえた" % (n1, n2))
