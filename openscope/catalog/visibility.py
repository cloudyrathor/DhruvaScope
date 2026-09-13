from datetime import datetime

from ..tracking.astronomy import AstronomyService, EquatorialTarget, ObserverLocation
from .objects import CATALOG_OBJECTS


def list_visible_catalog_objects(
    observer: ObserverLocation,
    observation_time: str | datetime,
) -> list[dict[str, object]]:
    """Return local fixed objects currently above the mathematical horizon."""
    astronomy = AstronomyService()
    visible: list[dict[str, object]] = []
    for catalog_object in CATALOG_OBJECTS:
        solution = astronomy.calculate_target(
            EquatorialTarget(catalog_object.name, catalog_object.ra_deg, catalog_object.dec_deg),
            observer,
            observation_time,
        )
        item = catalog_object.as_dict()
        item["altitude_deg"] = solution.altitude_deg
        item["azimuth_deg"] = solution.azimuth_deg
        if solution.above_horizon:
            visible.append(item)
    return sorted(visible, key=lambda item: float(item["altitude_deg"]), reverse=True)
