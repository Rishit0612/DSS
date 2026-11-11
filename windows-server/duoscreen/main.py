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
from .web_server import WebStreamingServer

log = logging.getLogger("duoscreen")

BANNER = r"""
╔══════════════════════════════════════════════════╗
║         DSS — Dual Screening Studio              ║
║  Stream your display to an iPad as a 2nd monitor ║
╚══════════════════════════════════════════════════╝
"""

def _get_local_ip() -> str:
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


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
    web_server = WebStreamingServer(host="0.0.0.0", port=5000)

    # --- USB tunnel (best-effort) ---
    device = tunnel.find_device()
    if device is not None:
        tunnel.create_tunnel(device, cfg.server_port, cfg.server_port)

    # --- Screen capture ---
    capture.start(cfg.capture_monitor)

    # --- Input handling ---
    import ctypes  # noqa: WPS433

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
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
    web_server.set_input_callback(on_input)

    local_ip = _get_local_ip()

    # --- Print instructions ---
    print(f"  Capture Monitor : {cfg.capture_monitor}")
    print(f"  Target FPS      : {cfg.fps}")
    print(f"  Quality         : {cfg.jpeg_quality}%")
    print(f"  TCP Native Port : {cfg.server_port}")
    print("━" * 52)
    print("  📱 NO MAC NEEDED! OPEN THIS ON YOUR IPAD SAFARI:")
    print(f"     👉 http://{local_ip}:5000")
    print("  (Tip: Tap 'Share' -> 'Add to Home Screen' for Fullscreen)")
    print("━" * 52)
    print(f"  Native TCP Socket listening on {cfg.host}:{cfg.server_port}\n")

    # --- Run servers + stream loop concurrently ---
    stream_task = asyncio.create_task(server.stream_loop(capture, encoder, cfg, web_server=web_server))
    server_task = asyncio.create_task(server.start(cfg.host, cfg.server_port, capture, encoder, cfg))
    web_task = asyncio.create_task(web_server.start())

    try:
        await asyncio.gather(server_task, stream_task, web_task, return_exceptions=True)
    finally:
        await server.stop()
        await web_server.stop()
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
