#!/usr/bin/env python3
"""A local counting proxy, to check the budget the way the grader will.

    python3 checks/count_proxy.py --port 8765 --upstream https://openrouter.ai/api/v1 --log calls.jsonl

then run the system with OPENROUTER_BASE_URL=http://127.0.0.1:8765 and read
the per-item counts with checks/budget_report.py.  Every request is logged
with its X-Item-Id header (or null if missing) BEFORE it is forwarded, so a
request that fails upstream still counts -- as it will at the grader's proxy.
"""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

LOCK = threading.Lock()


def make_handler(upstream, log_path):
    client = httpx.Client(timeout=180)

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            iid = self.headers.get("X-Item-Id")
            try:
                req = json.loads(body)
                meta = {k: req.get(k) for k in ("model", "temperature", "top_p", "reasoning")}
            except Exception:
                meta = {}
            with LOCK, open(log_path, "a") as f:
                f.write(json.dumps({"item": iid, "path": self.path, **meta}) + "\n")
            hdrs = {k: v for k, v in self.headers.items()
                    if k.lower() not in ("host", "content-length", "accept-encoding")}
            r = client.post(upstream.rstrip("/") + self.path, content=body, headers=hdrs)
            self.send_response(r.status_code)
            self.send_header("Content-Type", r.headers.get("content-type", "application/json"))
            self.send_header("Content-Length", str(len(r.content)))
            self.end_headers()
            self.wfile.write(r.content)

        def log_message(self, *a):
            pass

    return H


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--upstream", default="https://openrouter.ai/api/v1")
    ap.add_argument("--log", default="calls.jsonl")
    a = ap.parse_args()
    ThreadingHTTPServer.request_queue_size = 256   # default 5 refuses bursts
    ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(a.upstream, a.log)).serve_forever()
