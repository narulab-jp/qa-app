# -*- coding: utf-8 -*-
r"""公開サイトの図が、手元のものと同じかを1枚ずつ確かめる。

  ・図97枚を実際に取得して中身を突き合わせる
  ・GitHub 側は改行が CRLF になるので、改行をそろえてから比べる
  ・キャッシュに当たらないよう、URLに時刻を付ける

  python tools\check_live_figs.py
"""
import glob
import hashlib
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = "https://narulab-jp.github.io/qa-app/"


def norm(b):
    return b.replace(b"\r\n", b"\n")


def sha(b):
    return hashlib.sha256(norm(b)).hexdigest()


def get(url):
    req = urllib.request.Request(url)
    req.add_header("Cache-Control", "no-cache")
    req.add_header("User-Agent", "check-live-figs")
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.status, r.read()


def main():
    figs = sorted(glob.glob(os.path.join(ROOT, "figures", "*.svg")))
    print("手元の図 %d枚を、公開サイトと突き合わせる" % len(figs))
    t = str(int(time.time()))
    same, diff, err = 0, [], []
    for p in figs:
        name = os.path.basename(p)
        local = open(p, "rb").read()
        try:
            st, body = get(SITE + "figures/" + name + "?v=" + t)
        except Exception as e:
            err.append("%s %s" % (name, e))
            continue
        if st != 200:
            err.append("%s HTTP %s" % (name, st))
        elif sha(body) == sha(local):
            same += 1
        else:
            diff.append("%s 公開%d/手元%d bytes" % (name, len(body), len(local)))
    print("  一致 %d ／ 不一致 %d ／ 取れなかった %d" % (same, len(diff), len(err)))
    for x in diff[:6]:
        print("   ★不一致 %s" % x)
    for x in err[:6]:
        print("   ★取得失敗 %s" % x)
    ok = (same == len(figs))
    print("公開の図: %s" % ("全%d枚が手元と一致" % len(figs) if ok else "★ずれあり"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
