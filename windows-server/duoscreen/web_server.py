"""Robust HTTP and WebSocket server for iPad Safari and web clients."""

from __future__ import annotations

import asyncio
import http.server
import json
import logging
import os
import struct
import threading
from typing import Callable, Optional, Set

from websockets.asyncio.server import ServerConnection, serve

log = logging.getLogger(__name__)

HTML_PATH = os.path.join(os.path.dirname(__file__), "web", "index.html")


class WebStreamingServer:
    """Serves index.html via ThreadingHTTPServer and streams frames via WebSockets."""

    def __init__(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        self.host = host
        self.port = port
        self.ws_port = port + 1
        self.clients: Set[ServerConnection] = set()
        self._input_callback: Optional[Callable[[dict], None]] = None
        self._httpd: Optional[http.server.ThreadingHTTPServer] = None
        self._http_thread: Optional[threading.Thread] = None
        self._ws_server = None

    def set_input_callback(self, cb: Callable[[dict], None]) -> None:
        self._input_callback = cb

    def _start_http_server(self) -> None:
        server_self = self

        class RobustHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if os.path.exists(HTML_PATH):
                    with open(HTML_PATH, "rb") as f:
                        body = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_error(404, "index.html not found")

            def log_message(self, format: str, *args) -> None:  # noqa: A002
                pass

        try:
            http.server.ThreadingHTTPServer.allow_reuse_address = True
            self._httpd = http.server.ThreadingHTTPServer((self.host, self.port), RobustHandler)
            log.info("HTTP Server listening on http://%s:%d", self.host, self.port)
            self._httpd.serve_forever()
        except Exception as exc:
            log.error("Failed to start HTTP server on port %d: %s", self.port, exc)

    async def _handle_ws(self, connection: ServerConnection) -> None:
        """Handle incoming WebSocket connections from iPad / browsers."""
        self.clients.add(connection)
        log.info("Web client connected: %s (Total: %d)", connection.remote_address, len(self.clients))

        try:
            async for message in connection:
                if isinstance(message, str):
                    try:
                        data = json.loads(message)
                        if data.get("type") == "input" and self._input_callback:
                            self._input_callback({
                                "x": float(data["x"]),
                                "y": float(data["y"]),
                                "action": int(data["action"]),
                            })
                    except Exception as e:
                        log.debug("Invalid message from web client: %s", e)
        except Exception as exc:
            log.debug("Web client disconnected: %s (%s)", connection.remote_address, exc)
        finally:
            self.clients.discard(connection)
            log.info("Web client left: %s (Remaining: %d)", connection.remote_address, len(self.clients))

    async def broadcast_frame(self, jpeg_bytes: bytes, timestamp_ms: int) -> None:
        """Broadcast a JPEG frame to all connected web clients."""
        if not self.clients:
            return

        header = struct.pack("<Q", timestamp_ms)
        payload = header + jpeg_bytes

        disconnected = set()
        for client in self.clients:
            try:
                await client.send(payload)
            except Exception:
                disconnected.add(client)

        for client in disconnected:
            self.clients.discard(client)

    async def start(self) -> None:
        """Start both HTTP thread and WebSocket async server."""
        self._http_thread = threading.Thread(target=self._start_http_server, daemon=True)
        self._http_thread.start()

        self._ws_server = await serve(self._handle_ws, self.host, self.ws_port)
        log.info("WebSocket Server listening on ws://%s:%d", self.host, self.ws_port)

        await self._ws_server.serve_forever()

    async def stop(self) -> None:
        if self._httpd:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
        if self._ws_server:
            try:
                self._ws_server.close()
                await self._ws_server.wait_closed()
            except Exception:
                pass
