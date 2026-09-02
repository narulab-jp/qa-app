# -*- coding: utf-8 -*-
"""アプリのアイコンを自作する（外部から画像を取得しない）。

icon.svg と同じ図案を、Edge のヘッドレス撮影で PNG に書き出す。
    python tools\\make_icons.py
生成物: icons/icon-192.png / icon-512.png / icon-maskable.png
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ICONS = os.path.join(ROOT, "icons")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# scale = 図案の大きさ（1.0 で画面いっぱい）。maskable は安全領域に収めるため小さくする。
PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;width:{sz}px;height:{sz}px;overflow:hidden;}}
.bg{{width:{sz}px;height:{sz}px;background:{bg};display:flex;
     align-items:center;justify-content:center;border-radius:{radius}px;}}
.in{{width:{inner}px;height:{inner}px;display:flex;flex-direction:column;
     align-items:center;justify-content:center;}}
.t{{font-family:"Yu Gothic UI","Meiryo","Noto Sans JP",sans-serif;font-weight:bold;
    color:#fff;line-height:1.06;font-size:{fs}px;letter-spacing:0;}}
</style></head><body>
<div class="bg"><div class="in"><div class="t">一問</div><div class="t">一答</div></div></div>
</body></html>"""

JOBS = [
    # (出力名, 画像サイズ, 角丸, 図案の占める割合)
    ("icon-192.png", 192, 36, 0.86),
    ("icon-512.png", 512, 96, 0.86),
    # maskable は端が切り取られるため、図案を中央60%の安全領域に収め背景を全面に敷く
    ("icon-maskable.png", 512, 0, 0.58),
]


def main():
    if not os.path.exists(EDGE):
        print("★Edge が見つかりません: %s" % EDGE)
        return 1
    os.makedirs(ICONS, exist_ok=True)
    tmp = os.path.join(os.environ["TEMP"], "qa_icon")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    ok = 0
    for name, sz, radius, ratio in JOBS:
        inner = int(sz * ratio)
        html = PAGE.format(sz=sz, bg="#1a4d7a", radius=radius,
                           inner=inner, fs=int(inner * 0.40))
        hp = os.path.join(tmp, name + ".html")
        with open(hp, "w", encoding="utf-8") as f:
            f.write(html)
        out = os.path.join(ICONS, name)
        if os.path.exists(out):
            os.remove(out)
        cmd = [EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--hide-scrollbars", "--force-device-scale-factor=1",
               "--user-data-dir=" + os.path.join(tmp, "ud"),
               "--window-size=%d,%d" % (sz, sz),
               "--screenshot=" + out,
               "file:///" + hp.replace("\\", "/")]
        subprocess.run(cmd, capture_output=True, timeout=180)
        if os.path.exists(out):
            ok += 1
            print("  %-20s %d x %d  %s bytes" % (name, sz, sz, os.path.getsize(out)))
        else:
            print("  ★%s の生成に失敗" % name)
    shutil.rmtree(tmp, ignore_errors=True)
    print("生成 %d / %d" % (ok, len(JOBS)))
    return 0 if ok == len(JOBS) else 1


if __name__ == "__main__":
    sys.exit(main())

