#!/usr/bin/env python3
"""词表 → App 词库（抓英美音标、下载真人发音、按天分课）。

words.txt 里用 "# 列表名" 这样的行标记分段，例如：
    # Word List 1
    advance
    advanced
    # Word List 2
    critic

天数规则：默认每天 per_day 个词，**按顺序连续排**。再导入新的一页时，先补齐
上一天没满的额度，然后往下续天数——已经分好的天不会被打乱，学习进度不会错位。

用法:
    python3 -I build_words.py ../src/words.txt --out ../app/data/words.json
"""
import argparse
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import Counter

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
AUDIO_BASE = "https://dict.youdao.com/dictvoice"


def get(url, binary=False, timeout=15, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://dict.youdao.com/"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read() if binary else r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.6 * (i + 1))
    raise last


def cached_json(word):
    os.makedirs(CACHE, exist_ok=True)
    fp = os.path.join(CACHE, "json_" + hashlib.md5(word.encode()).hexdigest() + ".json")
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    data = json.loads(get("https://dict.youdao.com/jsonapi?q=" + urllib.parse.quote(word)))
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return data


def short_meanings(data, limit=3):
    """摘出「词性 + 简短释义」，滤掉人名地名等词典噪声。"""
    out = []
    ec = data.get("ec") or {}
    for block in (ec.get("word") or [])[:1]:
        for item in block.get("trs", []):
            for lines in item.get("tr") or []:
                s = "".join(lines.get("l", {}).get("i", []) or []).strip()
                if not s or "【" in s or "人名" in s or "地名" in s:
                    continue
                s = re.split(r"[；;]", s)[0]
                s = re.sub(r"^([a-z]+\.)\s*", r"\1 ", s)
                s = s[:20].strip()
                if s and s not in out:
                    out.append(s)
                if len(out) >= limit:
                    return out
    return out


def clean_ipa(s):
    """去掉零宽字符，只保留第一个读音——和实际播放的录音对齐。"""
    s = (s or "").replace("\u200b", "").replace("\u200c", "").strip()
    return s.split(";")[0].strip()


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


def safe_name(word):
    return re.sub(r"[^a-z0-9_-]", "_", word.lower())


def ensure_audio(word, accent, outdir):
    safe = safe_name(word)
    stem = os.path.join(outdir, "audio", accent, safe)
    for ext in ("mp3", "wav", "ogg", "m4a"):
        if os.path.exists(stem + "." + ext) and os.path.getsize(stem + "." + ext) > 1000:
            return "audio/%s/%s.%s" % (accent, safe, ext)
    os.makedirs(os.path.dirname(stem), exist_ok=True)
    try:
        blob = get(AUDIO_BASE + "?audio=%s&type=%s" % (urllib.parse.quote(word), "2" if accent == "us" else "1"),
                   binary=True)
    except Exception:
        return None
    ext = audio_ext(blob)
    if len(blob) < 1000 or not ext:
        return None
    with open(stem + "." + ext, "wb") as f:
        f.write(blob)
    return "audio/%s/%s.%s" % (accent, safe, ext)


def split_label(label):
    """把 "# 高频词 · Word List 3" 拆成 (类别, 列表名)。"""
    if "·" in label:
        cat, lst = label.split("·", 1)
        return cat.strip(), lst.strip()
    return label.strip(), label.strip()


def parse_words(path):
    """返回 [(word, 原始标签)]，支持 "# 标签" 分段。"""
    items, cur = [], ""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                cur = line.lstrip("# ").strip()
                continue
            for w in re.split(r"[,，\s]+", line):
                w = w.lower()
                if re.fullmatch(r"[a-z][a-z'\-]*", w):
                    items.append((w, cur))
    return items


def split_page(n, k):
    """把 n 个词平均分成 k 天，除不尽的余数分给前面几天。"""
    k = max(1, min(k, n))
    base, rem = divmod(n, k)
    return [base + (1 if i < rem else 0) for i in range(k)]


def build_plan(items, days_per_page):
    """按教材「页」排学习计划：每页固定切 days_per_page 天，页内平均分。

    这样每一课都明确落在教材的某一页上，翻着书就能对得上。

    返回 (day_info, pages, cats)：
        day_info[w] = (页序号, 页内第几天, 本类全局第几天)
    """
    groups, order = {}, []
    for w, label in items:
        cat, lst = split_label(label)
        key = (cat, lst)
        if key not in groups:
            groups[key] = []
            order.append(key)          # 保持教材原有页序
        groups[key].append(w)

    day_info, pages, cat_order = {}, [], []
    gday = {}
    for cat, lst in order:
        if cat not in gday:
            gday[cat] = 0
            cat_order.append(cat)
        ws = groups[(cat, lst)]
        idx = sum(1 for p in pages if p["cat"] == cat) + 1
        rows, pos = [], 0
        for d, n in enumerate(split_page(len(ws), days_per_page), 1):
            gday[cat] += 1
            for w in ws[pos:pos + n]:
                day_info[w] = (idx, d, gday[cat])
            rows.append({"day": d, "count": n, "gday": gday[cat]})
            pos += n
        pages.append({"cat": cat, "index": idx, "name": lst,
                      "count": len(ws), "days": rows})

    cats = []
    for cat in cat_order:
        pgs = [p for p in pages if p["cat"] == cat]
        cats.append({
            "name": cat,
            "count": sum(p["count"] for p in pgs),
            "pageCount": len(pgs),
            "dayCount": sum(len(p["days"]) for p in pgs),
            "days": [{"day": d["gday"], "count": d["count"]} for p in pgs for d in p["days"]],
            "pages": pgs,
        })
    return day_info, pages, cats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words_file")
    ap.add_argument("--out", default="../app/data/words.json")
    ap.add_argument("--days-per-page", type=int, default=4, help="教材每页切成几天学")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=0.15)
    args = ap.parse_args()

    parsed = parse_words(args.words_file)
    seen, items = set(), []
    for w, lst in parsed:
        if w not in seen:
            seen.add(w)
            items.append((w, lst))
    if args.limit:
        items = items[: args.limit]
    print("待处理:", len(items))

    outdir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(outdir, exist_ok=True)

    day_info, pages, cats = build_plan(items, args.days_per_page)

    result, no_audio, no_ipa = [], [], []
    for i, (w, lst) in enumerate(items, 1):
        try:
            data = cached_json(w)
        except Exception as e:  # noqa: BLE001
            print("  ! %-16s 查询失败 %s" % (w, str(e)[:40]))
            data = {}
        head = ((data.get("ec") or {}).get("word") or [{}])[0]
        us = clean_ipa(head.get("usphone", ""))
        uk = clean_ipa(head.get("ukphone", ""))
        if not us and not uk:
            no_ipa.append(w)
        aus, auk = ensure_audio(w, "us", outdir), ensure_audio(w, "uk", outdir)
        if not aus or not auk:
            no_audio.append(w)
        cat, listname = split_label(lst)
        page, day, gday = day_info.get(w, (1, 1, 1))
        result.append({
            "w": w, "us": us or uk, "uk": uk or us,
            "m": "；".join(short_meanings(data)) or "（缺释义）",
            "us_audio": aus, "uk_audio": auk,
            "cat": cat, "list": listname,
            "page": page, "day": day, "gday": gday,
        })
        if i % 25 == 0:
            print("  进度 %d/%d" % (i, len(items)))
        time.sleep(args.sleep)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"daysPerPage": args.days_per_page, "count": len(result),
                   "categories": cats, "pages": pages, "words": result},
                  f, ensure_ascii=False, indent=1)

    print("完成 -> %s" % args.out)
    print("词数 %d ｜ 无音标 %s ｜ 缺音频 %s" %
          (len(result), no_ipa or "无", no_audio or "无"))
    for c in cats:
        print("  【%s】%d 词 ｜ %d 页 ｜ %d 天（每页 %d 天）" %
              (c["name"], c["count"], c["pageCount"], c["dayCount"], args.days_per_page))
        for p in c["pages"]:
            print("      %-13s %3d 词 → %s" %
                  (p["name"], p["count"], " / ".join(str(d["count"]) for d in p["days"])))


if __name__ == "__main__":
    main()
