#!/usr/bin/env python3
"""按「音色」批量重录词库 —— 一个词录三套，App 里随时换着听。

三个音色（用户选定，全部原声不变调）：

    m  男声 · 厚重有力          am_fenrir
    f  女声 · 自然亲和          af_heart
    c  夹子音 · 甜、最像真人     af_bella

输出到 `app/data/audio/v/<key>/<word>.mp3`，词库里写进一个 `v` 字段：

    "v": {"m": "audio/v/m/advance.mp3", "f": "...", "c": "..."}

原来的 us_audio / uk_audio（有道老录音）一个字节都不动，留作后备。

用法:
    # 分开跑，三个终端并行（每个吃 3~4 个核，合起来刚好）
    python3 tools/tts_voices.py --key m
    python3 tools/tts_voices.py --key f
    python3 tools/tts_voices.py --key c

    # 全录完后写进 words.json
    python3 tools/tts_voices.py --apply
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from tts_kokoro import WORDS, write_wav, to_mp3, load  # noqa: E402

# key → (Kokoro 音色, 界面上的名字)
VOICES = {
    "m": ("am_fenrir", "男声 · 厚重有力"),
    "f": ("af_heart", "女声 · 自然亲和"),
    "c": ("af_bella", "夹子音 · 甜"),
}
AUDIO = os.path.join(os.path.dirname(WORDS), "audio")


def safe_name(word):
    return word.lower().replace(" ", "_").replace("/", "_")


def target(w, key):
    return os.path.join(AUDIO, "v", key, safe_name(w["w"]) + ".mp3")


def record(key, speed, limit=0):
    voice, label = VOICES[key]
    with open(WORDS, encoding="utf-8") as f:
        words = json.load(f)["words"]
    todo = [w for w in words if w.get("us_audio")]
    if limit:
        todo = todo[:limit]
    k = load()
    done = 0
    for w in todo:
        dst = target(w, key)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and os.path.getsize(dst) > 800:
            done += 1
            continue                        # 断点续跑：已经录好的不再重来
        samples, sr = k.create(w["w"], voice=voice, speed=speed, lang="en-us")
        wav = dst + ".wav"
        write_wav(wav, samples, sr)
        to_mp3(wav, dst)
        os.remove(wav)
        done += 1
        if done % 100 == 0:
            print("%s 已录 %d / %d" % (label, done, len(todo)), flush=True)
    print("%s 完成 %d 词" % (label, done))


def apply():
    with open(WORDS, encoding="utf-8") as f:
        doc = json.load(f)
    hit, miss = 0, []
    for w in doc["words"]:
        if not w.get("us_audio"):
            continue                        # ComfyUI 的模型名继续走系统 TTS
        paths = {}
        for key in VOICES:
            p = target(w, key)
            if os.path.exists(p):
                paths[key] = "audio/v/%s/%s.mp3" % (key, safe_name(w["w"]))
        if len(paths) == len(VOICES):
            w["v"] = paths
            hit += 1
        elif paths:
            miss.append(w["w"])
    if miss:
        print("三套不齐、未写入 %d 词：%s" % (len(miss), miss[:15]))
    # 和 build_words.py 一致：紧凑单行，别把 diff 撑成一万行
    with open(WORDS, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
    print("已写入 words.json：%d 词带三套录音" % hit)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", choices=list(VOICES), help="录哪一套")
    ap.add_argument("--speed", type=float, default=0.92, help="1.0 标准，0.92 慢一点点")
    ap.add_argument("--limit", type=int, default=0, help="只录前 N 个（测速用）")
    ap.add_argument("--apply", action="store_true", help="写进 words.json")
    args = ap.parse_args()
    if args.apply:
        apply()
    elif args.key:
        record(args.key, args.speed, args.limit)
    else:
        ap.error("要么 --key m/f/c，要么 --apply")


if __name__ == "__main__":
    main()
