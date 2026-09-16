from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Camera(ABC):
    """Interface shared by physical and hardware-free cameras."""

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def read(self) -> bytes: ...

    @abstractmethod
    def capture(self, path: Path, metadata: dict[str, Any] | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def status(self) -> dict[str, Any]: ...
