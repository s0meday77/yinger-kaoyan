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
# 词条行：`word [音标] …`（豆包旧版式）或 `word /音标/ …`（145 页起的新版式）
# 斜杠里只许音标字符：不然 `place/put emphasis on sth. 强调 / 重视某事`
# 会被当成 place + 音标 /put emphasis on sth. /（171 页踩到）
PHON = r"[A-Za-zəɪʊɒʌæɑɔɜðθʃʒŋɡɚɝːˈˌ'’\-()\s]{1,45}"
ENTRY_RE = re.compile(r"^([A-Za-z][A-Za-z'\- ]*?)\s*(?:\[[^\]]{0,40}\]|/" + PHON + r"/)")
# 词性：n. / vt. / vt.&vi. / a. / ad. / adj. 等——必须带句点，
# 否则 "a dvances in technology" 这种搭配行会被误判成词性 a. + 释义
POS_TOKEN = r"(?:n|v|vt|vi|a|ad|adj|adv|prep|conj|pron|num|art|int|aux|det|pl)"
POS_RE = re.compile(r"^(" + POS_TOKEN + r"(?:\.(?:&|/)\s*" + POS_TOKEN + r")*\.)\s*")
# 义项标记 [C,U] [C-常用sing.] [sing.,U] 等；
# 书上还会在前面挂个括注：`(ethics) [pl.] 道德准则`
MARK_RE = re.compile(r"^(?:\([a-zA-Z\-]+\)\s*)?\[([^\]]{1,20})\]\s*")
HAN_RE = re.compile(r"[一-鿿]")
PAGE_RE = re.compile(r"^Page\s*\d*\s*$", re.I)
# 「链P46」是跨页索引，手机上看没用；106 页起豆包把「链」认成了「纯」
LINK_RE = re.compile(r"\s*[链纯]\s*P\d+\s*")
MARK_TAG_RE = re.compile(r"[\[【](族|近|反|派)[\]】]")
# 并排的近反义/派生行首标记（tab 版式里偶尔落在中间那格）
TAG_START_RE = re.compile(r"^(?:【(记|扩|近|反|族)[】\]]|(扩|近|反|族)\s|\[(近|反|族|扩)\])")
PREP_RE = re.compile(r"^(?:in|on|at|for|of|to|with|by|from|as|about|into|over|under)\b", re.I)
DROPPED = []                                     # 被判定为 OCR 截断、丢掉的搭配
CJK_PUNCT = "（【「《"
PAGE_MARK_RE = re.compile(r"^(?:#\s*P\d+|={2,}.+?={2,})$")
# 内部哨兵：tab 版式里「义项」那一格，明确是新义项，不走「英文+中文=例句」的判断
SENSE_MARK = "\x01"


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


def fix_ocr(s):
    """豆包逐批出现过的固定认错，统一在这里改回来（verify_star 也用这一套）。"""
    # 「v. link-v」被认成「v.-link」（106~124 页 constitute）
    s = re.sub(r"^([a-z]{1,3})\.-link\b", r"\1. link-v", s)
    # 括注没闭合、中间夹着「；」的（「（被认为或看作是；被算作」），
    # 那个「；」其实是「）」认错了
    if s.startswith("（") and "）" not in s and "；" in s:
        s = s.replace("；", "）", 1)
    # 行尾的圈码（⓪①②…）是书上标考频的符号，不进词库（152 页起大量出现）
    s = re.sub(r"\s*[①-⑳⓪-⓿]+\s*$", "", s)
    return s


def fix_cell(s):
    """tab 格里的纯中文义项偶尔把「，」认成「→」（content：很符合自己心意的→满意的）。

    【记】里的 → 是词根推导，绝不能动，所以只在 normalize_tabs 的格子上用。
    """
    if "→" in s and not re.search(r"[A-Za-z]", s):
        s = s.replace("→", "，")
    return s


def clean(s):
    s = s.replace("​", "").strip()
    s = LINK_RE.sub(" ", s)
    s = fix_ocr(s)
    return re.sub(r"\s+", " ", s).strip()


def split_pair(line):
    """「英文搭配 中文意思」→ (英文, 中文)；分不清就返回 (None, None)。"""
    i = first_han(line)
    if i <= 0:
        return None, None
    en = line[:i].strip(" ,，、;；(（[【")
    # 英文后面那半截括号会落到中文里（「National Health Council(加拿大)…」），去掉
    zh = re.sub(r"(?<=[一-鿿])\)", "", line[i:].strip())
    # 「the identity between A and B A和B的相同之处」——原文 A 和汉字之间没空格，
    # 切在汉字前的那个大写字母其实是中文句子的一部分，还回去
    tail = re.search(r"([A-Z])$", en)
    if tail and i > 0 and line[i - 1] != " ":
        en = en[:-1].strip()
        zh = tail.group(1) + zh
    # 「the commercial use of… ……的商业用途」——后半截省略号被算进了英文侧，
    # 中文就只剩「的商业用途」。末尾留一个省略号给英文，其余还给中文
    dots = re.search(r"(…+)\s*$", en)
    if dots and dots.group(1) != "…":
        head = en[:dots.start()].strip()
        if head.endswith("…"):
            en = head                                  # 英文自己已经带省略号了
            zh = dots.group(1) + zh
        else:
            en = head + "…"
            zh = dots.group(1)[1:] + zh
    zh = re.sub(r"^…{3,}", "……", zh)          # 中文里的省略号统一成「……」
    if not re.search(r"[A-Za-z]{2}", en) or not zh:
        return None, None
    return en, zh


def normalize_tabs(text):
    """豆包对同一本书的前后两半用了两种版式，后半截是「一行多列、tab 分隔」：

        ■ neglect [nɪˈɡlekt] v./n. 【记】neg-（不）+lect（选择）→…
        用
        vt.	忽略；忽视；不予重视	neglect the happiness 忽略快乐
        	疏漏；疏忽	neglect to do sth. 遗漏做某事
        		neglect social science 不重视社会科学
        扩 [族] neglectful a. 忽视的	[近] ignore vt. 忽视

    先摊回「一个元素一行」，后面的解析逻辑就通用了。
    中间那一格是书上印的义项，用哨兵标一下——不然像「（the military）[sing.]
    军人；军队」这种会被当成「英文搭配 + 中文」变成例句。
    """
    out = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if PAGE_MARK_RE.match(line.strip()):
            continue
        if line.lstrip().startswith("■"):
            line = line.lstrip()[1:].strip()
        if "\t" not in line:
            out.append(line)
            continue
        # 跨页索引先摘掉：106 页起豆包写成「纯P144」，留在最后一格会被当成释义续句
        cells = [LINK_RE.sub(" ", c).strip() for c in line.split("\t")]
        if len(cells) >= 3:
            # 不能死认「第一格是词性」：125 页起第一格常是「用」「扩」这种分组小标题，
            # 词性挪到了第二格。按内容认格子：
            #   用/扩/近/反 → 小标题（parse 里本来就跳过）
            #   纯词性格 → 单独成行，交给「词性行」分支
            #   [近]/[族]… → 并排的近反义/派生
            #   首格或末格 → 原样（带释义的词性行 / 例句）
            #   中间其它 → 义项
            for idx, c in enumerate(cells):
                if not c:
                    continue
                if c in ("用", "扩", "近", "反", "记", "族", "派"):
                    continue
                if re.fullmatch(POS_TOKEN + r"(?:\.(?:&|/)\s*" + POS_TOKEN + r")*\.", c):
                    out.append(c)
                    continue
                if TAG_START_RE.match(c):
                    out.append(c)
                    continue
                if idx == 0 or idx == len(cells) - 1:
                    out.append(fix_cell(c))
                else:
                    out.append(SENSE_MARK + fix_cell(c))
        else:
            # 两列：派生/近反义并排，各自独立成行
            out.extend(fix_cell(c) for c in cells if c)
    return out


def join_split_entries(text):
    """豆包偶尔把词条拆成两行：

        decrease
        [dɪˈkriːs] v.
        [ˈdiːkriːs] n.

    单独一个纯小写单词、下一行正好是音标，就合并成 `decrease [dɪˈkriːs] v.`，
    其后紧跟的其它读音行（第二词性的音标）丢掉。

    还有一种：书上标了词根拆解，豆包把拆解写进了词条行，音标跑到下一行——

        estimate  estim价值
        ['estɪmət] n. / ['estɪmeɪt] v. →估价

    这种词条行有两个以上空格 + 中文，下一行又正好以 `[` 开头，同样合并。
    不加这条，estimate / surface / differ 这种词会整条漏掉。
    """
    lines = []
    src = text if isinstance(text, list) else text.splitlines()
    raw = [l.strip() for l in src]
    i = 0
    while i < len(raw):
        l = raw[i]
        head = re.fullmatch(r"([a-z][a-z'\-]*)(?:\s{2,}.*)?", l)
        if head and i + 1 < len(raw) and raw[i + 1].startswith("["):
            lines.append(head.group(1) + " " + raw[i + 1])
            i += 2
            while i < len(raw) and re.fullmatch(r"\[[^\]]{0,40}\]\s*[a-z.&/]*\s*", raw[i]):
                i += 1
            continue
        # 跨页时豆包把记忆法排到了下一页词条的前面（general 的
        # 「gener（出生）+-al（形容词后缀）→…→普遍的」就掉了 P45 后面），
        # 把它挪到词条行之后，否则整条的【记】就没了。
        # 纯词根小标题（`milit 兵`）没有 `+` 和 `→`，不算，照旧忽略
        if ("+" in l and "→" in l and HAN_RE.search(l)
                and i + 1 < len(raw) and ENTRY_RE.match(raw[i + 1])
                and "【记】" not in raw[i + 1]):
            lines.append(raw[i + 1])
            lines.append("【记】" + l)
            i += 2
            continue
        lines.append(l)
        i += 1
    return lines


def is_form_of(tok, word):
    """tok 是不是 word 的变形或派生（classifiable ← classify、advances ← advance）。

    只认「以词根开头」，不能用公共前缀长度：classical 和 classify 前六个字母
    都是 classi，但它们是两个不同的词，共前缀会把 classical 的例句挂到 classify 上。
    """
    if len(word) < 6:
        return False
    return tok.startswith(word) or tok.startswith(word[:-1])


def other_word(en, exclude, known):
    """这句搭配是不是别的词条的（跨页时书会把下一词的例句排到上一词的【扩】后面）。"""
    toks = re.findall(r"[a-z][a-z'\-]{2,}", en.lower())
    for t in toks:
        if t in known and t != exclude:
            return t
    for t in toks:
        for k in known:
            if k != exclude and is_form_of(t, k):
                return k
    return None


def parse(text):
    """解析成「按书本顺序排列的块」。

    每个词条是一条 blocks 列表，顺序和书上完全一致：

        {"k": "记", "v": "本身为词根，意为“前”→…"}
        {"k": "注", "v": "亦作 center"}
        {"k": "义", "pos": "n.", "def": "[C,U] 进步；进展"}
        {"k": "例", "p": "scientific advances", "t": "科学进步"}
        {"k": "扩", "v": "[族] advancement n. 进步"}
        {"k": "近", "v": "progressive a. 先进的"}
        {"k": "反", "v": "primitive a. 落后的"}

    分开放（senses 一坨、phrases 一坨）的话，义项和它下面的例句就配不上对，
    书上是一义项带几条例句交替排的，只能按顺序存。
    """
    entries, cur = {}, None
    aliases = {}                     # 词条行标了「亦作 xxx」的变体，判断搭配归属时算主词
    DROPPED.clear()
    lines = join_split_entries(normalize_tabs(text))
    known = set()
    for l in lines:
        me = ENTRY_RE.match(l)
        if me:
            ww = me.group(1).strip().lower()
            if re.fullmatch(r"[a-z][a-z'\-]*", ww):
                known.add(ww)
    after_meta = False       # 进了【扩】【近】【反】之后，搭配行要额外把关
    pending_pos = ""         # 词性单独占一行时，等下一行义项来认领
    last_pos = ""            # 最近一次出现的词性，tab 版式的续行义项要继承它
    for li, line in enumerate(lines):
        # tab 版式明确标出来的义项：这一格内容就是释义，去做例句判断
        if line.startswith(SENSE_MARK):
            body = clean(line[1:])
            if not body or cur is None:
                continue
            pos = pending_pos or last_pos
            mark = ""
            mm0 = MARK_RE.match(body)
            if mm0:
                mark = "[" + mm0.group(1) + "] "
                body = body[mm0.end():].strip()
            cur["blocks"].append({"k": "义", "pos": pos, "def": mark + body})
            pending_pos = ""
            after_meta = False
            continue
        line = clean(line)
        if not line:
            continue
        if PAGE_RE.match(line):
            continue
        if re.fullmatch(r"链\s*P\d+", line):
            continue                     # 单独残留的跨页索引

        m = ENTRY_RE.match(line)
        if m:
            word = m.group(1).strip().lower()
            # 只留真正的词条：单个词，或带连字符的复合词
            if not re.fullmatch(r"[a-z][a-z'\-]*", word):
                continue
            cur = entries.setdefault(word, {"w": word, "blocks": []})
            after_meta = False
            pending_pos = ""
            last_pos = ""
            # `centre [...]（亦作center）n.` —— 英美拼写变体，考研英二爱考，别丢
            tail = line[m.end():].strip()
            alias = re.search(r"[(（]亦作\s*([A-Za-z\- ]+)[)）]", tail)
            if alias:
                cur["blocks"].append({"k": "注", "v": "亦作 " + alias.group(1).strip()})
                aliases.setdefault(word, set()).add(alias.group(1).strip().lower())
                tail = (tail[:alias.start()] + tail[alias.end():]).strip()
            # 这一批文档把【记】挤在词条行末尾了
            note = re.search(r"【记】\s*(.*)$", line)
            if note:
                cur["blocks"].append({"k": "记", "v": clean(note.group(1))})
                continue
            pm2 = POS_RE.match(tail)
            if pm2 and "[" not in tail and HAN_RE.search(tail[pm2.end():]):
                body = tail[pm2.end():].strip()
                mark = ""
                mm2 = MARK_RE.match(body)
                if mm2:
                    mark = "[" + mm2.group(1) + "] "
                    body = body[mm2.end():].strip()
                cur["blocks"].append({"k": "义", "pos": pm2.group(1), "def": mark + body})
            continue

        if cur is None:
            continue                     # 词条之前的词根标题、页码碎行

        # defence 的「（亦作defense）n.」被豆包拆成了独立一行
        alt = re.match(r"^[(（]亦作\s*([A-Za-z\- ]+)[)）]\s*(.*)$", line)
        if alt:
            cur["blocks"].append({"k": "注", "v": "亦作 " + alt.group(1).strip()})
            aliases.setdefault(cur["w"], set()).add(alt.group(1).strip().lower())
            pm3 = POS_RE.match(alt.group(2).strip())
            if pm3:
                pending_pos = pm3.group(1)
                last_pos = pm3.group(1)
            continue

        # 书上的分组小标题：单独一行的「用」「扩」「近」「反」——
        # 上面是义项、下面是例句/派生。不挡住的话「用」「扩」会被当成
        # 释义的续句拼进去，变成「相异；有区别；不同于；用；扩」这种鬼东西
        if line in ("用", "扩", "近", "反", "记", "族", "派"):
            continue

        # 【近] 这种半角右括号的错字书上有，得一起认；【族】是派生词，同【扩】
        # 这一批还有不带括号的写法：`扩 [族] xxx`、`[近] xxx`
        tag = re.match(r"^(?:【用】\s*)?(?:【(记|扩|近|反|族)[】\]]|(扩|近|反|族)\s+|\[(近|反|族|扩)\])\s*(.*)$", line)
        if tag:
            kind = tag.group(1) or tag.group(2) or tag.group(3)
            body = clean(tag.group(4))
            # 书上还有「扩 [近] duty n. 责任」这种套一层的写法，以内层的标记为准
            inner = MARK_TAG_RE.match(body)
            if inner:
                kind = inner.group(1)
                body = body[inner.end():].strip()
            label = "扩" if kind in ("扩", "族") else kind
            cur["blocks"].append({"k": label, "v": body})
            after_meta = True
            pending_pos = ""
            continue

        # 双读音词条的第二行：`segment ['seɡmənt] n.` + `[seɡ'ment] v. 【记】…`
        # 豆包把第二个音标和词性排到了行首，这一行只需要它的【记】，
        # 不拦住的话会被当成「[xxx] 开头的义项」，整条混进释义里
        mz = re.match(r"^\[[^\]]{1,40}\]\s*" + POS_TOKEN
                      + r"(?:\.(?:&|/)\s*" + POS_TOKEN + r")*\.\s*【记】\s*(.*)$", line)
        if mz:
            cur["blocks"].append({"k": "记", "v": clean(mz.group(1))})
            after_meta = False
            pending_pos = ""
            continue

        # 词性行 → 新义项
        pm = POS_RE.match(line)
        if pm and len(pm.group(1)) <= 12:
            pos = pm.group(1)
            if pos == "vi.&vi.":
                pos = "vt.&vi."      # 书上把 vt 打成了 vi，别照抄错的词性
            body = line[pm.end():].strip()
            mark = ""
            mm = MARK_RE.match(body)
            if mm:
                mark = "[" + mm.group(1) + "] "
                body = body[mm.end():].strip()
            if not body and not mark:
                # 词性单独占一行，释义在下一行（`n.` / `[U,C] 批评；批判`），
                # 先记下来，下一行的义项接着用
                pending_pos = pos
                last_pos = pos
                after_meta = False
                continue
            cur["blocks"].append({"k": "义", "pos": pos, "def": mark + body})
            last_pos = pos
            after_meta = False
            continue

        # [C,U] 开头、没有词性的义项
        mm = MARK_RE.match(line)
        if mm:
            pos = pending_pos
            pending_pos = ""
            cur["blocks"].append({"k": "义", "pos": pos, "def": "[" + mm.group(1) + "] " + line[mm.end():].strip()})
            after_meta = False
            continue

        en, zh = split_pair(line)
        if en:
            # 词根标题行也会落在这里（「ag, act 做 act 行动」「car, carr 车」），
            # 特征是英文部分只有一两个小写短词、可能用逗号并列，不像短语
            # 词根小标题也可能是大写（`VOC 叫喊`）
            if re.fullmatch(r"[a-z]{1,7}(?:,\s*[a-z]{1,7})*", en, re.I):
                continue
            # 「intellig 学会 intellect 学习」——词根小标题排在词条行正上方，
            # 后面跟的是带音标的词条。单个小写词 + 下一行就是词条，认作标题跳过
            if re.fullmatch(r"[a-z]{1,12}", en, re.I):
                nxt = next((clean(x) for x in lines[li + 1:] if clean(x)), "")
                if ENTRY_RE.match(nxt):
                    continue
            self_names = [cur["w"]] + sorted(aliases.get(cur["w"], ()))
            if en.lower().strip() in self_names:
                continue                      # 「apt 适应」这种就是单词本身，不算搭配
            # 【扩】后面常跟着派生词自己的例句（classify 下面挂着 classic 的例子），
            # 那些不能算到主词头上——除非这句里确实出现了主词本身
            # （或词条行标过的英美变体：enquiry 下的 inquiry、sceptical 下的 skeptical）。
            # 但跨页时书会把**下一个词**的例句也排在这里（conclude 段尾的
            # 「in conclusion 最后」、classify 段尾的 classical 例句），
            # 那就认出来是谁的，直接挂过去，别丢
            def is_self(text):
                t = text.lower()
                if re.search(r"\b" + re.escape(cur["w"]), t):
                    return True
                # 变体允许词尾变化：inquiry → inquiries（y → ies）
                for a in aliases.get(cur["w"], ()):
                    forms = {a, a + "s"}
                    if a.endswith("y"):
                        forms.add(a[:-1] + "ies")
                    if any(re.search(r"\b" + re.escape(f) + r"\b", t) for f in forms):
                        return True
                return False

            if after_meta and not is_self(en):
                toks = re.findall(r"[a-z][a-z'\-]{2,}", en.lower())
                # 主词自己的派生词（书上漏印 [族]）：classifiable ← classify
                if any(is_form_of(t, cur["w"]) for t in toks):
                    cur["blocks"].append({"k": "扩", "v": en + " " + zh})
                    continue
                tgt = other_word(en, cur["w"], known)
                if tgt and tgt in entries:
                    entries[tgt]["blocks"].append({"k": "例", "p": en, "t": zh})
                elif not tgt:
                    DROPPED.append((cur["w"], en))
                continue
            # 豆包偶尔把搭配截断了，只剩个介词短语（immigrant 下面那条
            # 「in the U.S. 在美国的亚洲移民」就是少了前半句），主词都不在，
            # 留着只会让他学到半句话——丢掉，并在结尾列出来让人复核
            stem = cur["w"][:max(3, len(cur["w"]) - 3)]
            if len(en) < 16 and PREP_RE.match(en) and stem not in en.lower():
                DROPPED.append((cur["w"], en))
                continue
            pending_pos = ""
            cur["blocks"].append({"k": "例", "p": en, "t": zh})
            continue

        # 剩下的是纯中文 → 上一个义项的续句（书上换行了，得补个分隔否则会粘成一团）
        if HAN_RE.search(line):
            # 词性单独占一行、下一行就是释义（`a.` / 令人愉快的…），
            # 但前面可能已经排着【记】【扩】之类——先认领 pending_pos 开新义项，
            # 别落到下面“续句”分支里被丢掉（86~105 页 15 个词就是这么丢的）
            if pending_pos:
                cur["blocks"].append({"k": "义", "pos": pending_pos, "def": line})
                last_pos = pending_pos
                pending_pos = ""
                after_meta = False
                continue
            target = None
            for b in reversed(cur["blocks"]):
                if b["k"] == "义":
                    target = b
                    break
                if b["k"] in ("记", "扩", "近", "反"):
                    break            # 已经在元信息区，后面不会再有释义续句
            if target:
                prev = target["def"]
                sep = "" if prev and prev[-1] in "；;，,。.】" else "；"
                target["def"] = prev + sep + line
    return entries


def senses_of(blocks):
    return [b for b in blocks if b["k"] == "义"]


def phrases_of(blocks):
    return [b for b in blocks if b["k"] == "例"]


def merge_senses(blocks):
    """把义项压成手机上能看的一行（只用于控制台预览）。

    同一词性连续出现的义项合并成 `n. 进步；进展；进步`，词性变了就另起一段。
    """
    out, last_pos = [], None
    for b in senses_of(blocks):
        pos, d = b["pos"], b["def"].strip()
        if not d:
            continue
        if out and (pos == last_pos or not pos):
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

    total_p = sum(len(phrases_of(e["blocks"])) for e in entries.values())
    print("词条 %d ｜ 搭配 %d 条 ｜ 平均每词 %.1f 条" %
          (len(entries), total_p, total_p / max(1, len(entries))))
    no_p = [w for w, e in entries.items() if not phrases_of(e["blocks"])]
    no_m = [w for w, e in entries.items() if not senses_of(e["blocks"])]
    print("没有搭配:", no_p or "无")
    print("没有释义:", no_m or "无")
    cnt = {}
    for e in entries.values():
        cnt["记"] = cnt.get("记", 0) + sum(1 for b in e["blocks"] if b["k"] == "记")
        cnt["扩"] = cnt.get("扩", 0) + sum(1 for b in e["blocks"] if b["k"] == "扩")
        cnt["近"] = cnt.get("近", 0) + sum(1 for b in e["blocks"] if b["k"] == "近")
        cnt["反"] = cnt.get("反", 0) + sum(1 for b in e["blocks"] if b["k"] == "反")
    print("记忆法 %d ｜ 派生 %d ｜ 近义 %d ｜ 反义 %d" % (cnt["记"], cnt["扩"], cnt["近"], cnt["反"]))
    if DROPPED:
        print("丢弃的残缺搭配 %d 条（OCR 截断，主词不在里面）:" % len(DROPPED))
        for w, en in DROPPED:
            print("   %-18s %s" % (w, en))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    print("已写入", args.out)

    for w, e in list(entries.items())[: args.show or 0]:
        print("\n[%s] %s" % (w, " / ".join(merge_senses(e["blocks"]))))
        for b in e["blocks"]:
            if b["k"] == "例":
                print("   · %-46s %s" % (b["p"], b["t"]))
            elif b["k"] != "义":
                print("   【%s】%s" % (b["k"], b["v"]))


if __name__ == "__main__":
    main()
