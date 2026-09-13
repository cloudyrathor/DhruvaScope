from dataclasses import dataclass

from ..core.errors import ConfigurationError
from ..core.motor import MotorDirection
from ..core.telescope import TelescopeState
from ..devices.base import TelescopeDevice


@dataclass
class MotionController:
    """Safety gate for open-loop and feedback-capable motion devices.

    Position feedback is deliberately not required. Software speed and enable
    checks work with the minimum hardware; future feedback can improve state
    estimation without changing this command boundary.
    """

    device: TelescopeDevice
    state: TelescopeState

    def _motor_and_speed(self, motor_id: str, speed: float) -> None:
        motor = self.state.motor(motor_id)
        if not motor.enabled:
            raise ConfigurationError(f"motor {motor_id} is disabled")
        if speed <= 0 or speed > motor.max_speed:
            raise ConfigurationError(f"speed must be between 0 and {motor.max_speed} deg/s")

    def move(self, motor_id: str, direction: MotorDirection, speed: float) -> None:
        self._motor_and_speed(motor_id, speed)
        self.device.move(motor_id, direction, speed)

    def set_tracking_rate(self, motor_id: str, direction: MotorDirection, rate: float) -> None:
        """Start or update a continuous open-loop tracking rate."""
        self._motor_and_speed(motor_id, rate)
        status = self.device.status().get("motors", {}).get(motor_id, {})
        if status.get("state") == "MOVING":
            self.device.set_rate(motor_id, rate)
        else:
            self.device.move(motor_id, direction, rate)

    def stop(self, motor_id: str) -> None:
        self.device.stop(motor_id)

    def emergency_stop(self) -> None:
        self.device.emergency_stop()

    def set_rate_pair(self, ra_rate: float, dec_rate: float) -> None:
        """Apply signed RA/DEC rates; zero stops that axis."""
        for motor_id, rate in (("RA", ra_rate), ("DEC", dec_rate)):
            if rate == 0:
                self.stop(motor_id)
                continue
            direction = MotorDirection.POS if rate > 0 else MotorDirection.NEG
            self.set_tracking_rate(motor_id, direction, abs(rate))
