"""DuoScreen configuration."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields


@dataclass
class DuoScreenConfig:
    """Runtime configuration for the DuoScreen server."""

    capture_monitor: int = 0
    width: int = 1024
    height: int = 768
    fps: int = 30
    jpeg_quality: int = 70
    server_port: int = 59000
    host: str = "127.0.0.1"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str = "config.json") -> "DuoScreenConfig":
        """Load config from *path*, falling back to defaults for missing keys.

        If the file does not exist the pure-default config is returned.
        """
        cfg = cls()
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            valid_names = {f.name for f in fields(cls)}
            for key, value in data.items():
                if key in valid_names:
                    setattr(cfg, key, value)
        return cfg

    def save(self, path: str = "config.json") -> None:
        """Persist the current config to *path*."""
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
