# -*- coding: utf-8 -*-
"""Markdown を PDF に変換する（外部ライブラリを使わず、Edge の印刷機能で出力する）。

    python tools\\md2pdf.py スマホ設定手順.md
出力: 同じ名前の .pdf
"""
import html
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

CSS = """
@page{ size:A4 portrait; margin:16mm 15mm; }
*{box-sizing:border-box;}
body{margin:0;color:#111;line-height:1.75;font-size:10.5pt;
     font-family:"Yu Gothic UI","Meiryo","Noto Sans JP",sans-serif;}
h1{font-size:19pt;margin:0 0 6mm;padding-bottom:2mm;border-bottom:1.5pt solid #1a4d7a;
   color:#1a4d7a;}
h2{font-size:14pt;margin:7mm 0 3mm;padding:1.5mm 3mm;background:#e8effa;
   border-left:3pt solid #1a4d7a;break-after:avoid;page-break-after:avoid;}
h3{font-size:12pt;margin:5mm 0 2mm;break-after:avoid;page-break-after:avoid;}
p{margin:0 0 3mm;}
ul,ol{margin:0 0 3mm;padding-left:7mm;}
li{margin:0 0 1mm;}
code{font-family:"Consolas","Yu Gothic UI",monospace;background:#f0f0f0;
     padding:0 1mm;border-radius:2px;font-size:9.5pt;}
pre{background:#f5f5f3;border:0.8pt solid #000;border-radius:3px;
    padding:2.5mm 3mm;margin:0 0 3mm;white-space:pre-wrap;font-size:10pt;
    break-inside:avoid;page-break-inside:avoid;}
pre code{background:none;padding:0;font-size:10pt;}
blockquote{margin:0 0 3mm;padding:2mm 3mm;border-left:2.5pt solid #000;
           background:#fafafa;color:#333;}
blockquote p{margin:0;}
table{width:100%;border-collapse:collapse;margin:0 0 4mm;font-size:10pt;
      break-inside:avoid;page-break-inside:avoid;}
th,td{border:0.8pt solid #000;padding:1.5mm 2mm;text-align:left;vertical-align:top;}
th{background:#eef2f8;}
hr{border:0;border-top:0.8pt solid #000;margin:5mm 0;}
strong{color:#000;}
"""


def inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return s


def md2html(md):
    out, i, lines = [], 0, md.split("\n")
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):                      # コードブロック
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(html.escape(lines[i])); i += 1
            i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
            continue
        if re.match(r"^\s*(---|===)\s*$", ln):
            out.append("<hr>"); i += 1; continue
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            n = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (n, inline(m.group(2)), n)); i += 1; continue
        if ln.strip().startswith("|") and i + 1 < len(lines) \
           and re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i+1]):
            head = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = "<table><tr>" + "".join("<th>%s</th>" % inline(c) for c in head) + "</tr>"
            for r in rows:
                t += "<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>"
            out.append(t + "</table>")
            continue
        if re.match(r"^\s*>\s?", ln):
            buf = []
            while i < len(lines) and re.match(r"^\s*>\s?", lines[i]):
                buf.append(inline(re.sub(r"^\s*>\s?", "", lines[i]))); i += 1
            out.append("<blockquote><p>" + "<br>".join(buf) + "</p></blockquote>")
            continue
        if re.match(r"^\s*[-*]\s+", ln):
            buf = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                buf.append("<li>" + inline(re.sub(r"^\s*[-*]\s+", "", lines[i])) + "</li>")
                i += 1
            out.append("<ul>" + "".join(buf) + "</ul>")
            continue
        if re.match(r"^\s*\d+\.\s+", ln):
            buf = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                buf.append("<li>" + inline(re.sub(r"^\s*\d+\.\s+", "", lines[i])) + "</li>")
                i += 1
            out.append("<ol>" + "".join(buf) + "</ol>")
            continue
        if ln.strip() == "":
            i += 1; continue
        buf = []
        while i < len(lines) and lines[i].strip() != "" \
                and not re.match(r"^(#{1,6}\s|```|\s*[-*]\s|\s*\d+\.\s|\s*>|\s*\||\s*---\s*$)",
                                 lines[i]):
            buf.append(inline(lines[i])); i += 1
        if buf:
            out.append("<p>" + "<br>".join(buf) + "</p>")
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("使い方: python tools\\md2pdf.py <file.md>")
        return 1
    src = sys.argv[1]
    if not os.path.isabs(src):
        src = os.path.join(ROOT, src)
    if not os.path.exists(src):
        print("★見つかりません: %s" % src); return 1
    md = open(src, encoding="utf-8").read()
    title = os.path.splitext(os.path.basename(src))[0]
    doc = ('<!doctype html><html lang="ja"><head><meta charset="utf-8">'
           '<title>%s</title><style>%s</style></head><body>%s</body></html>'
           % (html.escape(title), CSS, md2html(md)))
    hp = os.path.join(os.environ["TEMP"], title + ".html")
    open(hp, "w", encoding="utf-8").write(doc)
    out = os.path.splitext(src)[0] + ".pdf"
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--user-data-dir=" + os.path.join(os.environ["TEMP"], "md2pdf_ud"),
                    "--print-to-pdf=" + out, "--print-to-pdf-no-header",
                    "--no-pdf-header-footer",
                    "file:///" + hp.replace("\\", "/")],
                   capture_output=True, timeout=180)
    if os.path.exists(out):
        print("出力: %s（%s bytes）" % (out, os.path.getsize(out)))
        return 0
    print("★PDFの生成に失敗しました")
    return 1


if __name__ == "__main__":
    sys.exit(main())
