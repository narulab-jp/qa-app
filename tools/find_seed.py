# -*- coding: utf-8 -*-
"""冊Dの正解の位置が規則的に並ばないよう、配り方の seed を選ぶ。

  冊Dの並びは
    問1〜14  … 6択（対応型）      配り役から
    問15・16 … 9択（2軸型）      2・4（軸の並びに意味があるので動かさない）
    問17〜32 … 4択（2軸型）      配り役から
    問33〜40 … 4択（2文の正誤）  0,2,1,3,0,2,1,3（正正は①、誤誤は④で固定）
    問41〜48 … 8択（3文の正誤）  0,4,1,6,2,3,5,7（正の数が同じ位置の中で散らす）
  このうち動かせるのは前半2つだけなので、そこを振って
  「隣り合う問で正解が±1になる割合」と「連続して上がり続ける長さ」を
  いちばん小さくする seed を探す。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from honban_kata import Positions          # noqa: E402

FIX9 = [2, 4]
FIX_S2 = [0, 2, 1, 3, 0, 2, 1, 3]
FIX_S3 = [0, 4, 1, 6, 2, 3, 5, 7]


def sequence(seed):
    pos = Positions({6: 14, 4: 16}, seed)
    s = [pos.take(6) for _ in range(14)]
    s += FIX9
    s += [pos.take(4) for _ in range(16)]
    s += FIX_S2 + FIX_S3
    return s


def score(s):
    adj = sum(1 for i in range(1, len(s)) if abs(s[i] - s[i - 1]) == 1)
    same = sum(1 for i in range(1, len(s)) if s[i] == s[i - 1])
    up, cur = 1, 1
    for i in range(1, len(s)):
        if s[i] - s[i - 1] == 1:
            cur += 1
            up = max(up, cur)
        else:
            cur = 1
    return adj, same, up


def main():
    best = None
    for seed in range(1, 200000):
        s = sequence(seed)
        adj, same, up = score(s)
        k = (adj, up, same)
        if best is None or k < best[0]:
            best = (k, seed, s)
            if adj <= 5 and up <= 2 and same <= 2:
                break
    seed, s = best[1], best[2]
    adj, same, up = score(s)
    print("seed = %d" % seed)
    print("  ±1の隣接 %d/%d = %.0f%%" % (adj, len(s) - 1,
                                       100.0 * adj / (len(s) - 1)))
    print("  上がり続ける最長 %d問／同じ位置が続く %d回" % (up, same))
    for i in range(0, len(s), 12):
        print("  問%2d-%2d: %s" % (i + 1, min(i + 12, len(s)),
                                  " ".join(map(str, s[i:i + 12]))))


if __name__ == "__main__":
    main()
