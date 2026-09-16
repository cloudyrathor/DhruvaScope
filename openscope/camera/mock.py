from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from ..core.errors import DeviceError
from .base import Camera


class MockCamera(Camera):
    """Camera implementation for tests and development without hardware."""

    def __init__(self):
        self._opened = False

    def open(self) -> None:
        self._opened = True

    def read(self) -> bytes:
        if not self._opened:
            raise DeviceError("camera is not open")
        import cv2
        import numpy as np
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        frame[:, :, 1] = 90
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            raise DeviceError("mock JPEG encoding failed")
        return encoded.tobytes()

    def capture(self, path: Path, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.read())
        record = {"captured_at": datetime.now(timezone.utc).isoformat(), "path": str(path), **(metadata or {})}
        path.with_suffix(path.suffix + ".json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return record

    def close(self) -> None:
        self._opened = False

    @property
    def status(self) -> dict[str, Any]:
        return {"type": "mock", "open": self._opened}
