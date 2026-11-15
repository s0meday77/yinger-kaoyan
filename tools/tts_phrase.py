#!/usr/bin/env python3
"""词组也用同一套音色录 —— 点 `advances in technology` 时不能再冒出手机自带的声音。

路径是约定好的，不往 words.json 里塞路径（818 条 × 3 套太占地方）：

    app/data/audio/ph/<key>/<单词>_<序号>.mp3

`序号` 就是这个词 sb 块里第几条「例」，从前到后数，和前端渲染的顺序一一对应。

用法:
    python3 tools/tts_phrase.py --key f        # 录一套
    python3 tools/tts_phrase.py --key f --limit 20
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from tts_kokoro import WORDS, write_wav, to_mp3, load  # noqa: E402
from tts_voices import VOICES, safe_name  # noqa: E402

AUDIO = os.path.join(os.path.dirname(WORDS), "audio")


def phrase_target(word, idx, key):
    return os.path.join(AUDIO, "ph", key, "%s_%d.mp3" % (safe_name(word), idx))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", choices=list(VOICES), required=True)
    ap.add_argument("--speed", type=float, default=0.92)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    voice, label = VOICES[args.key]
    with open(WORDS, encoding="utf-8") as f:
        words = json.load(f)["words"]

    jobs = []
    for w in words:
        blocks = w.get("sb") or []
        idx = 0
        for b in blocks:
            if b.get("k") != "例":
                continue
            p = (b.get("p") or "").strip()
            if p:
                jobs.append((w["w"], idx, p))
            idx += 1
    if args.limit:
        jobs = jobs[: args.limit]

    k = load()
    done = 0
    for word, idx, text in jobs:
        dst = phrase_target(word, idx, args.key)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and os.path.getsize(dst) > 800:
            done += 1
            continue
        samples, sr = k.create(text, voice=voice, speed=args.speed, lang="en-us")
        wav = dst + ".wav"
        write_wav(wav, samples, sr)
        to_mp3(wav, dst)
        os.remove(wav)
        done += 1
        if done % 100 == 0:
            print("%s 词组已录 %d / %d" % (label, done, len(jobs)), flush=True)
    print("%s 词组完成 %d 条" % (label, done))


if __name__ == "__main__":
    main()
