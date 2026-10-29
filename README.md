# 英二考研

考研英语（二）教材词汇 → **点一下就朗读**的手机 App；听写、默写、对着教材一页页学。

装上之后：**一点就开，不用电脑、不用联网。**

---

## 目录

```
英二考研/
├── app/                     前端 PWA（这是部署到网上的部分）
│   ├── index.html
│   ├── style.css            6 套皮肤
│   ├── ui.js                皮肤 + 连听
│   ├── app.js               状态 / 发音 / 页天导航 / 离线打包
│   ├── list.js              点听列表
│   ├── practice.js          听写 / 错词本
│   ├── sw.js                Service Worker（离线缓存）
│   └── data/
│       ├── words.json       词库（音标、释义、类别/页/天）
│       ├── words.js         同上的 window 版本，给本地双击用
│       └── audio/{us,uk}/   971×2 个真人录音
├── src/
│   ├── photos/              教材照片原图
│   └── words.txt            词表
├── tools/                   拍照 → OCR → 查词 → 录音 全流水线
├── tests/                   前端回归测试（jsdom）
├── CLAUDE.md                开发备忘（结构、铁律、流水线命令）
└── 手机安装说明.md
```

## 学习结构

```
类别（高频/中频/低频/偶考/基础/补充）
  └─ 教材页（Word List N）
       └─ 页内第几天（每页固定 4 天）
            └─ 全局第 N 天（12 页 × 4 = 48 天）
```

词是**按教材页组织**的，翻着纸质书一页一页对得上。

## 当前进度

| 类别 | 词数 | 页数 | 天数 | 状态 |
|---|---|---|---|---|
| 高频词 | 971 | 12 | 48 | ✅ |
| 中频词 | — | — | — | 待导入 |
| 低频词 | — | — | — | 待导入 |
| 偶考词 | — | — | — | 待导入 |
| 基础词 | — | — | — | 待导入 |
| 补充词 | — | — | — | 待导入 |

## 读音怎么保证准

1. 每页 OCR 词数必须等于书上印的「/NN 词」
2. 每个词必须能在词典拿到音标和释义
3. 双遍 OCR 交叉比对 + 裁图复核
4. `tools/audit.py` 体检：音标合法性、音频大小/格式、MD5 串音、重复词
5. `tools/wordcheck.py` 词形校验：对照 23.6 万词系统词表，专抓认错的词

971 个词全部通过，没有一个错词。

## 自己跑起来

```bash
# 起本地服务器（手机同 WiFi 可访问）
python3 -I tools/serve.py 8766

# 体检
python3 -I tools/audit.py app/data/words.json
python3 -I tools/wordcheck.py app/data/words.json

# 回归测试
cd tests && npm i && node test3.js
```

## 导入新一类词

照片放进 `src/photos/<新目录>/`，然后：

```bash
/tmp/ocrvenv/bin/python -I tools/ocr/vision_ocr.py src/photos/<新目录>/
python3 -I tools/ocr/parse_ocr.py
python3 -I tools/build_words.py src/words.txt --out app/data/words.json --days-per-page 4
python3 -I tools/json2js.py
```

## 部署

推送到 `main` 分支，GitHub Actions 会自动把 `app/` 发布到 Pages。
改了前端记得把 `app/sw.js` 里的 `VER` 加一位，否则手机上的旧缓存不失效。

---

音频来自有道词典真人发音，仅个人学习使用。
