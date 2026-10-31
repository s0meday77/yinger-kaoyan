#!/usr/bin/env python3
"""把 ComfyUI 词汇并入词库，作为独立类别「ComfyUI词汇」。

词表在 comfy_words.json，释义人工撰写（有道的通用释义对不上专业语境）。
音标和真人录音能查到的就填，查不到留空，前端自动走系统 TTS。

用法:
    python3 -I tools/build_comfy_words.py
然后照常跑 json2js.py 导出 words.js。
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_words as bw  # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "app", "data")


def split_page(n, k):
    """把 n 个词平均分到 k 天，余数给前面几天（和教材词一致）。"""
    k = max(1, min(k, n))
    base, rem = divmod(n, k)
    return [base + (1 if i < rem else 0) for i in range(k)]


def lookup(word):
    """查有道音标；查不到返回空串。"""
    try:
        data = bw.cached_json(word)
    except Exception:
        return "", ""
    ec = data.get("ec") or {}
    head = ec.get("word") or [{}]
    if isinstance(head, list):
        head = head[0] if head else {}
    if not isinstance(head, dict):
        head = {}
    return bw.clean_ipa(head.get("usphone", "")), bw.clean_ipa(head.get("ukphone", ""))


def main():
    with open(os.path.join(HERE, "comfy_words.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cat = cfg["category"]
    dpp = cfg.get("daysPerPage", 4)

    words, pages = [], []
    gday = 0
    no_ipa = no_audio = 0

    # 有道查询是逐个串行的话 80 个词要跑十几分钟，容易被打断，改成并发
    def fetch(item):
        w = item["w"]
        us, uk = lookup(w)
        return w, us, uk, bw.ensure_audio(w, "us", DATA), bw.ensure_audio(w, "uk", DATA)

    all_items = [it for page in cfg["pages"] for it in page["words"]]
    with ThreadPoolExecutor(max_workers=8) as ex:
        fetched = {r[0]: r for r in ex.map(fetch, all_items)}
    print("已查完 %d 个词" % len(fetched), flush=True)

    for idx, page in enumerate(cfg["pages"], 1):
        ws = page["words"]
        rows, pos = [], 0
        for d, n in enumerate(split_page(len(ws), dpp), 1):
            gday += 1
            for item in ws[pos:pos + n]:
                w = item["w"]
                _, us, uk, aus, auk = fetched[w]
                if not us and not uk:
                    no_ipa += 1
                if not aus and not auk:
                    no_audio += 1
                words.append({
                    "w": w, "us": us, "uk": uk, "m": item["m"],
                    "us_audio": aus, "uk_audio": auk,
                    "cat": cat, "list": page.get("short") or page["name"],
                    "page": idx, "day": d, "gday": gday,
                })
            rows.append({"day": d, "count": n, "gday": gday})
            pos += n
        pages.append({
            "cat": cat, "index": idx, "name": page["name"],
            "short": page.get("short") or page["name"],
            "count": len(ws), "days": rows,
        })
        print("第 %d 页 %-6s %2d 词 / %d 天" % (idx, page["name"], len(ws), len(rows)))

    category = {
        "name": cat,
        "count": len(words),
        "pageCount": len(pages),
        "dayCount": gday,
        "days": [{"day": r["gday"], "count": r["count"]} for p in pages for r in p["days"]],
        "pages": pages,
    }

    path = os.path.join(DATA, "words.json")
    with open(path, encoding="utf-8") as f:
        db = json.load(f)
    db["words"] = [w for w in db["words"] if w.get("cat") != cat]
    db["categories"] = [c for c in db["categories"] if c.get("name") != cat]
    db["words"].extend(words)
    db["categories"].append(category)
    db["count"] = len(db["words"])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, separators=(",", ":"))

    print("并入完成：%d 词 / %d 页 / %d 天" % (len(words), len(pages), gday))
    print("无音标 %d 个（前端自动隐藏）｜无真人录音 %d 个（自动走系统 TTS）" % (no_ipa, no_audio))
    print("词库总数：%d" % db["count"])


if __name__ == "__main__":
    main()
