"""Screen capture with dxcam (GPU-accelerated) and mss fallback."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try to import dxcam; fall back to mss
# ---------------------------------------------------------------------------

try:
    import dxcam  # type: ignore[import-untyped]
    _HAS_DXCAM = True
except ImportError:
    _HAS_DXCAM = False
    log.info("dxcam unavailable — falling back to mss for screen capture")


class ScreenCapture:
    """Captures frames from a specific monitor.

    Uses *dxcam* when available for GPU-accelerated DirectX capture.  Falls
    back to *mss* (pure-Python) otherwise.
    """

    def __init__(self) -> None:
        self._camera: object | None = None
        self._sct: object | None = None
        self._monitor_index: int = 0
        self._using_dxcam: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, monitor_index: int = 0) -> None:
        """Initialise capture on *monitor_index* (0-based)."""
        self._monitor_index = monitor_index

        if _HAS_DXCAM:
            try:
                self._camera = dxcam.create(output_idx=monitor_index, output_color="RGB")
                self._camera.start(target_fps=60, video_mode=True)  # type: ignore[union-attr]
                self._using_dxcam = True
                log.info("dxcam capture started on monitor %d", monitor_index)
                return
            except Exception as exc:  # noqa: BLE001
                log.warning("dxcam failed (%s) — falling back to mss", exc)

        # Fallback: mss
        import mss as _mss  # noqa: WPS433

        self._sct = _mss.mss()
        self._using_dxcam = False
        log.info("mss capture started on monitor %d", monitor_index)

    def get_frame(self) -> Optional[np.ndarray]:
        """Return the latest frame as an RGB ``np.ndarray``, or *None*."""
        if self._using_dxcam and self._camera is not None:
            frame = self._camera.get_latest_frame()  # type: ignore[union-attr]
            return frame  # already RGB ndarray or None

        if self._sct is not None:
            import mss.tools  # noqa: WPS433

            monitors = self._sct.monitors  # type: ignore[union-attr]
            # mss monitors[0] is the "all-in-one"; individual displays start at 1
            idx = self._monitor_index + 1
            if idx >= len(monitors):
                idx = 1  # safe default
            shot = self._sct.grab(monitors[idx])  # type: ignore[union-attr]
            # mss returns BGRA; convert to RGB ndarray
            img = np.array(shot)
            return img[:, :, :3][:, :, ::-1].copy()  # BGRA → BGR → RGB

        return None

    def stop(self) -> None:
        """Release capture resources."""
        if self._using_dxcam and self._camera is not None:
            try:
                self._camera.stop()  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                pass
            self._camera = None

        if self._sct is not None:
            try:
                self._sct.close()  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                pass
            self._sct = None

        log.info("Screen capture stopped")
