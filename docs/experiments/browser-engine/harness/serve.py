"""
A static file server for dist/ that behaves like a static host (GitHub Pages, Netlify, S3 +
CloudFront): gzip when the client accepts it, `application/wasm` for .wasm, and a 10-minute
`Cache-Control`, so the harness measures realistic transfer sizes and repeat visits.

    python3 harness/serve.py [--port 8765]        then open http://localhost:8765/?engine=ts
"""
from __future__ import annotations

import argparse
import gzip
import mimetypes
import threading
from functools import lru_cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DIST = Path(__file__).resolve().parent.parent / "dist"
TYPES = {".wasm": "application/wasm", ".mjs": "text/javascript", ".js": "text/javascript", ".py": "text/x-python",
         ".json": "application/json", ".zip": "application/zip", ".css": "text/css", ".html": "text/html"}


@lru_cache(maxsize=None)
def _gzipped(path: Path, mtime: float) -> bytes:
    return gzip.compress(path.read_bytes(), compresslevel=6)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def log_message(self, *args):  # quiet
        pass

    def do_GET(self):
        rel = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        path = (DIST / rel).resolve()
        if not path.is_file() or DIST not in path.parents:
            self.send_error(404)
            return
        body = path.read_bytes()
        encoding = None
        if "gzip" in self.headers.get("Accept-Encoding", ""):
            body, encoding = _gzipped(path, path.stat().st_mtime), "gzip"
        self.send_response(200)
        self.send_header("Content-Type", TYPES.get(path.suffix) or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=600")
        if encoding:
            self.send_header("Content-Encoding", encoding)
        self.end_headers()
        self.wfile.write(body)


def start(port: int = 0) -> tuple[ThreadingHTTPServer, str]:
    """Serve dist/ in a background thread; returns the server and its base URL."""
    if not (DIST / "index.html").is_file():
        raise SystemExit("dist/ is missing: run `npm run build` first")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server, url = start(args.port)
    print(f"serving {DIST} at {url}?engine=ts  (ctrl-c to stop)")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
