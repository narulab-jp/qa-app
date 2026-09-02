# -*- coding: utf-8 -*-
"""図表・読図問題を書くための共通の型。

  ・すべて4択のマーク式。記述型は作らない。
  ・answer は choices の 0 から始まる添字。
  ・a は正解の表示用（間違いノートと印刷が従来のしくみのまま使える）。
"""
MARK = ["①", "②", "③", "④"]
_seq = [0]


def reset(start):
    _seq[0] = start - 1


def Q(no, set_id, skill, level, figures, q, choices, answer, exp, grounds):
    assert len(choices) == 4, "選択肢は4つでなければならない: %s" % q
    assert len(set(choices)) == 4, "選択肢が重複している: %s" % q
    assert 0 <= answer <= 3, "answer の範囲が違う: %s" % q
    assert len(grounds) >= 2, "根拠は2つ以上必要: %s" % q
    assert figures, "図のない問題は作らない: %s" % q
    _seq[0] += 1
    return {
        "no": no, "seq": _seq[0], "setId": set_id, "skill": skill, "level": level,
        "type": skill,
        "figures": list(figures),
        "q": q, "choices": list(choices), "answer": answer,
        "a": MARK[answer] + " " + choices[answer],
        "exp": exp, "grounds": list(grounds),
    }
