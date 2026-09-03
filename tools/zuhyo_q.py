# -*- coding: utf-8 -*-
"""図表・読図問題を書くための共通の型。

  ・すべて4択のマーク式。記述型は作らない。
  ・answer は choices の 0 から始まる添字。
  ・a は正解の表示用（間違いノートと印刷が従来のしくみのまま使える）。
"""
MARK = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨"]
_seq = [0]


def reset(start):
    _seq[0] = start - 1


def skip(n):
    """問を削ったところで通し番号を空ける。

       通し番号は利用者の間違いノートが問を指すのに使っている。
       削った分だけ後ろが繰り上がると、保存済みのノートが
       別の問を指してしまう。だから欠番のまま残す。"""
    _seq[0] += n
    return None


def Q(no, set_id, skill, level, figures, q, choices, answer, exp, grounds):
    assert 4 <= len(choices) <= 9, "選択肢は4〜9でなければならない: %s" % q
    assert len(set(choices)) == len(choices), "選択肢が重複している: %s" % q
    assert 0 <= answer < len(choices), "answer の範囲が違う: %s" % q
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
