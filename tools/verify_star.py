#!/usr/bin/env python3
"""逐行核对：《词汇闪过》docx 原文是否每一行都进了词库的 sb 块。

2026-11-16 那次核对脚本放在 /tmp，重启就丢了，这里固化下来。

用法:
    python3 -I tools/verify_star.py app/data/words.json ~/Desktop/词汇闪过*.docx

判定口径（和 11-16 那次一致）：
1. 原文行归一化（去空格标点）后，要能在该词的 sb 块里找到；
   「词性 + 释义」这种合在一行的，拆成两段各自比对。
2. 当前词里找不到、却挂在别的词名下的，标「↪ 挂到 X 名下」，不算丢。
3. parse_star 判为 OCR 残句丢掉的，单独列出，必须人工看一眼。
4. 词库根本没导入这个词的，单独列出来。

退出码：有「没进词库」的行时为 1，方便下一批当关卡用。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_star as P  # noqa: E402

HAN_RE = re.compile(r"[一-鿿]")
# 词性标记（非锚定，行内任意位置）
POS_ANY = re.compile(r"(?:^|\s)((?:n|v|vt|vi|a|ad|adj|adv|prep|conj|pron|num|art|int|aux)"
                     r"(?:\.(?:&|/)\s*(?:n|v|vt|vi|a|ad|adj|adv|prep|conj|pron|num|art|int|aux))*\.)")
PUNCT = "，。、；：！？,.;:!?·•…—－-—\"'“”‘’（）()【】[]《》<>〈〉「」『』/\\*＋+"


def norm(s):
    """去空格标点、统一小写，只保留字母数字和汉字。"""
    s = str(s)
    s = s.replace(P.SENSE_MARK, "")
    s = re.sub(r"链\s*P\d+", "", s)     # 跨页索引，词库里本来就不存
    out = []
    for ch in s:
        if ch.isspace() or ch in PUNCT:
            continue
        out.append(ch.lower())
    return "".join(out)


def fields_of(blocks):
    """把一个词的 sb 块拍平成字符串列表（音标、词性标记不参与）。"""
    out = []
    for b in blocks:
        k = b.get("k")
        if k == "义":
            out.append(b.get("def", ""))
        elif k == "例":
            out.append(b.get("p", ""))
            out.append(b.get("t", ""))
        else:
            out.append(b.get("v", ""))
    return [f for f in out if str(f).strip()]


def hit(part, fields):
    p = norm(part)
    if len(p) < 2:
        return True                    # 空段 / 词性标记，不参与判断
    for f in fields:
        q = norm(f)
        if not q:
            continue
        if p in q or (len(q) >= 3 and q in p):
            return True
    return False


def line_ok(line, fields):
    line = line.replace(P.SENSE_MARK, "").strip()
    line = P.fix_ocr(line)             # 和 parse 用同一套 OCR 订正
    if not line:
        return True
    # 行首的分类标记（`扩 [族] …`/`[近] …`）词库里只存后面的内容
    line = re.sub(r"^(记|扩|近|反)\s*", "", line)
    line = re.sub(r"^\[(族|近|反|派)\]\s*", "", line)
    # 书上 a. (dynamics) [pl.]… 这种英文括注只是词形提示，parse 有意不存，
    # 比对时连去括注的版本一起试（中文括号里的释义要保留）
    no_paren = re.sub(r"\([A-Za-z'\- ]{2,24}\)", "", line)
    for cand in ([line, no_paren] if no_paren != line else [line]):
        if hit(cand, fields):
            return True
        m = POS_ANY.search(cand)       # 「词性 + 释义」拆开各自比对
        if m and hit(cand[:m.start()], fields) and hit(cand[m.end():], fields):
            return True
        idx = HAN_RE.search(cand)      # 「英文 + 中文」拆开各自比对
        if idx and idx.start() > 0 and hit(cand[:idx.start()], fields) \
                and hit(cand[idx.start():], fields):
            return True
    return False


def segments(lines):
    """按词条行切段：{word: [原始行, ...]}，保持书本顺序。"""
    out, cur = {}, None
    for line in lines:
        me = P.ENTRY_RE.match(line)
        if me:
            ww = me.group(1).strip().lower()
            if re.fullmatch(r"[a-z][a-z'\-]*", ww):
                cur = out.setdefault(ww, [])
                continue
        if cur is not None:
            cur.append(line)
    return out


LINK_ONLY = re.compile(r"^链\s*P\d+$")


def skip_line(line):
    line = line.strip()
    if not line:
        return True
    if P.PAGE_MARK_RE.match(line) or P.PAGE_RE.match(line):
        return True
    if re.fullmatch(r"【?\s*Page\s*\d+\s*】?", line, re.I):
        return True
    if LINK_ONLY.match(line):
        return True
    return False


def is_root_title(line, next_line):
    """词根小标题（`ag, act 做`、`imag 想象`）不是内容行，和 parse_star 同一套判据。"""
    en, _zh = P.split_pair(line)
    if not en:
        return False
    if re.fullmatch(r"[a-z]{1,7}(?:,\s*[a-z]{1,7})*", en, re.I):
        return True
    if re.fullmatch(r"[a-z]{1,12}", en, re.I):
        if P.ENTRY_RE.match(next_line or ""):
            return True
        # 「intellig 学会 intellect 学习」：中文段里又套了一个短英文词干
        toks = re.findall(r"[a-z]{2,12}", _zh.lower())
        if toks and len(HAN_RE.findall(_zh)) <= 6:
            return True
    return False


def main():
    if len(sys.argv) < 3:
        sys.exit("用法: python3 -I tools/verify_star.py app/data/words.json <docx...>")
    words_path, docxs = sys.argv[1], sys.argv[2:]
    import json
    with open(words_path, encoding="utf-8") as f:
        data = json.load(f)
    words = data["words"] if isinstance(data, dict) else data
    # 词库里有同名不同大小写的词条（高频词 prompt / ComfyUI 的 Prompt），
    # setdefault 先到先得：词库顺序里高频/中频在前，不会被 ComfyUI 的空 sb 覆盖
    sb_map = {}
    for w in words:
        sb = w.get("sb") or []
        sb_map.setdefault(w["w"], sb)
        sb_map.setdefault(w["w"].lower(), sb)
    field_map = {k: fields_of(v) for k, v in sb_map.items() if v}

    bad_total = 0
    for path in docxs:
        if not os.path.exists(path):
            sys.exit("找不到文件: " + path)
        text = P.docx_to_text(path)
        lines = P.join_split_entries(P.normalize_tabs(text))
        P.parse(text)                  # 只为填充 DROPPED
        segs = segments(lines)

        lines_total = matched = not_imported = 0
        bad, moved = [], []
        for ww, rows in segs.items():
            fields = field_map.get(ww)
            for i, line in enumerate(rows):
                if skip_line(line):
                    continue
                nxt = next((r for r in rows[i + 1:] if r.strip()), "")
                if is_root_title(line, nxt):
                    continue
                lines_total += 1
                if fields is None:
                    not_imported += 1
                    bad.append((ww, line, "词库未导入"))
                    continue
                if line_ok(line, fields):
                    matched += 1
                    continue
                # 看看是不是挂到别的词名下了
                owner = None
                for other, ofields in field_map.items():
                    if other != ww and line_ok(line, ofields):
                        owner = other
                        break
                if owner:
                    moved.append((ww, owner, line))
                else:
                    bad.append((ww, line, "没进词库"))

        print("== %s" % os.path.basename(path))
        print("   词条 %d ｜ 内容行 %d ｜ 对上 %d ｜ 挂到别词 %d ｜ 没对上 %d ｜ 未导入词 %d"
              % (len(segs), lines_total, matched, len(moved), len(bad), not_imported))
        for ww, line, why in bad[:50]:
            print("   ❌ [%s] %s  ← %s" % (ww, line.strip(), why))
        if len(bad) > 50:
            print("   ……还有 %d 条" % (len(bad) - 50))
        for ww, owner, line in moved[:50]:
            print("   ↪ [%s] %s  → 挂在 %s 名下" % (ww, line.strip(), owner))
        if P.DROPPED:
            print("   被判残句丢弃 %d 条（人工确认是否真残句）:" % len(P.DROPPED))
            for ww, en in P.DROPPED:
                print("   ✂ [%s] %s" % (ww, en))
        bad_total += len(bad)

    print("\n合计「没进词库」%d 条" % bad_total)
    sys.exit(1 if bad_total else 0)


if __name__ == "__main__":
    main()
