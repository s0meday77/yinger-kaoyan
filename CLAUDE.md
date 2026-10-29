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
│   ├── sw.js                 Service Worker（当前 VER=v19）
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
```

> `/tmp/ocrvenv` 是临时目录，重启后可能没了。重建：
> `python3 -m venv /tmp/ocrvenv && /tmp/ocrvenv/bin/pip install pyobjc-framework-Vision pyobjc-framework-Quartz`

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
- 改前端后跑回归（首次需 `cd tests && npm i jsdom`）：
  ```bash
  cd /Users/diting/英二考研/tests && node test3.js      # 50 项功能断言
  cd /Users/diting/英二考研/tests && node filetest.js   # 模拟 file:// 真实加载顺序
  ```

单文件都控制在 500 行以内（全局规范）。

## 已知限制

- 局域网 http 下 Service Worker 不生效（浏览器只允许 https 或 localhost），真离线要装到主屏幕后由浏览器缓存兜着
- `dictionaryapi.dev` 是英式词典，和有道美音会有合理的英美差异，交叉核对主要看「查不到的词」——那才是 OCR 认错的强信号
