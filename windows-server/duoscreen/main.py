"""DuoScreen entry-point — ``python -m duoscreen.main``."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

from .capture import ScreenCapture
from .config import DuoScreenConfig
from .encoder import FrameEncoder
from .input_injector import InputInjector
from .server import DuoScreenServer
from .usb_tunnel import USBTunnel

log = logging.getLogger("duoscreen")

BANNER = r"""
╔══════════════════════════════════════════════════╗
║           DuoScreen — Windows Server             ║
║  Stream your display to an iPad as a 2nd monitor ║
╚══════════════════════════════════════════════════╝
"""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DuoScreen Windows server — streams a monitor to an iPad.",
    )
    parser.add_argument(
        "--monitor",
        type=int,
        default=None,
        help="Monitor index to capture (0-based, default from config or 0)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=None,
        help="Target frames per second (default from config or 30)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=None,
        help="JPEG quality 1-100 (default from config or 70)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="TCP listen port (default from config or 59000)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to config.json (default: config.json)",
    )
    return parser.parse_args()


def _apply_overrides(cfg: DuoScreenConfig, args: argparse.Namespace) -> None:
    if args.monitor is not None:
        cfg.capture_monitor = args.monitor
    if args.fps is not None:
        cfg.fps = args.fps
    if args.quality is not None:
        cfg.jpeg_quality = args.quality
    if args.port is not None:
        cfg.server_port = args.port


async def _run(cfg: DuoScreenConfig) -> None:
    # --- Components ---
    capture = ScreenCapture()
    encoder = FrameEncoder()
    injector = InputInjector()
    server = DuoScreenServer()
    tunnel = USBTunnel()

    # --- USB tunnel (best-effort) ---
    device = tunnel.find_device()
    if device is not None:
        tunnel.create_tunnel(device, cfg.server_port, cfg.server_port)
    else:
        print(
            f"[i] No USB tunnel. The iPad app can still connect over Wi-Fi\n"
            f"    to this machine's IP on port {cfg.server_port}.\n"
        )

    # --- Screen capture ---
    capture.start(cfg.capture_monitor)

    # --- Input handling ---
    # Determine monitor bounds for the input injector.
    import ctypes  # noqa: WPS433

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    # For simplicity, use the primary monitor bounds
    mon_w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
    mon_h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
    monitor_bounds = (0, 0, mon_w, mon_h)

    def on_input(event: dict) -> None:
        injector.inject_mouse_event(
            event["x"],
            event["y"],
            event["action"],
            monitor_bounds,
        )

    server.set_input_callback(on_input)

    # --- Print instructions ---
    print(f"  Monitor : {cfg.capture_monitor}")
    print(f"  FPS     : {cfg.fps}")
    print(f"  Quality : {cfg.jpeg_quality}")
    print(f"  Port    : {cfg.server_port}")
    print(f"  Host    : {cfg.host}")
    print()
    print(f"  Waiting for iPad to connect on {cfg.host}:{cfg.server_port} …")
    print()

    # --- Run server + stream loop concurrently ---
    stream_task = asyncio.create_task(server.stream_loop(capture, encoder, cfg))
    server_task = asyncio.create_task(server.start(cfg.host, cfg.server_port, capture, encoder, cfg))

    try:
        await asyncio.gather(server_task, stream_task)
    finally:
        await server.stop()
        capture.stop()
        tunnel.stop()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    args = _parse_args()
    cfg = DuoScreenConfig.load(args.config)
    _apply_overrides(cfg, args)

    print(BANNER)

    loop = asyncio.new_event_loop()

    # Graceful Ctrl+C on Windows
    def _shutdown() -> None:
        for task in asyncio.all_tasks(loop):
            task.cancel()

    try:
        signal.signal(signal.SIGINT, lambda *_: _shutdown())
    except (ValueError, OSError):
        pass

    try:
        loop.run_until_complete(_run(cfg))
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[DuoScreen] Shutting down…")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
