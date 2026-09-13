from dataclasses import dataclass, field
from datetime import datetime, timezone

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
class MountAlignment:
    """Open-loop mount coordinate reference; sensors are not required."""

    aligned: bool = False
    ra_deg: float | None = None
    dec_deg: float | None = None
    source: str | None = None
    updated_at_utc: str | None = None

    def set_position(self, ra_deg: float, dec_deg: float, source: str = "manual") -> None:
        if not 0.0 <= ra_deg < 360.0:
            raise ConfigurationError("alignment RA must be between 0 and 360 degrees")
        if not -90.0 <= dec_deg <= 90.0:
            raise ConfigurationError("alignment DEC must be between -90 and 90 degrees")
        if not source.strip():
            raise ConfigurationError("alignment source is required")
        self.aligned = True
        self.ra_deg = ra_deg
        self.dec_deg = dec_deg
        self.source = source
        self.updated_at_utc = datetime.now(timezone.utc).isoformat()

    def as_dict(self) -> dict[str, object]:
        return {
            "aligned": self.aligned,
            "ra_deg": self.ra_deg,
            "dec_deg": self.dec_deg,
            "source": self.source,
            "updated_at_utc": self.updated_at_utc,
            "feedback_required": False,
        }


@dataclass
class TelescopeState:
    """Complete host-side state for the configured equatorial mount."""

    mount_type: str = "equatorial"
    motors: dict[str, MotorChannel] = field(default_factory=dict)
    alignment: MountAlignment = field(default_factory=MountAlignment)

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
