"""USB tunnel to an iOS device via pymobiledevice3 / usbmuxd.

If pymobiledevice3 is not installed or no device is found, the class
prints instructions for using ``iproxy`` (from libimobiledevice) as a
manual fallback.
"""

from __future__ import annotations

import logging
import socket
import threading
from typing import Any, Optional

log = logging.getLogger(__name__)

try:
    from pymobiledevice3.usbmux import list_devices  # type: ignore[import-untyped]
    from pymobiledevice3.tcp_forwarder import TcpForwarder  # type: ignore[import-untyped]
    _HAS_PMD3 = True
except ImportError:
    _HAS_PMD3 = False
    log.info("pymobiledevice3 not available — USB auto-tunnel disabled")


class USBTunnel:
    """Discover an iOS device over USB and create a TCP tunnel."""

    def __init__(self) -> None:
        self._forwarder: Any | None = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    def find_device(self) -> Any | None:
        """Return the first connected iOS device, or *None*.

        Prints a helpful message when pymobiledevice3 is missing or no
        device is attached.
        """
        if not _HAS_PMD3:
            self._print_manual_instructions()
            return None

        try:
            devices = list_devices()
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to query usbmuxd: %s", exc)
            print(
                "\n[!] Could not communicate with usbmuxd / Apple Mobile Device Service.\n"
                "    Make sure iTunes (or Apple Devices) is installed.\n"
            )
            return None

        if not devices:
            print(
                "\n[!] No iOS device found over USB.\n"
                "    Connect your iPad via cable and trust this computer.\n"
            )
            return None

        device = devices[0]
        log.info("Found device: %s", device)
        return device

    # ------------------------------------------------------------------
    # Tunnel creation
    # ------------------------------------------------------------------

    def create_tunnel(
        self,
        device: Any,
        local_port: int,
        device_port: int,
    ) -> bool:
        """Forward *local_port* → *device_port* over USB.

        Returns ``True`` on success.
        """
        if not _HAS_PMD3 or device is None:
            self._print_manual_instructions(local_port, device_port)
            return False

        try:
            self._forwarder = TcpForwarder(
                device,
                local_port,
                device_port,
            )
            self._thread = threading.Thread(
                target=self._forwarder.start,
                daemon=True,
            )
            self._thread.start()
            log.info(
                "USB tunnel open: localhost:%d → device:%d",
                local_port,
                device_port,
            )
            print(f"[✓] USB tunnel active — localhost:{local_port} → iPad:{device_port}")
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to create USB tunnel: %s", exc)
            self._print_manual_instructions(local_port, device_port)
            return False

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Tear down the tunnel if running."""
        if self._forwarder is not None:
            try:
                self._forwarder.stop()
            except Exception:  # noqa: BLE001
                pass
            self._forwarder = None
        self._thread = None
        log.info("USB tunnel stopped")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _print_manual_instructions(
        local_port: int = 59000,
        device_port: int = 59000,
    ) -> None:
        print(
            "\n"
            "──────────────────────────────────────────────────\n"
            "  Manual USB tunnel (requires libimobiledevice):\n"
            f"    iproxy {local_port} {device_port}\n"
            "──────────────────────────────────────────────────\n"
            "  Install libimobiledevice:\n"
            "    • Windows: choco install libimobiledevice\n"
            "    • macOS:   brew install libimobiledevice\n"
            "──────────────────────────────────────────────────\n"
        )
