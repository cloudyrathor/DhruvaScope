import socket

from ..core.errors import DeviceError
from .base import LineTransport


class WifiTransport(LineTransport):
    """TCP line transport for the DhruvaScope ESP32 firmware."""

    def __init__(self, host: str, port: int = 9999, timeout: float = 3.0):
        self.host, self.port, self.timeout = host, port, timeout
        self.socket: socket.socket | None = None

    def connect(self) -> None:
        try:
            self.socket = socket.create_connection((self.host, self.port), self.timeout)
            self.socket.settimeout(self.timeout)
        except OSError as exc:
            raise DeviceError(f"Wi-Fi connection failed: {exc}") from exc

    def request(self, payload: bytes) -> bytes:
        if self.socket is None:
            self.connect()
        try:
            self.socket.sendall(payload)
            return self.socket.makefile("rb").readline()
        except OSError as exc:
            raise DeviceError(f"Wi-Fi request failed: {exc}") from exc

    def close(self) -> None:
        if self.socket:
            self.socket.close()
            self.socket = None
