from pathlib import Path

from openscope.configuration import load_yaml, telescope_state_from_config
from openscope.core.motor import MotorDirection
from openscope.devices.mock import MockDevice
from openscope.tracking.tracker import SIDEREAL_RATE_DEG_PER_SECOND, SiderealTracker


def test_example_configuration_loads_five_channels():
    path = Path(__file__).parents[1] / "config" / "example_equatorial.yaml"
    state = telescope_state_from_config(load_yaml(path))
    assert len(state.motors) == 5
    assert state.motor("RA").enabled is True
    assert state.motor("AUX2").enabled is False


def test_sidereal_tracker_starts_and_stops_ra_only():
    state = telescope_state_from_config(load_yaml(Path(__file__).parents[1] / "config" / "example_equatorial.yaml"))
    device = MockDevice(state)
    tracker = SiderealTracker(device, ra_direction=MotorDirection.NEG)

    tracker.start()

    assert tracker.status() == {
        "mode": "SIDEREAL",
        "running": True,
        "motor": "RA",
        "direction": "NEG",
        "rate_deg_per_second": SIDEREAL_RATE_DEG_PER_SECOND,
    }
    assert state.motor("RA").state.value == "MOVING"
    assert state.motor("DEC").state.value == "IDLE"

    tracker.stop()

    assert tracker.running is False
    assert state.motor("RA").state.value == "IDLE"


def test_sidereal_tracker_rejects_disabled_ra():
    state = telescope_state_from_config(load_yaml(Path(__file__).parents[1] / "config" / "example_equatorial.yaml"))
    state.motor("RA").enabled = False
    device = MockDevice(state)
    tracker = SiderealTracker(device)

    try:
        tracker.start()
    except Exception as exc:
        assert "RA motor is disabled" in str(exc)
    else:
        raise AssertionError("disabled RA should not start tracking")


def test_astronomy_service_calculates_fixed_target():
    import pytest

    pytest.importorskip("astropy")
    from openscope.tracking.astronomy import AstronomyService, EquatorialTarget, ObserverLocation

    solution = AstronomyService().calculate_target(
        EquatorialTarget("Test Star", 0.0, 0.0),
        ObserverLocation(0.0, 0.0),
        "2025-01-01T00:00:00Z",
    )

    assert solution.name == "Test Star"
    assert 0.0 <= solution.apparent_ra_deg < 360.0
    assert -90.0 <= solution.apparent_dec_deg <= 90.0
    assert -90.0 <= solution.altitude_deg <= 90.0
    assert 0.0 <= solution.azimuth_deg < 360.0

