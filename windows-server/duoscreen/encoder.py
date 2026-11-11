"""MJPEG frame encoder."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

# Prefer OpenCV for speed; fall back to Pillow.
try:
    import cv2  # type: ignore[import-untyped]
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

if not _HAS_CV2:
    from PIL import Image  # type: ignore[import-untyped]
    import io


class FrameEncoder:
    """Encodes raw RGB frames to JPEG bytes."""

    def encode_mjpeg(self, frame: np.ndarray, quality: int = 70) -> Optional[bytes]:
        """Encode an RGB *frame* to JPEG at the given *quality* (1-100).

        Returns the compressed JPEG bytes, or *None* on failure.
        """
        if _HAS_CV2:
            # cv2 expects BGR
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            ok, buf = cv2.imencode(
                ".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality]
            )
            if ok:
                return buf.tobytes()
            log.warning("cv2.imencode failed")
            return None

        # Pillow fallback
        try:
            img = Image.fromarray(frame, mode="RGB")
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality)
            return buffer.getvalue()
        except Exception as exc:  # noqa: BLE001
            log.warning("Pillow JPEG encode failed: %s", exc)
            return None
