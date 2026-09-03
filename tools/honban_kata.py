# -*- coding: utf-8 -*-
"""組合せ形式の選択肢を、本番と同じ並びで作る道具。

  本番の選択肢の並びは決まっている（3対3なら6通りを辞書順に並べた表）。
  したがって正解の位置は、こちらで選ぶものではなく
  「正しい対応が表の何番目に来るか」で自動的に決まる。
  ここではその並びを作り、正解の位置を計算して返す。
"""
import itertools
import random

SEI = "正"
GO = "誤"


class Positions(object):
    """正解の位置を、択数ごとに均等に配りつつ、規則的な並びを避ける。

       ①②③④…と順に並ぶと、問題を読まなくても当てられてしまう。
       択数ごとの回数（＝分布）は変えず、配る順番だけを混ぜる。
       seed を決め打ちにしてあるので、作り直しても同じ並びになる。"""

    def __init__(self, counts, seed):
        rng = random.Random(seed)
        self.pool, self.i = {}, {}
        for n in sorted(counts):
            seq = [k % n for k in range(counts[n])]
            rng.shuffle(seq)
            self.pool[n] = seq
            self.i[n] = 0

    def take(self, n):
        k = self.i[n]
        if k >= len(self.pool[n]):
            raise AssertionError("%d択の割り当てが足りない" % n)
        self.i[n] = k + 1
        return self.pool[n][k]

    def rest(self):
        return dict((n, len(self.pool[n]) - self.i[n]) for n in self.pool)


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


def seigo_bun(head, bun, target, shime=""):
    """正誤の組合せを、文の並べ替えで指定の位置に置く。

       bun は [(文, 正しいか, その文についての解説), ...]。
       文を並べ替えれば正解の位置は動くが、動かせるのは
       「正の数が同じ」位置だけである（正正は必ず①、誤誤は必ず最後）。
       問題文も解説も並べ替えたあとの順で組み立てるので、
       ａ・ｂ・ｃの指す文と解説はいつも一致する。

       返り値 (問題文, 選択肢, 正解の位置)。"""
    n = len(bun)
    combos = list(itertools.product([True, False], repeat=n))
    order = None
    for p in itertools.permutations(range(n)):
        if combos.index(tuple(bun[k][1] for k in p)) == target:
            order = p
            break
    if order is None:
        raise AssertionError(
            "正誤の位置を %d にできない（正の数が合わない）: %s" % (target, head))
    lab = "ａｂｃ"[:n]
    q = head + "".join("\n%s　%s" % (lab[k], bun[order[k]][0])
                       for k in range(n))
    exp = "".join("%sは%s。%s"
                  % (lab[k], SEI + "しい" if bun[order[k]][1] else "誤り",
                     bun[order[k]][2])
                  for k in range(n))
    ch, ans = seigo([bun[k][1] for k in order])
    return q, ch, ans, (exp + shime)
