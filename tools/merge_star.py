#!/usr/bin/env python3
"""把《词汇闪过》解析结果挂进词库：每个词多两个字段。

    sm = 书上释义，按词性分行，如 ["n. [C,U] 进步；进展", "vt. 促进；推动"]
    sp = 书上搭配，如 [{"p": "scientific advances", "t": "科学进步"}]

有道来的 m（释义）原样保留：书上还没导入的词继续用有道的显示。
书上的内容进新字段而不是覆盖 m，是因为后面还要一组一组往下导入，
得能一眼看出哪些词已经换成了书上的内容。

用法:
    python3 -I tools/merge_star.py ~/Desktop/词汇闪过1-15页.docx
    python3 -I tools/merge_star.py /tmp/star.json --dry-run
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from parse_star import docx_to_text, merge_senses, parse  # noqa: E402

WORDS = os.path.join(HERE, "..", "app", "data", "words.json")


def load_entries(src):
    """支持 .docx / .txt（现场解析）和 .json（已经解析过的）。"""
    if src.lower().endswith(".json"):
        with open(src, encoding="utf-8") as f:
            return json.load(f)
    return parse(docx_to_text(src))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--words", default=WORDS)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    entries = load_entries(args.src)
    with open(args.words, encoding="utf-8") as f:
        doc = json.load(f)
    index = {w["w"]: w for w in doc["words"]}

    hit, miss = [], []
    for word, e in entries.items():
        w = index.get(word)
        if not w:
            miss.append(word)
            continue
        senses = merge_senses(e["senses"])
        if senses:
            w["sm"] = senses
        if e["phrases"]:
            w["sp"] = e["phrases"]
        hit.append((word, len(e["phrases"]), len(senses)))

    covered = sum(1 for w in doc["words"] if w.get("sp") or w.get("sm"))
    print("本次导入 %d 词 ｜ 匹配 %d ｜ 未匹配 %d %s" %
          (len(entries), len(hit), len(miss), miss if miss else ""))
    print("词库累计覆盖 %d / %d（%.1f%%）" %
          (covered, len(doc["words"]), covered * 100.0 / len(doc["words"])))
    no_p = [h[0] for h in hit if h[1] == 0]
    if no_p:
        print("书上没给搭配:", no_p)

    if args.dry_run:
        print("（dry-run，未写入）")
        return
    # 和 build_words.py 保持一致：紧凑单行，别把 diff 撑成一万行
    with open(args.words, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
    print("已写入", os.path.normpath(args.words))


if __name__ == "__main__":
    main()
