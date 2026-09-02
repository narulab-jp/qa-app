# -*- coding: utf-8 -*-
"""統合CSV → data/chiri.json を生成する。

使い方（QA_APP フォルダで実行）:
    python tools\\csv2json.py

CSV を直したときは、このスクリプトを再実行するだけで JSON が更新される。
問題文・解答・解説は一切書き換えず、CSV の内容をそのまま入れる。
"""
import csv
import json
import os
import re
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

HOME = os.path.expanduser("~")
CSVNAME = "地理一問一答_全講統合.csv"
# 統合CSVの置き場所（先に見つかった方を使う）
SRC = os.path.join(HOME, "Downloads", "CHIRI_QA_20260901", "CSV", CSVNAME)
ALT = os.path.join(HOME, "OneDrive", "デスクトップ", "CHIRI_QA_20260901", "CSV", CSVNAME)
OUT = os.path.join(ROOT, "data", "chiri.json")

SUBJECT_ID = "chiri"
SUBJECT_NAME = "共通テスト地理"
UNIT_LABEL = "講"          # 表示上の呼び名。英語なら "Lesson"、古文なら "章" に変える
SOURCE = "一問一答 全28講828問"

SELF_CHECK_LEN = 40        # 識別型でこの字数を超える解答は自己採点にする

# --------------------------------------------------------------------------
# 読みの辞書（音声認識がひらがなで返した場合に拾うための許容解答）
#   キー = CSVの解答文字列そのもの／値 = 読みの候補
#   足したいときはここに1行追加して csv2json.py を再実行するだけでよい。
#   ここに無い解答でも、漢字表記での照合と部分一致は働く。
# --------------------------------------------------------------------------
YOMI = {
    "緯度": ["いど"],
    "グリニッジ天文台": ["ぐりにっじてんもんだい"],
    "標準時子午線／東経135度": ["ひょうじゅんじしごせん", "とうけい135ど"],
    "大圏航路（大圏コース）": ["たいけんこうろ", "たいけんこーす"],
    "メルカトル図法": ["めるかとるずほう"],
    "正距方位図法": ["せいきょほういずほう"],
    "グード図法（ホモロサイン図法）": ["ぐーどずほう", "ほもろさいんずほう"],
    "正積図法": ["せいせきずほう"],
    "GIS（地理情報システム）": ["じーあいえす", "ちりじょうほうしすてむ"],
    "GNSS（全球測位衛星システム）／GPS":
        ["じーえぬえすえす", "ぜんきゅうそくいえいせいしすてむ", "じーぴーえす"],
    "リモートセンシング": ["りもーとせんしんぐ"],
    "メッシュマップ（メッシュ地図）": ["めっしゅまっぷ", "めっしゅちず"],
    "文献調査（室内調査）": ["ぶんけんちょうさ", "しつないちょうさ"],
    "野外調査（フィールドワーク）": ["やがいちょうさ", "ふぃーるどわーく"],
    "地理院地図": ["ちりいんちず"],
}


def expand(ans):
    """解答から別名を機械的に展開する（／での分割、括弧内の別名）。"""
    out = []
    for part in ans.split("／"):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(.+?)（(.+?)）$", part)
        if m:
            out.append(m.group(1))
            for alt in re.split(r"[・、]", m.group(2)):
                alt = alt.strip()
                if alt:
                    out.append(alt)
        else:
            out.append(re.sub(r"[（）]", "", part))
    return out


def build_accept(typ, ans, self_check):
    """accept は用語型・識別型のみに付ける。理由型には付けない。"""
    if typ not in ("用語", "識別"):
        return None
    if self_check:
        return []          # 自己採点の問では照合に使わない
    acc = [x for x in expand(ans) if x != ans] + YOMI.get(ans, [])
    seen, uniq = set(), []
    for x in acc:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def main():
    src = SRC if os.path.exists(SRC) else ALT
    if not os.path.exists(src):
        print("★CSVが見つかりません: %s" % SRC)
        return 1
    with open(src, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    head, body = rows[0], rows[1:]
    need = ["講番号", "講名", "節番号", "問番号", "通し番号", "重要度",
            "出題タイプ", "問題文", "解答", "解説"]
    if head != need:
        print("★CSVの列が想定と違います: %s" % head)
        return 1

    units, order = {}, []
    for r in body:
        uid, uname = r[0], r[1]
        if uid not in units:
            units[uid] = {"id": uid, "name": uname, "questions": []}
            order.append(uid)
        typ, ans = r[6], r[8]
        self_check = (typ == "理由") or (typ == "識別" and len(ans) > SELF_CHECK_LEN)
        q = {"no": int(r[3]), "seq": int(r[4]), "section": r[2],
             "level": r[5], "type": typ, "q": r[7], "a": ans, "exp": r[9],
             "selfCheck": self_check}
        acc = build_accept(typ, ans, self_check)
        if acc is not None:
            q["accept"] = acc
        units[uid]["questions"].append(q)

    doc = {
        "subjectId": SUBJECT_ID,
        "subjectName": SUBJECT_NAME,
        "unitLabel": UNIT_LABEL,
        "source": SOURCE,
        "updated": datetime.date.today().isoformat(),
        "units": [units[u] for u in order],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    total = sum(len(u["questions"]) for u in doc["units"])
    print("入力: %s" % src)
    print("出力: %s" % OUT)
    print("単元 %d／問題 %d問" % (len(doc["units"]), total))
    ns = sum(1 for u in doc["units"] for q in u["questions"] if q["selfCheck"])
    print("  自己採点 %d問／自動判定 %d問" % (ns, total - ns))
    for u in doc["units"]:
        print("  %s %s %d問" % (u["id"], u["name"], len(u["questions"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

