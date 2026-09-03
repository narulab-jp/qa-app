# -*- coding: utf-8 -*-
"""本番形式編（冊D 組合せ形式48問／冊E 通し演習30マーク）を
   data/chiri-honban.json に書き出し、subjects.json に登録する。
   あわせて、作りの正しさを機械的に検算する。"""
import io
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import fieldtag          # noqa: E402
import honban_d          # noqa: E402
import omoi_level        # noqa: E402
import honban_e          # noqa: E402
import honban_f          # noqa: E402
import honban_g          # noqa: E402

OUT = os.path.join(ROOT, "data", "chiri-honban.json")
SUBJ = os.path.join(ROOT, "subjects.json")
FIGDIR = os.path.join(ROOT, "figures")
REPORT = []
# 本番の形式に照らした目安（Phase 1 で本試験2年分から実測した値）
HONBAN_KUMI_2026 = 22          # 30マーク中


def rec(ok, title, detail=""):
    st = ok if isinstance(ok, str) else ("OK" if ok else "NG")
    REPORT.append((st, title, detail))
    print("[%s] %s %s" % (st, title, detail))
    return st == "OK"


def build():
    data = {
        "subjectId": "chiri-honban",
        "subjectName": "共通テスト地理 本番形式",
        "unitLabel": "冊",
        "format": "choice",
        "units": [
            {"id": "D", "name": "組合せ形式", "questions": honban_d.QUESTIONS},
            {"id": "E", "name": "通し演習 第1回（60分）",
             "questions": honban_e.QUESTIONS},
            {"id": "F", "name": "残りの技能・形式",
             "questions": honban_f.QUESTIONS},
            {"id": "G", "name": "地域調査",
             "questions": honban_g.QUESTIONS},
        ],
    }
    omoi_level.apply(data)      # 思考レベル R1〜R4 を level2 として付ける
    miss = fieldtag.apply(data)  # 指示H Phase C：分野と優先度を付ける
    if miss:
        raise SystemExit("★分野が決まらなかった問がある: %s" % miss[:20])
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    s = json.loads(io.open(SUBJ, encoding="utf-8-sig").read())
    ids = [x["id"] for x in s["subjects"]]
    entry = {"id": "chiri-honban", "name": "共通テスト地理 本番形式",
             "file": "data/chiri-honban.json", "unitLabel": "冊",
             "enabled": True}
    if "chiri-honban" in ids:
        s["subjects"][ids.index("chiri-honban")] = entry
    else:
        s["subjects"].append(entry)
    io.open(SUBJ, "w", encoding="utf-8", newline="\n").write(
        json.dumps(s, ensure_ascii=False, indent=1) + "\n")
    return data


def is_kumi(q):
    """組合せ形式か（選択肢が「〜＝〜」を2つ以上含む）"""
    return q["choices"][0].count("=") >= 2


def check(data):
    qs = [(u, q) for u in data["units"] for q in u["questions"]]
    d = [q for (u, q) in qs if u["id"] == "D"]
    e = [q for (u, q) in qs if u["id"] == "E"]
    fq = [q for (u, q) in qs if u["id"] == "F"]
    gq = [q for (u, q) in qs if u["id"] == "G"]

    rec(len(d) == 48 and len(e) == 30 and len(fq) == 13 and len(gq) == 12,
        "冊D=48問・冊E=30マーク・冊F=13問・冊G=12問である",
        "冊D %d問／冊E %dマーク／冊F %d問／冊G %d問／合計 %d問"
        % (len(d), len(e), len(fq), len(gq), len(qs)))

    # 冊D：3つの型がそろっているか
    t = Counter(q["skill"][:3] for q in d)
    rec(len(t) == 3 and min(t.values()) >= 14,
        "冊Dに本番の3つの型がそろっている",
        "／".join("%s…%d問" % (k, v) for k, v in sorted(t.items())))

    # 冊E：本番と同じ大問構成・マーク数
    plan = [("第1問 生活文化", 4), ("第2問 地域調査", 4),
            ("第3問 自然環境と自然災害", 6), ("第4問 資源・産業", 5),
            ("第5問 人口と都市", 6), ("第6問 地誌", 5)]
    got = Counter(q["skill"] for q in e)
    bad = [k for (k, n) in plan if got.get(k, 0) != n]
    rec(not bad, "冊Eの大問構成とマーク数が本番と同じ",
        "／".join("%s %dマーク" % (k, n) for (k, n) in plan)
        if not bad else str(bad))

    # 冊E：配点が100点になるか
    pt = sum(q["haiten"] for q in e)
    dai = {}
    for q in e:
        dai[q["skill"]] = dai.get(q["skill"], 0) + q["haiten"]
    rec(pt == 100 and dai["第1問 生活文化"] == 13 and dai["第3問 自然環境と自然災害"] == 21,
        "冊Eの配点が本番と同じ（合計100点）",
        "／".join("%s%d点" % (k[:4], v) for k, v in dai.items()))

    # 組合せ形式の割合が本番に近いか
    nk = sum(1 for q in e if is_kumi(q))
    rec(abs(nk - HONBAN_KUMI_2026) <= 3,
        "冊Eの組合せ形式の割合が本番に近い",
        "冊E %dマーク（本番2026年度は%dマーク）" % (nk, HONBAN_KUMI_2026))
    nkd = sum(1 for q in d if is_kumi(q))
    rec(nkd + sum(1 for q in d if "＝" in q["choices"][0]
                  or "正" in q["choices"][0]) >= 48,
        "冊Dは全問が組合せ形式である",
        "対応型・2軸型・正誤の組合せ型のみで48問")

    # 択数と正解の位置
    for (nm, arr) in (("冊D", d), ("冊E", e), ("冊F", fq), ("冊G", gq)):
        cnt = Counter(len(q["choices"]) for q in arr)
        rec(min(cnt) >= 4 and max(cnt) <= 9,
            "%sの択数が4〜9におさまっている" % nm,
            "／".join("%d択 %d問" % (k, v) for k, v in sorted(cnt.items())))
    for n in (4, 6, 8):
        sub = [q for q in d if len(q["choices"]) == n]
        if not sub:
            continue
        c = Counter(q["answer"] for q in sub)
        rec(max(c.values()) - min(c.values()) <= 1 and len(c) == n,
            "冊Dの%d択で正解の位置が均等に散っている" % n,
            "／".join("%d番目 %d問" % (k + 1, v) for k, v in sorted(c.items())))
    # 3文の正誤は8通りすべてを使う
    s3 = [q for q in d if len(q["choices"]) == 8]
    rec(len(set(q["answer"] for q in s3)) == 8,
        "冊Dの3文正誤は8通りの正誤パターンをすべて使っている",
        "%d問で%d通り" % (len(s3), len(set(q["answer"] for q in s3))))

    # 図版
    used = set()
    for (_, q) in qs:
        used.update(q["figures"])
    missing = [f for f in sorted(used)
               if not os.path.isfile(os.path.join(ROOT, f.replace("/", os.sep)))]
    rec(not missing, "使う図版がすべて存在する",
        "%d枚（うち図表編からの再利用が%d枚）"
        % (len(used), len([f for f in used if "E2_talk" not in f]))
        if not missing else str(missing))

    # 選択肢の重複・根拠
    bad = [q["setId"] + "-" + str(q["no"]) for (_, q) in qs
           if len(set(q["choices"])) != len(q["choices"])]
    rec(not bad, "同じ選択肢が重複している問題がない", "重複なし")
    bad = [q["setId"] + "-" + str(q["no"]) for (_, q) in qs
           if not q["exp"] or len(q["grounds"]) < 2]
    rec(not bad, "全問に解説があり、根拠が2つ以上ある", "%d問すべて" % len(qs))

    # 日本語以外の文字の混入
    pat = re.compile(r"[Ѐ-ӿ؀-ۿ]")
    bad = []
    for (_, q) in qs:
        blob = " ".join([q["q"], q["exp"]] + q["choices"] + q["grounds"])
        if pat.search(blob):
            bad.append(q["setId"] + "-" + str(q["no"]))
    rec(not bad, "問題文・選択肢・解説に日本語以外の文字が混じっていない",
        "%d問すべて確認" % len(qs) if not bad else str(bad))

    # ---- 正解の位置が規則的に並んでいないか ----
    #   ①②③…と順に並ぶと、問題を読まずに当てられてしまう。
    seq_d = [q["answer"] for q in d]
    adj = sum(1 for i in range(1, len(seq_d))
              if abs(seq_d[i] - seq_d[i - 1]) == 1)
    up, cur = 1, 1
    for i in range(1, len(seq_d)):
        if seq_d[i] - seq_d[i - 1] == 1:
            cur += 1
            up = max(up, cur)
        else:
            cur = 1
    rate = 100.0 * adj / (len(seq_d) - 1)
    rec(rate <= 30.0 and up <= 3,
        "冊Dの正解が、隣の問と続き番号で並んでいない",
        "隣り合う問で正解が±1になる割合 %d/%d＝%.0f%%／"
        "1ずつ上がり続ける最長 %d問" % (adj, len(seq_d) - 1, rate, up))

    # ---- 冊Eの図が図表編と共有していないか ----
    #   通し演習は初見の資料を読む訓練なので、見慣れた図では意味がない。
    zdoc = json.loads(io.open(os.path.join(ROOT, "data", "chiri-zuhyo.json"),
                              encoding="utf-8").read())
    zfig = set()
    for u in zdoc["units"]:
        for q in u["questions"]:
            zfig.update(q["figures"])
    efig = set()
    for q in e:
        efig.update(q["figures"])
    share = sorted(efig & zfig)
    dai_share = []
    for dai in ("第1問 生活文化", "第2問 地域調査", "第6問 地誌"):
        f = set()
        for q in e:
            if q["skill"] == dai:
                f.update(q["figures"])
        if f & zfig:
            dai_share.append(dai)
    rec(not dai_share,
        "冊Eの第1問・第2問・第6問は、図表編と図を共有していない",
        "冊Eの図 %d枚／うち図表編と共有 %d枚（新規 %d枚）"
        % (len(efig), len(share), len(efig) - len(share))
        if not dai_share else "共有が残っている大問=" + str(dai_share))

    # ---- 冊Eに既出の問がまじっていないか ----
    others = [q for u in zdoc["units"] for q in u["questions"]] + d + fq
    dup = []
    for q in e:
        for o in others:
            if q["q"] == o["q"] and sorted(q["choices"]) == sorted(o["choices"]):
                dup.append("E%d←%s-%d" % (q["seq"], o["setId"], o["no"]))
    rec(not dup, "冊Eに、ほかの冊子と同じ問がまじっていない",
        "30マークすべて新作" if not dup else str(dup))

    # ---- 資料の中に答えを書いていないか ----
    #   図に「〜だから〜である」と書いてしまうと、読図の問題にならない。
    #   冊E専用の図（G…）について、判断を述べる言い回しがないかを見る。
    NG_WORDS = ["ため、", "ためである", "だから", "ので、", "から、",
                "といえる", "と考えられる", "ことがわかる", "が課題",
                "に適して", "を意味する"]
    bad = []
    for name in sorted(os.listdir(FIGDIR)):
        if not (name.startswith("G") or name.startswith("H")):
            continue
        body = io.open(os.path.join(FIGDIR, name), encoding="utf-8").read()
        txt = " ".join(re.findall(r">([^<>]+)</text>", body))
        for wnd in NG_WORDS:
            if wnd in txt:
                bad.append("%s に「%s」" % (name, wnd))
    rec(not bad, "冊E・冊G専用の資料に、答えや理由を文章で書いていない",
        "%d枚すべて、数値・記号・位置だけを示している"
        % len([n for n in os.listdir(FIGDIR)
               if n.startswith("G") or n.startswith("H")])
        if not bad else str(bad[:5]))

    # ---- 思考レベル R1〜R4 の内訳（指示G 第7章） ----
    #   目標は R3・R4 が6割以上。届かないときは、届かないと出す。
    lv = Counter(q["level2"] for (_, q) in qs)
    hi = lv["R3"] + lv["R4"]
    rec("OK" if hi >= len(qs) * 0.6 else "要確認",
        "本番形式編の思考レベル（R3・R4が6割以上か）",
        "R1 %d／R2 %d／R3 %d／R4 %d問　R3+R4=%d問（%.0f%%）"
        % (lv["R1"], lv["R2"], lv["R3"], lv["R4"], hi,
           100.0 * hi / len(qs)))
    for (nm, arr) in (("冊D", d), ("冊E", e), ("冊F", fq), ("冊G", gq)):
        c2 = Counter(q["level2"] for q in arr)
        h2 = c2["R3"] + c2["R4"]
        rec(True, "　%sの内訳（参考）" % nm,
            "R1 %d／R2 %d／R3 %d／R4 %d　R3+R4=%.0f%%"
            % (c2["R1"], c2["R2"], c2["R3"], c2["R4"],
               100.0 * h2 / len(arr)))
    # 通し番号
    seqs = [q["seq"] for (_, q) in qs]
    rec(len(seqs) == len(set(seqs)), "通し番号が重複していない",
        "冊D 1〜%d／冊E 101〜%d／冊F 201〜%d"
        % (max(q["seq"] for q in d), max(q["seq"] for q in e),
           max(q["seq"] for q in fq)))


def main():
    data = build()
    n = sum(len(u["questions"]) for u in data["units"])
    print("data/chiri-honban.json を書き出した（%d問）" % n)
    print("-" * 68)
    check(data)
    ng = [r for r in REPORT if r[0] == "NG"]
    print("-" * 68)
    print("データの検算: %s（OK %d / NG %d）"
          % ("NGなし" if not ng else "★NG あり",
             len([r for r in REPORT if r[0] == "OK"]), len(ng)))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
