from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from ..core.errors import DeviceError
from .base import Camera


class OpenCVCamera(Camera):
    """OpenCV ``VideoCapture`` adapter with JPEG output and metadata sidecars."""

    def __init__(self, source: int | str = 0):
        self.source = source
        self._capture = None

    def open(self) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise DeviceError("opencv-python is required for a physical camera") from exc
        self._capture = cv2.VideoCapture(self.source)
        if not self._capture.isOpened():
            self._capture.release()
            self._capture = None
            raise DeviceError(f"could not open camera source {self.source!r}")

    def read(self) -> bytes:
        if self._capture is None:
            raise DeviceError("camera is not open")
        import cv2
        ok, frame = self._capture.read()
        if not ok:
            raise DeviceError("camera frame read failed")
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            raise DeviceError("camera JPEG encoding failed")
        return encoded.tobytes()

    def capture(self, path: Path, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        frame = self.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(frame)
        record = {"captured_at": datetime.now(timezone.utc).isoformat(), "path": str(path), **(metadata or {})}
        path.with_suffix(path.suffix + ".json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return record

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    @property
    def status(self) -> dict[str, Any]:
        return {"type": "opencv", "source": self.source, "open": self._capture is not None}
