"""Serve the live session view, pushing changes as they happen.

It listens on localhost unless told otherwise: `SESSION_TREE_HOST` (or the
CLI's `--host`) names the address to bind, so a phone on the same tailnet can
open it. There is no authentication, so the address should be one only your
own devices can reach, never 0.0.0.0 on a shared network.

The watcher thread re-reads what has been appended to the transcripts several
times a second and pushes to every open browser over server-sent events, so the
page is a live instrument rather than something to refresh.
"""

from __future__ import annotations

import contextlib
import json
import os
import queue
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from session_tree.state import build

HERE = Path(__file__).resolve().parent
PAGE = HERE / "index.html"
DEFAULT_PORT = 8787
DEFAULT_HOST = "127.0.0.1"
POLL_SECONDS = 0.4
CLIENT_QUEUE_DEPTH = 8
HEARTBEAT_SECONDS = 15
QUEUE_WAIT_SECONDS = 5

_clients: list[queue.Queue[str]] = []
_clients_lock = threading.Lock()
_latest: dict[str, Any] = {"payload": "", "at": 0.0}


def snapshot() -> str:
    """Return the current picture as a JSON string."""
    return json.dumps(build(), ensure_ascii=False, default=str)


def _broadcast(payload: str) -> None:
    with _clients_lock:
        targets = list(_clients)
    for sink in targets:
        # a browser that cannot keep up simply gets the next one
        with contextlib.suppress(queue.Full):
            sink.put_nowait(payload)


def watch(stop: threading.Event | None = None) -> None:
    """Poll the transcripts and push whenever the picture changes."""
    previous: str | None = None
    while stop is None or not stop.is_set():
        try:
            payload = snapshot()
        except Exception as error:  # noqa: BLE001 - the thread must never die
            sys.stderr.write(f"watch error: {error!r}\n")
        else:
            if payload != previous:
                previous = payload
                _latest["payload"] = payload
                _latest["at"] = time.time()
                _broadcast(payload)
        time.sleep(POLL_SECONDS)


class Handler(BaseHTTPRequestHandler):
    """Serves the page, the current state, and the event stream."""

    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Stay quiet; this runs beside an interactive terminal."""

    def do_GET(self) -> None:
        """Route a GET request."""
        path = self.path.split("?")[0]
        if path == "/api/ping":
            self._send(HTTPStatus.OK, '{"service":"session-tree"}', "application/json")
        elif path == "/api/state":
            self._send(HTTPStatus.OK, _latest["payload"] or snapshot(), "application/json")
        elif path == "/events":
            self._stream()
        elif path in ("/", "/index.html"):
            self._send_page()
        else:
            self._send(HTTPStatus.NOT_FOUND, "not found", "text/plain")

    def _send(self, code: HTTPStatus, body: str | bytes, content_type: str) -> None:
        raw = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_page(self) -> None:
        try:
            body = PAGE.read_bytes()
        except OSError:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, "index.html missing", "text/plain")
            return
        self._send(HTTPStatus.OK, body, "text/html; charset=utf-8")

    def _stream(self) -> None:
        sink: queue.Queue[str] = queue.Queue(maxsize=CLIENT_QUEUE_DEPTH)
        with _clients_lock:
            _clients.append(sink)
        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self._push(_latest["payload"] or snapshot())
            last_beat = time.time()
            while True:
                try:
                    self._push(sink.get(timeout=QUEUE_WAIT_SECONDS))
                except queue.Empty:
                    if time.time() - last_beat > HEARTBEAT_SECONDS:
                        self.wfile.write(b": beat\n\n")  # keep the socket open
                        self.wfile.flush()
                        last_beat = time.time()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # the browser went away, which is ordinary
        finally:
            with _clients_lock:
                if sink in _clients:
                    _clients.remove(sink)

    def _push(self, payload: str) -> None:
        self.wfile.write(b"data: " + payload.encode("utf-8") + b"\n\n")
        self.wfile.flush()


def resolve_host(host: str | None = None) -> str:
    """Return the address to bind: the argument, else SESSION_TREE_HOST, else localhost."""
    return host or os.environ.get("SESSION_TREE_HOST") or DEFAULT_HOST


def make_server(port: int, host: str) -> ThreadingHTTPServer:
    """Bind the server to host:port without serving yet."""
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server


def serve(port: int | None = None, host: str | None = None) -> None:
    """Start the watcher and serve until interrupted."""
    chosen = port or int(os.environ.get("SESSION_TREE_PORT", DEFAULT_PORT))
    where = resolve_host(host)
    threading.Thread(target=watch, daemon=True).start()
    server = make_server(chosen, where)
    sys.stderr.write(f"session-tree on http://{where}:{chosen}/\n")
    server.serve_forever()


if __name__ == "__main__":
    serve()
