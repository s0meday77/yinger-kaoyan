#!/usr/bin/env python3
"""拿第二家词典（Wiktionary 数据的 dictionaryapi.dev）独立核对每个词。

两类可疑：
A. 这家词典根本查不到这个词  → 很可能是 OCR 认错的词（最重要）
B. 查得到，但音标和有道差很多 → 需要人工听一下

用法:
    python3 -I crosscheck.py ../app/data/words.json [--out ../src/crosscheck.json]
"""
import argparse
import io
import json
import re
import socket
import sys
import time
import urllib.parse
import urllib.request

# 本机 IPv6 出网会卡在 SSL 握手（要等 20 多秒才超时），强制走 IPv4，0.6 秒一个词
_orig_gai = socket.getaddrinfo


def _gai_v4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_gai(host, port, socket.AF_INET, type, proto, flags)


socket.getaddrinfo = _gai_v4


def get_json(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def norm(s):
    """把两家音标归一化到可比较的形式。"""
    s = (s or "").lower()
    s = s.replace("ː", "").replace("ˈ", "").replace("ˌ", "").replace("'", "")
    s = s.replace("ɡ", "g").replace("ɹ", "r").replace("ʤ", "dʒ").replace("ʧ", "tʃ")
    s = re.sub(r"[()\[\]/\s.\-]", "", s)
    return s


def sim(a, b):
    """简单的字符重合度，够用来筛可疑项。"""
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    return inter / max(len(sa), len(sb))


def lookup(word):
    url = "https://api.dictionaryapi.dev/api/v2/entries/en/" + urllib.parse.quote(word)
    try:
        data = get_json(url)
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "code", None)
        if code == 404:
            return None, None
        raise
    if not isinstance(data, list) or not data:
        return None, None
    entry = data[0]
    ipa = entry.get("phonetic") or ""
    if not ipa:
        for p in entry.get("phonetics", []) or []:
            if p.get("text"):
                ipa = p["text"]
                break
    return entry.get("word"), ipa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words_json", nargs="?", default="../app/data/words.json")
    ap.add_argument("--out", default="../src/crosscheck.json")
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    with io.open(args.words_json, encoding="utf-8") as f:
        words = json.load(f)["words"]

    missing, differ, same = [], [], []
    for i, w in enumerate(words, 1):
        word = w["w"]
        try:
            found, ipa = lookup(word)
        except Exception as e:  # noqa: BLE001
            print("  ! %-16s 查询出错 %s" % (word, str(e)[:40]), file=sys.stderr)
            time.sleep(2)
            continue
        if found is None:
            missing.append(word)
        else:
            ours = norm(w.get("us") or w.get("uk"))
            theirs = norm(ipa)
            score = sim(ours, theirs)
            (same if score >= 0.6 else differ).append(
                {"w": word, "ours": w.get("us"), "theirs": ipa, "score": round(score, 3)})
        if i % 50 == 0:
            print("  进度 %d/%d ｜ 查不到 %d ｜ 差异 %d" % (i, len(words), len(missing), len(differ)),
                  file=sys.stderr)
        time.sleep(args.sleep)

    print("\n" + "=" * 60)
    print("交叉核对结果：一致 %d ｜ 音标差异 %d ｜ 查不到 %d" % (len(same), len(differ), len(missing)))
    print("=" * 60)
    if missing:
        print("\n⚠️ 查不到的词（最可能是 OCR 认错）：")
        for w in missing:
            print("    " + w)
    if differ:
        print("\n🔍 音标差异较大的（可能是英美差异，也可能有问题）：")
        for d in sorted(differ, key=lambda x: x["score"])[:60]:
            print("    %-16s 有道 %-18s 词典 %-18s 相似度 %.2f" %
                  (d["w"], d["ours"], d["theirs"], d["score"]))

    with io.open(args.out, "w", encoding="utf-8") as f:
        json.dump({"missing": missing, "differ": differ}, f, ensure_ascii=False, indent=1)
    print("\n明细已写入 %s" % args.out)


if __name__ == "__main__":
    main()
