from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..core.errors import ConfigurationError
from .astronomy import ObserverLocation


@dataclass(frozen=True)
class MoonSolution:
    """Topocentric apparent Moon position for one observation time."""

    observation_time_utc: str
    apparent_ra_deg: float
    apparent_dec_deg: float
    altitude_deg: float
    azimuth_deg: float
    distance_km: float
    above_horizon: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": "Moon",
            "observation_time_utc": self.observation_time_utc,
            "apparent_ra_deg": self.apparent_ra_deg,
            "apparent_dec_deg": self.apparent_dec_deg,
            "altitude_deg": self.altitude_deg,
            "azimuth_deg": self.azimuth_deg,
            "distance_km": self.distance_km,
            "above_horizon": self.above_horizon,
        }


class MoonService:
    """Calculate the Moon position without involving motion or firmware."""

    def calculate(
        self,
        observer: ObserverLocation,
        observation_time: str | datetime,
        mount_type: str = "equatorial",
    ) -> MoonSolution:
        if mount_type != "equatorial":
            raise ConfigurationError("M7 currently supports equatorial mounts only")
        if not -90.0 <= observer.latitude_deg <= 90.0:
            raise ConfigurationError("observer latitude must be between -90 and 90 degrees")
        if not -180.0 <= observer.longitude_deg <= 180.0:
            raise ConfigurationError("observer longitude must be between -180 and 180 degrees")

        try:
            from astropy import units as u
            from astropy.coordinates import AltAz, CIRS, EarthLocation, get_body
            from astropy.time import Time
        except ImportError as exc:
            raise ConfigurationError("Astropy is required for M7 Moon calculations") from exc

        try:
            obstime = Time(observation_time, scale="utc")
            location = EarthLocation.from_geodetic(
                lon=observer.longitude_deg * u.deg,
                lat=observer.latitude_deg * u.deg,
                height=observer.elevation_m * u.m,
            )
            moon = get_body("moon", obstime, location=location)
            apparent = moon.transform_to(CIRS(obstime=obstime, location=location))
            horizontal = moon.transform_to(AltAz(obstime=obstime, location=location))
        except (TypeError, ValueError) as exc:
            raise ConfigurationError(f"invalid Moon observation time or location: {exc}") from exc

        altitude_deg = float(horizontal.alt.to_value(u.deg))
        return MoonSolution(
            observation_time_utc=obstime.utc.isot,
            apparent_ra_deg=float(apparent.ra.to_value(u.deg)) % 360.0,
            apparent_dec_deg=float(apparent.dec.to_value(u.deg)),
            altitude_deg=altitude_deg,
            azimuth_deg=float(horizontal.az.to_value(u.deg)) % 360.0,
            distance_km=float(moon.distance.to_value(u.km)),
            above_horizon=altitude_deg >= 0.0,
        )
