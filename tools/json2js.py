#!/usr/bin/env python3
"""words.json → words.js

浏览器用 file:// 双击打开时，fetch() 会被安全策略拦住，词库读不到。
改成 script 标签加载就没这个问题，所以每次生成 json 后顺手导一份 js。

用法:
    python3 -I json2js.py ../app/data/words.json ../app/data/words.js
"""
import io
import json
import sys


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    with io.open(src, encoding="utf-8") as f:
        data = json.load(f)
    with io.open(dst, "w", encoding="utf-8") as f:
        f.write("/* 自动生成，勿手改 —— 双击打开 index.html 时用这份数据 */\n")
        f.write("window.__WORDS__ = ")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print("已写入 %s（%d 词）" % (dst, data.get("count", 0)))


if __name__ == "__main__":
    main()
