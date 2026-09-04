from pathlib import Path

from openscope.configuration import load_yaml, telescope_state_from_config


def test_example_configuration_loads_five_channels():
    path = Path(__file__).parents[1] / "config" / "example_equatorial.yaml"
    state = telescope_state_from_config(load_yaml(path))
    assert len(state.motors) == 5
    assert state.motor("RA").enabled is True
    assert state.motor("AUX2").enabled is False
