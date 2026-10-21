# -*- coding: utf-8 -*-
"""
按高频考点组 5 套押题卷。

  - 每道真题按关键词归到一个考点（points.py），考点频次 = 出现过的考期数；
  - 每套卷：30 单选 + 5 多选 + 6 简答 + 1 论述 + 1 案例，对应 1910 年以来的真题结构；
  - 同一考点的题在不同卷之间轮流使用，同一套卷内尽量不重复考点；
  - 每章题量设上限，避免卷面过度集中在某一章；
  - 输出 data/mock.json。
"""
from __future__ import annotations

import argparse
import difflib
import io
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from points import POINTS, CHAPTERS  # noqa: E402

PT = {p["id"]: p for p in POINTS}

STRUCT = dict(single=30, multi=5, short=6, essay=1, case=1)
PAPERS = 5
CH_CAP = {30: 7, 5: 2}   # 单选 / 多选 每章上限


def bad_item(it: dict) -> bool:
    t = it.get("t", "")
    if len(t) < 6 or len(t) > 260:
        return True
    for k in ("原试卷", "暂缺", "未显示", "略去", "图片"):
        if k in t:
            return True
    if it.get("kind") == "choice" and any(not o.strip() for o in it["o"]):
        return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--data", default=os.path.join(here, "data", "papers.json"))
    ap.add_argument("--out", default=os.path.join(here, "data", "mock.json"))
    args = ap.parse_args()

    data = json.load(io.open(args.data, encoding="utf-8"))

    choice, essay, texts = [], [], []
    for p in data["periods"]:
        for q in p["choice"]:
            it = dict(q)
            it.update(pid=p["id"], label=p["label"], kind="choice", multi=len(q["a"]) > 1)
            it["text"] = q["t"] + " " + " ".join(q["o"])
            choice.append(it)
            texts.append(it["text"])
        for q in p["essay"]:
            it = dict(q)
            it.update(pid=p["id"], label=p["label"], kind="essay")
            it["text"] = q["t"]
            essay.append(it)
            texts.append(it["text"])

    N = len(texts)
    df = Counter()
    for t in texts:
        for pt in POINTS:
            for k in pt["kw"]:
                if k in t:
                    df[k] += 1
    idf = {k: math.log((N + 1) / (df[k] + 1)) + 1 for k in df}

    def best_point(text: str):
        best = None
        for pt in POINTS:
            hits = [(idf.get(k, 1.0) * pt["pri"], len(k), k) for k in pt["kw"] if k in text]
            if not hits:
                continue
            h = max(hits)
            if best is None or h[0] > best[0] or (h[0] == best[0] and h[1] > best[1]):
                best = (h[0], h[1], pt["id"])
        return best[2] if best else None

    for it in choice + essay:
        # 先只看题干，题干认不出来再看选项
        it["pt"] = best_point(it["t"]) or best_point(it["text"])
        it["ok"] = (not bad_item(it)) and bool(it.get("exp", "").strip()) and len(it.get("exp", "")) >= 24

    usable_choice = [it for it in choice if it["ok"] and it["pt"]]
    usable_essay = [it for it in essay if it["ok"] and it["pt"]]
    print("可用选择题 %d / %d，可用主观题 %d / %d" % (len(usable_choice), len(choice), len(usable_essay), len(essay)))

    pt_periods = defaultdict(set)
    for it in usable_choice + usable_essay:
        pt_periods[it["pt"]].add(it["pid"])
    pt_freq = {k: len(v) for k, v in pt_periods.items()}

    by_pt = defaultdict(list)
    for it in usable_choice:
        by_pt[(it["multi"], it["pt"])].append(it)
    for lst in by_pt.values():
        lst.sort(key=lambda x: (x["label"], -x["no"]), reverse=True)
    essay_by = defaultdict(list)
    for it in usable_essay:
        essay_by[(it["type"], it["pt"])].append(it)
    for lst in essay_by.values():
        lst.sort(key=lambda x: (x["label"], -x["no"]), reverse=True)

    ordered_pts = sorted(pt_freq, key=lambda k: (-pt_freq[k], PT[k]["ch"], PT[k]["name"]))
    core, rest = ordered_pts[:12], ordered_pts[12:]

    used = set()
    picked_text = {"choice": [], "essay": []}   # [(考点, 归一化题干)]

    def key(it):
        return (it["pid"], it["kind"], it["no"])

    def norm_text(t):
        return re.sub(r"[\s，。；：、？！“”‘’（）()《》<>\"'·…—,.;:?!\-]", "", t)

    def too_similar(it, kind, th=0.82):
        t = norm_text(it["t"])
        for pt, s in picked_text[kind]:
            # 只有同一个考点下的高度相似题干才算重复（喜剧/荒诞这种不同考点不算）
            if abs(len(t) - len(s)) <= 24:
                r = difflib.SequenceMatcher(None, t, s).ratio()
                if r >= 0.8 or (pt == it["pt"] and r >= th):
                    return True
        return False

    def remember(it):
        picked_text["choice" if it["kind"] == "choice" else "essay"].append((it["pt"], norm_text(it["t"])))

    papers = []
    for pi in range(PAPERS):
        paper = {"no": pi + 1, "title": "考前押题卷（%s）" % "一二三四五"[pi], "choice": [], "essay": []}
        points_used = set()
        ch_count = Counter()
        ch_count_m = Counter()

        shift = (pi * 5) % len(rest) if rest else 0
        order = core + (rest[shift:] + rest[:shift] if rest else [])

        def fill(n, multi):
            got = []
            counter = ch_count_m if multi else ch_count
            # 三轮逐步放宽：先严格不重复考点，再放宽章上限，最后允许重复考点
            for relax in range(3):
                if len(got) >= n:
                    break
                for pid in order:
                    if len(got) >= n:
                        break
                    ch = PT[pid]["ch"]
                    cap = CH_CAP[5 if multi else 30] + relax * 2
                    if counter[ch] >= cap:
                        continue
                    if relax < 2 and pid in points_used:
                        continue
                    cand = [x for x in by_pt[(multi, pid)] if key(x) not in used and not too_similar(x, "choice", 0.84)]
                    if not cand:
                        cand = [x for x in by_pt[(multi, pid)] if key(x) not in used]
                    if not cand:
                        continue
                    it = cand[0]
                    used.add(key(it))
                    points_used.add(pid)
                    counter[ch] += 1
                    remember(it)
                    got.append(it)
            return got

        paper["choice"].extend(fill(STRUCT["single"], False))
        paper["choice"].extend(fill(STRUCT["multi"], True))

        def take_essay(typ, n):
            out = []
            pid_order = ordered_pts[:]
            sft = (pi * 3) % max(1, len(pid_order))
            pid_order = pid_order[sft:] + pid_order[:sft]
            for relax in range(2):
                if len(out) >= n:
                    break
                for pid in pid_order:
                    if len(out) >= n:
                        break
                    if relax == 0 and pid in points_used:
                        continue
                    cand = [x for x in essay_by[(typ, pid)] if key(x) not in used and not too_similar(x, "essay", 0.72)]
                    if not cand:
                        cand = [x for x in essay_by[(typ, pid)] if key(x) not in used]
                    if not cand:
                        continue
                    it = cand[0]
                    used.add(key(it))
                    points_used.add(pid)
                    remember(it)
                    out.append(it)
            if len(out) < n:
                for x in usable_essay:
                    if len(out) >= n:
                        break
                    if x["type"] != typ or key(x) in used or too_similar(x, "essay"):
                        continue
                    used.add(key(x))
                    points_used.add(x["pt"])
                    remember(x)
                    out.append(x)
            return out

        paper["essay"].extend(take_essay("简答", STRUCT["short"]))
        paper["essay"].extend(take_essay("论述", STRUCT["essay"]))
        paper["essay"].extend(take_essay("案例", STRUCT["case"]))

        for q in paper["choice"]:
            q["ch"] = PT[q["pt"]]["ch"]
            q["ptname"] = PT[q["pt"]]["name"]
        for q in paper["essay"]:
            q["ch"] = PT[q["pt"]]["ch"]
            q["ptname"] = PT[q["pt"]]["name"]

        paper["choice"].sort(key=lambda x: (x["ch"], ordered_pts.index(x["pt"]), x["t"]))
        singles = [q for q in paper["choice"] if not q["multi"]]
        multis = [q for q in paper["choice"] if q["multi"]]
        for i, q in enumerate(singles + multis):
            q["qno"] = i + 1
        paper["choice"] = singles + multis
        paper["essay"].sort(key=lambda x: {"简答": 0, "论述": 1, "案例": 2}[x["type"]])
        for i, q in enumerate(paper["essay"]):
            q["qno"] = i + 1

        paper["stat"] = {
            "single": sum(1 for x in paper["choice"] if not x["multi"]),
            "multi": sum(1 for x in paper["choice"] if x["multi"]),
            "short": sum(1 for x in paper["essay"] if x["type"] == "简答"),
            "essay": sum(1 for x in paper["essay"] if x["type"] == "论述"),
            "case": sum(1 for x in paper["essay"] if x["type"] == "案例"),
            "periods": len({x["pid"] for x in paper["choice"] + paper["essay"]}),
            "points": len({x["pt"] for x in paper["choice"] + paper["essay"]}),
            "chapters": [sum(1 for x in paper["choice"] if x["ch"] == c) for c in range(6)],
            "chapters_all": [sum(1 for x in paper["choice"] + paper["essay"] if x["ch"] == c) for c in range(6)],
        }
        papers.append(paper)

    ranking = []
    for pid in sorted(pt_freq, key=lambda k: (-pt_freq[k], PT[k]["ch"], PT[k]["name"])):
        ranking.append({
            "id": pid, "name": PT[pid]["name"], "ch": PT[pid]["ch"], "pri": PT[pid]["pri"],
            "periods": pt_freq[pid],
            "choice": sum(1 for x in usable_choice if x["pt"] == pid),
            "essay": sum(1 for x in usable_essay if x["pt"] == pid),
        })

    payload = {
        "meta": {
            "title": "00037《美学》考前押题卷",
            "papers": PAPERS,
            "structure": STRUCT,
            "builtFrom": "2016—2026 年 21 套真题",
        },
        "ranking": ranking,
        "papers": papers,
    }
    with io.open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print("\n高频考点 TOP 15：")
    for r in ranking[:15]:
        print("  %-6s %-24s 考期 %2d" % (r["id"], r["name"], r["periods"]))
    for p in papers:
        s = p["stat"]
        print("\n卷%s：单选%d 多选%d 简答%d 论述%d 案例%d | 考点%d | 来自%d个考期 | 选择章分布%s | 全部%s" % (
            "一二三四五"[p["no"] - 1], s["single"], s["multi"], s["short"], s["essay"], s["case"],
            s["points"], s["periods"], s["chapters"], s["chapters_all"]))
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
