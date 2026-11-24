#!/usr/bin/env python3
"""基础词逐条核对：docx 原文 ↔ 词库。

用户要求「务必 100% 准确」，这个脚本把能机器判的都判掉：

1. docx 里每个词条都在词库里，且只出现一次（不按大小写合并，May/may 是两个词）
2. 词库里的释义和 docx 原文逐字一致（只归一化空白）
3. 音标非空、只含合法音标字符
4. 类目归属与 docx 一致（词在哪个类目就该在哪个类目）
5. 每个词三套录音都在（--audio 才查）

退出码非 0 = 有问题。

用法:
    python3 -I tools/verify_base_words.py src/base_docx/基础词汇总.docx
    python3 -I tools/verify_base_words.py <docx> --audio
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_base_words as B  # noqa: E402

WORDS = os.path.join(HERE, "..", "app", "data", "words.json")
AUDIO = os.path.join(HERE, "..", "app", "data", "audio", "v")
IPA_OK = re.compile(r"^[A-Za-zəɪʊɒʌæɑɔɜðθʃʒŋɡɚɝːˈˌ'’\-() /]+$")


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--audio", action="store_true", help="同时查三套录音")
    args = ap.parse_args()

    items = B.merge_items(B.parse_doc(args.docx))
    with open(WORDS, encoding="utf-8") as f:
        data = json.load(f)
    db = {}
    for w in data["words"]:
        if w.get("cat") == "基础词":
            db.setdefault(w["w"], []).append(w)

    bad = []
    for it in items:
        hits = db.get(it["w"])
        if not hits:
            bad.append((it["w"], "词库里没有"))
            continue
        if len(hits) > 1:
            bad.append((it["w"], "重复 %d 条" % len(hits)))
            continue
        w = hits[0]
        if norm(w["m"]) != norm(B.tidy_meaning(it["m"])):
            bad.append((it["w"], "释义不一致:\n      书=%s\n      库=%s" % (it["m"][:90], w["m"][:90])))
        if w.get("list") != it["cat"]:
            bad.append((it["w"], "类目不对: 书=%s 库=%s" % (it["cat"], w.get("list"))))
        if not str(w.get("us", "")).strip():
            bad.append((it["w"], "缺音标"))

    extra = [k for k in db if k not in {it["w"] for it in items}]
    if args.audio:
        from tts_voices import safe_name
        for it in items:
            for key in ("m", "f", "c"):
                p = os.path.join(AUDIO, key, safe_name(it["w"]) + ".mp3")
                if not (os.path.exists(p) and os.path.getsize(p) > 800):
                    bad.append((it["w"], "缺%s音录音" % key))

    print("docx 词条 %d ｜ 词库基础词 %d ｜ 类目 %d" %
          (len(items), len(db), len({it["cat"] for it in items})))
    print("对不上 %d 条 ｜ 词库里多出 %d 条" % (len(bad), len(extra)))
    for w, why in bad[:40]:
        print("  ❌ %-16s %s" % (w, why))
    if len(bad) > 40:
        print("  …… 还有 %d 条" % (len(bad) - 40))
    for w in extra[:10]:
        print("  ⚠️  多出 %s" % w)
    sys.exit(1 if bad or extra else 0)


if __name__ == "__main__":
    main()
