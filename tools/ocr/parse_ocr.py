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

# 首字母可大写，其余必须小写：教材词表就是这个形态。
# 放宽到全大小写会把页眉装饰字（如 EAtSiaI）当成单词收进来，挤掉真词
WORD_RE = re.compile(r"[A-Za-z][a-z'\-]+$")
COUNT_RE = re.compile(r"/\s*(\d{2,3})")
# 教材页眉上的「Word List 13」。中频词不从 1 开始，接着高频词的编号往下排，
# 所以这个数字必须照书上原样保留，用户是照着纸质书翻的
TITLE_RE = re.compile(r"Word\s*List\s*(\d+)", re.I)


def load_dict():
    """系统自带词表（Webster's 第二版，23.6 万词），用来分辨「真词」和「装饰字乱码」。"""
    for p in ("/usr/share/dict/words",):
        try:
            with open(p, encoding="utf-8", errors="ignore") as f:
                return {w.strip().lower() for w in f if w.strip()}
        except OSError:
            continue
    return None


DICT_WORDS = load_dict()


def natural_key(s):
    """让 中2 排在 中10 前面——纯字符串排序会把 中10 排到 中2 前头。"""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def list_number(items):
    """从页面上找「Word List N」的编号；找不到返回 None。"""
    for i in items:
        m = TITLE_RE.search(i["text"])
        if m:
            return int(m.group(1))
    return None


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


def parse(items, want=None, rot=0):
    # 旋转 270° 时 Vision 吐出来的坐标轴是双向反的（x、y 都要翻回来），
    # 不翻的话词序会整个倒着排，用户照着书对不上
    if rot % 360 == 270:
        items = [dict(i, x=1 - i["x"], y=1 - i["y"]) for i in items]
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

    if want is not None:
        # 书上印着「/NN 词」就以它为准：各列全部收下，多余的从最长的列尾部剔。
        # 例句区永远在词表最下面，按这个规则剔掉的一定是例句而不是真题词。
        # （之前先按行距切尾，遇到 29 词 5 列这种短词表会切掉一大半）
        for c in by_col:
            by_col[c].sort(key=lambda i: -i["y"])
        total = sum(len(v) for v in by_col.values())
        while total > want:
            c = max(by_col, key=lambda k: len(by_col[k]))
            by_col[c].pop()
            total -= 1
        rows = [i for c in sorted(by_col) for i in by_col[c]]
    else:
        # 没读到书上词数：沿用「行距突变切尾」的老办法（高频词那 12 页就是这么来的）
        rows = []
        for col in sorted(by_col):
            rows.extend(cut_tail(sorted(by_col[col], key=lambda i: -i["y"]), 2.2))

    rows.sort(key=lambda i: (i["col"], -i["y"]))
    # 去重：页面底部的词条讲解会再把第一个词印一遍，容易混进词表末尾
    seen, out = set(), []
    for i in rows:
        w = i["text"].strip().lower()
        if w in seen:
            continue
        seen.add(w)
        out.append((w, i["conf"]))
    return out, len(by_col)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ocr_json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--image", default=None)
    ap.add_argument("--min-conf", type=float, default=0.35)
    # 按页输出 "# 中频词 · Word List 13" 这样的段头，直接拼进 src/words.txt。
    # --first-list 是页面上认不出编号时的兜底起点
    ap.add_argument("--segment", default=None, help="类别名，如 中频词")
    ap.add_argument("--first-list", type=int, default=1)
    # 用户要求：每一类都从 Word List 1 重新编号，不跟书上印的页码走
    ap.add_argument("--seq", action="store_true",
                    help="忽略页眉编号，按照片顺序从 --first-list 开始编")
    args = ap.parse_args()

    with open(args.ocr_json, encoding="utf-8") as f:
        raw = json.load(f)
    # 兼容两种格式：{path: [...]} 或 {path: {rotation, items}}
    data, rots = {}, {}
    for k, v in raw.items():
        if isinstance(v, dict) and "items" in v:
            data[k] = v["items"]
            rots[k] = v.get("rotation", 0)
        else:
            data[k] = v
            rots[k] = 0
    if args.image:
        data = {k: v for k, v in data.items() if k.endswith(args.image)}

    all_words, problems, segments = [], [], []
    idx = 0
    for path, items in sorted(data.items(), key=lambda kv: natural_key(kv[0])):
        name = path.split("/")[-1]
        if not items:
            problems.append("%s 没有识别结果" % name)
            continue
        want = expected_count(items)
        words, ncols = parse(items, want, rots.get(path, 0))
        # 置信度低、又不在任何词表里的，基本是页眉装饰字被认成了单词
        #（曾把「微语境记忆」认成 miathiziz，把「中频词」认成 EAtSiaI）
        # 真词哪怕置信度低（spy / mock / reap）也会因为在词表里而被留下来
        if DICT_WORDS:
            kept = [(w, c) for w, c in words if c >= 0.6 or w in DICT_WORDS]
            if len(kept) != len(words):
                dropped = [w for w, c in words if not (c >= 0.6 or w in DICT_WORDS)]
                print("    剔除疑似乱码: %s" % ", ".join(dropped), file=sys.stderr)
                words = kept
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

        idx += 1
        filed = list_number(items)
        num = None if args.seq else filed
        if num is None:
            num = args.first_list + idx - 1
        if filed is not None and args.seq:
            print("    → Word List %d（书上印的是 %d，按用户要求重排）" % (num, filed),
                  file=sys.stderr)
        else:
            print("    → Word List %d" % num, file=sys.stderr)
        segments.append((num, [w for w, _ in words]))

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
            if args.segment:
                # 按教材页分段：分页信息是铁律，绝不能把所有词混成一坨
                blocks = ["# %s · Word List %d\n%s" %
                          (args.segment, n, "\n".join(ws)) for n, ws in segments]
                f.write("\n\n".join(blocks) + "\n")
            else:
                f.write("\n".join(final))
        print("已写入 %s" % args.out, file=sys.stderr)
    else:
        print("\n".join(final))


if __name__ == "__main__":
    main()
