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
│   ├── sw.js                 Service Worker（当前 VER=v9）
│   ├── manifest.webmanifest  添加到主屏幕用
│   ├── icons/                应用图标
│   └── data/
│       ├── words.json        词库（含音标、释义、所属类别/页/天）
│       ├── words.js          同上，包成 window.__WORDS__，给 file:// 用
│       └── audio/{us,uk}/    971×2 个有道真人录音
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
            └─ 全局第 N 天（12 页 × 4 = 48 天）
```

**必须先按教材页汇总，再在页内分天，绝不能跨页混排天数。** 用户原话——"你这样搞我会乱的啊，我怎么对着教材学啊"。他要翻着纸质教材一页一页对。

当前进度：

| 类别 | 词数 | 页数 | 天数 | 状态 |
|---|---|---|---|---|
| 高频词 | 971 | 12 | 48 | ✅ 完成 |
| 中频词 | — | — | — | 待导入 |
| 低频词 | — | — | — | 待导入 |
| 偶考词 | — | — | — | 待导入 |
| 基础词 | — | — | — | 待导入 |
| 补充词 | — | — | — | 待导入 |

## 手机独立安装（用户首选，2026-10-29 上线）

**线上地址：<https://s0meday77.github.io/yinger-kaoyan/>**
**仓库：<https://github.com/s0meday77/yinger-kaoyan>**（完整源码仓库，`app/` 由 GitHub Actions 发布到 Pages）

iPhone Safari 打开 → 添加到主屏幕 → 从图标进 App → ⚙ 设置 → **📥 打包到手机**。
打包会把 1942 个音频灌进 Cache Storage，之后**彻底离线**：不用电脑、不用联网、不用开服务器。

详见 `手机安装说明.md`，二维码在 `二维码.png`。

**发布更新：**
```bash
cd /Users/diting/英二考研
# ⚠️ 改了 app/ 里的前端文件，一定要先把 app/sw.js 的 VER 往上加一位，
#    否则手机上的旧缓存不会失效，用户看不到新版
git add -A && git commit -m "feat: <改动描述>" && git push
```
推送后 `.github/workflows/deploy.yml` 自动把 `app/` 发布到 Pages，约 20 秒~1 分钟生效。
手机端从图标重开 App 即可拿到新版。

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

# 2. 版面重建 → src/words.txt（会追加到现有词表，按类别分段）
python3 -I tools/ocr/parse_ocr.py

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

2026-10-29 首次全量结果：971 词全部通过前四项；第五项只有 12 个"查不到"，
逐个核对全是合理的英式拼写（centre/judgement/sceptical/theatre/endeavour/fulfil）
或现代词（automation/airline/database），美式对应写法在词表里都有，**没有一个怪词**。

## 前端铁律

**`<script>` 加载顺序：`data/words.js` → `ui.js` → `app.js` → `list.js` → `practice.js`**

- `ui.js` 必须第一，否则 `boot()` 同步执行 `applyTheme()` 时 `BAR_COLOR` 处在 TDZ 会崩
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
