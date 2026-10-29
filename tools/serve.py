#!/usr/bin/env python3
"""在本机起一个静态服务器，手机连同一个 Wi-Fi 就能打开这个 App。

用法: python3 -I serve.py            # 默认 8765 端口
      python3 -I serve.py 9000
"""
import http.server
import socket
import socketserver
import sys
import os

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".webmanifest": "application/manifest+json",
        ".json": "application/json; charset=utf-8",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
    }

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print("服务已启动：")
        print("  本机打开  http://localhost:%d" % PORT)
        print("  手机打开  http://%s:%d" % (lan_ip(), PORT))
        print("  （手机需与本机连同一个 Wi-Fi；Ctrl+C 停止）")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止")
