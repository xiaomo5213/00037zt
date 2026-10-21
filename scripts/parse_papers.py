# -*- coding: utf-8 -*-
"""
解析「美学 anki 2016-2026.4」里按考期拆分的 docx，输出结构化题库。

输入目录里每个考期两个文件：`1604 单.docx`（选择题）、`1604 简答.docx`（主观题）。
输出：data/papers.json 与 data/exam.js（window.EXAM_DATA）。

用法：
    python scripts/parse_papers.py --src "C:\\...\\美学 anki 2016-2026.4"
"""
from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import sys
import glob

from docx import Document

OPT_RE = re.compile(r"^([A-EＡ-Ｅ])\s*[.、．]\s*(.+)$")
Q_RE = re.compile(r"^\s*(\d{1,2})\s*[.、．]\s*(.*)$")
ANS_RE = re.compile(r"^答案?\s*[:：]\s*(.*)$")
EXP_RE = re.compile(r"^解析\s*[:：]\s*(.*)$")

TYPE_BY_NO = {
    # 旧格式 1604-1904
    "old": [(26, 29, "名词解释"), (30, 34, "简答"), (35, 36, "论述")],
    # 新格式 1910 起
    "new": [(36, 41, "简答"), (42, 42, "论述"), (43, 43, "案例")],
}


def clean(text: str) -> str:
    text = text.replace("<br/>", "\n").replace("<br />", "\n").replace("<br>", "\n")
    text = html.unescape(text).replace("\u00a0", " ").replace("\u200b", "")
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def paragraphs(path: str) -> list[str]:
    doc = Document(path)
    return [clean(p.text) for p in doc.paragraphs if p.text.strip()]


def parse_choice(path: str) -> list[dict]:
    out: list[dict] = []
    cur = None
    mode = None
    expect = 1
    for line in paragraphs(path):
        m = Q_RE.match(line)
        if m and not OPT_RE.match(line) and int(m.group(1)) == expect:
            expect += 1
            if cur:
                out.append(cur)
            cur = {"no": int(m.group(1)), "t": m.group(2).strip(), "o": [], "a": [], "exp": ""}
            mode = "q"
            continue
        if cur is None:
            continue
        mo = OPT_RE.match(line)
        if mo and mode in ("q", "opt"):
            cur["o"].append(mo.group(2).strip())
            mode = "opt"
            continue
        ma = ANS_RE.match(line)
        if ma:
            letters = re.sub(r"[^A-E]", "", ma.group(1).upper())
            cur["a"] = [ord(ch) - 65 for ch in letters]
            mode = "ans"
            continue
        me = EXP_RE.match(line)
        if me:
            cur["exp"] = me.group(1).strip()
            mode = "exp"
            continue
        if mode == "q" and not cur["o"]:
            cur["t"] += line
        elif mode == "exp":
            cur["exp"] += "\n" + line
    if cur:
        out.append(cur)
    return out


def parse_essay(path: str, style: str) -> list[dict]:
    out: list[dict] = []
    cur = None
    mode = None
    expect = 26 if style == "old" else 36
    for line in paragraphs(path):
        m = Q_RE.match(line)
        if m and int(m.group(1)) == expect:
            expect += 1
            if cur:
                out.append(cur)
            cur = {"no": int(m.group(1)), "t": m.group(2).strip(), "ans": "", "exp": ""}
            mode = "q"
            continue
        if cur is None:
            continue
        ma = ANS_RE.match(line)
        if ma:
            cur["ans"] = ma.group(1).strip()
            mode = "ans"
            continue
        me = EXP_RE.match(line)
        if me:
            cur["exp"] = me.group(1).strip()
            mode = "exp"
            continue
        if mode == "q":
            cur["t"] += line
        elif mode == "ans":
            cur["ans"] += ("\n" if cur["ans"] else "") + line
        elif mode == "exp":
            cur["exp"] += "\n" + line
    if cur:
        out.append(cur)

    for item in out:
        item["type"] = "简答"
        for lo, hi, name in TYPE_BY_NO[style]:
            if lo <= item["no"] <= hi:
                item["type"] = name
    return out


def label_of(pid: str) -> tuple[int, int, str]:
    year = 2000 + int(pid[:2])
    month = int(pid[2:])
    return year, month, f"{year}年{month}月"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=r"C:\Users\Administrator\Desktop\美学 anki 2016-2026.4\美学 anki 2016-2026.4")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
    args = ap.parse_args()

    files = {}
    for f in glob.glob(os.path.join(args.src, "*.docx")):
        name = os.path.basename(f)
        m = re.match(r"(\d{4})\s*(单|简答)\.docx$", name)
        if m:
            files[(m.group(1), m.group(2))] = f

    periods = []
    for pid in sorted({k[0] for k in files}):
        style = "old" if pid < "1910" else "new"
        choice = parse_choice(files[(pid, "单")]) if (pid, "单") in files else []
        essay = parse_essay(files[(pid, "简答")], style) if (pid, "简答") in files else []
        year, month, label = label_of(pid)
        periods.append({
            "id": pid, "year": year, "month": month, "label": label,
            "choice": choice, "essay": essay,
        })

    # 校验
    problems = []
    for p in periods:
        for q in p["choice"]:
            if len(q["o"]) < 4 or not q["a"]:
                problems.append((p["id"], q["no"], "选项/答案缺失"))
            if q["a"] and max(q["a"]) >= len(q["o"]):
                problems.append((p["id"], q["no"], "答案越界"))
            q["multi"] = len(q["a"]) > 1
        for q in p["essay"]:
            if not q["ans"]:
                problems.append((p["id"], q["no"], "主观题答案缺失"))

    payload = {
        "meta": {
            "title": "00037《美学》历年真题",
            "periods": len(periods),
            "choice": sum(len(p["choice"]) for p in periods),
            "essay": sum(len(p["essay"]) for p in periods),
            "first": periods[0]["id"] if periods else "",
            "last": periods[-1]["id"] if periods else "",
        },
        "periods": periods,
    }

    os.makedirs(args.out, exist_ok=True)
    with io.open(os.path.join(args.out, "papers.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write("\n")
    with io.open(os.path.join(args.out, "exam.js"), "w", encoding="utf-8", newline="\n") as f:
        f.write("/* 由 scripts/parse_papers.py 生成，请勿手改 */\n")
        f.write("window.EXAM_DATA = ")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    print("考期 %d 个，选择题 %d 道，主观题 %d 道" % (payload["meta"]["periods"], payload["meta"]["choice"], payload["meta"]["essay"]))
    for p in periods:
        print("  %s %-9s 选择 %2d（单选 %d / 多选 %d）  主观 %2d" % (
            p["id"], p["label"], len(p["choice"]),
            sum(1 for q in p["choice"] if not q["multi"]),
            sum(1 for q in p["choice"] if q["multi"]),
            len(p["essay"])))
    if problems:
        print("\n问题 %d 处：" % len(problems))
        for x in problems[:20]:
            print("  ", x)
        sys.exit(1)


if __name__ == "__main__":
    main()
