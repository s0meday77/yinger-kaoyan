#!/usr/bin/env python3
"""把「基础词汇总」docx 按**语义类目**导进词库（不是按教材页）。

用户 2026-11-25 明确要求：基础词不分页，按豆包分好的类目（行为/习惯、
人体器官、人物/关系…）归类。docx 结构是：

    与人相关            ← 主题（后面紧跟另一个标题时才认）
    行为/习惯            ← 类目（后面跟词条）
    think  [θɪŋk]  vt.&vi. 想；思考…
    project  [ˈprɒdʒekt]  n. [C]项目…     ← 一词多音，下一条只有音标和释义
    [prəˈdʒekt]  vt. 规划…

    其他
    常见动词
    …

落到词库里的约定（和 ComfyUI 章节同一套）：

- `cat`   = 基础词
- `list`  = 类目名（行为/习惯）
- `page`  = 类目序号（1 起，页按钮显示类目名）
- `day`   = 类目内按 ≤20 词切一天
- `gday`  = 整个「基础词」里的第几天

用法:
    python3 -I tools/build_base_words.py ~/Desktop/基础词汇总.docx
    python3 -I tools/build_base_words.py <docx> --dry-run
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parse_star import docx_to_text  # noqa: E402

WORDS = os.path.join(HERE, "..", "app", "data", "words.json")
PER_DAY = 20

POS_START = re.compile(
    r"^(?:n|v|vt|vi|a|ad|adj|adv|prep|conj|pron|num|art|int|aux|det|pl|modal)\.",
    re.I)
PAGE_RE = re.compile(r"^(?:【\s*Page[^】]*】|=+\s*PAGE\s*\d+\s*=+)$", re.I)
HEADER_WRAP = re.compile(r"^=+\s*(.+?)\s*=+$")
IPA_RE = re.compile(r"^[\[/]\s*([^\]]*?)\s*[\]/]$")

# 页按钮上的短名（类目全名太长会撑爆按钮）
SHORT = {
    "行为/习惯": "行为/习惯",
    "人体器官": "人体器官",
    "人物/关系": "人物/关系",
    "心理感受": "心理感受",
    "人物评价": "人物评价",
    "地点/场所": "地点/场所",
    "日常交流": "日常交流",
    "服装穿戴": "服装穿戴",
    "旅游/出行": "旅游/出行",
    "日常用品": "日常用品",
    "日常饮食": "日常饮食",
    "疾病/医疗": "疾病/医疗",
    "工作/职业": "工作/职业",
    "国家政经": "国家政经",
    "商业/娱乐": "商业/娱乐",
    "颜色/形状": "颜色/形状",
    "大小/数量": "大小/数量",
    "动物/植物": "动物/植物",
    "资源/景观": "资源/景观",
    "天气/气候": "天气/气候",
    "学校/课程": "学校/课程",
    "文化/艺术": "文化/艺术",
    "体育运动": "体育运动",
    "常见动词": "常见动词",
    "常见名词": "常见名词",
    "常见形容词": "常见形容词",
    "常见副词": "常见副词",
    "常见介词": "常见介词",
    "常见连词": "常见连词",
    "常见代词": "常见代词",
    "常见冠词、情态动词、系动词与限定词": "冠词/情态/系动词",
}


def is_header(s):
    """纯中文、不像词条、也不像释义续句 → 标题。"""
    if "\t" in s or POS_START.match(s):
        return False
    if re.search(r"[A-Za-z]{2}", s):
        return False
    return bool(s) and len(s) <= 24


def ipa_of(cell):
    """`[θɪŋk]` → θɪŋk；`[ˈɔːtəm]/[fɔːl]` 这种两个读音的用「 / 」连起来。"""
    cell = cell.strip()
    parts = [p.strip() for p in re.findall(r"\[([^\]]+)\]", cell)]
    if parts:
        return " / ".join(parts)
    m = IPA_RE.match(cell)
    return m.group(1).strip() if m else ""


def parse_doc(path):
    """→ [(theme, 类目, 词条 dict), ...]，保持书本顺序。"""
    lines = [l.rstrip() for l in docx_to_text(path).splitlines()]
    items, theme, cat, cur = [], "", "", None
    pending_headers = []
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        if PAGE_RE.match(s) or re.match(r"^【Page\s*\d+[^】]*】$", s, re.I):
            continue
        m = HEADER_WRAP.match(s)
        if m:
            s = m.group(1).strip()
        if is_header(s):
            pending_headers.append(s)
            continue
        cells = [c.strip() for c in s.split("\t") if c.strip()]
        if pending_headers:
            # 连着的两个标题：前一个是主题，最后一个是类目
            if len(pending_headers) >= 2:
                theme = pending_headers[-2]
            cat = pending_headers[-1]
            pending_headers = []
            cur = None
        if len(cells) >= 3:
            word, ipa, mean = cells[0], ipa_of(cells[1]), cells[2]
            # autumn/fall、a/an、o’clock 这些也是书上原样的词条，别丢
            if not re.fullmatch(r"[A-Za-z][A-Za-z'’\- ./]*", word):
                continue
            cur = {"w": word, "ipa": [ipa] if ipa else [], "m": mean, "cat": cat, "theme": theme}
            items.append(cur)
        elif len(cells) == 2:
            # 一词多音：这一行只有音标和释义，算上一个词的
            ipa, mean = ipa_of(cells[0]), cells[1]
            if cur is None:
                continue
            if ipa:
                cur["ipa"].append(ipa)
            if mean:
                cur["m"] = (cur["m"] + " " + mean).strip()
        elif cur is not None:
            # 释义换行续句（`n. [C]主人；东道主…`）
            cur["m"] = (cur["m"] + " " + s).strip()
    return items


def merge_items(items):
    """同一个词出现两次（excuse/conflict 分名词动词两行）就合成一条。"""
    out, seen = [], {}
    for it in items:
        # 按原样去重：`May`（五月）和 `may`（情态动词）是两个词，不能并
        key = it["w"]
        if key in seen:
            tgt = seen[key]
            if it["m"] not in tgt["m"]:
                tgt["m"] = (tgt["m"] + " " + it["m"]).strip()
            for ip in it["ipa"]:
                if ip not in tgt["ipa"]:
                    tgt["ipa"].append(ip)
            continue
        seen[key] = it
        out.append(it)
    return out


def build(items):
    """→ (词条列表, 类别对象)，类目按出现顺序编号，类目内每 20 词一天。"""
    pages, order = {}, []
    for it in items:
        name = it["cat"]
        if name not in pages:
            pages[name] = {"name": name, "theme": it["theme"], "items": []}
            order.append(name)
        pages[name]["items"].append(it)

    words, page_objs = [], []
    gday = 0
    for idx, name in enumerate(order, 1):
        p = pages[name]
        days = []
        for i, it in enumerate(p["items"]):
            d = i // PER_DAY + 1
            if d > len(days):
                gday += 1
                days.append({"day": d, "count": 0, "gday": gday})
            days[-1]["count"] += 1
            words.append({
                "w": it["w"],
                "us": " / ".join(it["ipa"]),
                "uk": " / ".join(it["ipa"]),
                "m": it["m"],
                "us_audio": None,
                "uk_audio": None,
                "cat": "基础词",
                "list": name,
                "page": idx,
                "day": d,
                "gday": gday,
            })
        page_objs.append({
            "cat": "基础词", "index": idx, "name": name,
            "short": SHORT.get(name, name[:6]),
            "theme": p["theme"], "count": len(p["items"]), "days": days,
        })
    cat_obj = {
        "name": "基础词",
        "count": len(words),
        "pageCount": len(page_objs),
        "dayCount": sum(len(p["days"]) for p in page_objs),
        "days": [{"day": d["gday"], "count": d["count"]} for p in page_objs for d in p["days"]],
        "pages": page_objs,
    }
    return words, cat_obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    items = merge_items(parse_doc(args.docx))
    words, cat_obj = build(items)
    print("基础词 %d 词 ｜ %d 个类目 ｜ %d 天" %
          (len(words), cat_obj["pageCount"], cat_obj["dayCount"]))
    for p in cat_obj["pages"]:
        print("   %-22s %4d 词 ｜ %d 天" % (p["name"], p["count"], len(p["days"])))
    if args.dry_run:
        return

    with open(WORDS, encoding="utf-8") as f:
        data = json.load(f)
    old = [w for w in data["words"] if w.get("cat") != "基础词"]
    # 基础词排在教材六类之后、ComfyUI 之前（只在第一个 ComfyUI 词前插一次）
    result = []
    placed = False
    for w in old:
        if not placed and w.get("cat") == "ComfyUI词汇":
            result.extend(words)
            placed = True
        result.append(w)
    if not placed:
        result.extend(words)
    data["words"] = result
    data["count"] = len(result)
    data["categories"] = [c for c in data["categories"] if c["name"] != "基础词"] + [cat_obj]
    order = ["高频词", "中频词", "低频词", "偶考词", "基础词", "补充词", "ComfyUI词汇"]
    data["categories"].sort(key=lambda c: order.index(c["name"]) if c["name"] in order else 99)
    with open(WORDS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("已写入 %s（%d 词）" % (WORDS, data["count"]))


if __name__ == "__main__":
    main()
