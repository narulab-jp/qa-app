# -*- coding: utf-8 -*-
"""指示G 第7章：思考レベル（R1〜R4）を機械的に決める。

  R1 … 資料だけで解ける（基本読取）
  R2 … 資料＋基礎知識
  R3 … 複数資料の統合
  R4 … 資料＋知識＋因果推論

  推測でつけない。次の4つを問ごとに測り、その組合せで決める。

    figs   与えられている資料の枚数
    refs   解説と根拠が実際に指している資料の数（「資料1」「資料2」…）
           資料が2枚あっても片方しか指していなければ、統合はしていない
    reason 因果や推論を問うているか
           （問題文に 理由／なぜ／言えない／読み取れない／判断できない、
             または正解が「〜ため」「〜から」で終わる）
    know   資料に書かれていない地理用語が、正解や解説に必要か
           （一問一答851問の用語型の解答を、地理用語の辞書として使う）

  決め方
    figs>=2 かつ refs>=2 かつ reason      → R4
    figs>=2 かつ refs>=2 かつ not reason  → R3
    それ以外で reason または know          → R2
    それ以外                               → R1

  ※ 資料が2枚あっても解説が片方しか指していない問は R3 にしない。
    「複数資料問題を作ったつもりが単純読取だった」を見つけるための
    しくみなので、ここをゆるめると意味がなくなる。
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG = os.path.join(ROOT, "figures")

# 「考えられる」は「〜と考えられる地点」のように、ていねいな言い方としても
# 使われる。因果のしるしとしては広すぎるので入れない。
REASON_Q = re.compile(r"理由|なぜ|言えない|読み取れない|判断できない|"
                      r"言えること|どの要因|条件として|ねらい")
REASON_A = re.compile(r"(ため|から|ためである)$")
_cache = {}


def figtext(name):
    key = name.split("/")[-1]
    if key not in _cache:
        p = os.path.join(FIG, key)
        if os.path.isfile(p):
            body = io.open(p, encoding="utf-8").read()
            _cache[key] = " ".join(re.findall(r">([^<>]+)</text>", body))
        else:
            _cache[key] = ""
    return _cache[key]


def load_terms():
    """一問一答の用語型の解答を、地理用語の辞書として読む"""
    p = os.path.join(ROOT, "data", "chiri.json")
    terms = set()
    if not os.path.isfile(p):
        return terms
    d = json.loads(io.open(p, encoding="utf-8").read())
    for u in d["units"]:
        for q in u["questions"]:
            if q.get("type") != "用語":
                continue
            for a in [q["a"]] + list(q.get("accept") or []):
                for part in re.split(r"[／（）・、]", a):
                    part = part.strip()
                    if len(part) >= 3 and re.search(r"[一-龥ァ-ヴ]", part):
                        terms.add(part)
    return terms


TERMS = load_terms()


def judge(q):
    """1問の思考レベルを決めて (レベル, 測った値) を返す"""
    figs = len(q.get("figures") or [])
    body = q.get("exp", "") + " " + " ".join(q.get("grounds") or [])
    refs = len(set(re.findall(r"資料([0-9１-９])", body)))
    ans = q["choices"][q["answer"]] if q.get("choices") else q.get("a", "")
    reason = bool(REASON_Q.search(q.get("q", ""))) or bool(REASON_A.search(ans))
    # 資料に書かれていない地理用語が要るか
    ft = " ".join(figtext(f) for f in (q.get("figures") or []))
    need = [t for t in TERMS if t in ans and t not in ft]
    know = bool(need)

    if figs >= 2 and refs >= 2:
        lv = "R4" if reason else "R3"
    elif reason or know:
        lv = "R2"
    else:
        lv = "R1"
    return lv, {"figs": figs, "refs": refs, "reason": reason,
                "know": know, "need": need[:3]}


def apply(data):
    """科目データ全体に level2 を付ける"""
    for u in data["units"]:
        for q in u["questions"]:
            lv, _ = judge(q)
            q["level2"] = lv
    return data


def summary(data):
    from collections import Counter
    c = Counter()
    per = {}
    for u in data["units"]:
        cu = Counter()
        for q in u["questions"]:
            c[q["level2"]] += 1
            cu[q["level2"]] += 1
        per[u["id"]] = cu
    return c, per
