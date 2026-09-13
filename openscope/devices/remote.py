from typing import Any

from ..core.errors import DeviceError
from ..core.motor import MotorDirection
from ..core.telescope import TelescopeState
from ..protocol import decode_response, encode_command
from ..transport.base import LineTransport
from .base import TelescopeDevice


class Esp32Device(TelescopeDevice):
    """Device adapter for the DhruvaScope ESP32 JSON Lines firmware."""

    def __init__(self, transport: LineTransport, state: TelescopeState):
        self.transport, self.state = transport, state
        self._command_id = 0

    def _request(self, command: str, **fields) -> dict[str, Any]:
        self._command_id += 1
        response = decode_response(self.transport.request(encode_command(self._command_id, command, **fields)))
        if response["id"] != self._command_id or response["status"] != "OK":
            raise DeviceError(response.get("error", "device rejected command"))
        return response.get("data", {})

    def move(self, motor_id: str, direction: MotorDirection, speed: float | None = None) -> None:
        self._request("MOVE", motor=motor_id, direction=direction.value, speed=speed or self.state.motor(motor_id).speed)

    def stop(self, motor_id: str) -> None:
        self._request("STOP", motor=motor_id)

    def emergency_stop(self) -> None:
        self._request("STOP", motor="ALL")

    def set_speed(self, motor_id: str, speed: float) -> None:
        self._request("SET_SPEED", motor=motor_id, speed=speed)

    def set_rate(self, motor_id: str, rate: float) -> None:
        self._request("SET_RATE", motor=motor_id, rate=rate)

    def enable(self, motor_id: str) -> None:
        self._request("ENABLE", motor=motor_id)

    def disable(self, motor_id: str) -> None:
        self._request("DISABLE", motor=motor_id)

    def status(self) -> dict[str, Any]:
        return self._request("STATUS")

    def close(self) -> None:
        self.transport.close()
