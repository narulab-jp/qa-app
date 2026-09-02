# -*- coding: utf-8 -*-
"""スマホ設定手順.md の残りの表記を直す。"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "スマホ設定手順.md")
t = io.open(P, encoding="utf-8-sig").read().replace("\r\n", "\n")
ok = True


def sub(old, new, tag):
    global t, ok
    if old not in t:
        print("★未検出: %s" % tag)
        ok = False
        return
    t = t.replace(old, new, 1)


sub("""続きから再開できます（やり方は6を参照）。""",
    """続きから再開できます（やり方は7を参照）。""", "参照番号")
sub("""「中断して保存」で保存した `chiri_resume.json` を、
トップ画面の **「中断した周回を再開する」** から選ぶと、続きから始められます。""",
    """「中断して保存」で保存したファイル（例：`chiri_resume_たろう.json`）を、
トップ画面の **「中断した周回を再開する」** から選ぶと、続きから始められます。
このファイルにも自分の名前が入ります。""", "中断ファイル名")

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("スマホ設定手順.md: %s" % ("更新しました" if ok else "★未検出あり"))
sys.exit(0 if ok else 1)
