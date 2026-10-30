from abc import ABC, abstractmethod
from typing import Any

from ..core.motor import MotorDirection


class TelescopeDevice(ABC):
    """Interface implemented by mock and physical telescope devices."""

    @abstractmethod
    def move(self, motor_id: str, direction: MotorDirection, speed: float | None = None) -> None: ...

    @abstractmethod
    def stop(self, motor_id: str) -> None: ...

    @abstractmethod
    def emergency_stop(self) -> None: ...

    @abstractmethod
    def set_speed(self, motor_id: str, speed: float) -> None: ...

    @abstractmethod
    def set_rate(self, motor_id: str, rate: float) -> None: ...

    @abstractmethod
    def enable(self, motor_id: str) -> None: ...

    @abstractmethod
    def disable(self, motor_id: str) -> None: ...

    def step(self, motor_id: str, direction: MotorDirection, steps: int, speed: float) -> None:
        raise NotImplementedError("this device does not support step moves")

    @abstractmethod
    def status(self) -> dict[str, Any]: ...
