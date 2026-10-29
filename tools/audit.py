#!/usr/bin/env python3
"""词库体检：确认每个词的读音都靠得住。

查四件事：
1. 音标非空、字符合法、长度正常
2. 音频文件存在、大小正常、能认出格式
3. 有没有两个词共用同一个音频文件（串音）
4. 单词本身有没有异常（重复、超短、可疑）

用法:
    python3 -I audit.py ../app/data/words.json
"""
import hashlib
import io
import json
import os
import re
import sys
from collections import defaultdict

# 括号是可选音标记，如 ˈkæptʃə(r)、ˈbæt(ə)l
IPA_OK = re.compile(r"^[a-zæɑɒɔəɜɪʊʌʃʒθðŋɡʤʧː'ˈˌ.\-() ]+$")
MIN_AUDIO = 2000      # 小于这个基本是错误页/空音频
MAX_AUDIO = 400000    # 大于这个不正常


def audio_ext(blob):
    if blob.startswith(b"ID3") or blob[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xfa"):
        return "mp3"
    if blob.startswith(b"RIFF"):
        return "wav"
    if blob.startswith(b"OggS"):
        return "ogg"
    if blob[4:8] == b"ftyp":
        return "m4a"
    return None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../app/data/words.json"
    with io.open(path, encoding="utf-8") as f:
        data = json.load(f)
    root = os.path.dirname(os.path.abspath(path))
    words = data["words"]

    problems = defaultdict(list)
    hashes = defaultdict(list)
    sizes = []

    for w in words:
        for accent, key, ipa in (("us", "us_audio", w.get("us")), ("uk", "uk_audio", w.get("uk"))):
            # --- 音标 ---
            if not ipa:
                problems["音标为空"].append(f"{w['w']}({accent})")
            elif not IPA_OK.match(ipa.lower()):
                problems["音标含异常字符"].append(f"{w['w']}({accent}): {ipa}")
            elif len(ipa) < 2 or len(ipa) > 40:
                problems["音标长度异常"].append(f"{w['w']}({accent}): {ipa}")

            # --- 音频 ---
            rel = w.get(key)
            if not rel:
                problems["音频缺失"].append(f"{w['w']}({accent})")
                continue
            fp = os.path.join(root, rel)
            if not os.path.exists(fp):
                problems["音频文件不存在"].append(f"{w['w']}({accent}) -> {rel}")
                continue
            size = os.path.getsize(fp)
            sizes.append(size)
            if not audio_ext(open(fp, "rb").read(64)):
                problems["音频格式认不出"].append(f"{w['w']}({accent}) {size}B")
            if size < MIN_AUDIO:
                problems["音频过小"].append(f"{w['w']}({accent}) {size}B")
            if size > MAX_AUDIO:
                problems["音频过大"].append(f"{w['w']}({accent}) {size}B")

            # --- 串音：不同单词共享同一份音频 ---
            with open(fp, "rb") as fh:
                h = hashlib.md5(fh.read()).hexdigest()
            hashes[h].append((w["w"], accent, rel))

    for h, items in hashes.items():
        names = {i[0] for i in items}
        if len(names) > 1:
            problems["不同单词共用同一音频"].append(
                " / ".join(f"{n}@{a}" for n, a, _ in items))

    # --- 单词本身 ---
    seen = defaultdict(int)
    for w in words:
        seen[w["w"]] += 1
    for word, n in seen.items():
        if n > 1:
            problems["单词重复"].append(f"{word} ×{n}")
    for w in words:
        if len(w["w"]) <= 2:
            problems["超短词(可能是误识别)"].append(w["w"])
        if not re.fullmatch(r"[a-z][a-z'\-]*", w["w"]):
            problems["词形异常"].append(w["w"])

    print("=" * 62)
    print("词库体检：%d 词 ｜ %d 个音频 ｜ 音频大小 %d~%dB（中位 %dB）" % (
        len(words), len(sizes), min(sizes) if sizes else 0,
        max(sizes) if sizes else 0, sorted(sizes)[len(sizes) // 2] if sizes else 0))
    print("=" * 62)
    if not problems:
        print("✅ 全部通过：没有空音标、没有坏音频、没有串音、没有重复词")
        return
    total = 0
    for kind, items in problems.items():
        total += len(items)
        print("\n⚠️  %s（%d 项）" % (kind, len(items)))
        for it in items[:40]:
            print("    " + it)
        if len(items) > 40:
            print("    ... 还有 %d 项" % (len(items) - 40))
    print("\n共 %d 项需要复核" % total)


if __name__ == "__main__":
    main()
