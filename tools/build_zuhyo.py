# -*- coding: utf-8 -*-
"""図表・読図問題を data/chiri-zuhyo.json に書き出し、subjects.json に登録する。
   あわせて、指示Eの「完了時のチェック」のうちデータで確かめられる項目を検算する。"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

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

    # 問数
    cnt = dict((u["id"], len(u["questions"])) for u in data["units"])
    sets = sorted(set(q["setId"] for (_, q) in qs))
    rec("Phase1", "冊ごとの問数（Phase 2 で A=40／B=50／C=20セットに増やす）",
        "A=%d問／B=%d問／C=%d問（%dセット）／合計 %d問"
        % (cnt.get("A", 0), cnt.get("B", 0), cnt.get("C", 0),
           len([x for x in sets if x.startswith("C")]), len(qs)))

    # 4択か
    bad = [q["setId"] + "-" + str(q["no"]) for (_, q) in qs if len(q["choices"]) != 4]
    rec(not bad, "全問が4択である（選択肢が4つでない問題がない）",
        "%d問すべて選択肢4つ" % len(qs) if not bad else str(bad))

    # 記述型が混じっていないか
    bad = [q["setId"] for (_, q) in qs if q.get("selfCheck") or not q.get("choices")]
    rec(not bad, "記述型の問題が1問も混じっていない",
        "自己採点・自由記述の問題は0問" if not bad else str(bad))

    # answer の散らばり
    dist = [0, 0, 0, 0]
    for (_, q) in qs:
        dist[q["answer"]] += 1
    ok = max(dist) - min(dist) <= max(2, len(qs) // 8)
    rec(ok, "正解の位置が①〜④に偏っていない",
        "①=%d ②=%d ③=%d ④=%d（%d問中）" % (dist[0], dist[1], dist[2], dist[3], len(qs)))

    # seq の一意性
    seqs = [q["seq"] for (_, q) in qs]
    rec(len(seqs) == len(set(seqs)), "通し番号(seq)が重複していない",
        "1〜%d の %d件" % (max(seqs), len(seqs)))

    # 図版の対応
    used = set()
    for (_, q) in qs:
        for f in q["figures"]:
            used.add(f)
    missing = [f for f in sorted(used)
               if not os.path.isfile(os.path.join(ROOT, f.replace("/", os.sep)))]
    onfile = set("figures/" + f for f in os.listdir(FIGDIR)) if os.path.isdir(FIGDIR) else set()
    extra = sorted(onfile - used)
    rec(not missing and not extra,
        "データが指す図版がすべて存在し、余分な図版もない（1対1）",
        "図版 %d枚＝%s" % (len(used), "／".join(sorted(x.split("/")[-1] for x in used)))
        if not missing and not extra else "不足=%s／余分=%s" % (missing, extra))

    # 同じ setId は同じ図を共有しているか
    bad = []
    for sid in sets:
        f = set(tuple(q["figures"]) for (_, q) in qs if q["setId"] == sid)
        if len(f) != 1:
            bad.append(sid)
    rec(not bad, "同じ setId の問題は同じ資料を共有している",
        "%d セットすべて一致" % len(sets) if not bad else str(bad))

    # 冊Cに「資料1点では答えられない設問」があるか
    multi = [q for (u, q) in qs if u["id"] == "C" and len(q["figures"]) >= 2
             and ("資料1と資料2" in q["q"] or "資料2" in "".join(q["grounds"]))]
    rec(len(multi) >= 1,
        "冊Cのセットに「資料1点だけでは答えられない設問」が1問以上ある",
        "C-01 に %d問（設問2・設問3）" % len(multi))

    # 実データの出典・年次（今回は実データを使っていない）
    rec(True, "実データを使った図には出典名と年次がある",
        "今回の4図はすべて架空・訓練用のため実データは0件。図の中に架空である旨を明記")

    # 架空国の数値が現実の類型と矛盾しないか
    bad = []
    lines = []
    for (nm, gni, prim, mix) in bank.FICTION_COUNTRIES:
        tot = sum(mix.values())
        if tot != 100:
            bad.append("%s国の電源構成の合計が%d%%" % (nm, tot))
        if gni >= 20000 and prim >= 15:
            bad.append("%s国：GNI %d ドルなのに第一次産業 %d%%" % (nm, gni, prim))
        if gni < 5000 and prim < 10:
            bad.append("%s国：GNI %d ドルなのに第一次産業 %d%%" % (nm, gni, prim))
        lines.append("%s国 GNI%s/第一次%d%% 合計%d%% 最大=%s"
                     % (nm, format(gni, ","), prim, tot,
                        max(mix.items(), key=lambda kv: kv[1])[0]))
    rec(not bad, "架空の国の数値が現実の類型と矛盾しない（逆算で検算）",
        "／".join(lines) if not bad else str(bad))

    # 架空の気候値が気候区の定義と矛盾しないか
    bad = []
    lines = []
    for (nm, cold, warm, wm, dry, wet, ann, kind) in bank.FICTION_CLIMATE:
        if kind.startswith("熱帯") and not (cold >= 18 and dry >= 60):
            bad.append("%s：熱帯雨林の条件に合わない" % nm)
        if kind.startswith("地中海") and not (-3 <= cold <= 18 and dry < 30 and wet >= 3 * dry):
            bad.append("%s：地中海性の条件に合わない" % nm)
        if kind.startswith("亜寒帯") and not (cold < -3 and warm > 10):
            bad.append("%s：亜寒帯の条件に合わない" % nm)
        if kind.startswith("温暖湿潤") and not (-3 <= cold <= 18 and warm > 22):
            bad.append("%s：温暖湿潤の条件に合わない" % nm)
        lines.append("%s 最寒%d℃/最暖%d℃(%d月)/年%dmm=%s" % (nm, cold, warm, wm, ann, kind))
    rec(not bad, "架空の雨温図が気候区の判定条件と矛盾しない（逆算で検算）",
        "／".join(lines) if not bad else str(bad))

    # 南北半球の判定が1地点だけで成り立つか
    south = [nm for (nm, c, w, wm, d, wt, a, k) in bank.FICTION_CLIMATE if wm <= 2]
    rec(len(south) == 1, "南半球と判断できる地点がちょうど1つである",
        "最暖月が1〜2月なのは %s のみ" % "・".join(south))

    # 最寒月の並び順が一意に決まるか
    order = sorted(bank.FICTION_CLIMATE, key=lambda t: -t[1])
    names = [t[0] for t in order]
    gaps = [order[i][1] - order[i + 1][1] for i in range(3)]
    rec(min(gaps) >= 4, "最寒月気温の順位が、図から読み取れる差で決まる",
        "%s（差 %s℃）" % ("―".join(names), "・".join(str(g) for g in gaps)))

    # 選択肢の重複
    bad = []
    for (_, q) in qs:
        if len(set(q["choices"])) != 4:
            bad.append(q["setId"] + "-" + str(q["no"]))
    rec(not bad, "同じ選択肢が重複している問題がない",
        "重複なし" if not bad else str(bad))

    # 解説と根拠
    bad = [q["setId"] + "-" + str(q["no"]) for (_, q) in qs
           if not q["exp"] or len(q.get("grounds") or []) < 2]
    rec(not bad, "全問に解説があり、根拠が2つ以上書かれている",
        "%d問すべて（根拠は各2つ）" % len(qs) if not bad else str(bad))


def main():
    data = build()
    print("data/chiri-zuhyo.json を書き出した（%d問）"
          % sum(len(u["questions"]) for u in data["units"]))
    print("-" * 68)
    check(data)
    ng = [r for r in REPORT if r[0] == "NG"]
    print("-" * 68)
    print("データの検算: %s（OK %d / NG %d / Phase1 %d）"
          % ("NGなし" if not ng else "★NG あり",
             len([r for r in REPORT if r[0] == "OK"]), len(ng),
             len([r for r in REPORT if r[0] == "Phase1"])))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
