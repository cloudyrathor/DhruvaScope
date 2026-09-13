from datetime import datetime

from ..core.errors import ConfigurationError
from ..tracking.astronomy import ObserverLocation


SOLAR_SYSTEM_BODIES = (
    ("SUN", "Sun", "star", "sun"),
    ("MOON", "Moon", "natural_satellite", "moon"),
    ("MERCURY", "Mercury", "planet", "mercury"),
    ("VENUS", "Venus", "planet", "venus"),
    ("MARS", "Mars", "planet", "mars"),
    ("JUPITER", "Jupiter", "planet", "jupiter"),
    ("SATURN", "Saturn", "planet", "saturn"),
    ("URANUS", "Uranus", "planet", "uranus"),
    ("NEPTUNE", "Neptune", "planet", "neptune"),
)


def list_solar_system_objects(
    observer: ObserverLocation,
    observation_time: str | datetime,
) -> list[dict[str, object]]:
    """Calculate current apparent positions for selectable solar-system bodies."""
    try:
        from astropy import units as u
        from astropy.coordinates import AltAz, CIRS, EarthLocation, get_body
        from astropy.time import Time
    except ImportError as exc:
        raise ConfigurationError("Astropy is required for solar-system objects") from exc

    try:
        obstime = Time(observation_time, scale="utc")
        location = EarthLocation.from_geodetic(
            lon=observer.longitude_deg * u.deg,
            lat=observer.latitude_deg * u.deg,
            height=observer.elevation_m * u.m,
        )
        objects: list[dict[str, object]] = []
        for object_id, name, object_type, body_name in SOLAR_SYSTEM_BODIES:
            body = get_body(body_name, obstime, location=location)
            apparent = body.transform_to(CIRS(obstime=obstime, location=location))
            horizontal = body.transform_to(AltAz(obstime=obstime, location=location))
            altitude_deg = float(horizontal.alt.to_value(u.deg))
            objects.append({
                "id": object_id,
                "name": name,
                "object_type": object_type,
                "ra_deg": float(apparent.ra.to_value(u.deg)) % 360.0,
                "dec_deg": float(apparent.dec.to_value(u.deg)),
                "description": f"Dynamic {name} position",
                "altitude_deg": altitude_deg,
                "azimuth_deg": float(horizontal.az.to_value(u.deg)) % 360.0,
                "distance_km": float(body.distance.to_value(u.km)),
                "above_horizon": altitude_deg >= 0.0,
            })
        return objects
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"invalid solar-system observation time or location: {exc}") from exc
