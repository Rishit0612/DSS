"""Convert normalised touch coordinates to Win32 SendInput mouse events."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Win32 constants & structures for SendInput
# ---------------------------------------------------------------------------

INPUT_MOUSE = 0

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000

# Normalised coordinate range for MOUSEEVENTF_ABSOLUTE
_ABS_MAX = 65535


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT(ctypes.Structure):
    class _UNION(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT)]

    _anonymous_ = ("u",)
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("u", _UNION),
    ]


_SendInput = ctypes.windll.user32.SendInput  # type: ignore[attr-defined]
_SendInput.argtypes = [
    ctypes.c_uint,
    ctypes.POINTER(_INPUT),
    ctypes.c_int,
]
_SendInput.restype = ctypes.c_uint

# Touch action constants (must match protocol.py)
ACTION_DOWN = 0
ACTION_MOVE = 1
ACTION_UP = 2


class InputInjector:
    """Translate normalised touch events into Win32 mouse events."""

    def inject_mouse_event(
        self,
        x_norm: float,
        y_norm: float,
        action: int,
        monitor_bounds: tuple[int, int, int, int],
    ) -> None:
        """Inject a mouse event.

        Parameters
        ----------
        x_norm, y_norm:
            Touch position normalised to [0, 1].
        action:
            0 = down, 1 = move, 2 = up.
        monitor_bounds:
            ``(left, top, right, bottom)`` in *virtual-screen* pixel
            coordinates for the target monitor.
        """
        left, top, right, bottom = monitor_bounds
        mon_w = right - left
        mon_h = bottom - top

        # Map normalised coords → absolute virtual-screen position
        screen_x = left + int(x_norm * mon_w)
        screen_y = top + int(y_norm * mon_h)

        # Convert to 0–65535 range relative to the full virtual desktop
        virt_w = ctypes.windll.user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        virt_h = ctypes.windll.user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        virt_x0 = ctypes.windll.user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        virt_y0 = ctypes.windll.user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN

        abs_x = int((screen_x - virt_x0) / virt_w * _ABS_MAX)
        abs_y = int((screen_y - virt_y0) / virt_h * _ABS_MAX)

        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE

        if action == ACTION_DOWN:
            flags |= MOUSEEVENTF_LEFTDOWN
        elif action == ACTION_UP:
            flags |= MOUSEEVENTF_LEFTUP
        # ACTION_MOVE just moves (flags already has MOVE|ABSOLUTE)

        inp = _INPUT()
        inp.type = INPUT_MOUSE
        inp.mi.dx = abs_x
        inp.mi.dy = abs_y
        inp.mi.dwFlags = flags
        inp.mi.time = 0
        inp.mi.mouseData = 0
        inp.mi.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))

        _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))
