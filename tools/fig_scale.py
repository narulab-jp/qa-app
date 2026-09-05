# -*- coding: utf-8 -*-
r"""図が紙の上で何mmになるかを、置き方の規則から先に計算する。

  線の太さは「紙に出たときの mm」で決めたい。ところが同じ図でも、
  1つで置かれるか2つ並ぶかで 78mm〜169mm と2倍以上ちがう。
  そこで、図ごとに「いちばん小さく置かれるときの mm」を出しておき、
  図を作るときにその値を使って太さを決める（figlib.set_target）。

  ここでは組版の規則そのものを使って計算する（できあがったPDFを
  読むのではない）。PDFを作る前に走らせられるようにするため。
  縮尺 sc で拡大される場合は、拡大後のほうが大きい＝線は太くなるので、
  拡大なしで見積もっておけば足りる（安全側）。

  python tools\fig_scale.py        … 一覧を出す
  出力: tools/fig_display.json
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build_zuhyo_pdf as Z         # noqa: E402  図表編・本番形式編・分冊で共通
import build_yomimono as Y          # noqa: E402  読み物

FIG = os.path.join(ROOT, "figures")
OUT = os.path.join(HERE, "fig_display.json")
HTML = Z.HTML_DIR
RE_IMG = re.compile(
    r'<img src="([^"]+)"[^>]*style="width:([\d.]+)mm;height:[\d.]+mm"')

DATA = [("data/chiri-zuhyo.json", "図表編"),
        ("data/chiri-honban.json", "本番形式編")]


def vb_of(name):
    p = os.path.join(FIG, name)
    if not os.path.isfile(p):
        return None
    t = io.open(p, encoding="utf-8").read()
    vb = t.split('viewBox="')[1].split('"')[0].split()
    return float(vb[2]), float(vb[3])


def size(w, h, maxh, scale=1.0):
    return min(Z.CW, maxh * w / h * scale)


def main():
    best = {}

    def put(name, mm, where):
        if name not in best or mm < best[name][0]:
            best[name] = (mm, where)

    for rel, label in DATA:
        p = os.path.join(ROOT, rel)
        if not os.path.isfile(p):
            continue
        d = json.loads(io.open(p, encoding="utf-8").read())
        for u in d["units"]:
            for q in u["questions"]:
                figs = q.get("figures") or []
                if not figs:
                    continue
                single = (len(figs) == 1)
                for f in figs:
                    name = os.path.basename(f)
                    vb = vb_of(name)
                    if not vb:
                        continue
                    put(name, size(vb[0], vb[1], 150.0 if single else 120.0),
                        "%s（%s）" % (label, "単独" if single else "2つ並び"))

    # 読み物（単体のPDFと、分冊に入るとき）
    p = os.path.join(ROOT, "data", "yomimono.json")
    if os.path.isfile(p):
        d = json.loads(io.open(p, encoding="utf-8").read())
        for r in d.get("readings", []):
            for s in r.get("sections", []):
                for b in s.get("body", []):
                    if b.get("t") != "fig" or not b.get("src"):
                        continue
                    name = os.path.basename(b["src"])
                    vb = vb_of(name)
                    if not vb:
                        continue
                    put(name, min(Z.CW, 130.0 * vb[0] / vb[1]), "読み物")
                    put(name, size(vb[0], vb[1], 150.0, 0.80), "分冊の読み物")

    # どこにも出てこない図（将来のぶん）は、いちばん厳しい値で見ておく
    for name in sorted(os.listdir(FIG)):
        if name.endswith(".svg") and name not in best:
            vb = vb_of(name)
            if vb:
                put(name, size(vb[0], vb[1], 120.0), "（未使用・安全側）")

    # ★組版のときに、ページに収めるため図を縮めることがある（sc）。
    #   それは規則からは読めないので、いちばん最近作ったHTMLに書かれている
    #   実際の mm を読んで、小さいほうを採る。
    #   図の大きさは線の太さに依存しないので、1回読み戻せば決まる。
    n_html = 0
    for root, _d, fs in os.walk(HTML):
        for fn in fs:
            if not fn.endswith(".html") or fn.startswith("_"):
                continue
            n_html += 1
            s = io.open(os.path.join(root, fn), encoding="utf-8",
                        errors="replace").read()
            for m in RE_IMG.finditer(s):
                nm = os.path.basename(m.group(1))
                if nm.endswith(".svg"):
                    put(nm, float(m.group(2)), "実際の組版（%s）" % fn[:20])
    print("できあがったHTML %d本から、実際の大きさも読み込んだ" % n_html)

    table = {}
    rows = []
    for name, (mm, where) in best.items():
        vb = vb_of(name)
        table[name] = round(mm, 2)
        rows.append((mm / vb[0], mm, vb[0], name, where))
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(table, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    rows.sort()
    print("図 %d枚の「いちばん小さく置かれるときの大きさ」を求めた" % len(rows))
    print("→ %s\n" % OUT)
    print("%-24s %8s %8s %9s  %s"
          % ("SVG", "最小mm", "viewBox", "mm/単位", "そのときの置き方"))
    for r in rows[:10]:
        print("%-24s %8.1f %8.0f %9.4f  %s" % (r[3], r[1], r[2], r[0], r[4]))
    print("   …")
    for r in rows[-3:]:
        print("%-24s %8.1f %8.0f %9.4f  %s" % (r[3], r[1], r[2], r[0], r[4]))
    u = rows[0][0]
    print("\nいちばん厳しい図で 1単位 = %.4fmm" % u)
    print("  0.25mm を出すのに %.2f 単位、0.35mm を出すのに %.2f 単位"
          % (0.25 / u, 0.35 / u))
    return 0


if __name__ == "__main__":
    sys.exit(main())
