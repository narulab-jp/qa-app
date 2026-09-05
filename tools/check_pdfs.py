# -*- coding: utf-8 -*-
r"""できあがったPDFを、紙に出す前にまとめて点検する。

  見た目の印象ではなく、PDFの中身を読んで機械で判定する。

    1. 線の太さ            0.25mm 以上か（塗りつぶし図形の縁は対象外）
    2. 図の中の文字        4pt 以上か
    3. 紙面の外にはみ出し  文字や図が用紙の外に出ていないか
    4. 設問の載り漏れ      全設問の問題文と正解が、どれかの紙に載っているか
    5. 文字化け・豆腐      表示できない字（.notdef）が無いか
    6. フォント埋め込み    すべて埋め込まれているか
    7. ページ番号          全ページにあるか
    8. 用紙                A4縦か

  python tools\check_pdfs.py
"""
import collections
import glob
import io
import json
import os
import re
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, "Downloads", "CHIRI_QA_20260901")
PDF_DIRS = [os.path.join(BASE, "PDF"), os.path.join(BASE, "PDF", "優先順位版")]

PT2MM = 25.4 / 72.0
MIN_MM = 0.25          # 線の太さの下限
MIN_FIG_PT = 4.0       # 図の中の文字の下限
A4 = (595.0, 842.0)
RE_PNO = re.compile(r"(\d+)\s*/\s*(\d+)")
res = []


def rec(ok, title, detail=""):
    res.append(("OK" if ok else "NG", title, detail))
    print("[%s] %-42s %s" % ("OK" if ok else "NG", title, detail))
    return ok


def lum(c):
    if not c:
        return 0.0
    try:
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    except Exception:
        return 0.0


def pdfs():
    out = []
    for d in PDF_DIRS:
        for p in sorted(glob.glob(os.path.join(d, "*.pdf"))):
            out.append(p)
    return out


def main():
    files = pdfs()
    print("点検するPDF %d本\n" % len(files))

    thin, small, over, tofu, nofont, nopage, notA4 = [], [], [], [], [], [], []
    npages = 0
    alltext = []
    minw, minpt = 99.0, 99.0

    for p in files:
        name = os.path.basename(p)
        doc = pymupdf.open(p)
        npages += len(doc)
        # 8. 用紙
        for i in range(len(doc)):
            r = doc[i].rect
            if abs(r.width - A4[0]) > 2 or abs(r.height - A4[1]) > 2:
                notA4.append("%s p%d %.0fx%.0f" % (name, i + 1, r.width, r.height))
                break
        # 6. フォント
        for i in range(len(doc)):
            for f in doc.get_page_fonts(i):
                if f[0] == 0:
                    nofont.append("%s p%d %s" % (name, i + 1, f[3]))
        for i in range(len(doc)):
            page = doc[i]
            # 1. 線の太さ
            for d in page.get_drawings():
                t = d.get("type")
                if t not in ("s", "fs"):
                    continue
                if t == "fs" and lum(d.get("fill")) < 0.5:
                    continue
                w = d.get("width")
                if w is None:
                    continue
                mm = w * PT2MM
                minw = min(minw, mm)
                if mm < MIN_MM - 0.003:
                    thin.append("%s p%d %.3fmm" % (name, i + 1, mm))
            # 2/3/5/7. 文字まわり
            txt = page.get_text()
            alltext.append(txt)
            # 1枚もののポスターにページ番号は要らないので対象外にする
            if len(doc) > 1 and not RE_PNO.search(txt):
                nopage.append("%s p%d" % (name, i + 1))
            raw = page.get_text("rawdict")
            for b in raw["blocks"]:
                for l in b.get("lines", []):
                    for s in l.get("spans", []):
                        sz = s["size"]
                        minpt = min(minpt, sz)
                        if sz < MIN_FIG_PT:
                            small.append("%s p%d %.1fpt %s"
                                         % (name, i + 1, sz,
                                            "".join(c["c"] for c in s["chars"])[:10]))
                        for c in s["chars"]:
                            # 表示できない字（豆腐）
                            if c.get("c") in ("�",):
                                tofu.append("%s p%d" % (name, i + 1))
                        bb = s["bbox"]
                        if bb[0] < -1 or bb[1] < -1 or \
                                bb[2] > page.rect.width + 1 or \
                                bb[3] > page.rect.height + 1:
                            over.append("%s p%d %s" % (name, i + 1,
                                                       [round(x) for x in bb]))
        doc.close()

    rec(not thin, "1. 線の太さが 0.25mm 以上",
        "全PDFの最細 %.3fmm" % minw if not thin
        else "★%d本が細い %s" % (len(thin), thin[:3]))
    rec(not small, "2. 文字が 4pt 以上",
        "いちばん小さい文字 %.1fpt" % minpt if not small
        else "★%d字が4pt未満 %s" % (len(small), small[:3]))
    rec(not over, "3. 紙面の外にはみ出した文字が無い",
        "%dページを確認" % npages if not over else "★%s" % over[:3])
    rec(not tofu, "5. 表示できない字（豆腐）が無い",
        "全ページ" if not tofu else "★%s" % tofu[:3])
    rec(not nofont, "6. フォントがすべて埋め込まれている",
        "全ページ" if not nofont else "★%s" % nofont[:3])
    rec(not nopage, "7. 全ページにページ番号がある",
        "%dページすべて" % npages if not nopage
        else "★%d箇所 %s" % (len(nopage), nopage[:5]))
    rec(not notA4, "8. すべて A4縦（595x842pt）",
        "%d本すべて" % len(files) if not notA4 else "★%s" % notA4[:3])

    # 4. 設問の載り漏れ
    whole = "".join(alltext)
    whole = re.sub(r"\s+", "", whole)
    miss_q, miss_a, nq = [], [], 0
    for fn in ("chiri.json", "chiri-zuhyo.json", "chiri-honban.json"):
        p = os.path.join(ROOT, "data", fn)
        if not os.path.isfile(p):
            continue
        d = json.loads(io.open(p, encoding="utf-8").read())
        for u in d["units"]:
            for q in u["questions"]:
                nq += 1
                key = re.sub(r"\s+", "", str(q.get("q", "")))[:24]
                if key and key not in whole:
                    miss_q.append("%s %s" % (fn[:12], q.get("seq")))
                ans = re.sub(r"\s+", "", str(q.get("a", "")))[:20]
                if ans and ans not in whole:
                    miss_a.append("%s %s" % (fn[:12], q.get("seq")))
    rec(not miss_q, "4a. 全設問の問題文が紙に載っている",
        "%d問すべて" % nq if not miss_q
        else "★%d問が見つからない %s" % (len(miss_q), miss_q[:5]))
    rec(not miss_a, "4b. 全設問の正解が紙に載っている",
        "%d問すべて" % nq if not miss_a
        else "★%d問が見つからない %s" % (len(miss_a), miss_a[:5]))

    ng = [x for x in res if x[0] == "NG"]
    print("=" * 76)
    print("PDF点検: %s（OK %d / NG %d）／ %d本・%dページ"
          % ("NGなし" if not ng else "★NGあり", len(res) - len(ng), len(ng),
             len(files), npages))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
