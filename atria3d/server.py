#!/usr/bin/env python3
"""逐帧捕获服务器: 接收页面 POST 的 dataURL PNG, 存 frames/f%05d.png"""
import http.server, base64, os, sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
os.makedirs(OUT, exist_ok=True)

class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode()
        if self.path.startswith("/frame/"):
            i = int(self.path.split("/")[-1])
            b64 = body.split(",", 1)[1]
            open(f"{OUT}/f{i:05d}.png", "wb").write(base64.b64decode(b64))
        elif self.path == "/done":
            open(f"{OUT}/DONE", "w").write("1")
            print("capture done", flush=True)
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
    def do_GET(self):  # 静态文件
        p = self.path.split("?")[0]
        if p == "/": p = "/index.html"
        fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), p.lstrip("/"))
        if os.path.exists(fp):
            self.send_response(200)
            ct = "text/html" if fp.endswith(".html") else \
                 "text/javascript" if fp.endswith(".js") else "application/octet-stream"
            self.send_header("Content-Type", ct)
            self.end_headers()
            self.wfile.write(open(fp, "rb").read())
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *a): pass

http.server.ThreadingHTTPServer(("127.0.0.1", 8777), H).serve_forever()
