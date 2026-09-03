# -*- coding: utf-8 -*-
"""本番形式編のPDFを、中身を読んで確かめる。

  いちばん大事なのは「全部の設問が紙に載っているか」。
  資料の点数が多いと、紙面から設問が押し出されて消えることがある。
  ファイルサイズやページ数だけ見ていては気づけないので、
  PDFの文字を取り出して、1問ずつ本文と選択肢を照合する。
"""
import io
import json
import os
import re
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PDF = os.path.join(os.path.expanduser("~"), "Downloads", "CHIRI_QA_20260901",
                   "PDF")
PT = 25.4 / 72.0
NAMES = {"D": "地理本番_D_組合せ形式.pdf",
         "E": "地理本番_E_通し演習 第1回.pdf",
         "F": "地理本番_F_残りの技能・形式.pdf",
         "G": "地理本番_G_地域調査.pdf"}
res = []


def rec(ok, title, detail=""):
    st = "OK" if ok else "NG"
    res.append((st, title, detail))
    print("[%s] %s %s" % (st, title, detail))


def norm(s):
    return re.sub(r"\s+", "", s)


def main():
    doc = json.loads(io.open(os.path.join(ROOT, "data", "chiri-honban.json"),
                             encoding="utf-8").read())
    for u in doc["units"]:
        name = NAMES.get(u["id"])
        if not name or not os.path.isfile(os.path.join(PDF, name)):
            rec(False, "冊%s のPDFがある" % u["id"], name or "（名前が未登録）")
            continue
        d = pymupdf.open(os.path.join(PDF, name))
        text = norm("\n".join(p.get_text() for p in d))
        sizes = set((round(p.rect.width * PT), round(p.rect.height * PT))
                    for p in d)
        col = []
        for pg in d:
            for dr in pg.get_drawings():
                for cc in (dr.get("color"), dr.get("fill")):
                    if cc and len(cc) == 3 and (max(cc) - min(cc)) > 0.05:
                        col.append(pg.number + 1)
        npage = d.page_count
        d.close()

        # 1問ずつ、問題文の頭と正解の選択肢が紙に載っているか
        miss_q, miss_c = [], []
        for q in u["questions"]:
            head = norm(q["q"].split("\n")[0])[:24]
            if head and head not in text:
                miss_q.append(q["no"])
            ans = norm(q["choices"][q["answer"]])[:20]
            if ans and ans not in text:
                miss_c.append(q["no"])
        rec(not miss_q, "冊%s：全%d問の問題文が紙に載っている"
            % (u["id"], len(u["questions"])),
            "%d問すべて確認" % len(u["questions"]) if not miss_q
            else "載っていない問=" + str(miss_q))
        rec(not miss_c, "冊%s：全%d問の正解の選択肢が紙に載っている"
            % (u["id"], len(u["questions"])),
            "%d問すべて確認" % len(u["questions"]) if not miss_c
            else "載っていない問=" + str(miss_c))
        rec(sizes == {(210, 297)} and not col,
            "冊%s：A4縦で、色を使っていない" % u["id"],
            "%dページ／すべてA4縦／色なし" % npage if not col
            else "色のあるページ=" + str(sorted(set(col))))

    ng = [r for r in res if r[0] == "NG"]
    print("-" * 68)
    print("本番形式編PDFの確認: %s（OK %d / NG %d）"
          % ("NGなし" if not ng else "★NG あり",
             len([r for r in res if r[0] == "OK"]), len(ng)))
    out = os.path.join(ROOT, "動作確認結果_本番形式編PDF.txt")
    io.open(out, "w", encoding="utf-8-sig", newline="\r\n").write(
        "本番形式編PDFの確認\n" + "=" * 60 + "\n\n"
        + "\n\n".join("[%s] %s\n      %s" % r for r in res)
        + "\n\n" + "=" * 60 + "\n判定: %s（OK %d / NG %d）\n"
        % ("NGなし" if not ng else "★NG あり",
           len([r for r in res if r[0] == "OK"]), len(ng)))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
