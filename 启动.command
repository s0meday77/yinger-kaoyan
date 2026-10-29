#!/bin/bash
# 双击这个文件就能启动「考研英二」App（关掉终端窗口即停止）
cd "$(dirname "$0")" || exit 1

# 已有服务就先停掉，避免端口占用
lsof -ti tcp:8766 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1

IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "本机IP")

echo "================================================"
echo "  考研英二 App 已启动"
echo ""
echo "  手机（连同一个 WiFi）打开："
echo "      http://$IP:8766"
echo ""
echo "  iPhone Safari 打开后：分享按钮 → 添加到主屏幕"
echo ""
echo "  用完直接关掉这个窗口就行"
echo "================================================"
echo ""

python3 -I tools/serve.py 8766
