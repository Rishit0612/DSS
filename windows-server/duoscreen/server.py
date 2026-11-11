"""Async TCP server for DuoScreen — streams MJPEG and handles input."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

from .capture import ScreenCapture
from .config import DuoScreenConfig
from .encoder import FrameEncoder
from .protocol import (
    PACKET_INPUT,
    _INPUT_SIZE,
    build_config_packet,
    build_video_packet,
    parse_input_packet,
)

log = logging.getLogger(__name__)


class DuoScreenServer:
    """Single-client async TCP server that streams frames and receives input."""

    def __init__(self) -> None:
        self._server: Optional[asyncio.AbstractServer] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = asyncio.Event()
        self._running = False
        self._input_callback: Optional[Callable[[dict], None]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_input_callback(self, cb: Callable[[dict], None]) -> None:
        """Register a callback invoked with each parsed input packet dict."""
        self._input_callback = cb

    async def start(
        self,
        host: str,
        port: int,
        capture: ScreenCapture,
        encoder: FrameEncoder,
        config: DuoScreenConfig,
    ) -> None:
        """Start the server and begin streaming once a client connects."""
        self._running = True
        self._server = await asyncio.start_server(
            self._handle_client, host, port
        )
        addrs = ", ".join(str(s.getsockname()) for s in self._server.sockets)
        print(f"[DuoScreen] Listening on {addrs}")
        log.info("Server listening on %s", addrs)

        async with self._server:
            # Keep accepting new connections (one at a time)
            await self._server.serve_forever()

    async def stop(self) -> None:
        """Gracefully shut down the server."""
        self._running = False
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        print("[DuoScreen] Server stopped")

    # ------------------------------------------------------------------
    # Connection handler
    # ------------------------------------------------------------------

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername")
        print(f"[DuoScreen] Client connected: {peer}")
        log.info("Client connected: %s", peer)

        # Only one client at a time
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass

        self._writer = writer
        self._connected.set()

        # Read input packets in the background
        input_task = asyncio.create_task(self._read_input(reader))

        try:
            # Wait until the reader task exits (disconnect)
            await input_task
        finally:
            self._connected.clear()
            self._writer = None
            print(f"[DuoScreen] Client disconnected: {peer}")
            log.info("Client disconnected: %s", peer)

    async def _read_input(self, reader: asyncio.StreamReader) -> None:
        """Continuously read input packets from the client."""
        try:
            while self._running:
                data = await reader.readexactly(_INPUT_SIZE)
                try:
                    event = parse_input_packet(data)
                    if self._input_callback is not None:
                        self._input_callback(event)
                except ValueError as exc:
                    log.warning("Bad input packet: %s", exc)
        except (asyncio.IncompleteReadError, ConnectionError):
            # Client disconnected
            pass

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def stream_loop(
        self,
        capture: ScreenCapture,
        encoder: FrameEncoder,
        config: DuoScreenConfig,
        web_server: Optional[object] = None,
    ) -> None:
        """Capture → encode → send loop, runs at *config.fps* for both TCP and Web clients."""
        interval = 1.0 / config.fps
        sent_tcp_config = False

        while self._running:
            has_tcp = self._connected.is_set() and self._writer is not None
            has_web = web_server is not None and len(getattr(web_server, "clients", [])) > 0

            if not has_tcp and not has_web:
                sent_tcp_config = False
                await asyncio.sleep(0.05)
                continue

            # Send config packet to native TCP client once upon connecting
            if has_tcp and not sent_tcp_config:
                try:
                    cfg_pkt = build_config_packet(config.width, config.height, config.fps)
                    self._writer.write(cfg_pkt)  # type: ignore[union-attr]
                    await self._writer.drain()  # type: ignore[union-attr]
                    sent_tcp_config = True
                except Exception:
                    pass

            t0 = time.monotonic()
            frame = capture.get_frame()
            if frame is not None:
                jpeg = encoder.encode_mjpeg(frame, quality=config.jpeg_quality)
                if jpeg is not None:
                    ts_ms = int(time.time() * 1000)

                    # 1. Send to native TCP client if connected
                    if has_tcp:
                        packet = build_video_packet(jpeg, ts_ms)
                        try:
                            self._writer.write(packet)  # type: ignore[union-attr]
                            await self._writer.drain()  # type: ignore[union-attr]
                        except (ConnectionError, OSError):
                            log.info("TCP write failed — client likely disconnected")
                            self._connected.clear()
                            sent_tcp_config = False

                    # 2. Broadcast to iPad Safari Web clients
                    if has_web and web_server is not None:
                        try:
                            await web_server.broadcast_frame(jpeg, ts_ms)  # type: ignore[union-attr]
                        except Exception as e:
                            log.debug("Web broadcast error: %s", e)

            elapsed = time.monotonic() - t0
            sleep_for = interval - elapsed
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
