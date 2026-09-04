from dataclasses import dataclass, field

from .errors import ConfigurationError
from .motor import MOTOR_IDS, MotorChannel


DEFAULT_MOTOR_NAMES = {
    "RA": "Right Ascension",
    "DEC": "Declination",
    "FOCUS": "Focuser",
    "AUX1": "Auxiliary 1",
    "AUX2": "Auxiliary 2",
}


@dataclass
class TelescopeState:
    """Complete host-side state for the configured equatorial mount."""

    mount_type: str = "equatorial"
    motors: dict[str, MotorChannel] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mount_type != "equatorial":
            raise ConfigurationError("Only equatorial mounts are supported")
        unknown = set(self.motors) - set(MOTOR_IDS)
        if unknown:
            raise ConfigurationError(f"Unsupported motor channels: {sorted(unknown)}")

    @classmethod
    def with_default_channels(cls, enabled: dict[str, bool] | None = None) -> "TelescopeState":
        enabled = enabled or {}
        return cls(
            motors={
                motor_id: MotorChannel(
                    id=motor_id,
                    name=DEFAULT_MOTOR_NAMES[motor_id],
                    enabled=enabled.get(motor_id, False),
                )
                for motor_id in MOTOR_IDS
            }
        )

    def motor(self, motor_id: str) -> MotorChannel:
        try:
            return self.motors[motor_id]
        except KeyError as exc:
            raise ConfigurationError(f"Unknown motor channel: {motor_id}") from exc
