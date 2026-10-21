# -*- coding: utf-8 -*-
"""
把 data/mock.json 里的 5 套押题卷排成 A4 打印页（HTML），再用 Chrome 转 PDF。

用法：
    python scripts/build_pdf.py            # 生成 pdf/paper-1.html ... paper-5.html
"""
from __future__ import annotations

import io
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data", "mock.json")
OUT = os.path.join(HERE, "pdf", "src")

CN = "一二三四五"

CSS = r"""
@page { size: A4; margin: 17mm 16mm 16mm; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: "Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif;
  font-size: 10.6pt;
  line-height: 1.64;
  color: #1f1c18;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
p { margin: 0 0 .45em; }
b, strong { font-weight: 700; }
.accent { color: #a8442f; }

/* 封面 */
.cover {
  height: 248mm;
  display: flex;
  flex-direction: column;
  page-break-after: always;
}
.cover-seal {
  width: 14mm; height: 14mm;
  margin-top: 2mm;
  display: flex; align-items: center; justify-content: center;
  background: #a8442f; color: #fff;
  font-size: 20pt; line-height: 1;
  border-radius: 2.6mm;
}
.cover-kicker {
  margin-top: 12mm;
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  font-size: 9pt; letter-spacing: .28em; color: #8b8275;
}
.cover h1 {
  margin: 4mm 0 0;
  font-size: 31pt;
  font-weight: 700;
  letter-spacing: .04em;
  line-height: 1.25;
}
.cover h1 span { font-size: 24pt; color: #a8442f; }
.cover-sub { margin-top: 3mm; font-size: 11pt; color: #5d564b; }
.cover-rule { height: 1px; background: #d9d0bf; margin: 8mm 0 5mm; }
.cover-meta { list-style: none; margin: 0; padding: 0; display: flex; gap: 10mm; font-size: 10pt; color: #3f3a32; }
.cover-meta li::before { content: "·"; color: #a8442f; margin-right: 2mm; }
.cover-note {
  margin-top: 7mm;
  padding: 6mm 7mm;
  border-left: 2px solid #a8442f;
  background: #faf6ef;
  font-size: 9.6pt;
  line-height: 1.85;
  color: #3f3a32;
}
.cover-note b { display: block; margin-bottom: 1.5mm; font-size: 9pt; letter-spacing: .12em; color: #a8442f; }
.cover-note p { margin: 0; }
.points { margin-top: 7mm; }
.points h2 {
  margin: 0 0 3mm;
  font-size: 10pt; font-weight: 700; letter-spacing: .16em; color: #5d564b;
}
.points ul { list-style: none; margin: 0; padding: 0; }
.points li {
  display: inline-block;
  margin: 0 2mm 2mm 0;
  padding: 1.2mm 2.6mm;
  border: 1px solid #d9d0bf;
  border-radius: 8mm;
  font-size: 8.8pt;
  color: #3f3a32;
}
.points li i { font-style: normal; color: #a8442f; margin-left: 1.2mm; }
.cover-foot {
  margin-top: auto;
  padding-top: 4mm;
  border-top: 1px solid #e5ddcf;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 8.5pt; letter-spacing: .08em; color: #8b8275;
  display: flex; justify-content: space-between;
}

/* 正文 */
.paper-head {
  display: flex; align-items: baseline; justify-content: space-between;
  border-bottom: 1.5px solid #1f1c18;
  padding-bottom: 2.5mm;
  margin-bottom: 3mm;
}
.paper-head h2 { margin: 0; font-size: 13pt; letter-spacing: .04em; }
.paper-head span { font-family: "Microsoft YaHei", sans-serif; font-size: 8.5pt; color: #8b8275; }
.exam-line {
  display: flex; gap: 12mm;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 9pt; color: #5d564b;
  margin-bottom: 6mm;
}
.part {
  margin: 5.5mm 0 3mm;
  font-size: 11pt;
  font-weight: 700;
  page-break-after: avoid;
}
.part span { font-weight: 400; font-size: 9.2pt; color: #6b6458; margin-left: 2mm; }

.q { margin: 0 0 3.2mm; page-break-inside: avoid; }
.qt { text-indent: 0; }
.qt .no { font-weight: 700; margin-right: 1.5mm; }
.opts { margin: 1.2mm 0 0 5.5mm; display: flex; flex-wrap: wrap; }
.opt { width: 50%; padding-right: 4mm; font-size: 10.2pt; }
.opt .l { font-weight: 700; margin-right: 1.2mm; }
.opt.long { width: 100%; }

/* 答案 */
.answers { page-break-before: always; }
.answers > h2 {
  margin: 0 0 2mm;
  font-size: 15pt;
  letter-spacing: .08em;
  padding-bottom: 2mm;
  border-bottom: 1.5px solid #a8442f;
}
.answers .tip {
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 8.8pt; color: #8b8275; margin-bottom: 6mm;
}
.key {
  margin: 0 0 8mm;
  border: 1px solid #ddd4c4;
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
}
.key td {
  border: 1px solid #e7dfd2;
  padding: 1.4mm 1mm;
  text-align: center;
  font-size: 9pt;
  font-family: "Microsoft YaHei", sans-serif;
}
.key td b { color: #a8442f; margin-left: 1.5mm; }
.key td.blank { background: #faf7f1; }

.ans-part { margin-top: 7mm; }
.ans-part h3 {
  margin: 0 0 3mm;
  font-size: 11pt;
  padding-bottom: 1.5mm;
  border-bottom: 1px solid #e0d7c7;
  page-break-after: avoid;
}
.qbrief {
  font-size: 9.4pt;
  color: #6b6458;
  margin: 0 0 1.6mm;
  line-height: 1.65;
}
.qbrief .no { font-weight: 700; color: #1f1c18; margin-right: 1.4mm; }
.score-table {
  margin: 6mm 0 0;
  border-collapse: collapse;
  font-size: 9pt;
  font-family: "Microsoft YaHei", sans-serif;
  color: #3f3a32;
}
.score-table th, .score-table td {
  border-bottom: 1px solid #e5ddcf;
  padding: 1.6mm 9mm 1.6mm 0;
  text-align: left;
  font-weight: 400;
}
.score-table th { color: #8b8275; font-size: 8.4pt; letter-spacing: .08em; }
.score-table td:last-child { color: #a8442f; }
.cover-tip {
  margin-top: 3mm;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 8pt;
  color: #8b8275;
}
.ans-item { margin: 0 0 4.5mm; page-break-inside: avoid; }
.ans-head {
  font-weight: 700;
  font-size: 10.4pt;
  margin-bottom: 1mm;
}
.ans-head .no { margin-right: 1.5mm; }
.ans-head .letter { color: #a8442f; }
.ans-item .exp { font-size: 9.6pt; line-height: 1.78; color: #3f3a32; }
.ans-item .ref {
  border-left: 2px solid #d9cbb5;
  padding-left: 3.5mm;
  margin-bottom: 2mm;
  font-size: 9.9pt;
}
.ans-item .ref p { margin: 0 0 .35em; }
.ans-item .label {
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 8pt; letter-spacing: .1em; color: #a8442f;
  display: block; margin-bottom: .6mm;
}
.foot-note {
  margin-top: 8mm;
  padding-top: 3mm;
  border-top: 1px solid #e5ddcf;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 8pt; color: #8b8275;
  display: flex; justify-content: space-between;
}
"""


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def smart_quotes(s: str) -> str:
    """把成对的英文直引号换成中文引号，排版更顺眼。"""
    s = re.sub(r'"([^"\n]{1,90})"', "“\\1”", s)
    return s


def nl2br(s: str) -> str:
    return esc(smart_quotes(s)).replace("\n", "<br>")


def answer_letters(q: dict) -> str:
    return "".join("ABCDE"[i] for i in q["a"])


def render_choice(q: dict) -> str:
    opts = []
    for i, o in enumerate(q["o"]):
        long_cls = " long" if len(o) > 26 else ""
        opts.append('<div class="opt%s"><span class="l">%s.</span>%s</div>' % (long_cls, "ABCDE"[i], nl2br(o)))
    return (
        '<div class="q"><p class="qt"><span class="no">%d.</span>%s</p>'
        '<div class="opts">%s</div></div>' % (q["qno"], nl2br(q["t"]), "".join(opts))
    )


def render_essay(q: dict) -> str:
    return '<div class="q"><p class="qt"><span class="no">%d.</span>%s</p></div>' % (q["qno"], nl2br(q["t"]))


def wordy_points(paper: dict, ranking: list[dict]) -> str:
    ids = []
    for q in paper["choice"] + paper["essay"]:
        if q["pt"] not in ids:
            ids.append(q["pt"])
    rank = {r["id"]: r for r in ranking}
    ids.sort(key=lambda x: -rank.get(x, {}).get("periods", 0))
    items = []
    for pid in ids[:14]:
        r = rank.get(pid)
        if not r:
            continue
        items.append('<li>%s<i>%d 期</i></li>' % (esc(r["name"]), r["periods"]))
    return "".join(items)


def render_paper(paper: dict, ranking: list[dict]) -> str:
    n = paper["no"]
    singles = [q for q in paper["choice"] if not q["multi"]]
    multis = [q for q in paper["choice"] if q["multi"]]
    shorts = [q for q in paper["essay"] if q["type"] == "简答"]
    essays = [q for q in paper["essay"] if q["type"] == "论述"]
    cases = [q for q in paper["essay"] if q["type"] == "案例"]

    # 题号连续编号（选择题 1-35，主观题 36-43）
    for i, q in enumerate(singles + multis):
        q["no2"] = i + 1
        q["qno"] = i + 1
    for i, q in enumerate(shorts + essays + cases):
        q["no2"] = i + 36
        q["qno"] = i + 36

    out = []
    out.append("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>")
    out.append("<title>00037《美学》考前押题卷（%s）</title>" % CN[n - 1])
    out.append("<style>%s</style></head><body>" % CSS)

    # 封面
    out.append('<section class="cover">')
    out.append('<div class="cover-seal">美</div>')
    out.append('<div class="cover-kicker">自考 00037 · 美学</div>')
    out.append('<h1>考前押题卷<span>（%s）</span></h1>' % CN[n - 1])
    out.append('<p class="cover-sub">按 2016—2026 年 21 套真题的高频考点重组 · 共 5 套</p>')
    out.append('<div class="cover-rule"></div>')
    out.append('<ul class="cover-meta"><li>满分 100 分</li><li>建议用时 150 分钟</li>'
               '<li>35 道选择题 + 8 道主观题</li></ul>')
    out.append('<table class="score-table"><tr><th>题型</th><th>题量</th><th>分值</th></tr>'
               '<tr><td>单项选择题</td><td>30</td><td>30 分</td></tr>'
               '<tr><td>多项选择题</td><td>5</td><td>10 分</td></tr>'
               '<tr><td>简答题</td><td>6</td><td>30 分</td></tr>'
               '<tr><td>论述题</td><td>1</td><td>10 分</td></tr>'
               '<tr><td>案例分析题</td><td>1</td><td>20 分</td></tr></table>')
    out.append('<div class="cover-note"><b>使用建议</b><p>先按考试时间闭卷完成，再翻到「参考答案与详解」'
               '逐题核对。做错的选择题，回到教材找出该考点所在的章节，把相关表述完整背一遍；'
               '主观题先自己写要点，再对照参考答案补漏。五套卷的考点互相错开，建议每天两套。</p></div>')
    out.append('<div class="points"><h2>本卷覆盖的高频考点</h2><ul>%s</ul>'
               '<p class="cover-tip">考点频次按 21 套真题题干关键词归类统计，同一道题可能涉及多个考点，仅作复习优先级参考。</p></div>'
               % wordy_points(paper, ranking))
    out.append('<div class="cover-foot"><span>00037《美学》 · 考前 2 天冲刺</span>'
               '<span>第 %d / 5 套</span></div>' % n)
    out.append("</section>")

    # 试卷
    out.append('<section class="paper">')
    out.append('<div class="paper-head"><h2>00037《美学》考前押题卷（%s）</h2>'
               '<span>按 1910 年以来真题结构组卷</span></div>' % CN[n - 1])
    out.append('<div class="exam-line"><span>姓名：____________</span><span>得分：____________</span>'
               '<span>限时：150 分钟</span></div>')

    out.append('<div class="part">一、单项选择题<span>（30 小题，每小题 1 分，共 30 分）</span></div>')
    for q in singles:
        out.append(render_choice(q))

    out.append('<div class="part">二、多项选择题<span>（5 小题，每小题 2 分，共 10 分）</span></div>')
    for q in multis:
        out.append(render_choice(q))

    out.append('<div class="part">三、简答题<span>（6 小题，每小题 5 分，共 30 分）</span></div>')
    for q in shorts:
        out.append(render_essay(q))

    out.append('<div class="part">四、论述题<span>（1 小题，共 10 分）</span></div>')
    for q in essays:
        out.append(render_essay(q))

    out.append('<div class="part">五、案例分析题<span>（1 小题，共 20 分）</span></div>')
    for q in cases:
        out.append(render_essay(q))
    out.append("</section>")

    # 答案与详解
    out.append('<section class="answers">')
    out.append('<h2>参考答案与详解</h2>')
    out.append('<p class="tip">选择题先看速查表，再逐题看解析；主观题对照参考答案，重点记加粗的得分点。</p>')
    out.append('<table class="key">')
    cells = []
    for q in singles + multis:
        cells.append('<td>%d<b>%s</b></td>' % (q["no2"], answer_letters(q)))
    while len(cells) % 7:
        cells.append('<td class="blank"></td>')
    for i in range(0, len(cells), 7):
        out.append("<tr>%s</tr>" % "".join(cells[i:i + 7]))
    out.append("</table>")

    out.append('<div class="ans-part"><h3>一、单项选择题</h3>')
    for q in singles:
        out.append('<div class="ans-item"><div class="ans-head"><span class="no">%d.</span>'
                   '<span class="letter">%s</span></div><div class="exp">%s</div></div>' % (
                       q["no2"], answer_letters(q), nl2br(q["exp"])))
    out.append("</div>")

    out.append('<div class="ans-part"><h3>二、多项选择题</h3>')
    for q in multis:
        out.append('<div class="ans-item"><div class="ans-head"><span class="no">%d.</span>'
                   '<span class="letter">%s</span></div><div class="exp">%s</div></div>' % (
                       q["no2"], answer_letters(q), nl2br(q["exp"])))
    out.append("</div>")

    def essay_block(title: str, items: list[dict]) -> str:
        s = ['<div class="ans-part"><h3>%s</h3>' % title]
        for q in items:
            ans = "".join('<p>%s</p>' % nl2br(line) for line in q["ans"].split("\n") if line.strip())
            exp = nl2br(q.get("exp", ""))
            s.append('<div class="ans-item">'
                     '<p class="qbrief"><span class="no">%d.</span>%s</p>'
                     '<div class="ref"><span class="label">参考答案</span>%s</div>'
                     '%s</div>' % (
                         q["no2"], nl2br(q["t"]),
                         ans,
                         ('<div class="exp"><span class="label">解析</span>%s</div>' % exp) if exp else ""))
        s.append("</div>")
        return "".join(s)

    out.append(essay_block("三、简答题", shorts))
    out.append(essay_block("四、论述题", essays))
    out.append(essay_block("五、案例分析题", cases))

    out.append('<div class="foot-note"><span>00037《美学》考前押题卷（%s） · 参考答案</span>'
               '<span>题目取自 2016—2026 年真题高频考点</span></div>' % CN[n - 1])
    out.append("</section>")

    out.append("</body></html>")
    return "".join(out)


def main() -> None:
    data = json.load(io.open(DATA, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    for paper in data["papers"]:
        html = render_paper(paper, data["ranking"])
        path = os.path.join(OUT, "paper-%d.html" % paper["no"])
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        print("wrote", path)


if __name__ == "__main__":
    main()
