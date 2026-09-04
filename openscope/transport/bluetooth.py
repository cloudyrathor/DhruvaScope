from ..core.errors import DeviceError
from .base import LineTransport


class BluetoothTransport(LineTransport):
    """Bluetooth Classic serial transport using a host serial device path."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 3.0):
        self.port, self.baudrate, self.timeout = port, baudrate, timeout
        self.serial = None

    def connect(self) -> None:
        try:
            import serial

            self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        except (ImportError, OSError) as exc:
            raise DeviceError(f"Bluetooth serial connection failed: {exc}") from exc

    def request(self, payload: bytes) -> bytes:
        if self.serial is None:
            self.connect()
        try:
            self.serial.write(payload)
            return self.serial.readline()
        except OSError as exc:
            raise DeviceError(f"Bluetooth request failed: {exc}") from exc

    def close(self) -> None:
        if self.serial:
            self.serial.close()
            self.serial = None
