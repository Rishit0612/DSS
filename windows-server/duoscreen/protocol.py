"""Wire protocol for DuoScreen.

All multi-byte integers are LITTLE-ENDIAN.

Video packet layout:
    DUOS (4 B) | type 0x01 (1 B) | payload_size uint32 (4 B)
    | timestamp_ms uint64 (8 B) | JPEG payload (payload_size B)

Input packet layout (14 bytes total):
    DUOS (4 B) | type 0x02 (1 B) | x float32 (4 B) | y float32 (4 B)
    | action uint8 (1 B)

Config packet layout (10 bytes total):
    DUOS (4 B) | type 0x03 (1 B) | width uint16 (2 B) | height uint16 (2 B)
    | fps uint8 (1 B)
"""

from __future__ import annotations

import struct

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAGIC: bytes = b"DUOS"

PACKET_VIDEO: int = 0x01
PACKET_INPUT: int = 0x02
PACKET_CONFIG: int = 0x03

# Struct formats (all little-endian)
_VIDEO_HEADER_FMT = "<4sB I Q"  # magic, type, payload_size, timestamp_ms
_VIDEO_HEADER_SIZE = struct.calcsize(_VIDEO_HEADER_FMT)  # 4+1+4+8 = 17

_INPUT_FMT = "<4sB f f B"  # magic, type, x, y, action
_INPUT_SIZE = struct.calcsize(_INPUT_FMT)  # 4+1+4+4+1 = 14

_CONFIG_FMT = "<4sB H H B"  # magic, type, width, height, fps
_CONFIG_SIZE = struct.calcsize(_CONFIG_FMT)  # 4+1+2+2+1 = 10

# Touch action constants
ACTION_DOWN = 0
ACTION_MOVE = 1
ACTION_UP = 2


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def build_video_packet(frame_data: bytes, timestamp_ms: int) -> bytes:
    """Build a video packet from raw JPEG *frame_data* and a timestamp."""
    header = struct.pack(
        _VIDEO_HEADER_FMT,
        MAGIC,
        PACKET_VIDEO,
        len(frame_data),
        timestamp_ms,
    )
    return header + frame_data


def build_config_packet(width: int, height: int, fps: int) -> bytes:
    """Build a config packet advertising resolution and frame-rate."""
    return struct.pack(_CONFIG_FMT, MAGIC, PACKET_CONFIG, width, height, fps)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_input_packet(data: bytes) -> dict:
    """Parse a 14-byte input packet into a dict.

    Returns ``{"x": float, "y": float, "action": int}``
    where *action* is 0=down, 1=move, 2=up.

    Raises ``ValueError`` on bad magic or packet type.
    """
    if len(data) < _INPUT_SIZE:
        raise ValueError(
            f"Input packet too short: expected {_INPUT_SIZE} bytes, got {len(data)}"
        )

    magic, ptype, x, y, action = struct.unpack_from(_INPUT_FMT, data)

    if magic != MAGIC:
        raise ValueError(f"Bad magic: {magic!r}")
    if ptype != PACKET_INPUT:
        raise ValueError(f"Expected INPUT type 0x{PACKET_INPUT:02X}, got 0x{ptype:02X}")

    return {"x": x, "y": y, "action": action}


def parse_packet_header(data: bytes) -> tuple[int, bytes]:
    """Read the 5-byte common header (magic + type) and return (packet_type, remaining)."""
    if len(data) < 5:
        raise ValueError("Data too short for header")
    magic = data[:4]
    if magic != MAGIC:
        raise ValueError(f"Bad magic: {magic!r}")
    return data[4], data[5:]
