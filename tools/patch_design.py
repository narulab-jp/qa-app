# -*- coding: utf-8 -*-
"""デザイン刷新にともなう調整。
・s-home は既定で表示のままにする（読み込み失敗の案内を出すため）
・Service Worker のキャッシュ名を上げる
機能とロジックには触らない。"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok = True


def patch(path, old, new, tag):
    global ok
    p = os.path.join(ROOT, path)
    t = io.open(p, encoding="utf-8-sig").read().replace("\r\n", "\n")
    if old not in t:
        print("★未検出: %s" % tag)
        ok = False
        return
    io.open(p, "w", encoding="utf-8", newline="\n").write(t.replace(old, new, 1))
    print("適用: %s" % tag)


patch("index.html",
      '  <section id="s-home" hidden>',
      '  <section id="s-home">',
      "s-home を既定表示に戻す")
patch("sw.js", 'var VERSION = "v3";', 'var VERSION = "v4";',
      "キャッシュ名 v3 → v4")

sys.exit(0 if ok else 1)
