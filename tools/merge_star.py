#!/usr/bin/env python3
"""把《词汇闪过》解析结果挂进词库：每个词多一个 `sb` 字段。

`sb` 是按**书本顺序**排好的块列表，书上有什么就有什么：

    {"k": "记", "v": "本身为词根，意为“前”→…"}     记忆法
    {"k": "义", "pos": "n.", "def": "[C,U] 进步；进展"}
    {"k": "例", "p": "scientific advances", "t": "科学进步"}
    {"k": "扩", "v": "[族] advancement n. 进步"}      派生
    {"k": "近", "v": "progressive a. 先进的"}
    {"k": "反", "v": "primitive a. 落后的"}

分开存（释义一坨、词组一坨）不行：书上是一个义项下面跟几条例句再接下个义项，
必须按顺序存才能还原成一模一样。

有道来的 m（释义）原样保留：书上还没导入的词继续用有道显示。

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

from parse_star import docx_to_text, parse, phrases_of, senses_of  # noqa: E402

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
        w["sb"] = e["blocks"]
        w.pop("sm", None)          # 早期版本的两个字段，统一到 sb
        w.pop("sp", None)
        hit.append((word, len(phrases_of(e["blocks"])), len(senses_of(e["blocks"]))))

    covered = sum(1 for w in doc["words"] if w.get("sb"))
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
