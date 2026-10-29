#!/usr/bin/env python3
"""拿系统自带词表（/usr/share/dict/words，23.6 万词）离线校验每个词形是否存在。

这一步专门抓 OCR 认错：把 finance 认成 tinance 时，音标和录音都会"正确"地
读一个不存在的词，只有词形校验能发现。

用法:
    python3 -I wordcheck.py ../app/data/words.json
"""
import io
import json
import re
import sys

DICT = "/usr/share/dict/words"


def variants(w):
    """列出一个词可能的原形/屈折形式，任一命中就算合法。"""
    out = {w}
    if w.endswith("ies"):
        out.add(w[:-3] + "y")
    if w.endswith("ied"):
        out.add(w[:-3] + "y")
    if w.endswith("es"):
        out.add(w[:-2])
    if w.endswith("s"):
        out.add(w[:-1])
    if w.endswith("ed"):
        out.add(w[:-2])
        out.add(w[:-1])
        out.add(w[:-3])          # 去掉 e，如 moved -> mov? 不合法，但 harmless
    if w.endswith("ing"):
        out.add(w[:-3])
        out.add(w[:-3] + "e")
        if len(w) > 4 and w[-4] == w[-5]:
            out.add(w[:-4])      # running -> run
    if w.endswith("ly"):
        out.add(w[:-2])
    if w.endswith("er"):
        out.add(w[:-2])
        out.add(w[:-1])
    if w.endswith("est"):
        out.add(w[:-3])
        out.add(w[:-2])
    if w.endswith("ness") or w.endswith("ment") or w.endswith("tion"):
        out.add(w)
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../app/data/words.json"
    with io.open(path, encoding="utf-8") as f:
        words = json.load(f)["words"]

    vocab = set()
    with io.open(DICT, encoding="utf-8", errors="ignore") as f:
        for line in f:
            vocab.add(line.strip().lower())

    unknown = []
    for w in words:
        word = w["w"].lower()
        if not any(v in vocab for v in variants(word)):
            unknown.append(w["w"])

    print("=" * 58)
    print("词形离线校验：%d 个词对照系统词表 %d 条" % (len(words), len(vocab)))
    print("=" * 58)
    if not unknown:
        print("✅ 全部通过：每个词都能在系统词表里找到")
        return
    print("\n⚠️  系统词表里找不到（共 %d 个，需要人工确认）：" % len(unknown))
    for w in unknown:
        print("    " + w)
    print("\n提示：Webster's 第二版是老词表，部分现代词（如 online、smartphone）"
          "\n      本来就不收录，属正常。真正要警惕的是看起来像少/多了一个字母的怪词。")


if __name__ == "__main__":
    main()
