from abc import ABC, abstractmethod


class LineTransport(ABC):
    """Byte transport carrying newline-delimited protocol messages."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def request(self, payload: bytes) -> bytes: ...

    @abstractmethod
    def close(self) -> None: ...
