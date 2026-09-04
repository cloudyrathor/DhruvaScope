from dataclasses import dataclass
from enum import StrEnum

from .errors import ConfigurationError


class MotorState(StrEnum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    DISABLED = "DISABLED"
    FAULT = "FAULT"


class MotorDirection(StrEnum):
    POS = "POS"
    NEG = "NEG"


MOTOR_IDS = ("RA", "DEC", "FOCUS", "AUX1", "AUX2")


@dataclass
class MotorChannel:
    """Hardware-independent state and limits for one logical motor channel."""

    id: str
    name: str
    enabled: bool = True
    direction: int = 1
    current_position: float = 0.0
    target_position: float = 0.0
    speed: float = 0.0
    max_speed: float = 5.0
    acceleration: float = 1.0
    software_min: float | None = None
    software_max: float | None = None
    state: MotorState = MotorState.IDLE

    def __post_init__(self) -> None:
        if self.id not in MOTOR_IDS:
            raise ConfigurationError(f"Unsupported motor channel: {self.id}")
        if self.direction not in (-1, 1):
            raise ConfigurationError("direction must be -1 or 1")
        if self.max_speed <= 0 or self.acceleration <= 0:
            raise ConfigurationError("max_speed and acceleration must be positive")
        if self.software_min is not None and self.software_max is not None:
            if self.software_min > self.software_max:
                raise ConfigurationError("software_min cannot exceed software_max")
        if not self.enabled:
            self.state = MotorState.DISABLED

    def set_speed(self, speed: float) -> None:
        if speed < 0 or speed > self.max_speed:
            raise ConfigurationError(
                f"speed must be between 0 and {self.max_speed} deg/s"
            )
        self.speed = speed

    def move(self, direction: MotorDirection, speed: float | None = None) -> None:
        if not self.enabled:
            raise ConfigurationError(f"motor {self.id} is disabled")
        if speed is not None:
            self.set_speed(speed)
        if self.speed <= 0:
            raise ConfigurationError("movement speed must be greater than zero")
        self.state = MotorState.MOVING

    def stop(self) -> None:
        self.speed = 0.0
        self.state = MotorState.IDLE if self.enabled else MotorState.DISABLED
