# -*- coding: utf-8 -*-
"""組合せ形式の選択肢を、本番と同じ並びで作る道具。

  本番の選択肢の並びは決まっている（3対3なら6通りを辞書順に並べた表）。
  したがって正解の位置は、こちらで選ぶものではなく
  「正しい対応が表の何番目に来るか」で自動的に決まる。
  ここではその並びを作り、正解の位置を計算して返す。
"""
import itertools

SEI = "正"
GO = "誤"


def taiou(rows, correct):
    """対応型。rows は行見出し（例：気候区名3つ）、correct はそれぞれに
       対応する記号のタプル（例：("ア","イ","ウ")）。
       記号の全順列を辞書順に並べたものが選択肢になる。"""
    marks = sorted(set(correct))
    perms = list(itertools.permutations(marks))
    ch = ["　".join("%s=%s" % (rows[k], p[k]) for k in range(len(rows)))
          for p in perms]
    return ch, perms.index(tuple(correct))


def nijiku(n1, v1, n2, v2, correct):
    """2軸型。v1・v2 はそれぞれの軸の候補（2つずつなら4択、3つずつなら9択）。
       correct は正しい組合せ (v1の値, v2の値)。"""
    combos = [(a, b) for a in v1 for b in v2]
    ch = ["%s=%s　%s=%s" % (n1, a, n2, b) for (a, b) in combos]
    return ch, combos.index(tuple(correct))


def taiou_at(mapping, target):
    """対応型。mapping は {行見出し: 正しい記号}。
       行見出しの並べ方で正解の位置が決まるので、target の位置に来るよう並べる。
       （本番でも、行見出しの並び順は問題ごとに違う）"""
    marks = sorted(mapping.values())
    want = list(itertools.permutations(marks))[target]
    rev = dict((v, k) for k, v in mapping.items())
    rows = [rev[m] for m in want]
    return taiou(rows, want)


def nijiku_at(n1, correct1, other1, n2, correct2, other2, target):
    """2軸型（4択）。target の位置に正解が来るよう、候補の並べ方を決める。"""
    v1 = [correct1, other1] if target < 2 else [other1, correct1]
    v2 = [correct2, other2] if target % 2 == 0 else [other2, correct2]
    return nijiku(n1, v1, n2, v2, (correct1, correct2))


def seigo(truth):
    """正誤の組合せ。truth は各文が正しいかどうかの並び（True/False）。
       2文なら4択、3文なら8択。並びは 正正／正誤／誤正／誤誤 の順。"""
    n = len(truth)
    lab = "ａｂｃ"[:n]
    combos = list(itertools.product([True, False], repeat=n))
    ch = ["　".join("%s=%s" % (lab[k], SEI if c[k] else GO) for k in range(n))
          for c in combos]
    return ch, combos.index(tuple(truth))
