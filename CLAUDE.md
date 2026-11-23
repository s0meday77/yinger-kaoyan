# CLAUDE.md

全局规则见 `~/.claude/CLAUDE.md`，此文件只包含考研英二项目相关记录。

## 项目定位

把教材上的考研英语（二）词汇做成手机 App，**点一下就朗读**，能听写、能默写、能对着教材翻页学。

来源链路：教材拍照 → macOS Vision OCR → 有道词典取音标 + 真人录音 → 纯前端 PWA。

> **硬要求：读音必须准确，绝对不能出现读错的词。** 用户原话——"你把读音给我弄准就好了，不要让我学错"。

## 目录

```
考研英二/
├── app/                     前端（纯静态，无构建）
│   ├── index.html            加载顺序见下方「前端铁律」
│   ├── style.css             6 套皮肤（CSS 变量驱动）
│   ├── ui.js                 皮肤 + 连听        ← 必须第一个加载
│   ├── app.js                状态 / 发音 / 页天导航 / boot
│   ├── list.js               点听列表渲染
│   ├── practice.js           听写 / 错词本 / toast
│   ├── sw.js                 Service Worker（当前 VER=v20）
│   ├── manifest.webmanifest  添加到主屏幕用
│   ├── icons/                应用图标
│   └── data/
│       ├── words.json        词库（含音标、释义、所属类别/页/天）
│       ├── words.js          同上，包成 window.__WORDS__，给 file:// 用
│       └── audio/{us,uk}/    1606×2 个有道真人录音
├── src/
│   ├── photos/               教材照片原图
│   ├── words.txt             词表（`# 类别 · Word List N` 分段 + 每行一词）
│   └── crosscheck.json       第二词典交叉核对结果
├── tools/
│   ├── ocr/vision_ocr.py     调用 macOS Vision 框架做 OCR
│   ├── ocr/parse_ocr.py      版面重建 → words.txt
│   ├── build_words.py        查词取音标/释义/下载录音 → words.json
│   ├── json2js.py            words.json → words.js
│   ├── audit.py              词库体检
│   ├── crosscheck.py         第二词典独立核对
│   ├── parse_star.py         《词汇闪过》OCR 文本 → 释义/词组 JSON
│   ├── merge_star.py         把书上的释义/词组挂进 words.json（新字段 sb）
│   ├── tts_kokoro.py         Kokoro 本地 TTS 底座（试听样例 + 通用录词）
│   ├── tts_voices.py         按音色批量录 m/f/c 三套 → words.json 的 v 字段
│   ├── tts_cute.py           夹子音变调实验（asetrate+atempo 抬音调）
│   ├── tts_check.py          新录音体检：三套齐不齐、时长像不像一个词
│   └── serve.py              局域网静态服务器
└── 启动.command              双击启动服务器
```

## 数据分层（铁律，用户明确要求）

```
类别（高频/中频/低频/偶考/基础/补充）
  └─ 教材页（Word List N）
       └─ 页内第几天（每页固定 4 天）
            └─ 全局第 N 天（每类各自从第 1 天排：高频 48 天、中频 36 天）
```

**必须先按教材页汇总，再在页内分天，绝不能跨页混排天数。** 用户原话——"你这样搞我会乱的啊，我怎么对着教材学啊"。他要翻着纸质教材一页一页对。

当前进度：

| 类别 | 词数 | 页数 | 天数 | 状态 |
|---|---|---|---|---|
| 高频词 | 971 | 12 | 48 | ✅ 完成 |
| 中频词 | 635 | 9 | 36 | ✅ 完成 |
| ComfyUI词汇 | 80 | 5 | 20 | ✅ 完成（2026-11-01，非教材，自建章节）|
| 低频词 | — | — | — | 待导入 |
| 偶考词 | — | — | — | 待导入 |
| 基础词 | — | — | — | 待导入 |
| 补充词 | — | — | — | 待导入 |

## 手机独立安装（用户首选，2026-10-29 上线）

**线上地址：<https://s0meday77.github.io/yinger-kaoyan/>**
**仓库：<https://github.com/s0meday77/yinger-kaoyan>**（完整源码仓库，`app/` 由 GitHub Actions 发布到 Pages）

iPhone Safari 打开 → 添加到主屏幕 → 从图标进 App → ⚙ 设置 → **📥 打包到手机**。
打包会把 3212 个音频灌进 Cache Storage，之后**彻底离线**：不用电脑、不用联网、不用开服务器。

详见 `手机安装说明.md`，二维码在 `二维码.png`。

**⚠️ 有两个站点，每次发版必须同时推：**

| 仓库 | 地址 | 用途 |
|---|---|---|
| `s0meday77/yinger-kaoyan` | <https://s0meday77.github.io/yinger-kaoyan/> | 源码仓库，GitHub Actions 发布 |
| `s0meday77/kaoyan-yinger` | <https://s0meday77.github.io/kaoyan-yinger/> | **小龙手机主屏图标实际指向这个** |

2026-10-29 踩过的坑：新版全推到了 `yinger-kaoyan`，用户那个停在 v10，改了十几版他毫无变化。
**以后每次发版两个都要推，漏一个等于白干。**

**发布更新：**
```bash
cd /Users/diting/英二考研
# ⚠️ 改了 app/ 里的前端文件，必须同时改两处版本号：
#    app/sw.js 的 VER、app/index.html 的 <meta name="app-ver">
git add -A && git commit -m "feat: <改动描述>" && git push

# 同步到用户实际使用的仓库
rsync -a --delete --exclude='.git' app/ /tmp/kyy-publish/
cd /tmp/kyy-publish && git add -A && git commit -m "feat: <同一条>" && git push
```

**GitHub 22 端口在本机常连不通**，git 一律用：
```bash
git remote set-url origin ssh://git@ssh.github.com:443/s0meday77/<repo>.git
```

**⏱ GitHub Pages 的坑（2026-10-29 修复）**：所有文件都带 `Cache-Control: max-age=600`，
浏览器会把 HTML 缓存十分钟。表现为「Service Worker 报新版本号，但页面还是老样子」——
用户反复说"怎么弄都不更新"就是这个。已修：
- `sw.js` 的 `fetch` 与 `cache.add` 对页面请求一律 `cache: 'reload'`
- `register('sw.js', { updateViaCache: 'none' })`
- 设置面板同时显示「页面 vX · 缓存 vY」，两者不一致就是 HTML 还旧

推到 Pages 后约 20 秒~3 分钟生效（旧仓库 1942 个文件，legacy 构建慢些）。
紧急情况想让手机立刻拿到新版：用 Safari 打开 `<地址>/?v=<任意数字>`（换 URL 绕开 HTTP 缓存），再回图标打开。

> 仓库名用 `yinger-kaoyan` 不是中文「英二考研」：GitHub 会把纯中文仓库名规范化成 `-`，
> 直接创建会报「Name already exists」，Pages 路径也会变成一串百分号编码。
> 中文名只用在本地文件夹和 README 标题上。

## 另外两种打开方式（本地开发/应急用）

1. **双击 `app/index.html`** —— 直接可用（词库走 `data/words.js`，绕过 file:// 下 fetch 被拦的问题）；但没有 Service Worker，不能打包离线
2. **双击 `启动.command`** —— 起服务器，手机连同一个 WiFi 打开 `http://<本机IP>:8766`（同样没有 SW，因为 http 非 https）

## 导入新一类词（拍完照后照这个跑）

```bash
cd /Users/diting/英二考研

# 1. OCR（vision_ocr 需要 pyobjc，用专用 venv）
/tmp/ocrvenv/bin/python -I tools/ocr/vision_ocr.py src/photos/<新照片目录>/

# 2. 版面重建 → 按教材页分段（--seq：每类从 Word List 1 重新编号）
python3 -I tools/ocr/parse_ocr.py src/ocr_<类别>.json --segment 中频词 --seq \
    --first-list 1 --out /tmp/中频词.txt
#    逐页核对「识别词数 = 书上印的 /NN 词」，对不上必须人工查
#    再追加进总词表（高频词部分不能动）

# 3. 查词 + 下录音 → app/data/words.json
python3 -I tools/build_words.py src/words.txt --out app/data/words.json --days-per-page 4

# 4. 导出 words.js（file:// 双击可用，必做）
python3 -I tools/json2js.py

# 5. 体检（必跑）
python3 -I tools/audit.py app/data/words.json

# 6. 词形离线校验（必跑，专抓 OCR 认错词）
python3 -I tools/wordcheck.py app/data/words.json

# 7. 第二词典交叉核对（可选；接口有速率限制，容易 429）
python3 -I tools/crosscheck.py app/data/words.json --out src/crosscheck.json

# 8. 《词汇闪过》导入后逐行核对 docx 原文有没有全进词库（必跑）
python3 -I tools/verify_star.py app/data/words.json ~/Desktop/词汇闪过*.docx
```

> `/tmp/ocrvenv` 是临时目录，重启后可能没了。重建：
> `python3 -m venv /tmp/ocrvenv && /tmp/ocrvenv/bin/pip install pyobjc-framework-Vision pyobjc-framework-Quartz`

## 🎯 2026-11-16 收工交接（下次开工先看这里）

### 这一批做完了什么

《词汇闪过》**44~65 页 → 高频词 Word List 3 全部 88 词**（441 条搭配）已解析并写进词库：

- `genetic` … `administration`，和词库 Word List 3 的 88 词**逐词顺序完全一致**
- 记忆法 87 ｜ 派生 88 ｜ 近义 62 ｜ 反义 16
- 累计已导入 **259 词 / 1259 条搭配**（Word List 1 + 2 + 3 全覆盖）
- `test3.js` **79/79** 通过，`filetest.js` 正常
- 版本号 **v29**（`app/sw.js` 的 `VER` + `app/index.html` 的 `<meta name="app-ver">` 两处）
- **已发版并线上验证**：两个站点都是 v29，线上 `words.json` 259 词 / 1259 条，
  `data/audio/ph/f/advance_0.mp3` 等抽查 HTTP 200
- 用户当晚已在手机上「📥 打包到手机」并试听，**读音、音色、词组朗读都通过**；
  「释义和书上逐条对照」这件事留到 2026-11-17 抽空做

### 准确性是怎么验的（下次照做）

**脚本已固化：`tools/verify_star.py`**（原来放 `/tmp` 重启就没了，2026-11-23 搬进工具目录）：

```bash
python3 -I tools/verify_star.py app/data/words.json ~/Desktop/词汇闪过*.docx
```

- 输出「词条 / 内容行 / 对上 / 挂到别词 / 没对上 / 未导入词」六项，退出码非 0 就是有行没进词库
- 判据：原文行归一化后要在该词 `sb` 块里找到；「词性 + 释义」拆开各自比对；
  词根小标题（`ag, act 做`）、`链P352` 这类跨页索引、英文括注 `(dynamics)` 不计
- 「↪ 挂到别的词名下」是跨页内容挂对了地方，不算丢
- 用 1~65 页四批 docx 回测：**只剩 `immigrant` 那条已知残句**，和 11-16 手工核对结论一致

逐行核对的原理：把 docx 原文每行（四批共 **2649 行**带中文的）归一化后（去空格标点、把「词性 + 释义」
拆成两个字段再各自比对），检查是否出现在该词 `sb` 块的 JSON 里。**只有 2 行没对上，且都已定性**：

- `immigrant` 下那条 `in the U.S. 在美国的亚洲移民` —— 豆包把前半句 `Asian immigrants` 吃掉了，
  只剩个介词短语。判断规则已写进 `parse_star.py`（英文以介词开头 + 不到 16 字符 + 不含主词词干 → 判为残句丢弃），
  每次运行会把丢掉的列在结尾，**下次务必看一眼那几行是不是真残句**。
- `defence` 段的 `（亦作defense）n.` —— 内容在，只是拆成了「注：亦作 defense」+「义 pos=n.」两个块，
  是核对脚本按整行比对才露的假阳性。

跨页的 3 行（`classical` 两条例句、`in conclusion`）会**挂到正确的词条名下**，不在原词段里，
核对脚本单独列成「↪ 挂到别的词名下」，不算丢。

> 踩过的坑：判断「这句是不是主词的派生词」**不能用公共前缀长度**——`classical` 和 `classify`
> 前六个字母都是 `classi`，按公共前缀会把 classical 的例句塞进 classify 的【扩】。
> 现在只认 `tok.startswith(word)` 或 `tok.startswith(word[:-1])`（`classifiable` ← `classify`）。

### 词组音频（已补齐）

- 单词三套（`audio/v/{m,f,c}/`）齐全，词组三套（`audio/ph/{m,f,c}/`）**各 1259 条全齐**
- `python3 -I tools/tts_check.py --phrase` → 3777 个文件全部合格；`tts_check.py`（单词）4923 个全合格
- 断点续跑：`~/.tts-venv/bin/python -I tools/tts_phrase.py --key m`（f/c 同理，**串行跑，别并行**）
- **坑**：`sh -c "… --key m && … --key f && … --key c"` 这种链式命令，上一批在交互终端里
  被收掉时 m/f 只录到 `fundamental` 就停了、计数一直卡在 815。**别用链式子进程跑长任务**，
  直接一个 key 一条命令地跑，跑完查计数

### 下次开工的顺序（2026-11-17）

1. `git pull` 后先跑 `python3 -I tools/audit.py app/data/words.json` + `cd tests && node test3.js`
2. **先陪用户对书**：他要用手机 App 逐条对纸质书（1~65 页、259 词）。
   发现对不上就定位到「单词 + 第几块」，改 `parse_star.py` 后重跑四批 + `merge_star` + `json2js`；
   改完跑 `python3 -I tools/verify_star.py app/data/words.json ~/Desktop/词汇闪过*.docx` 复核
3. **《词汇闪过》高频词 1~209 页已全部录完**（2026-11-23，Word List 1~12 全覆盖，
   **971 词 / 4728 条搭配**）；下一步是等用户拍中频词章节（210 页起），
   或先把手机上的内容逐条对纸质书核一遍
4. 每批照「准确性是怎么验的」那节核对，别跳

### 发版清单（这次踩齐了，照抄即可）

1. 改 `app/sw.js` 的 `VER` + `app/index.html` 的 `<meta name="app-ver">`（两处必须一致）
2. `python3 -I tools/json2js.py`
3. `cd tests && node test3.js`（79/79）+ `node filetest.js`
4. 提交推 `yinger-kaoyan`，再 `rsync -a --delete --exclude='.git' app/ /tmp/kyy-publish/` 推 `kaoyan-yinger`
5. **两个站都要验**：`curl` 各自的 `index.html`，`app-ver` 两边都是新版本才算发完；
   GitHub Pages legacy 构建 3~5 分钟，`gh api repos/s0meday77/kaoyan-yinger/pages/builds/latest --jq .status`
6. 告诉用户重新「📥 打包到手机」**别忘了，这次是 8712 个音频 / 约 136MB，要提醒他别锁屏**

### 留给下一批的解析笔记

- 同一份 docx 可能是两种版式拼的：`# P44` 一行一个元素 + `===== P55 =====` 起变 tab 三列，
  `normalize_tabs()` 已经兼容，直接跑就行
- `扩 [近] duty n. 责任` 这种套一层的，已按内层标记归到【近】（这批 9 条）
- tab 版式的义项在 `normalize_tabs()` 里打哨兵 `\x01`，它只活在解析中间态，不该出现在 words.json 里

## ⏭ 下次继续导入（交接清单）

**已完成**：高频词 971（12 页 48 天）+ 中频词 635（9 页 36 天）= 1606 词 / 3212 音频 / 84 天，线上 v20。
**剩余四类**：低频词 → 偶考词 → 基础词 → 补充词（顺序按用户给照片的顺序，别自己排）。

每一步的判据（照做，不许跳）：

| 步骤 | 必须看到的输出 | 对不上怎么办 |
|---|---|---|
| OCR | `src/ocr_<类别>.json` 生成 | venv 没了照上面重建 |
| `parse_ocr.py` | 每页打印「识别 N ｜ 书上 M ｜ OK」 | 任何一页「不符」，**必须回看原图人工订正**，不许带着错往下走 |
| 双遍 OCR | 再跑一遍加 `--correct`，逐页 diff | 差异必须人工判断（形近真词只能靠人眼） |
| `build_words.py` | 「无音标 无 ｜ 缺音频 无」 | 有缺就去查有道缓存，别手写假数据 |
| `audit.py` | 只剩 3 组同音词（principle/principal、check/cheque） | 多出任何一条都要查 |
| `wordcheck.py` | 18 个以内，且全是英式拼写/现代词 | 出现「形近但不像词」就是 OCR 错了 |
| `test3.js` | 79/79 | 新增类别要补断言 |
| `filetest.js` | 页面版本显示新版本号 | — |

**新类别落地还要一起改的四处**（漏一处用户就看不到）：
1. `app/sw.js` 的 `VER` 加一位 + `app/index.html` 的 `<meta name="app-ver">` 同步
2. `README.md` / 本文件「当前进度」表补一行
3. 提交推 **两个仓库**：`yinger-kaoyan`（源码）+ `kaoyan-yinger`（用户手机在用）
4. 告诉用户重新「📥 打包到手机」（音频数会变）

**解析新类别时最容易翻车的三条**：
- `--seq --first-list 1` 必须带，用户要求每类从 Word List 1 重排
- 书上印的 `/NN 词` 是唯一裁决标准，识别数和它对不上就是错
- 页内天数固定 4 天，绝不跨页混排（用户要照着纸质书翻页对）

交接给下一个会话时，先读本文件 + `~/.claude/projects/-Users-diting-----/memory/英二考研项目.md`
（2026-11-24 从 `ccagent` / `cc-agent` 两个旧项目的 memory 转移到本项目），再看 `git log --oneline -10` 对版本。

## 《词汇闪过》释义与词组导入（进行中）

**🔴 页段结构（用户 2026-11-23 确认，不许再记错）**：

| 书本页 | 词库类别 | 对应教材 |
|---|---|---|
| 1~209 页 | **高频词** | 教材高频词 Word List 1~12（971 词） |
| 210 页起 | 中频词 | 教材中频词 Word List 1~9（635 词） |

> 66~209 页**全部还是高频词章节**，不是「中频词章节」。
> 之前口头上把 66 页往后说成中频词，是错的；数据本身没放错（中频词 0 个词带 `sb`，259 个 `sb` 全在高频词上）。
>
> **实际经过（2026-11-23 用户确认）**：2026-10-29 那一轮是先把**中频词整批录了**（教材照片 Word List 13~21 → 中频词 635 词），
> 《词汇闪过》高频词只做到第 65 页就停在那里；66~209 页（高频词）从 2026-11-23 起回头补。
> 两件事都对，只是顺序上跳了一段，用户自己都忘了中频词录过 😄

用户用豆包拍照识别成 docx 放桌面（如 `词汇闪过1-15页.docx`），按这个跑：

> **13 份高频词 docx 已归档到 `src/star_docx/`**（2026-11-24，456KB，随仓库备份）。
> 桌面原件可以删——`verify_star.py` 复核时改指归档目录即可：
> `python3 -I tools/verify_star.py app/data/words.json src/star_docx/*.docx`
> 中频词章节的 docx 也照这个放。

```bash
cd /Users/diting/英二考研
# 1. 先看解析对不对（抽样打印）
python3 -I tools/parse_star.py ~/Desktop/词汇闪过1-15页.docx --out /tmp/star.json --show 5
# 2. 匹配进词库（未匹配的词会列出来）
python3 -I tools/merge_star.py ~/Desktop/词汇闪过1-15页.docx
# 3. 重新导出 + 回归
python3 -I tools/json2js.py app/data/words.json app/data/words.js
cd tests && node test3.js
```

- 书上内容写进**一个字段 `sb`**：按书本顺序排好的块列表，书上有什么就有什么
  - `{"k":"记","v":...}` 词根记忆法 · `{"k":"义","pos":"n.","def":...}` 义项
  - `{"k":"例","p":"...","t":"..."}` 例句/搭配 · `{"k":"扩"/"近"/"反","v":...}` 派生/近义/反义
  - **必须按顺序存**：书上一个义项下面跟几条例句再接下个义项，分开存就还原不出原样
  - **不覆盖**有道的 `m` —— 还没导入的词继续显示有道释义（旧字段 `sm`/`sp` 已废弃）
- 前端：有 `sb` 的词，整块收在卡片里，**默认展开**（v30 起），点标题收起、再点打开，每张卡各管各的；
  没导入书上内容的词也走同一套折叠，有道释义放进折叠区
  （用户明确要求：不许全局一展开就全打开，学到哪个词点哪个）；
  点某条例句单独用系统语音朗读，遍数跟随「每词朗读」设置
- 解析靠「词条行 = 单词 + [音标]」分节：词性行开新义项，纯中文行是上一义项的换行续句，
  英文+中文的行是搭配；词条之前的 `ag, act 做` 是词根标题，忽略
- 书上有 `【近]` 这种半角错字、`【族】` 派生词，解析器都兼容了
- 豆包换批次后格式会变（词条行尾带【记】、`扩/近/反` 去掉方括号、单词与音标拆成两行），
  `parse_star.py` 的 `join_split_entries()` 和 tag 正则都已兼容
- **同一份 docx 里还可能是两种版式拼起来的**（44-65 页那批：前半 `# P44` 一行一个元素，
  后半 `===== P55 =====` 起变成 `■ 词 [音标]` + tab 分隔的「词性 \t 义项 \t 例句」三列）：
  `normalize_tabs()` 先把 tab 摊回一行一个元素，中间那格义项打内部哨兵 `\x01`，
  免得「（the military）[sing.] 军人」被当成「英文+中文」判成例句；
  `扩 [近] duty n. 责任` 这种套一层的，以内层标记为准归到【近】
- **扩块后面的搭配行要留一手**：书上会把派生词自己的例句排在【扩】之后，
  那些不能算到主词头上——规则是「不含主词本身的就丢」
- **OCR 会把搭配截断**（immigrant 下面只剩 `in the U.S. 在美国的亚洲移民`）：
  英文部分以介词开头、不到 16 字符、又不含主词词干的，判为残句丢掉，并在结尾列出来复核
- **进度**：《词汇闪过》高频词 **1~209 页全部完成 = 971 词 / 4728 条搭配**，
  教材高频词 Word List 1~12 全覆盖（最后一类 WL12：`resource` → `yield`，209~226 页）
- **2026-11-23 全书收尾终审（1~226 页全部录完后做的一轮全书体检）**：
  - **反向核对**：词库里每一个块（记/义/例/扩/近/反）的内容，都必须在书上原文里找得到
    （归一化后比对；多行合并的释义按「；」拆开逐段查）→ 最终 **0 条凭空内容**
  - 抓到并修掉 **73 处 tab 并排格被压成一行**：`[扩] admiration n. 钦佩  [近] appreciate vt. 欣赏`
    合成一条后【近】混进【扩】——新增 `split_side_tags()`，按内层标记拆回多条，内容一字不改
  - 抓到 `v.-link` 的旧修复有误（原来改成 `v. link-v`，`link-v` 会漏进释义）：
    `weigh` 多出一条垃圾义项、`constitute` 释义前面挂着 `link-v`——改成只留 `v.`，
    在 `_link` 正则里用 `link(?:-v)?\b`（`link-v?\b` 里的 `-` 是必需的，永远匹配不上）
  - 终审四项：① 逐块 971/971 一致 ② 全库词序与书完全一致 ③ 逐行 0 丢失
    （仅 `immigrant` 已知残句）④ 反向核对 0 条
- **2026-11-23 批次（209~226 页）**：88 词 / 445 条搭配，页码 209~226 连续无缺页（`Page 209` 版式）；
  词序与教材「高频词 · Word List 12」全 88 词逐位一致（`resource` → `yield`），
  逐词逐块 888 块全一致、逐行核对 1064/1064 0 丢失、全库 13 批 971 词条回归 0 不一致；测试 79/79。
  这一批版式回归 tab 三列（`Page NNN` 抬头），没有新坑
- ⚠️ 别把「中频词 · Word List 6」和「高频词 · Word List 6」搞混：前者 29 词（censorship 起）、
  后者 82 词（scholar → assure）。查剩余词时务必带上类别前缀过滤
- **2026-11-23 批次（66~85 页）**：81 词 / 394 条搭配，词序与书完全一致（`motor` 被 OCR 排到 `amount` 前，已按书序调回）；
  逐行核对 0 丢失；三套词组音频各补 394 条（共 4959 个文件体检全合格）；测试 79/79
- **2026-11-23 批次（86~105 页）**：82 词 / 399 条搭配（书上印 /82 词），词序与书完全一致；
  逐词逐块核对 796 块全一致、逐行核对 0 丢失；修了两个解析器 bug（见下）。**尚未发版，等 106~209 页全部做完一起推**
- **2026-11-23 批次（106~124 页）**：82 词 / 408 条搭配，页码标记 106~124 连续无缺页；
  词序与教材 Word List 6 前 82 词完全一致（`scholar` → `assure`），逐词逐块 811 块全一致、
  逐行核对 865/865 0 丢失；全库 504 词条回归 0 不一致；测试 79/79。**尚未发版，继续等后续批次一起推**
- **106~124 页踩到的三个新情况（都已修）**：
  1. 豆包把跨页索引「链Pxxx」认成「**纯**Pxxx」，且混进 tab 中间格/末尾格——
     `LINK_RE` 改成 `[链纯]`，`normalize_tabs` 分格后先摘索引再拼行
  2. tab 三列行的**中间格偶尔是并排的近反义**（`[近] aware a. 意识到`），原来被当成义项——
     新增 `TAG_START_RE`，中间格是标记行就不打义项哨兵
  3. **双读音词条**占两行（`segment ['seɡmənt] n.` + `[seɡ'ment] v. 【记】…`），
     第二行被 `[xxx]` 开头的义项分支吃掉，整条混进释义——新增分支只取它的【记】
  另外 `fix_ocr()` 收编两条固定认错：`v.-link`（连系动词标记，现已改为只留 `v.`，
  见 2026-11-23 收尾记录）、括注没闭合时把「；」认回「）」
  （`verify_star.py` 也调用同一个 `fix_ocr`，不会误报）
- **书本身会在跨页处重复一条义项**（`conscious`、`considerable`，Page 106/107、112/113 边界；
  125~144 批的 `technique`、`valuable` 也是）：
  这是书上原样，不是 OCR 重复，**保留**
- **2026-11-23 批次（145~151 页）**：33 词 / 142 条搭配，页码 145~151 连续无缺页；
  词序与教材「高频词 · Word List 8」全 33 词逐位一致（`aircraft` → `worthwhile`），
  逐词逐块 259 块全一致、逐行核对 237/237 0 丢失、全库 9 批 620 词条回归 0 不一致；测试 79/79。
  **尚未发版**
- **145 页起又换版式（已兼容）**：
  1. 音标改用斜杠 `/ˈeəkrɑːft/`，`ENTRY_RE` 同时认 `[音标]` 和 `/音标/`
  2. 组合标记 `【扩】【近】along prep. …`——按内层为准归到【近】，
     `MARK_TAG_RE` 从只认 `[近]` 扩成也认 `【近】`
  3. `【用】【近】president n. …`——`【用】` 是版式残留，tag 正则先跳过它，再按【近】处理
     （不处理的话这条会粘进 `chairman` 的释义尾巴）
- **2026-11-23 批次（152~170 页）**：88 词 / 432 条搭配，页码 152~170 连续无缺页；
  词序与教材「高频词 · Word List 9」全 88 词逐位一致（`ability` → `deal`），
  逐词逐块 932 块全一致、逐行核对 1069/1069 0 丢失、全库 10 批 708 词条回归 0 不一致；测试 79/79。
  **尚未发版**
- **152 页起例句行尾多了圈码**（`⓪①②…`，书上标考频的符号，321 行）：
  `fix_ocr()` 统一剥掉，不进词库；`verify_star` 共用同一套，不会误报。
  每页首还会重复上一页末尾的义项（`abroad` 就是 Page 152/153 各一条，书上原样，保留）
- **2026-11-23 批次（171~189 页）**：87 词 / 436 条搭配（书上印 /87 词），页码 171~189 连续无缺页；
  词序与教材「高频词 · Word List 10」全 87 词逐位一致（`decision` → `insist`），
  逐词逐块 884 块全一致、逐行核对 1019/1019 0 丢失、全库 11 批 795 词条回归 0 不一致；测试 79/79。
  **尚未发版**
- **2026-11-23 批次（190~208 页）**：88 词 / 410 条搭配，页码 190~208 连续无缺页；
  词序与教材「高频词 · Word List 11」全 88 词逐位一致（`inspire` → `reputation`），
  逐词逐块 794 块全一致、逐行核对 745/745 0 丢失、全库 12 批 883 词条回归 0 不一致；测试 79/79。
  **尚未发版**
- **190 页踩到的三个新情况（都已修）**：
  1. 豆包把 `perform [pəˈfɔːm] v.` **整条词条行吞了**，义项和搭配全挂到 `peer` 后面，
     记忆法那行掉到段尾还写成半角 `[记]`——新增 `LOST_ENTRY_PATCHES`（按锚点行补回词条，
     并删掉掉队的半角记录行）；`parse` 和 `verify_star` 统一走 `prep_lines()`
  2. **跨页索引行被重复抄到下一个词条**：`odd` 段尾又出现一次 `occupation` 的
     `[近] profession n. 职业  链P202`，会让他以为 odd 的近义是 profession——
     规则：行里带 `链P/纯P` 索引、且与上一个词条同类块一模一样 → 判为重复抄录跳过
  3. 派生行有**半角 `[` 残留**：`[扩][oddly ad. 怪异地；反常地` → tag 内容前多一个没闭合的 `[`，
     在 tag 分支里剥掉
  另外 `odd` 段尾 `[扩] occupy` 后那两条 occupy 例句（`the occupation of…`）按原有规则
  挂到了 `occupation` 名下（内容确实讲 occupation，verify 显示「挂到别词」不算丢），保留
- **171 页踩到的两个新情况（都已修）**：
  1. 搭配 `place/put emphasis on sth. 强调 / 重视某事` 被 ENTRY_RE 的斜杠音标分支误认成
     「place + 音标 `/put emphasis on sth. /`」→ 新增 `PHON` 字符集，斜杠里只许音标字符
     （不含句点），搭配行不再被吞
  2. `det.`（限定词）不在 `POS_TOKEN` 里，`double` 的「两倍的」被粘到上一个 `a.` 义项上
     → `POS_TOKEN` 补 `det|pl`；`verify_star.line_ok` 同时给纯词性行放行
     （fields_of 不收 pos，否则 `det.` 永远找不到，会被误判「挂到 decide 名下」）
- **2026-11-23 批次（125~144 页）**：83 词 / 403 条搭配，页码 125~144 连续无缺页；
  词序与教材「高频词 · Word List 7」全 83 词逐位一致（`attach` → `aware`），
  逐词逐块 833 块全一致、逐行核对 868/868 0 丢失、全库 8 批 587 词条回归 0 不一致；测试 79/79。
  **尚未发版，继续等后续批次一起推**
- **125~144 页踩到的四个新情况（都已修）**：
  1. tab 版式的第一格变成了「用」「扩」这种分组小标题，**词性挪到第二格**——
     `normalize_tabs` 改成按内容认格子（小标题跳过 / 纯词性格单独成行 / 首末格原样 / 中间格是义项），
     不再死认「第一格是词性」
  2. 词根小标题出现大写（`VOC 叫喊`），原来被当搭配丢掉——词根标题正则加 `re.I`
  3. 义项里的「→」是「，」认错了（`content`：很符合自己心意的→满意的）：
     只在 tab 格子的纯中文内容上替换（`fix_cell`），**【记】里的 → 是词根推导，绝不能动**
     （第一版改在全局，误伤 14 个历史词条，已回退）
  4. `vital` 段尾的 `VOC 叫喊` 被当成残句丢弃——同一处原因，根标题识别后消失

- **86~105 页踩到的两个解析 bug（都已修）**：
  1. 版式「`a.` 词性单独一行 + 下一行中文释义」，若前面已有【记】块，中文行会落进
     「续句」分支被静默丢掉——本页 15 个词因此没有义项（`pleasant`、`positive` 等）。
     修法：纯中文行遇到 `pending_pos` 就新建义项，不再往下找续句。
  2. 词条行的「亦作 xxx」只认全角括号，这批是半角 `(亦作 inquiry)`，导致
     `enquiry` 下的 inquiry 例句、`sceptical` 下的 skeptical 例句被判成「别人的」丢掉。
     修法：别名兼容全/半角括号，且判断归属时把别名算主词（含 y→ies 复数变化）。
- 每导入一批都要核对：书上词序 vs 词库词序（这批发现 account 位置错位，已按书序调整）

## 音色（2026-11-16 大改：整批换掉有道录音）

有道那批真人录音年代久、码率低，用户原话「**读音太老了，而且听不清楚，感觉咬字不清**」。
换成 **Kokoro**（82M 神经网络 TTS，本机跑，不联网不调 API），每个词录三套：

| key | 音色 | Kokoro |
|---|---|---|
| `m` | 男声 · 厚重有力 | `am_fenrir` |
| `f` | 女声 · 自然亲和（**默认**） | `af_heart` |
| `c` | 夹子音 · 甜 | `af_bella` |

- 模型在 `~/tts-models/`（`kokoro-v1.0.onnx` 310M + `voices-v1.0.bin` 27M），
  venv 在 `~/.tts-venv`（`pip install kokoro-onnx`），音素引擎 `brew install espeak-ng`
- 录音：`~/.tts-venv/bin/python -I tools/tts_voices.py --key m`（f/c 同理），三个并行最省时；
  `--apply` 把路径写进 words.json 的 `v` 字段。断点续跑，已有的跳过
- 音频存 `app/data/audio/v/<key>/<word>.mp3`；**旧的 `audio/us|uk/` 一个字节都不动**，留作后备
- 前端 `audioPath(w)` 优先 `w.v[state.voice]`，没有才退回老录音；
  ComfyUI 的模型名（`ng_deepnegative_v1_75t`）永远走系统 TTS，不念垃圾
- 「口音（美音/英音）」设置**已撤**，三套都是美音；`state.accent` 留着只管音标显示
- `edge-tts` 走不通（微软 WSS 恒定 403，换版本号也没用），别再试了。
  试听页 `app/trial.html`（第一轮 8 音色）、`app/trial2.html`（夹子音 5 底嗓 × 3 档音高）留着，
  以后想换音色直接加候选、重出试听页
- 夹子音的甜度靠 `asetrate+atempo` 抬音调（时长不变），见 `tools/tts_cute.py`；
  最终**没加变调**——用户试听后选的 `af_bella` 原声

## 读音五重保障

1. **每页 OCR 词数必须等于书上印的 "/NN 词"** —— 对不上就重扫
2. **每个词必须能在有道拿到音标和释义** —— 拿不到说明这词有问题
3. **双遍 OCR 交叉 diff + 贴边检测 + 裁图复核** —— 曾揪出 `tinance→finance`、`pertormance→performance`、`retorm→reform`、`understandin→understanding`、`unemploymen→unemployment`
4. **`audit.py` 本地体检** —— 音标合法性、音频大小/格式、MD5 串音（两个词共用一份录音）、重复词
5. **`wordcheck.py` 词形校验** —— 对照系统词表 `/usr/share/dict/words`（23.6 万词，Webster's 第二版），专抓"认成另一个不存在的词"这类错

## 释义怎么保证准（2026-10-29 修订）

`build_words.py` 的 `short_meanings()` 有三条铁律，改之前务必看懂：

| 规则 | 踩过的坑 |
|---|---|
| **先按「；」拆义项，再逐条过滤噪声** | 整行判断会把 `valley` 的释义全丢掉（那行末尾带「（Valley）人名」） |
| **按长度预算收义项（`SENSE_BUDGET=24`），停在义项边界** | 原来 `s[:20]` 硬切，把 `suffer` 切成「受苦，受折」、`judgement` 切成「（同 judgme」 |
| **不能只取第一个义项** | `departure` 有道第一义项是「背离」，最常用的「离开，启程」被漏掉 |

单个义项超过 30 字（`SENSE_MAX`）用 `clip()` 按标点收口，括号没闭合就从左括号断开
（`stem` 的 abbr. 行后面拖着一整串英文全称就是这种情况）。

噪声过滤只针对带 `<英>/<美>` 标记且去掉标记后≤2 字的纯译名（`<英>瓦利`），
**不能**误伤「（一件）衣服」这种整体带括号的真义项（`garment` 就吃过这个亏）。

2026-10-29 首次全量结果：971 词全部通过前四项；第五项只有 12 个"查不到"，
逐个核对全是合理的英式拼写（centre/judgement/sceptical/theatre/endeavour/fulfil）
或现代词（automation/airline/database），美式对应写法在词表里都有，**没有一个怪词**。

中频词 635 词累加后共 1606 词，复检结论一致：0 空释义、0 缺音标、0 缺录音、释义与有道缓存重算 0 差异。

## OCR 实战踩坑（2026-10-29 中频词 9 页）

`parse_ocr.py` 因此加了这些能力，以后拍新类别直接用：

| 参数/逻辑 | 解决什么 |
|---|---|
| `--segment 中频词 --seq --first-list 1` | 按页输出 `# 中频词 · Word List N` 段头；用户要求**每类从 1 重新编号**，不跟书上印的 13~21 |
| `natural_key()` | 让 中2 排在 中10 前面 |
| 旋转 270° 时翻转 x/y | 否则词序整个倒过来，用户照书对不上（第 7 页就是） |
| 书上印了 `/NN 词` 就按词数精确截断 | 原来先按行距切尾，29 词 5 列这种短表会被切掉一半（第 6 页 16/29） |
| 词形正则 `[A-Za-z][a-z'-]+$` | 放宽会把页眉装饰字当单词（`EAtSiaI` 挤掉了 `outlook`） |
| 低置信(<0.6) 且不在 `/usr/share/dict/words` 才剔 | 剔掉 `miathiziz`/`toster`，但保留 `spy`/`mock`/`reap` 这类低置信真词 |
| 页内去重 | 页面底部讲解区会把首词再印一遍 |

**双遍 OCR 必须做**：一遍普通、一遍 `--correct`（语言纠错），逐页 diff。
中频词 9 页里 7 页完全一致，2 页差异全部人工核实。

**人工修正记录（中频词）**：
- 第 2 页 `contirm→confirm`、`interterence→interference`、`intertere→interfere`、`sacritice→sacrifice`（fibre 是英式拼写，保留）
- 第 8 页 `toster→foster`、补回漏掉的 `loom`（靠「书上 74 vs 识别 73」发现的）

**教训**：词数对不上、或词表里出现"形近但不像词"的东西，一定是 OCR 错了。
`wordcheck.py` 只能抓「认成不存在的词」，**认成另一个真词的错只能靠双遍 OCR + 逐页目视**。

## 前端铁律

**`<script>` 加载顺序：`data/words.js` → `ui.js` → `app.js` → `list.js` → `practice.js`**

- `ui.js` 必须第一，否则 `boot()` 同步执行 `applyTheme()` 时 `BAR_COLOR` 处在 TDZ 会崩
- 录音存在固定名 `audio-v1` 缓存里，**不跟版本号走**——发新版不能清掉用户打的 3212 个音频。
  `activate` 里会把旧版缓存中的录音迁移过来，用户不必重新打包
- iOS 播音频会发 Range 分段请求，缓存里只有整段 → 必须 `fetch` 取整段转 blob 再播，
  同时 SW 侧手动切出 206 响应。否则离线时只有碰巧播过的词有声音
- `boot()` 必须等 `DOMContentLoaded` 再跑，否则 `bind()` 抢在 `practice.js` 之前执行 → `playCurrentDict is not defined`
- `localStorage` 在 file:// 下可能抛异常，读写都要包 try/catch
- 「回到顶部」箭头（`#toTop`，`setupToTop()`）只在**点听页**且 `scrollY > 360` 时显示，
  切标签要调 `window.__toTopSync()` 重新算，否则在错词页也会浮着
  滚动用 `scrollTo({behavior:'smooth'})`，350ms 后若没动起来就直接跳顶（老内核兜底）
- 改前端后跑回归（首次需 `cd tests && npm i jsdom`）：
  ```bash
  cd /Users/diting/英二考研/tests && node test3.js      # 73 项功能断言
  cd /Users/diting/英二考研/tests && node filetest.js   # 模拟 file:// 真实加载顺序
  ```

单文件都控制在 500 行以内（全局规范）。

## 版本记录

| 版本 | 日期 | 内容 |
|---|---|---|
| v32 | 2026-11-23 | **《词汇闪过》高频词 1~226 页全部导入**：971 词 / 4728 条搭配（Word List 1~12 全覆盖），反向核对 0 条凭空内容；并排标签拆条、`link-v` 释义清理 |
| v31 | 2026-11-23 | 词组朗读把 `place/put …` 的斜杠念成 or（录音与系统语音兜底同步改），避免念出 slash；《词汇闪过》171~189 页 87 词导入（436 条搭配，**Word List 10 全覆盖**） |
| v30 | 2026-11-23 | 释义区改成**默认展开**：跟着读时看得见意思，点标题一下收起、再点打开；未导入《词汇闪过》的词也走同一套折叠（有道释义在折叠区里） |
| v29 | 2026-11-16 | 《词汇闪过》44~65 页 88 词导入（441 条搭配，**Word List 3 全覆盖**）；`parse_star.py` 支持豆包 tab 三列版式 |
| v28 | 2026-11-16 | **全库换读音**：有道老录音整批换成 Kokoro 神经网络，每词三套音色（男声/女声/夹子音），设置面板「口音」改为「音色」；词组也用同一套音色录；《词汇闪过》22~43 页 88 词导入（Word List 2 全覆盖） |
| v27 | 2026-11-16 | 夹子音候选试听页（5 底嗓 × 3 档音高） |
| v26 | 2026-11-16 | 设置面板加「换新读音试听」入口 |
| v25 | 2026-11-16 | 书中内容改为**按书本顺序的完整块**（记忆法/义项/例句/派生/近反义全都在），卡片折叠改成每张卡各自点开，不再一起展开 |
| v24 | 2026-11-16 | 《词汇闪过》16~21 页 25 词导入，**Word List 1 的 83 词全部换成书上释义 + 词组**（391 条搭配）；account 位置按书的顺序挪到 recovery 之后 |
| v23 | 2026-11-16 | 点词组朗读的遍数改为跟随「每词朗读」设置（原来固定 1 遍）；点中的词组高亮，读完自动熄灭 |
| v22 | 2026-11-16 | 单词卡支持折叠显示《词汇闪过》的释义与词组（书上前 15 页 58 词已导入，其余词继续用有道释义）；点词组单独朗读 |
| v21 | 2026-11-01 | 新增独立章节「ComfyUI词汇」：80 词 / 5 页 / 20 天（负面嵌入→正面提示词→核心节点→采样参数→模型与概念）。页按钮显示中文名而非数字；专业词音标缺失时不再显示 `//`，无真人录音自动走系统 TTS |
| v20 | 2026-10-29 | 点听页加「回到顶部」悬浮箭头（下滑 360px 浮出，平滑回顶，切标签自动收起） |
| v19 | 2026-10-29 | 中频词 9 页 635 词上线（Word List 1~9、36 天）；释义提取规则重写（不再硬切、不漏常用义项） |
| v18 | 2026-10-29 | 修「代码更新了手机还显示旧页面」：`cache:'reload'` + `updateViaCache:'none'`；删掉「添加到主屏幕」提示 |
| v17 及以前 | 2026-10-29 | 高频词 971 词上线、离线打包、iOS Range 音频、连听、听写、错词本 |

### 2026-10-29 中频词上线全记录

- 教材在桌面「中频词」文件夹，9 页，书上印的是 Word List 13~21，**按用户要求重排为 1~9**
- 逐页词数：78 / 78 / 76 / 76 / 76 / 29 / 72 / 74 / 76 = **635 词**，与书上 `/NN 词` 全部一致
- 双遍 OCR 交叉 diff：7 页完全一致，2 页差异全部人工核实（见下方「人工修正记录」）
- 词形校验 18 个查不到，逐个核实全是合法英式拼写或现代词
- 释义抽检 27 个 + 全量重算：**0 处不一致、0 空释义、0 缺音标、0 缺录音**
- 合计 **1606 词 / 3212 个音频（2948 mp3 + 264 wav）/ 84 天**
- 三组「共用录音」是真正的同音词：principle-principal（英）、check-cheque（美/英），不用管

## 已知限制

- 局域网 http 下 Service Worker 不生效（浏览器只允许 https 或 localhost），真离线要装到主屏幕后由浏览器缓存兜着
- `dictionaryapi.dev` 是英式词典，和有道美音会有合理的英美差异，交叉核对主要看「查不到的词」——那才是 OCR 认错的强信号
