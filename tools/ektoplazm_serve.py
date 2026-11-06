#!/usr/bin/env python3
"""Serve the private alot preview on this Mac only, with the seeking support browsers need for audio.

  python3 -I ektoplazm_serve.py        then open http://127.0.0.1:8765/?lang=en#studio
"""
import functools, http.server, os, re

ROOT = os.path.expanduser('~/music-pipeline/ektoplazm/preview')
PORT = 8765

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def do_GET(self):
        path = self.translate_path(self.path)
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', self.headers.get('Range', ''))
        if not match or not os.path.isfile(path) or (not match.group(1) and not match.group(2)):
            return super().do_GET()
        size = os.path.getsize(path)
        if match.group(1):
            start, end = int(match.group(1)), int(match.group(2) or size - 1)
        else:
            start, end = max(0, size - int(match.group(2))), size - 1
        end = min(end, size - 1)
        if start > end:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.end_headers()
            return
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.end_headers()
        with open(path, 'rb') as source:
            source.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = source.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

if __name__ == '__main__':
    server = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), functools.partial(Handler, directory=ROOT))
    print(f'http://127.0.0.1:{PORT}/?lang=en#studio', flush=True)
    server.serve_forever()
