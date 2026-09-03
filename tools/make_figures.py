# -*- coding: utf-8 -*-
"""図表編の図版（SVG）をまとめて作る。

  ・教科書・資料集・過去問の図は一切写していない。
    地形は標高の式から等高線を計算して起こし、グラフも数値から目盛ごと描く。
  ・白黒印刷で判別できるよう、色ではなく線種・ハッチング・記号で区別する。
  ・架空の数値を使う図には、図の中に「架空」である旨を必ず書く。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import fig_a          # noqa: E402
import fig_b          # noqa: E402
import fig_c          # noqa: E402
import fig_f          # noqa: E402
import fig_g          # noqa: E402

FIG = os.path.join(ROOT, "figures")


def all_figures():
    d = {}
    for mod in (fig_a, fig_b, fig_c, fig_f, fig_g):
        d.update(mod.FIGURES)
    return d


def main():
    if not os.path.isdir(FIG):
        os.makedirs(FIG)
    figs = all_figures()
    keep = set(figs)
    for old in os.listdir(FIG):
        if old not in keep:
            os.remove(os.path.join(FIG, old))
            print("  （削除）%s" % old)
    total = 0
    for name in sorted(figs):
        body = figs[name]()
        p = os.path.join(FIG, name)
        io.open(p, "w", encoding="utf-8", newline="\n").write(body + "\n")
        total += os.path.getsize(p)
    print("図版 %d 枚を作成（合計 %.1f KB）" % (len(figs), total / 1024.0))


if __name__ == "__main__":
    main()
