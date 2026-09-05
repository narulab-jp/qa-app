# -*- coding: utf-8 -*-
r"""PDFに実際に入っている線の太さを測る。

  推定ではなく、PDFの中の線そのものの太さ（ポイント）を読み、mmに直す。
  紙に出たときの太さがそのまま分かる。

  白黒印刷でのめやす
    0.25mm（0.71pt）  … これを下回ると、家庭用のプリンタでは
                        かすれる・消える。等高線や境界線には足りない。
    0.35mm（0.99pt）  … 等高線・境界線・海岸線など、読み取る線の下限。
    0.50mm            … 枠・軸など、はっきり見せたい線。

  python tools\measure_lines.py <PDFのフォルダかファイル> [しきい値mm]
"""
import collections
import glob
import os
import sys

import fitz

PT2MM = 25.4 / 72.0
LIMIT = 0.25


def lum(c):
    """色の明るさ（0=黒, 1=白）。"""
    if not c:
        return 0.0
    try:
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    except Exception:
        return 0.0


def widths_of(path):
    """(太さmm → 本数) と、細い線のあるページ番号を返す。

      ★塗りつぶしてある図形（type "fs"）は、中が濃ければ縁の太さに
        関係なく見える。箇条書きの●がこれにあたる。
        縁の太さが問題になるのは
          ・線だけの図形（type "s"）
          ・塗りが薄い図形（白抜きの丸など）
        の2つ。ここを分けないと、●を「細い線」と数えてしまう。
    """
    doc = fitz.open(path)
    hist = collections.Counter()
    thin_pages = collections.Counter()
    for pno in range(len(doc)):
        page = doc[pno]
        try:
            drs = page.get_drawings()
        except Exception:
            continue
        for d in drs:
            t = d.get("type")
            if t not in ("s", "fs"):
                continue
            if t == "fs" and lum(d.get("fill")) < 0.5:
                continue                      # 中が濃いので縁は関係ない
            w = d.get("width")
            if w is None:
                continue
            mm = round(w * PT2MM, 3)
            n = len(d.get("items") or [])
            hist[mm] += max(1, n)
            if mm < LIMIT:
                thin_pages[pno + 1] += max(1, n)
    doc.close()
    return hist, thin_pages


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = sys.argv[1]
    lim = float(sys.argv[2]) if len(sys.argv) > 2 else LIMIT
    files = ([target] if os.path.isfile(target)
             else sorted(glob.glob(os.path.join(target, "*.pdf"))))
    if not files:
        print("PDFが見つかりません: %s" % target)
        return 1
    total = collections.Counter()
    print("%-46s %7s %7s %9s %9s"
          % ("PDF", "線の数", "最細mm", "0.25未満", "0.35未満"))
    print("-" * 84)
    ng = []
    for p in files:
        hist, thin = widths_of(p)
        if not hist:
            continue
        total.update(hist)
        n = sum(hist.values())
        mn = min(hist)
        u25 = sum(v for k, v in hist.items() if k < lim)
        u35 = sum(v for k, v in hist.items() if k < 0.35)
        print("%-46s %7d %7.3f %9d %9d"
              % (os.path.basename(p)[:46], n, mn, u25, u35))
        if u25:
            ng.append((os.path.basename(p), mn, u25,
                       sorted(thin.items(), key=lambda x: -x[1])[:5]))
    print("-" * 84)
    n = sum(total.values())
    print("合計 %d本 ／ 最細 %.3fmm ／ %.2fmm未満 %d本（%.1f%%） ／ "
          "0.35mm未満 %d本（%.1f%%）"
          % (n, min(total), lim,
             sum(v for k, v in total.items() if k < lim),
             100.0 * sum(v for k, v in total.items() if k < lim) / n,
             sum(v for k, v in total.items() if k < 0.35),
             100.0 * sum(v for k, v in total.items() if k < 0.35) / n))
    print("\n■ 太さの分布（mm：本数）　細い順に20段階")
    for k in sorted(total)[:20]:
        print("   %6.3f mm （%5.2f pt） %7d本" % (k, k / PT2MM, total[k]))
    if ng:
        print("\n■ %.2fmm 未満の線があるPDF（多いページ）" % lim)
        for name, mn, cnt, pages in ng:
            print("   %-44s 最細%.3f  %5d本  ページ %s"
                  % (name[:44], mn, cnt,
                     "、".join("%d(%d本)" % x for x in pages)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
