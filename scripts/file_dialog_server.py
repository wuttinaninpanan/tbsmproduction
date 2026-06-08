"""
file_dialog_server.py — รันบน Windows (ไม่ใช่ใน Docker)

วิธีใช้:
    python scripts/file_dialog_server.py

จากนั้นเปิด http://localhost:8003/inspection/inspection_modelss/
กดปุ่ม Browse ได้เลย — จะเปิด Windows file dialog และได้ path เต็มกลับมา
"""

import json
import tkinter as tk
from http.server import BaseHTTPRequestHandler, HTTPServer
from tkinter import filedialog

PORT = 8099
ALLOW_ORIGINS = {
    "http://localhost:8003",
    "http://127.0.0.1:8003",
}

FILETYPES = [
    ("Model files", "*.pt *.pth *.onnx *.pkl *.bin *.weights"),
    ("All files", "*.*"),
]


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get("Origin", "")
        allowed = origin if origin in ALLOW_ORIGINS else next(iter(ALLOW_ORIGINS))
        self.send_header("Access-Control-Allow-Origin", allowed)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/pick":
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                parent=root,
                title="เลือกไฟล์ Model",
                filetypes=FILETYPES,
            )
            root.destroy()
            path = path.replace("\\", "/") if path else ""
            self._json({"path": path})

        elif self.path == "/ping":
            self._json({"ok": True})

        else:
            self.send_response(404)
            self.end_headers()

    def _json(self, data: dict):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), Handler)
    print(f"✓ File dialog server → http://localhost:{PORT}")
    print("  กด Ctrl+C เพื่อหยุด\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("หยุดแล้ว")
