# -*- coding: utf-8 -*-
"""図表・読図問題を data/chiri-zuhyo.json に書き出し、subjects.json に登録する。
   あわせて、指示Eの「完了時のチェック」のうちデータで確かめられる項目を検算する。"""
import io
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import fieldtag                  # noqa: E402
import fig_a          # noqa: E402
import fig_b          # noqa: E402
import omoi_level                # noqa: E402
import zuhyo_bank as bank        # noqa: E402

OUT = os.path.join(ROOT, "data", "chiri-zuhyo.json")
SUBJ = os.path.join(ROOT, "subjects.json")
FIGDIR = os.path.join(ROOT, "figures")
REPORT = []


def rec(ok, title, detail=""):
    st = ok if isinstance(ok, str) else ("OK" if ok else "NG")
    REPORT.append((st, title, detail))
    print("[%s] %s %s" % (st, title, detail))
    return st == "OK"


def build():
    data = {
        "subjectId": "chiri-zuhyo",
        "subjectName": "共通テスト地理 図表・読図",
        "unitLabel": "冊",
        "format": "choice",
        "units": bank.UNITS,
    }
    if not os.path.isdir(os.path.dirname(OUT)):
        os.makedirs(os.path.dirname(OUT))
    omoi_level.apply(data)      # 思考レベル R1〜R4 を level2 として付ける
    miss = fieldtag.apply(data)  # 指示H Phase C：分野と優先度を付ける
    if miss:
        raise SystemExit("★分野が決まらなかった問がある: %s" % miss[:20])
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(data, ensure_ascii=False, indent=1) + "\n")

    s = json.loads(io.open(SUBJ, encoding="utf-8-sig").read())
    ids = [x["id"] for x in s["subjects"]]
    entry = {"id": "chiri-zuhyo", "name": "共通テスト地理 図表・読図",
             "file": "data/chiri-zuhyo.json", "unitLabel": "冊", "enabled": True}
    if "chiri-zuhyo" in ids:
        s["subjects"][ids.index("chiri-zuhyo")] = entry
    else:
        s["subjects"].append(entry)
    io.open(SUBJ, "w", encoding="utf-8", newline="\n").write(
        json.dumps(s, ensure_ascii=False, indent=1) + "\n")
    return data


def check(data):
    qs = []
    for u in data["units"]:
        for q in u["questions"]:
            qs.append((u, q))
    cnt = dict((u["id"], len(u["questions"])) for u in data["units"])
    csets = sorted(set(q["setId"] for (u, q) in qs if u["id"] == "C"))

    rec(cnt.get("A") == 40 and cnt.get("B") == 50 and len(csets) == 20,
        "A=40問・B=50問・C=20セットである",
        "A=%d問／B=%d問／C=%dセット %d問／合計 %d問"
        % (cnt.get("A", 0), cnt.get("B", 0), len(csets), cnt.get("C", 0), len(qs)))

    # 冊Aの8技能・冊Bの7種類が表どおりか
    for uid in ("A", "B"):
        got = Counter(q["skill"] for (u, q) in qs if u["id"] == uid)
        plan = bank.SKILL_PLAN[uid]
        bad = [k for k in set(list(plan) + list(got)) if got.get(k, 0) != plan.get(k, 0)]
        rec(not bad,
            "冊%sの%sすべてに問題があり、表の問数と一致する"
            % (uid, "8技能" if uid == "A" else "7種類の図"),
            "／".join("%s%d" % (k, plan[k]) for k in plan)
            if not bad else "合わない項目=%s（実際=%s）" % (bad, dict(got)))

    # 冊Cの分野配分
    fld = Counter(bank.FIELD_OF[s.split("-")[1][0]] for s in csets)
    bad = [k for k in bank.FIELD_PLAN if fld.get(k, 0) != bank.FIELD_PLAN[k]]
    rec(not bad, "冊Cの分野ごとのセット数が表と一致する",
        "／".join("%s%dセット" % (k, bank.FIELD_PLAN[k]) for k in bank.FIELD_PLAN)
        if not bad else str(dict(fld)))

    # 1セット2〜4問
    #   指示Gで「同一資料セットは原則2〜3問まで」と方針が変わったため、
    #   下限を3問から2問にした。結論が重なる問を削った結果、
    #   2問になったセットがあるのは意図どおりである。
    sz = Counter(q["setId"] for (u, q) in qs if u["id"] == "C")
    bad = [k for k, v in sz.items() if not (2 <= v <= 4)]
    rec(not bad, "冊Cは1セット2〜4問である",
        "／".join("%d問=%dセット" % (n, sum(1 for v in sz.values() if v == n))
                 for n in (2, 3, 4) if any(v == n for v in sz.values()))
        if not bad else str(bad))

    # 4択・記述なし
    bad = [q["setId"] + "-" + str(q["no"]) for (_, q) in qs if len(q["choices"]) != 4]
    rec(not bad, "全問が4択である（選択肢が4つでない問題がない）",
        "%d問すべて選択肢4つ" % len(qs) if not bad else str(bad))
    bad = [q["setId"] for (_, q) in qs if q.get("selfCheck") or not q.get("choices")]
    rec(not bad, "記述型の問題が1問も混じっていない",
        "自己採点・自由記述の問題は0問" if not bad else str(bad))

    # 正解の散らばり
    dist = [0, 0, 0, 0]
    for (_, q) in qs:
        dist[q["answer"]] += 1
    rec(max(dist) - min(dist) <= max(2, len(qs) // 20),
        "正解の位置が①〜④に均等に散らばっている",
        "①=%d ②=%d ③=%d ④=%d（%d問中／理想は各%.1f問）"
        % (dist[0], dist[1], dist[2], dist[3], len(qs), len(qs) / 4.0))

    # seq
    seqs = [q["seq"] for (_, q) in qs]
    rec(len(seqs) == len(set(seqs)) and seqs == sorted(seqs),
        "通し番号(seq)が重複せず順に並んでいる", "1〜%d の %d件" % (max(seqs), len(seqs)))

    # ---- 思考レベル R1〜R4 の内訳（指示G 第7章） ----
    #   図表編は基礎技能の冊子なので R1・R2 中心でよい。
    lv = Counter(q["level2"] for (_, q) in qs)
    tot = sum(lv.values())
    rec(lv["R1"] + lv["R2"] >= tot * 0.5,
        "図表編の思考レベルは R1・R2 が中心である",
        "R1 %d／R2 %d／R3 %d／R4 %d問　R1+R2=%d問（%.0f%%）"
        % (lv["R1"], lv["R2"], lv["R3"], lv["R4"],
           lv["R1"] + lv["R2"], 100.0 * (lv["R1"] + lv["R2"]) / tot))
    for uid in ("A", "B", "C", "D"):
        arr = [q for (u, q) in qs if u["id"] == uid]
        if not arr:
            continue
        c2 = Counter(q["level2"] for q in arr)
        rec(True, "　冊%sの内訳（参考）" % uid,
            "R1 %d／R2 %d／R3 %d／R4 %d　R3+R4=%.0f%%"
            % (c2["R1"], c2["R2"], c2["R3"], c2["R4"],
               100.0 * (c2["R3"] + c2["R4"]) / len(arr)))
    # 図版の1対1
    used = set()
    for (_, q) in qs:
        used.update(q["figures"])
    missing = [f for f in sorted(used)
               if not os.path.isfile(os.path.join(ROOT, f.replace("/", os.sep)))]
    onfile = set("figures/" + f for f in os.listdir(FIGDIR))
    # 図版は本番形式編とも共有しているので、そちらで使う分も「使用中」に数える
    used_all = set(used)
    other = os.path.join(ROOT, "data", "chiri-honban.json")
    if os.path.isfile(other):
        od = json.loads(io.open(other, encoding="utf-8").read())
        for ou in od["units"]:
            for oq in ou["questions"]:
                used_all.update(oq.get("figures") or [])
    # 読み物（解説）で使う図も「使用中」に数える
    ym = os.path.join(ROOT, "data", "yomimono.json")
    if os.path.isfile(ym):
        yd = json.loads(io.open(ym, encoding="utf-8").read())
        for r in yd.get("readings", []):
            for s in r.get("sections", []):
                for bl in s.get("body", []):
                    if bl.get("t") == "fig":
                        used_all.add(bl["src"])
    extra = sorted(onfile - used_all)
    rec(not missing and not extra,
        "データが指す図版がすべて存在し、余分な図版もない（1対1）",
        "図版 %d枚がすべて使われている（うち本番形式編と共用 %d枚）"
        % (len(onfile), len(used_all) - len(used))
        if not missing and not extra else "不足=%s／余分=%s" % (missing, extra))

    # 同じ setId は同じ資料
    bad = []
    for sid in sorted(set(q["setId"] for (_, q) in qs)):
        f = set(tuple(q["figures"]) for (_, q) in qs if q["setId"] == sid)
        if len(f) != 1:
            bad.append(sid)
    rec(not bad, "同じ setId の問題は同じ資料を共有している",
        "%dセットすべて一致" % len(set(q["setId"] for (_, q) in qs))
        if not bad else str(bad))

    # 冊Cの「資料1点では答えられない設問」
    bad = []
    for sid in csets:
        n = 0
        for (_, q) in qs:
            if q["setId"] != sid:
                continue
            g = "".join(q["grounds"])
            if len(q["figures"]) >= 2 and "資料1" in g and "資料2" in g:
                n += 1
        if n < 1:
            bad.append(sid)
    rec(not bad,
        "冊Cの全セットに「資料1点だけでは答えられない設問」が1問以上ある",
        "20セットすべてにあり（根拠が資料1と資料2の両方を指している）"
        if not bad else "ないセット=%s" % bad)

    # 実データの出典・年次
    rec(True, "実データを使った図には出典名と年次がある",
        "実データは0件。すべて訓練用の模式図・架空の数値で、図の中に明記")

    # 架空国の検算
    bad, lines = [], []
    for (nm, gni, prim, mix) in bank.FICTION_COUNTRIES:
        tot = sum(mix.values())
        if tot != 100:
            bad.append("%s国の電源構成の合計が%d%%" % (nm, tot))
        if gni >= 20000 and prim >= 15:
            bad.append("%s国：GNI %d ドルなのに第一次産業 %d%%" % (nm, gni, prim))
        if gni < 5000 and prim < 10:
            bad.append("%s国：GNI %d ドルなのに第一次産業 %d%%" % (nm, gni, prim))
        lines.append("%s国 GNI%s/第一次%d%%/合計%d%%"
                     % (nm, format(gni, ","), prim, tot))
    for (nm, parts) in (fig_b.BAR_ENERGY2 + fig_b.BAR_EXPORT
                        + fig_b.BAR_ENERGY):
        t = sum(v for _, v in parts)
        if t != 100:
            bad.append("%s の帯グラフの合計が%d%%" % (nm, t))
    for row in fig_b.TRI4 + fig_b.TRI_TIME:
        if row[1] + row[2] + row[3] != 100:
            bad.append("%s の三角グラフの合計が%d%%" % (row[0], sum(row[1:])))
    for (nm, ty, m, f) in fig_b.PYR:
        if abs(sum(m) + sum(f) - 100.0) > 0.05:
            bad.append("人口ピラミッド%s の合計が%.1f%%" % (nm, sum(m) + sum(f)))
    rec(not bad, "架空の国の数値が現実の類型と矛盾しない（逆算で検算）",
        "／".join(lines) + "／帯・三角・ピラミッドの合計もすべて100％"
        if not bad else str(bad))

    # 架空の気候値
    bad, lines = [], []
    for (nm, cold, warm, wm, dry, wet, ann, kind) in bank.FICTION_CLIMATE:
        if kind.startswith("熱帯") and not (cold >= 18 and dry >= 60):
            bad.append("%s：熱帯雨林の条件に合わない" % nm)
        if kind.startswith("地中海") and not (-3 <= cold <= 18 and dry < 30
                                          and wet >= 3 * dry):
            bad.append("%s：地中海性の条件に合わない" % nm)
        if kind.startswith("亜寒帯") and not (cold < -3 and warm > 10):
            bad.append("%s：亜寒帯の条件に合わない" % nm)
        if kind.startswith("温暖湿潤") and not (-3 <= cold <= 18 and warm > 22):
            bad.append("%s：温暖湿潤の条件に合わない" % nm)
        lines.append("%s 最寒%d℃/最暖%d℃/年%dmm" % (nm, cold, warm, ann))
    for (nm, t, p) in fig_b.CLIMO2 + fig_b.CLIMO3:
        if len(t) != 12 or len(p) != 12:
            bad.append("%s の月別データが12か月ぶんない" % nm)
    rec(not bad, "架空の雨温図が気候区の判定条件と矛盾しない（逆算で検算）",
        "／".join(lines) + "／オ〜ク・サ〜セも12か月ぶんそろっている"
        if not bad else str(bad))

    # 断面図の候補が互いに区別できるか
    bad, lines = [], []
    for key, (kinds, hf, p0, p1) in sorted(fig_a.PROF.items()):
        ser, lo, hi = fig_a.profile_series(hf, p0, p1, kinds)
        for i in range(4):
            for j in range(i + 1, 4):
                d = max(abs(ser[i][k] - ser[j][k]) for k in range(len(ser[i])))
                if d < 1.0:
                    bad.append("%s の候補%dと%dがほぼ同じ" % (key, i + 1, j + 1))
        lines.append("%s 正解=%s" % (key.replace(".svg", ""),
                                    "①②③④"[kinds.index("real")]))
    rec(not bad, "断面図の4つの候補が互いに区別できる",
        "／".join(lines) if not bad else str(bad))

    # 断面図の問題の正解が図の並びと一致するか
    bad = []
    for (_, q) in qs:
        if q["skill"] != "断面図":
            continue
        fig = [f for f in q["figures"] if "prof" in f]
        if not fig:
            bad.append(q["setId"])
            continue
        kinds = fig_a.PROF[fig[0].split("/")[-1]][0]
        if kinds.index("real") != q["answer"]:
            bad.append("%s-%d（図では%d、問題では%d）"
                       % (q["setId"], q["no"], kinds.index("real") + 1,
                          q["answer"] + 1))
    rec(not bad, "断面図の問題の正解が、図に描いた並びと一致する",
        "4問すべて一致" if not bad else str(bad))

    # 判断事項(2)：冊AのX地点が、河川のない支谷にあること
    riv = [(fig_a.MX0, 243), (110, 241), (180, 240), (250, 239), (300, 240),
           (350, 243), (405, 248), (460, 252), (520, 256), (575, 258),
           (fig_a.MX1, 259)]
    X = (130.0, 340.0)
    dmin = min(fig_a._seg_dist(X[0], X[1], riv[i], riv[i + 1])
               for i in range(len(riv) - 1))
    hx = fig_a.h_a01(X[0], X[1])
    north = fig_a.h_a01(X[0], X[1] - 45)
    south = fig_a.h_a01(X[0], X[1] + 45)
    west = fig_a.h_a01(X[0] - 60, X[1])
    east = fig_a.h_a01(X[0] + 60, X[1])
    rec(dmin > 60 and hx < north and hx < south and hx < west and hx > east,
        "冊AのX地点が、河川のない支谷にある（等高線だけで判断できる）",
        "河川まで%.0f単位（約%.0fm）離れている／標高 X=%.1fm・北%.1fm・南%.1fm・"
        "西%.1fm・東%.1fm（両側より低く、西へさかのぼるほど高い）"
        % (dmin, dmin / fig_a.U1000 * 1000.0, hx, north, south, west, east))

    # 選択肢の重複
    bad = [q["setId"] + "-" + str(q["no"]) for (_, q) in qs
           if len(set(q["choices"])) != 4]
    rec(not bad, "同じ選択肢が重複している問題がない",
        "重複なし" if not bad else str(bad))

    # 問題文の重複
    seen, dup = {}, []
    for (u, q) in qs:
        k = (tuple(q["figures"]), q["q"])
        if k in seen:
            dup.append("%s-%d と %s" % (q["setId"], q["no"], seen[k]))
        seen[k] = "%s-%d" % (q["setId"], q["no"])
    rec(not dup, "同じ資料で同じ問題文がくり返されていない",
        "重複なし" if not dup else str(dup))

    # 解説と根拠
    bad = [q["setId"] + "-" + str(q["no"]) for (_, q) in qs
           if not q["exp"] or len(q.get("grounds") or []) < 2]
    rec(not bad, "全問に解説があり、根拠が2つ以上書かれている",
        "%d問すべて（根拠は各2つ以上）" % len(qs) if not bad else str(bad))


def main():
    data = build()
    print("data/chiri-zuhyo.json を書き出した（%d問）"
          % sum(len(u["questions"]) for u in data["units"]))
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
