#!/usr/bin/env python3
"""用 macOS Vision 引擎识别教材照片里的单词，输出带坐标的 JSON。

自动尝试 0/90/180/270 四个方向，选识别出单词最多的那个。

用法:
    /tmp/ocrvenv/bin/python -I vision_ocr.py out.json 图片1 图片2 ...
"""
import base64
import json
import os
import re
import sys
import tempfile

import Quartz
import Vision
from Foundation import NSURL
from PIL import Image, ImageOps, ImageFilter

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*$")


def ocr_cgimage(cg, correct=False):
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg, None)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(0)          # 0 = accurate
    req.setUsesLanguageCorrection_(correct)
    req.setRecognitionLanguages_(["en-US"])
    ok, err = handler.performRequests_error_([req], None)
    if not ok:
        return []
    out = []
    for obs in (req.results() or []):
        cands = obs.topCandidates_(1)
        if not cands:
            continue
        top = cands[0]
        b = obs.boundingBox()
        out.append({
            "text": str(top.string()),
            "conf": round(float(top.confidence()), 3),
            "x": round(float(b.origin.x), 4),
            "y": round(float(b.origin.y), 4),
            "w": round(float(b.size.width), 4),
            "h": round(float(b.size.height), 4),
        })
    return out


def ocr_file(path, rotation=0, correct=False):
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        if rotation:
            img = img.rotate(rotation, expand=True)
        img = img.convert("RGB")
        img.save(tmp.name)
        url = NSURL.fileURLWithPath_(tmp.name)
        src = Quartz.CGImageSourceCreateWithURL(url, None)
        cg = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
        return ocr_cgimage(cg, correct)
    finally:
        os.unlink(tmp.name)


def layout_score(items):
    """判断方向是否摆正：书页上「Word List N」标题必须在单词块上方，
    且每行大约 4~5 个词（教材是 4 列排版）。"""
    toks = [i for i in items if WORD_RE.match(i["text"].strip()) and len(i["text"].strip()) > 1]
    if not toks:
        return -1
    ys = sorted(i["y"] for i in toks)
    span = (ys[-1] - ys[0]) or 1
    tol = span * 0.02
    rows, cur = 1, ys[0]
    for y in ys[1:]:
        if y - cur > tol:
            rows += 1
        cur = y
    per_row = len(toks) / rows
    score = 0
    if 3.0 <= per_row <= 6.0:
        score += 500
    # 标题位置：找 Word List 那几个字，它得在单词块的上方
    title = [i for i in items if re.search(r"word\s*list", i["text"], re.I)]
    if title:
        ty = max(t["y"] for t in title)
        if ty > ys[-1] + 0.01:
            score += 1000
        elif ty < ys[0] - 0.01:
            score -= 1000
    return score


def count_words(items):
    return sum(1 for i in items if WORD_RE.match(i["text"].strip()) and len(i["text"].strip()) > 1)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    correct = "--correct" in sys.argv
    argv = [a for a in sys.argv[1:] if a != "--correct"]
    out_path, paths = argv[0], argv[1:]
    result = {}
    for p in paths:
        best, best_score, best_n, best_rot = [], -1, 0, 0
        for rot in (0, 270, 90, 180):
            try:
                items = ocr_file(p, rot, correct)
            except Exception as e:  # noqa: BLE001
                print("  ! %s 旋转%3d 失败 %s" % (os.path.basename(p), rot, e), file=sys.stderr)
                continue
            n = count_words(items)
            # 摆正的特征：同一行能凑齐多个词。用这个判定方向，词数只作次要参考
            score = layout_score(items) * 10 + n
            if score > best_score:
                best, best_score, best_n, best_rot = items, score, n, rot
        result[os.path.abspath(p)] = {"rotation": best_rot, "items": best}
        print("%-14s 方向%3d  单词 %d" % (os.path.basename(p), best_rot, best_n), file=sys.stderr)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("已写入 %s" % out_path, file=sys.stderr)


if __name__ == "__main__":
    main()
