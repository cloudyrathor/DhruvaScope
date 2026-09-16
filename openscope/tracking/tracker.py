from dataclasses import dataclass

from ..core.errors import ConfigurationError
from ..core.motor import MotorDirection
from ..devices.base import TelescopeDevice
from ..motion.controller import MotionController


SIDEREAL_RATE_DEG_PER_SECOND = 15.041067 / 3600.0


@dataclass
class SiderealTracker:
    """Host-side controller for simple equatorial sidereal tracking.

    The device remains responsible for generating the continuous step pulses.
    This service only starts and stops the RA channel through the common device
    interface, so mock and physical devices follow the same control path.
    """

    device: TelescopeDevice
    ra_direction: MotorDirection = MotorDirection.POS
    rate_deg_per_second: float = SIDEREAL_RATE_DEG_PER_SECOND
    motion: MotionController | None = None
    _running: bool = False

    def __post_init__(self) -> None:
        if self.rate_deg_per_second <= 0:
            raise ConfigurationError("sidereal rate must be greater than zero")
        if self.motion is None:
            self.motion = MotionController(self.device, self.device.state)

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start sidereal tracking on RA through the device abstraction."""
        assert self.motion is not None
        if not self.device.state.motor("RA").enabled:
            raise ConfigurationError("RA motor is disabled")
        self.motion.set_tracking_rate("RA", self.ra_direction, self.rate_deg_per_second)
        self._running = True

    def stop(self) -> None:
        """Stop sidereal tracking without affecting DEC or auxiliary motors."""
        assert self.motion is not None
        self.motion.stop("RA")
        self._running = False

    def status(self) -> dict[str, object]:
        return {
            "mode": "SIDEREAL" if self._running else "IDLE",
            "running": self._running,
            "motor": "RA",
            "direction": self.ra_direction.value,
            "rate_deg_per_second": self.rate_deg_per_second,
        }
