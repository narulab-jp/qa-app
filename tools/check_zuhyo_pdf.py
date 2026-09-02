# -*- coding: utf-8 -*-
"""できあがったPDFを実際に読んで確かめる。ファイルサイズでは判定しない。
   ・A4縦か
   ・図が設問と同じページにあるか
   ・解答が設問と別のページにあるか
   ・全ページにページ番号があるか
   ・図が印刷で80mm以上あるか
"""
import io
import os
import sys

import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import zuhyo_bank as bank        # noqa: E402

HOME = os.path.expanduser("~")          # 公開前にユーザー名を除去
PDF_DIR = os.path.join(HOME, "Downloads", "CHIRI_QA_20260901", "PDF")
PT_MM = 25.4 / 72.0
res = []


def rec(ok, title, detail=""):
    st = ok if isinstance(ok, str) else ("OK" if ok else "NG")
    res.append((st, title, detail))
    print("[%s] %s %s" % (st, title, detail))


def main():
    for u in bank.UNITS:
        name = "地理図表_%s_%s.pdf" % (u["id"], u["name"])
        path = os.path.join(PDF_DIR, name)
        if not os.path.isfile(path):
            rec(False, "%s が出力されている" % name, "ファイルがない")
            continue
        d = fitz.open(path)
        sizes = set()
        texts = []
        figw = []           # ページごとの図の幅(mm)。0なら図なし
        # 本文の範囲（ヘッダ罫線とフッタ罫線の間）だけを見る
        y0 = (15.0 + 8.0 + 1.0) / PT_MM
        y1 = (297.0 - 15.0 - 8.0 - 1.0) / PT_MM
        for pg in d:
            sizes.add((round(pg.rect.width * PT_MM), round(pg.rect.height * PT_MM)))
            texts.append(pg.get_text())
            x0, x1 = None, None
            for dr in pg.get_drawings():        # ベクタで描かれた図
                b = dr["rect"]
                if b.y0 < y0 or b.y1 > y1:
                    continue
                x0 = b.x0 if x0 is None else min(x0, b.x0)
                x1 = b.x1 if x1 is None else max(x1, b.x1)
            w = (x1 - x0) * PT_MM if x0 is not None else 0.0
            for blk in pg.get_image_info():     # ラスタで貼られた図
                if blk["bbox"][1] >= y0 and blk["bbox"][3] <= y1:
                    w = max(w, (blk["bbox"][2] - blk["bbox"][0]) * PT_MM)
            figw.append(w)
        rec(sizes == {(210, 297)}, "%s がA4縦である" % name,
            "全%dページ %s mm" % (d.page_count, sorted(sizes)))

        # 設問のあるページ（設問番号 A−1 などがあるページ）に図があるか
        keys = ["%s−%d" % (u["id"], q["no"]) for q in u["questions"]]
        qpages = [i + 1 for i, t in enumerate(texts)
                  if any(k in t for k in keys) and "解答欄" in t]
        bad = [i for i in qpages if figw[i - 1] < 20]
        rec(qpages and not bad, "%s：図が設問と同じページにある" % name,
            "設問ページ=%s／図の幅=%s mm"
            % (qpages, [round(figw[i - 1]) for i in qpages])
            if not bad else "図のないページ %s" % bad)

        # 解答が別ページか
        apages = [i + 1 for i, t in enumerate(texts) if "解答・解説" in t and "正解 " in t]
        mix = [i for i in qpages if "正解 " in texts[i - 1]]
        rec(apages and not mix, "%s：解答が設問と別のページにまとまっている" % name,
            "解答ページ=%s／設問ページと混在なし" % apages)

        # ページ番号
        miss = [i + 1 for i, t in enumerate(texts)
                if ("冊%s" % u["id"]) not in t or ("%d/%d" % (i + 1, d.page_count)) not in t]
        rec(not miss, "%s：全ページにページ番号がある" % name,
            "「冊%s n/%d」が全%dページに入っている" % (u["id"], d.page_count, d.page_count)
            if not miss else str(miss))

        # 図の印刷幅
        ws = [figw[i - 1] for i in qpages]
        mn = min(ws) if ws else 0
        rec(mn >= 80, "%s：図が印刷時に80mm以上ある" % name,
            "設問ページの図の幅は最小 %.0fmm（%d ページ）" % (mn, len(ws)))

        # 色を使っていないか（白黒印刷でも判別できる）
        colored = []
        for pg in d:
            for dr in pg.get_drawings():
                for c in (dr.get("color"), dr.get("fill")):
                    if c and len(c) == 3 and (max(c) - min(c)) > 0.05:
                        colored.append(pg.number + 1)
        rec(not colored, "%s：色を使っておらず、白黒印刷で判別できる" % name,
            "全%dページとも黒・白・網かけのみ" % d.page_count
            if not colored else "色のあるページ %s" % sorted(set(colored)))

        # 全問が載っているか
        miss = []
        for q in u["questions"]:
            key = "%s−%d" % (u["id"], q["no"])
            if not any(key in t for t in texts):
                miss.append(key)
        rec(not miss, "%s：%d問すべてが載っている" % (name, len(u["questions"])),
            "%d問すべて確認" % len(u["questions"]) if not miss else str(miss))

        # 選択肢4つ
        miss = []
        for q in u["questions"]:
            for m in ["①", "②", "③", "④"]:
                if not any((m in t) for t in texts):
                    miss.append(m)
        rec(not miss, "%s：選択肢の番号①〜④が印刷されている" % name, "①②③④ すべてあり")
        d.close()

    ng = [r for r in res if r[0] == "NG"]
    print("-" * 68)
    print("PDFの確認: %s（OK %d / NG %d）"
          % ("NGなし" if not ng else "★NG あり",
             len([r for r in res if r[0] == "OK"]), len(ng)))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
