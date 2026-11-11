"""HTTP and WebSocket server for iPad Safari and web clients."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import struct
import time
from typing import Callable, Optional, Set

from websockets.asyncio.server import ServerConnection, serve

log = logging.getLogger(__name__)

HTML_PATH = os.path.join(os.path.dirname(__file__), "web", "index.html")


class WebStreamingServer:
    """Serves the web client HTML and streams frames via WebSockets."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self.clients: Set[ServerConnection] = set()
        self._input_callback: Optional[Callable[[dict], None]] = None
        self._running = False
        self._html_content = b""

        if os.path.exists(HTML_PATH):
            with open(HTML_PATH, "rb") as f:
                self._html_content = f.read()

    def set_input_callback(self, cb: Callable[[dict], None]) -> None:
        self._input_callback = cb

    async def _handle_http_or_ws(self, connection: ServerConnection) -> None:
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

        # Header: 8 bytes timestamp (uint64 LE) + JPEG data
        header = struct.pack("<Q", timestamp_ms)
        payload = header + jpeg_bytes

        # Send to all connected clients concurrently
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(payload)
            except Exception:
                disconnected.add(client)

        for client in disconnected:
            self.clients.discard(client)

    async def _handle_http_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Simple HTTP server handler for serving index.html."""
        try:
            req_line = await reader.readline()
            if not req_line:
                writer.close()
                return

            # Read remaining headers
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break

            # Serve index.html
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                b"Content-Length: " + str(len(self._html_content)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + self._html_content
            )
            writer.write(response)
            await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self) -> None:
        """Start HTTP server on self.port and WebSocket server on self.port (shared or distinct)."""
        self._running = True

        # HTTP Server on self.port
        http_server = await asyncio.start_server(self._handle_http_request, self.host, self.port)
        
        # WebSocket Server on self.port + 1 (e.g., 8081)
        ws_port = self.port + 1
        ws_server = await serve(self._handle_http_or_ws, self.host, ws_port)

        # Update index.html to point to ws_port dynamically
        log.info("Web Server listening on http://%s:%d (WebSocket on :%d)", self.host, self.port, ws_port)
        print(f"\n[🌐 Web Client Ready] Open on your iPad Safari: http://<laptop-ip>:{self.port}")

        await asyncio.gather(
            http_server.serve_forever(),
            ws_server.serve_forever(),
        )
