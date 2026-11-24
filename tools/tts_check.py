#!/usr/bin/env python3
"""体检新录的音色文件：三套齐不齐、时长像不像一个单词、有没有半截的。

录制中途被打断（Ctrl-C、关机）会留下写了一半的 mp3，那种文件能打开、
但播到一半就没声——靠肉眼看不出来，只能挨个量时长。

用法:
    python3 -I tools/tts_check.py            # 只报告
    python3 -I tools/tts_check.py --fix      # 顺手删掉不合格的，下次录制会重录
"""
import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = os.path.join(HERE, "..", "app", "data", "words.json")
AUDIO = os.path.join(HERE, "..", "app", "data", "audio")
KEYS = ["m", "f", "c"]
MIN_SEC, MAX_SEC = 0.18, 5.0


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def check(path):
    if not os.path.exists(path):
        return "missing", 0.0
    size = os.path.getsize(path)
    if size < 1000:
        return "tiny", 0.0
    d = duration(path)
    if d < MIN_SEC:
        return "short", d
    if d > MAX_SEC:
        return "long", d
    return None, d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="删掉不合格的文件")
    ap.add_argument("--phrase", action="store_true", help="体检词组录音（时长上限放宽）")
    args = ap.parse_args()

    global MAX_SEC
    if args.phrase:
        MAX_SEC = 9.0                    # 「a collection of geniuses」这种能念到六七秒

    with open(WORDS, encoding="utf-8") as f:
        # 教材词看有道录音，基础词本来就没有，按 v 字段判断
        words = [w for w in json.load(f)["words"]
                 if w.get("us_audio") or w.get("cat") == "基础词"]

    jobs = []
    for w in words:
        name = w["w"].lower().replace(" ", "_").replace("/", "_")
        if args.phrase:
            idx = 0
            for b in (w.get("sb") or []):
                if b.get("k") != "例":
                    continue
                if (b.get("p") or "").strip():
                    for k in KEYS:
                        jobs.append((w["w"], k, os.path.join(AUDIO, "ph", k, "%s_%d.mp3" % (name, idx))))
                idx += 1
        else:
            for k in KEYS:
                jobs.append((w["w"], k, os.path.join(AUDIO, "v", k, name + ".mp3")))

    def run(j):
        word, k, p = j
        kind, d = check(p)
        return (word, k, p, kind, d)

    bad = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for word, k, p, kind, d in ex.map(run, jobs):
            if kind:
                bad.append((word, k, kind, d, p))

    total = len(jobs)
    print("检查 %d 个文件（%d 词 × %d 套）" % (total, len(words), len(KEYS)))
    if not bad:
        print("✅ 全部合格")
        return
    stat = {}
    for word, k, kind, d, p in bad:
        stat[kind] = stat.get(kind, 0) + 1
    print("不合格 %d 个：%s" % (len(bad), stat))
    for word, k, kind, d, p in bad[:30]:
        print("  [%s] %-18s %-7s %.2fs" % (k, word, kind, d))
    if len(bad) > 30:
        print("  …… 还有 %d 个" % (len(bad) - 30))
    if args.fix:
        n = 0
        for word, k, kind, d, p in bad:
            if os.path.exists(p):
                os.remove(p)
                n += 1
        print("已删除 %d 个，重跑 tts_voices.py 会补上" % n)
    else:
        print("加 --fix 可以删掉它们，下次录制自动补")


if __name__ == "__main__":
    main()
