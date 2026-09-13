from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CatalogObject:
    """Small offline-first starter catalog for common fixed targets."""

    id: str
    name: str
    object_type: str
    ra_deg: float
    dec_deg: float
    description: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


CATALOG_OBJECTS: tuple[CatalogObject, ...] = (
    CatalogObject("M31", "Andromeda Galaxy", "galaxy", 10.6847, 41.2687, "Nearest large galaxy"),
    CatalogObject("M42", "Orion Nebula", "nebula", 83.8221, -5.3911, "Bright emission nebula"),
    CatalogObject("M45", "Pleiades", "open_cluster", 56.75, 24.1167, "Seven Sisters open cluster"),
    CatalogObject("NGC7000", "North America Nebula", "nebula", 314.7, 44.5, "Large emission nebula"),
    CatalogObject("POLARIS", "Polaris", "star", 37.9546, 89.2641, "North celestial pole star"),
    CatalogObject("SIRIUS", "Sirius", "star", 101.2872, -16.7161, "Brightest night-sky star"),
    CatalogObject("VEGA", "Vega", "star", 279.2347, 38.7837, "Bright summer star"),
)


def list_catalog_objects(query: str = "") -> list[dict[str, object]]:
    """Return catalog objects matching an optional case-insensitive search."""
    needle = query.strip().casefold()
    return [
        obj.as_dict()
        for obj in CATALOG_OBJECTS
        if not needle
        or needle in obj.id.casefold()
        or needle in obj.name.casefold()
        or needle in obj.object_type.casefold()
    ]
