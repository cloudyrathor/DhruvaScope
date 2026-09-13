from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..core.errors import ConfigurationError


@dataclass(frozen=True)
class ObserverLocation:
    """Geographic location used for topocentric coordinate calculations."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float = 0.0


@dataclass(frozen=True)
class EquatorialTarget:
    """A fixed target expressed in ICRS right ascension and declination."""

    name: str
    ra_deg: float
    dec_deg: float


@dataclass(frozen=True)
class TargetSolution:
    """Calculated apparent coordinates and local visibility for a target."""

    name: str
    observation_time_utc: str
    apparent_ra_deg: float
    apparent_dec_deg: float
    altitude_deg: float
    azimuth_deg: float
    above_horizon: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "observation_time_utc": self.observation_time_utc,
            "apparent_ra_deg": self.apparent_ra_deg,
            "apparent_dec_deg": self.apparent_dec_deg,
            "altitude_deg": self.altitude_deg,
            "azimuth_deg": self.azimuth_deg,
            "above_horizon": self.above_horizon,
        }


class AstronomyService:
    """Astropy-backed coordinate service for the first M6 workflow."""

    def calculate_target(
        self,
        target: EquatorialTarget,
        observer: ObserverLocation,
        observation_time: str | datetime,
        mount_type: str = "equatorial",
    ) -> TargetSolution:
        if mount_type != "equatorial":
            raise ConfigurationError("M6 currently supports equatorial mounts only")
        if not target.name.strip():
            raise ConfigurationError("target name is required")
        if not 0.0 <= target.ra_deg < 360.0:
            raise ConfigurationError("right ascension must be between 0 and 360 degrees")
        if not -90.0 <= target.dec_deg <= 90.0:
            raise ConfigurationError("declination must be between -90 and 90 degrees")
        if not -90.0 <= observer.latitude_deg <= 90.0:
            raise ConfigurationError("observer latitude must be between -90 and 90 degrees")
        if not -180.0 <= observer.longitude_deg <= 180.0:
            raise ConfigurationError("observer longitude must be between -180 and 180 degrees")

        try:
            from astropy import units as u
            from astropy.coordinates import AltAz, CIRS, EarthLocation, SkyCoord
            from astropy.time import Time
        except ImportError as exc:
            raise ConfigurationError("Astropy is required for M6 astronomy calculations") from exc

        try:
            obstime = Time(observation_time, scale="utc")
            location = EarthLocation.from_geodetic(
                lon=observer.longitude_deg * u.deg,
                lat=observer.latitude_deg * u.deg,
                height=observer.elevation_m * u.m,
            )
            target_icrs = SkyCoord(
                ra=target.ra_deg * u.deg,
                dec=target.dec_deg * u.deg,
                frame="icrs",
            )
            apparent = target_icrs.transform_to(CIRS(obstime=obstime, location=location))
            horizontal = target_icrs.transform_to(AltAz(obstime=obstime, location=location))
        except (TypeError, ValueError) as exc:
            raise ConfigurationError(f"invalid astronomical target or observation time: {exc}") from exc

        altitude_deg = float(horizontal.alt.to_value(u.deg))
        return TargetSolution(
            name=target.name,
            observation_time_utc=obstime.utc.isot,
            apparent_ra_deg=float(apparent.ra.to_value(u.deg)) % 360.0,
            apparent_dec_deg=float(apparent.dec.to_value(u.deg)),
            altitude_deg=altitude_deg,
            azimuth_deg=float(horizontal.az.to_value(u.deg)) % 360.0,
            above_horizon=altitude_deg >= 0.0,
        )
