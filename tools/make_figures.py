# -*- coding: utf-8 -*-
"""図表編の図版（SVG）をまとめて作る。

  ・教科書・資料集・過去問の図は一切写していない。
    地形は標高の式から等高線を計算して起こし、グラフも数値から目盛ごと描く。
  ・白黒印刷で判別できるよう、色ではなく線種・ハッチング・記号で区別する。
  ・架空の数値を使う図には、図の中に「架空」である旨を必ず書く。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import figlib          # noqa: E402

import fig_a          # noqa: E402
import fig_b          # noqa: E402
import fig_c          # noqa: E402
import fig_d          # noqa: E402
import fig_f          # noqa: E402
import fig_r          # noqa: E402  読み物（解説）の図
import fig_g          # noqa: E402
import fig_h          # noqa: E402

FIG = os.path.join(ROOT, "figures")


def all_figures():
    d = {}
    for mod in (fig_a, fig_b, fig_c, fig_d, fig_f, fig_g, fig_h, fig_r):
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
    # 図ごとに「紙の上で1単位が何mmになるか」を渡す。
    # これで線の太さが、紙に出たときの下限（主要0.35mm・補助0.25mm）に
    # そろう。表は tools/fig_scale.py が組版の規則から作る。
    disp = {}
    dp = os.path.join(HERE, "fig_display.json")
    if os.path.isfile(dp):
        disp = json.loads(io.open(dp, encoding="utf-8").read())
    else:
        print("  ※ fig_display.json がありません。安全側の既定値で作ります。")
    total = 0
    thin = []
    for name in sorted(figs):
        # 1回目は viewBox の幅を知るためだけに呼ぶ
        figlib.set_target(None)
        first = figs[name]()
        vbw = float(first.split('viewBox="')[1].split('"')[0].split()[2])
        mm = disp.get(name)
        figlib.set_target((mm / vbw) if mm else None)
        body = figs[name]()
        p = os.path.join(FIG, name)
        io.open(p, "w", encoding="utf-8", newline="\n").write(body + "\n")
        total += os.path.getsize(p)
        if mm:
            thin.append((figlib.unit_mm(), name))
    print("図版 %d 枚を作成（合計 %.1f KB）" % (len(figs), total / 1024.0))
    if thin:
        thin.sort()
        print("  いちばん小さく置かれる図: %s（1単位 %.4fmm）"
              % (thin[0][1], thin[0][0]))
        print("  主要な線はどの図でも %.2fmm 以上、補助線は %.2fmm 以上になる"
              % (figlib.MM_MAIN, figlib.MM_SUB))


if __name__ == "__main__":
    main()
