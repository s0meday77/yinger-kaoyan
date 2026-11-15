#!/usr/bin/env python3
"""《考研词汇闪过》OCR 文本 → 结构化 JSON。

文档是豆包拍照识别出来的纯文本，版式固定：

    advance [ədˈvɑːns] n./v./a.
    【记】本身为词根，意为"前"→向前发展的状态→进步
    n. [C,U] 进步；进展
    scientific advances 科学进步
    advances in technology 技术上的进步
    vt. 促进；推动
    advance economic globalization 促进经济全球化
    【扩】[族] advancement n. 进步  链P46
    【近】progressive a. 先进的  链P255

解析要点：
- 词条行 = 单词 + [音标]，是唯一的分节依据
- 词性行（n. / vt.&vi. / a. …）开新义项；[C,U] 开头的算同一批里的新义项
- 纯中文行是上一个义项的续句（书上排版换行了）
- 英文 + 中文的行是「搭配 / 例证」，也是最值钱的那部分
- 词条出现之前的零散行（ag, act 做 / Page3）是词根标题和页码，忽略

用法:
    python3 -I tools/parse_star.py ~/Desktop/词汇闪过1-15页.docx --out /tmp/star.json
"""
import argparse
import json
import os
import re
import subprocess
import sys

# 词条行：单词 + [音标]，后面可能跟 （亦作 center）n. 之类的尾巴
ENTRY_RE = re.compile(r"^([A-Za-z][A-Za-z'\- ]*?)\s*\[[^\]]{0,40}\]")
# 词性：n. / vt. / vt.&vi. / a. / ad. / adj. 等——必须带句点，
# 否则 "a dvances in technology" 这种搭配行会被误判成词性 a. + 释义
POS_TOKEN = r"(?:n|v|vt|vi|a|ad|adj|adv|prep|conj|pron|num|art|int|aux)"
POS_RE = re.compile(r"^(" + POS_TOKEN + r"(?:\.(?:&|/)\s*" + POS_TOKEN + r")*\.)\s*")
# 义项标记 [C,U] [C-常用sing.] [sing.,U] 等
MARK_RE = re.compile(r"^\[([^\]]{1,20})\]\s*")
HAN_RE = re.compile(r"[一-鿿]")
PAGE_RE = re.compile(r"^Page\s*\d*\s*$", re.I)
LINK_RE = re.compile(r"\s*链\s*P\d+\s*")          # 「链P46」是跨页索引，手机上看没用
MARK_TAG_RE = re.compile(r"\[(族|近|反|派)\]")
CJK_PUNCT = "（【「《"


def docx_to_text(path):
    """用 macOS 自带的 textutil 转文本，不依赖第三方库。"""
    if path.lower().endswith(".txt"):
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    out = subprocess.run(["textutil", "-convert", "txt", "-stdout", path],
                         capture_output=True, check=True)
    return out.stdout.decode("utf-8", "replace")


def first_han(s):
    m = HAN_RE.search(s)
    return m.start() if m else -1


def clean(s):
    s = s.replace("​", "").strip()
    s = LINK_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def split_pair(line):
    """「英文搭配 中文意思」→ (英文, 中文)；分不清就返回 (None, None)。"""
    i = first_han(line)
    if i <= 0:
        return None, None
    en = line[:i].strip(" ,，、;；")
    zh = line[i:].strip()
    if not re.search(r"[A-Za-z]{2}", en) or not zh:
        return None, None
    return en, zh


def parse(text):
    entries, cur = {}, None
    for raw in text.splitlines():
        line = clean(raw)
        if not line:
            continue
        if PAGE_RE.match(line):
            continue

        m = ENTRY_RE.match(line)
        if m:
            word = m.group(1).strip().lower()
            # 只留真正的词条：单个词，或带连字符的复合词
            if not re.fullmatch(r"[a-z][a-z'\-]*", word):
                continue
            cur = entries.setdefault(word, {
                "w": word, "senses": [], "phrases": [], "family": [],
                "syn": [], "ant": [], "root": "",
            })
            continue

        if cur is None:
            continue                     # 词条之前的词根标题、页码碎行

        # 【近] 这种半角右括号的错字书上有，得一起认；【族】是派生词，同【扩】
        tag = re.match(r"^【(记|扩|近|反|族)[】\]]\s*(.*)$", line)
        if tag:
            kind, body = tag.group(1), clean(line)
            body = re.sub(r"^【(记|扩|近|反|族)[】\]]\s*", "", body)
            body = MARK_TAG_RE.sub("", body).strip()
            if kind == "记":
                cur["root"] = body
            elif kind in ("扩", "族"):
                cur["family"].append(body)
            elif kind == "近":
                cur["syn"].append(body)
            else:
                cur["ant"].append(body)
            continue

        # 词性行 → 新义项
        pm = POS_RE.match(line)
        if pm and len(pm.group(1)) <= 8:
            pos = pm.group(1)
            body = line[pm.end():].strip()
            mark = ""
            mm = MARK_RE.match(body)
            if mm:
                mark = "[" + mm.group(1) + "] "
                body = body[mm.end():].strip()
            cur["senses"].append({"pos": pos, "def": mark + body})
            continue

        # [C,U] 开头、没有词性的义项
        mm = MARK_RE.match(line)
        if mm:
            cur["senses"].append({"pos": "", "def": "[" + mm.group(1) + "] " + line[mm.end():].strip()})
            continue

        en, zh = split_pair(line)
        if en:
            # 词根标题行也会落在这里（「ag, act 做 act 行动」「car, carr 车」），
            # 特征是英文部分只有一两个小写短词、可能用逗号并列，不像短语
            if re.fullmatch(r"[a-z]{1,7}(?:,\s*[a-z]{1,7})*", en):
                continue
            if en.lower().strip() == cur["w"]:
                continue                      # 「apt 适应」这种就是单词本身，不算搭配
            cur["phrases"].append({"p": en, "t": zh})
            continue

        # 剩下的是纯中文 → 上一个义项的续句（书上换行了，得补个分隔否则会粘成一团）
        if HAN_RE.search(line):
            if cur["senses"]:
                prev = cur["senses"][-1]["def"]
                sep = "" if prev and prev[-1] in "；;，,。.】" else "；"
                cur["senses"][-1]["def"] = prev + sep + line
            else:
                cur["senses"].append({"pos": "", "def": line})
    return entries


def merge_senses(senses):
    """把「词性 + 义项」压成手机上能看的一行。

    同一词性连续出现的义项合并成 `n. 进步；进展；进步`，
    词性变了就另起一段，最多保留 3 段。
    """
    out = []
    last_pos = None
    for s in senses:
        pos, d = s["pos"], s["def"].strip()
        if not d:
            continue
        if out and (pos == last_pos or not pos):
            # 并进上一条时把重复的 [C,U] 标记去掉，只留每段第一个
            out[-1] += "；" + re.sub(r"^\[[^\]]{0,20}\]\s*", "", d)
        else:
            out.append((pos + " " if pos else "") + d)
            last_pos = pos
    return out[:3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", default="/tmp/star.json")
    ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args()

    if not os.path.exists(args.src):
        sys.exit("找不到文件: " + args.src)
    entries = parse(docx_to_text(args.src))

    total_p = sum(len(e["phrases"]) for e in entries.values())
    print("词条 %d ｜ 搭配 %d 条 ｜ 平均每词 %.1f 条" %
          (len(entries), total_p, total_p / max(1, len(entries))))
    no_p = [w for w, e in entries.items() if not e["phrases"]]
    no_m = [w for w, e in entries.items() if not e["senses"]]
    print("没有搭配:", no_p or "无")
    print("没有释义:", no_m or "无")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    print("已写入", args.out)

    for w, e in list(entries.items())[: args.show or 0]:
        print("\n[%s] %s" % (w, " / ".join(merge_senses(e["senses"]))))
        for p in e["phrases"]:
            print("   · %-46s %s" % (p["p"], p["t"]))


if __name__ == "__main__":
    main()
