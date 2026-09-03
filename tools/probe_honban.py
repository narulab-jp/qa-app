# -*- coding: utf-8 -*-
"""指摘3件を実測で確かめる（修正前の現状把握）。"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(name):
    return json.loads(io.open(os.path.join(ROOT, "data", name),
                              encoding="utf-8").read())


def main():
    h = load("chiri-honban.json")
    z = load("chiri-zuhyo.json")
    U = dict((u["id"], u["questions"]) for u in h["units"])
    zq = [q for u in z["units"] for q in u["questions"]]

    print("=" * 72)
    print("【1】冊Dの正解の並び")
    d = U["D"]
    seq = [q["answer"] for q in d]
    for s in range(0, len(d), 12):
        print("  seq%3d-%3d : %s"
              % (d[s]["seq"], d[min(s + 11, len(d) - 1)]["seq"],
                 " ".join(str(x) for x in seq[s:s + 12])))
    run = 0
    for i in range(1, len(seq)):
        if abs(seq[i] - seq[i - 1]) == 1:
            run += 1
    print("  隣り合う問で正解が±1になる割合 : %d/%d = %.0f%%"
          % (run, len(seq) - 1, 100.0 * run / (len(seq) - 1)))
    # 3問以上つづけて +1 が続く区間
    longest, cur = 1, 1
    for i in range(1, len(seq)):
        if seq[i] - seq[i - 1] == 1:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 1
    print("  +1がつづく最長の並び          : %d問" % longest)

    print()
    print("【2】冊Eに既出の問がまじっていないか")
    others = [("図表編", q) for q in zq] + \
             [("冊D", q) for q in U["D"]] + \
             [("冊F", q) for q in U["F"]]
    for q in U["E"]:
        for (src, o) in others:
            same_q = (q["q"] == o["q"])
            same_ch = (sorted(q["choices"]) == sorted(o["choices"]))
            if same_q and same_ch:
                kind = "完全に同じ" if q["choices"] == o["choices"] \
                    else "選択肢の順だけ違う"
                print("  E%-4d ← %s %s（%s）"
                      % (q["seq"], src, o["setId"] + "-" + str(o["no"]), kind))
                print("        %s" % q["q"][:58])

    print()
    print("【3】冊Eの図の使い回し")
    zfig = set()
    for q in zq:
        zfig.update(q["figures"])
    efig = set()
    for q in U["E"]:
        efig.update(q["figures"])
    share = sorted(efig & zfig)
    print("  冊Eが使う図 %d枚／うち図表編と共有 %d枚（新規 %d枚）"
          % (len(efig), len(share), len(efig) - len(share)))
    for dai in ("第1問 生活文化", "第2問 地域調査", "第3問 自然環境と自然災害",
                "第4問 資源・産業", "第5問 人口と都市", "第6問 地誌"):
        f = set()
        for q in U["E"]:
            if q["skill"] == dai:
                f.update(q["figures"])
        print("    %-18s 図%2d枚／うち共有%2d枚  %s"
              % (dai, len(f), len(f & zfig),
                 "・".join(sorted(x.split("/")[1] for x in f))))
    print("=" * 72)


main()
