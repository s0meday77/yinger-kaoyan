#!/usr/bin/env python3
"""「夹子音」候选：林志玲那种甜、软、气声多的女声。

Kokoro 自带的音色都偏"标准播音"，甜度不够。林志玲音的三个特征是
**音调高、气声重、语速慢**，所以除了挑本来就清的底嗓，再叠加提高音调：

    asetrate=24000*R → aresample=24000 → atempo=1/R

音调升高 R 倍，速度再用 atempo 掰回来，时长不变、只变调门。
每个 +1 半音，R = 2^(1/12)。+4 半音大概是普通女声到"甜妹"的距离。

用法:
    python3 tools/tts_cute.py --out /tmp/cute
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from tts_kokoro import MODEL, VOICES, SAMPLE_WORDS, SAMPLE_PHRASE, write_wav, load  # noqa: E402
from tts_kokoro import to_mp3  # noqa: E402

SR = 24000
# 底嗓按"本身够不够甜"排：bella 最自然，sky/alloy 年轻，aoede 轻快，nicole 气声最重
BASES = [
    ("af_bella", "甜 · 最自然也最像真人"),
    ("af_sky", "嫩 · 年轻轻快"),
    ("af_alloy", "软 · 绵一点"),
    ("af_aoede", "俏 · 带点上扬"),
    ("af_nicole", "气 · 轻声细语"),
]
SEMITONES = [0, 3, 5]


def pitch(path, semitones):
    """升高 semitones 个半音，时长不变；就地覆盖原文件。"""
    if not semitones:
        return
    r = 2 ** (semitones / 12.0)
    tmp = path + ".t.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", path,
        "-af", "asetrate=%d*%.6f,aresample=%d,atempo=%.6f" % (SR, r, SR, 1 / r),
        "-codec:a", "libmp3lame", "-b:a", "96k", tmp,
    ], check=True)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/cute")
    ap.add_argument("--speed", type=float, default=0.9)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    k = load()
    texts = SAMPLE_WORDS + [SAMPLE_PHRASE]
    for vid, label in BASES:
        for semi in SEMITONES:
            tag = "%s_s%d" % (vid, semi)
            for i, text in enumerate(texts):
                samples, sr = k.create(text, voice=vid, speed=args.speed, lang="en-us")
                wav = os.path.join(args.out, tag + "_%d.wav" % i)
                write_wav(wav, samples, sr)
                mp3 = os.path.join(args.out, tag + "_%d.mp3" % i)
                to_mp3(wav, mp3)
                os.remove(wav)
                pitch(mp3, semi)
            print("生成", tag, label, "+%d 半音" % semi, flush=True)

    meta = [{"id": vid, "tag": "%s_s%d" % (vid, s), "label": label, "semi": s}
            for vid, label in BASES for s in SEMITONES]
    with open(os.path.join(args.out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print("完成", len(meta), "组")


if __name__ == "__main__":
    main()
