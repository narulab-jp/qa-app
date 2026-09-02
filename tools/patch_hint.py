# -*- coding: utf-8 -*-
"""ノートが空のときに次の一歩が分かるよう、案内を1行足す。
JavaScript は使わず、［はじめる］が押せない状態のときだけ CSS で出す。"""
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
      """      <button class="btn hero-go" id="btnNoteQuiz">はじめる</button>
      <details class="hero-more">""",
      """      <button class="btn hero-go" id="btnNoteQuiz">はじめる</button>
      <p class="hero-hint">まずは下の「単元から出題する」で何問か解いてください。
        間違えた問題がここにたまります。</p>
      <details class="hero-more">""",
      "index.html: 空のときの案内")

patch("app.css",
      """.hero-more{margin-top:16px;}""",
      """/* ［はじめる］が押せないとき（ノートが空のとき）だけ出す案内 */
.hero-hint{display:none;}
#btnNoteQuiz:disabled ~ .hero-hint{
  display:block; margin:16px 0 0; font-size:var(--fs-label);
  color:#B9C8D8; line-height:1.7;
}
.hero-more{margin-top:16px;}""",
      "app.css: 案内の表示条件")

sys.exit(0 if ok else 1)
