#!/usr/bin/env python3
"""Kokoro 本地神经网络发音 —— 替换有道的旧录音。

不联网、不走 API，模型在本机跑（~/tts-models）。3212 个词一次跑完，
音色统一、每个词咬字一致，不会出现有道那种不同来源录音质量参差的问题。

用法:
    # 试听：生成候选音色样例
    python3 tools/tts_kokoro.py --samples --out /tmp/tts_sample

    # 全量：把词库里每个词重录一遍
    python3 tools/tts_kokoro.py --all --voice af_heart --speed 0.9

音色（v1.0）:
    男声  am_onyx（低沉浑厚）am_fenrir am_michael bm_george（英式稳重）
    女声  af_sarah（沉稳御姐）af_heart（自然亲和）bf_emma（英式优雅）
    甜声  af_sky（年轻轻快）af_nicole（轻声）af_aoede
"""
import argparse
import array
import json
import os
import subprocess
import sys
import wave

MODEL_DIR = os.path.expanduser("~/tts-models")
MODEL = os.path.join(MODEL_DIR, "kokoro-v1.0.onnx")
VOICES = os.path.join(MODEL_DIR, "voices-v1.0.bin")

WORDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "data", "words.json")

# 试听用：一个单词 + 一条真实搭配，听得出咬字和语调
SAMPLE_WORDS = ["advance", "recognize", "opportunity"]
SAMPLE_PHRASE = "advances in technology"

CANDIDATES = [
    ("am_onyx", "男声 · 稳重浑厚"),
    ("am_fenrir", "男声 · 厚重有力"),
    ("bm_george", "男声 · 英式稳重"),
    ("af_sarah", "女声 · 御姐高级教师"),
    ("af_heart", "女声 · 自然亲和"),
    ("bf_emma", "女声 · 英式优雅"),
    ("af_sky", "甜声 · 年轻轻快"),
    ("af_nicole", "甜声 · 轻声细语"),
]


def write_wav(path, samples, sr=24000):
    pcm = array.array("h")
    for s in samples:
        v = int(max(-1.0, min(1.0, float(s))) * 32767)
        pcm.append(v)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(pcm.tobytes())


def to_mp3(wav, mp3, bitrate="96k"):
    """单词几十 KB 就够，压成 mp3 让手机缓存轻一点。"""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                    "-codec:a", "libmp3lame", "-b:a", bitrate, mp3], check=True)


def load():
    from kokoro_onnx import Kokoro
    return Kokoro(MODEL, VOICES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", action="store_true", help="生成各音色试听样例")
    ap.add_argument("--all", action="store_true", help="全量重录词库")
    ap.add_argument("--voice", default="af_heart")
    ap.add_argument("--speed", type=float, default=0.9, help="1.0 标准，0.9 慢一档")
    ap.add_argument("--out", default="/tmp/tts_sample")
    ap.add_argument("--only", default="", help="只重录这些词，逗号分隔（调试用）")
    args = ap.parse_args()

    if not os.path.exists(MODEL):
        sys.exit("缺少模型: " + MODEL)
    os.makedirs(args.out, exist_ok=True)
    k = load()

    if args.samples:
        for vid, label in CANDIDATES:
            for i, text in enumerate(SAMPLE_WORDS + [SAMPLE_PHRASE]):
                samples, sr = k.create(text, voice=vid, speed=args.speed, lang="en-us")
                wav = os.path.join(args.out, "%s_%d.wav" % (vid, i))
                write_wav(wav, samples, sr)
                to_mp3(wav, os.path.join(args.out, "%s_%d.mp3" % (vid, i)))
                os.remove(wav)
            print("生成", vid, label)
        return

    if args.all:
        with open(WORDS, encoding="utf-8") as f:
            doc = json.load(f)
        todo = doc["words"]
        if args.only:
            keep = set(args.only.split(","))
            todo = [w for w in todo if w["w"] in keep]
        base = os.path.join(os.path.dirname(WORDS), "audio")
        done = 0
        for w in todo:
            rel = "neu/%s.mp3" % w["w"].replace(" ", "_")
            dst = os.path.join(base, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst) and os.path.getsize(dst) > 800:
                done += 1
                continue                        # 断点续跑：已经录好的不再重来
            samples, sr = k.create(w["w"], voice=args.voice, speed=args.speed, lang="en-us")
            wav = dst + ".wav"
            write_wav(wav, samples, sr)
            to_mp3(wav, dst)
            os.remove(wav)
            done += 1
            if done % 100 == 0:
                print("已录 %d / %d" % (done, len(todo)), flush=True)
        print("完成 %d 词" % done)


if __name__ == "__main__":
    main()
