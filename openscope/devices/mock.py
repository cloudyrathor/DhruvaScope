from typing import Any

from ..core.motor import MotorDirection, MotorState
from ..core.telescope import TelescopeState
from .base import TelescopeDevice


class MockDevice(TelescopeDevice):
    """Hardware-free device that validates and records motor commands."""

    def __init__(self, state: TelescopeState):
        self.state = state
        self.command_log: list[tuple[str, str, str | float | None]] = []

    def move(self, motor_id: str, direction: MotorDirection, speed: float | None = None) -> None:
        motor = self.state.motor(motor_id)
        motor.move(direction, speed)
        self.command_log.append(("MOVE", motor_id, direction.value))

    def stop(self, motor_id: str) -> None:
        motor = self.state.motor(motor_id)
        motor.stop()
        self.command_log.append(("STOP", motor_id, None))

    def emergency_stop(self) -> None:
        for motor in self.state.motors.values():
            motor.stop()
        self.command_log.append(("STOP", "ALL", None))

    def set_speed(self, motor_id: str, speed: float) -> None:
        motor = self.state.motor(motor_id)
        motor.set_speed(speed)
        self.command_log.append(("SET_SPEED", motor_id, speed))

    def set_rate(self, motor_id: str, rate: float) -> None:
        motor = self.state.motor(motor_id)
        motor.set_speed(rate)
        self.command_log.append(("SET_RATE", motor_id, rate))

    def enable(self, motor_id: str) -> None:
        motor = self.state.motor(motor_id)
        motor.enabled = True
        motor.state = MotorState.IDLE
        self.command_log.append(("ENABLE", motor_id, None))

    def disable(self, motor_id: str) -> None:
        motor = self.state.motor(motor_id)
        motor.stop()
        motor.enabled = False
        motor.state = MotorState.DISABLED
        self.command_log.append(("DISABLE", motor_id, None))

    def status(self) -> dict[str, Any]:
        return {
            "mount_type": self.state.mount_type,
            "motors": {
                motor_id: {
                    "enabled": motor.enabled,
                    "state": motor.state.value,
                    "current_position": motor.current_position,
                    "target_position": motor.target_position,
                    "speed": motor.speed,
                }
                for motor_id, motor in self.state.motors.items()
            },
        }
