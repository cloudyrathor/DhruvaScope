from dataclasses import dataclass

from ..core.errors import ConfigurationError
from ..core.telescope import MountAlignment


def _shortest_ra_delta(target_ra_deg: float, current_ra_deg: float) -> float:
    """Return the shortest signed RA move in the range [-180, 180)."""
    return (target_ra_deg - current_ra_deg + 180.0) % 360.0 - 180.0


@dataclass(frozen=True)
class GoToPlan:
    """A coordinate plan; creating one never commands a motor."""

    name: str
    current_ra_deg: float
    current_dec_deg: float
    target_ra_deg: float
    target_dec_deg: float
    ra_delta_deg: float
    dec_delta_deg: float

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "current_ra_deg": self.current_ra_deg,
            "current_dec_deg": self.current_dec_deg,
            "target_ra_deg": self.target_ra_deg,
            "target_dec_deg": self.target_dec_deg,
            "ra_delta_deg": self.ra_delta_deg,
            "dec_delta_deg": self.dec_delta_deg,
            "execution_supported": False,
        }


class GoToPlanner:
    """Calculate an open-loop GoTo plan from the manually aligned position."""

    def plan(
        self,
        alignment: MountAlignment,
        target_ra_deg: float,
        target_dec_deg: float,
        name: str = "target",
    ) -> GoToPlan:
        if not alignment.aligned or alignment.ra_deg is None or alignment.dec_deg is None:
            raise ConfigurationError("mount alignment is required before planning a GoTo")
        if not 0.0 <= target_ra_deg < 360.0:
            raise ConfigurationError("GoTo target RA must be between 0 and 360 degrees")
        if not -90.0 <= target_dec_deg <= 90.0:
            raise ConfigurationError("GoTo target DEC must be between -90 and 90 degrees")
        if not name.strip():
            raise ConfigurationError("GoTo target name is required")
        return GoToPlan(
            name=name,
            current_ra_deg=alignment.ra_deg,
            current_dec_deg=alignment.dec_deg,
            target_ra_deg=target_ra_deg,
            target_dec_deg=target_dec_deg,
            ra_delta_deg=_shortest_ra_delta(target_ra_deg, alignment.ra_deg),
            dec_delta_deg=target_dec_deg - alignment.dec_deg,
        )
