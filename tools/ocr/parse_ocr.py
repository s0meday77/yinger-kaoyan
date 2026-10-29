#!/usr/bin/env python3
"""把 OCR 结果还原成教材上的词表顺序。

要点：
1. 词表按列排（第 1 列从上到下，再到第 2 列），先按 x 分列，列内按 y 从上到下。
2. 词表下方常有例句/词根讲解区，会混进额外单词 —— 用「行间距突变」切掉下面的区域，
   并尽量按封面印的「/NN 词」把多出来的尾部词剔掉。
3. 识别出的词数必须和书上印的一致，不一致就从末尾逐个剔除并标记出来人工核对。

用法:
    python3 -I parse_ocr.py ocr.json [--out words.txt]
"""
import argparse
import json
import re
import statistics
import sys

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*$")
COUNT_RE = re.compile(r"/\s*(\d{2,3})")


def cluster_columns(items, tol_ratio=0.05):
    xs = sorted(i["x"] for i in items)
    if not xs:
        return []
    span = (xs[-1] - xs[0]) or 1
    tol = span * tol_ratio
    groups, cur = [], [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] <= tol:
            cur.append(x)
        else:
            groups.append(cur)
            cur = [x]
    groups.append(cur)
    return [sum(g) / len(g) for g in groups]


def cut_tail(rows, factor):
    """rows 从上到下排好；行距突然放大（factor 倍）就切，只留词表主体。"""
    if len(rows) < 4:
        return rows
    gaps = [rows[i]["y"] - rows[i + 1]["y"] for i in range(len(rows) - 1)]
    med = statistics.median(gaps)
    if med <= 0:
        return rows
    for idx, g in enumerate(gaps):
        if g > med * factor and idx >= 2:
            return rows[: idx + 1]
    return rows


def expected_count(items):
    """页面上印的「掌握情况：___/88 词」——OCR 常把它识别成 "/88 1)" 之类。"""
    best = None
    for i in items:
        m = COUNT_RE.search(i["text"])
        if m:
            n = int(m.group(1))
            if 10 <= n <= 400:
                best = n if best is None else min(best, n)
    return best


def parse(items, want=None):
    cand = [i for i in items
            if WORD_RE.match(i["text"].strip()) and len(i["text"].strip()) > 1]

    # 先把「明显是例句区」的孤立列去掉：列内词数远小于中位数
    centers = cluster_columns(cand)
    for i in cand:
        i["col"] = min(range(len(centers)), key=lambda c: abs(centers[c] - i["x"]))
    by_col = {}
    for i in cand:
        by_col.setdefault(i["col"], []).append(i)
    if len(by_col) > 1:
        sizes = [len(v) for v in by_col.values()]
        med_size = statistics.median(sizes)
        for c in list(by_col):
            if len(by_col[c]) < med_size * 0.4:
                del by_col[c]
        # 重新编号，保证顺序稳定
        by_col = {new: by_col[old] for new, old in enumerate(sorted(by_col))}

    best_rows = None
    for factor in (2.2, 1.8, 1.5, 1.25, 1.0):
        rows = []
        for col in sorted(by_col):
            rows.extend(cut_tail(sorted(by_col[col], key=lambda i: -i["y"]), factor))
        best_rows = rows
        if want is None or len(rows) <= want:
            break
    rows = best_rows or []

    # 仍多于书上标注：从最底部逐个剔除（那些必然是讲解区混进来的）
    if want is not None:
        while len(rows) > want:
            rows.pop(max(range(len(rows)), key=lambda i: (rows[i]["col"], -rows[i]["y"])))

    rows.sort(key=lambda i: (i["col"], -i["y"]))
    return [(i["text"].strip().lower(), i["conf"]) for i in rows], len(by_col)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ocr_json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--image", default=None)
    ap.add_argument("--min-conf", type=float, default=0.35)
    args = ap.parse_args()

    with open(args.ocr_json, encoding="utf-8") as f:
        raw = json.load(f)
    # 兼容两种格式：{path: [...]} 或 {path: {rotation, items}}
    data = {k: (v["items"] if isinstance(v, dict) and "items" in v else v) for k, v in raw.items()}
    if args.image:
        data = {k: v for k, v in data.items() if k.endswith(args.image)}

    all_words, problems = [], []
    for path, items in sorted(data.items(), key=lambda kv: kv[0]):
        name = path.split("/")[-1]
        if not items:
            problems.append("%s 没有识别结果" % name)
            continue
        want = expected_count(items)
        words, ncols = parse(items, want)
        got = len(words)
        low = [w for w, c in words if c < args.min_conf]
        ok = want is None or want == got
        print("%-40s 识别 %3d ｜ 书上 %-4s ｜ %d 列 ｜ %s" %
              (name, got, want if want is not None else "?", ncols, "OK" if ok else "不符"),
              file=sys.stderr)
        if not ok:
            problems.append("%s 识别 %d 词，书上标 %s 词" % (name, got, want))
        if low:
            problems.append("%s 低置信词: %s" % (name, ", ".join(low)))
        all_words.extend(words)

    seen, final = set(), []
    for w, _ in all_words:
        if w not in seen:
            seen.add(w)
            final.append(w)

    print("\n合计 %d 词（去重后 %d）" % (len(all_words), len(final)), file=sys.stderr)
    if problems:
        print("需要人工核对：", file=sys.stderr)
        for p in problems:
            print("  ! " + p, file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(final))
        print("已写入 %s" % args.out, file=sys.stderr)
    else:
        print("\n".join(final))


if __name__ == "__main__":
    main()
