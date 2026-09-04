from pathlib import Path
from typing import Any

import yaml

from .core.errors import ConfigurationError
from .core.telescope import TelescopeState


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML configuration file and return its mapping."""
    config_path = Path(path)
    try:
        data = yaml.safe_load(config_path.read_text()) or {}
    except OSError as exc:
        raise ConfigurationError(f"Could not read configuration: {config_path}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError("Top-level configuration must be a mapping")
    return data


def telescope_state_from_config(config: dict[str, Any]) -> TelescopeState:
    """Build the five-channel telescope state from configuration."""
    mount_type = config.get("mount", {}).get("type", "equatorial")
    motor_config = config.get("motors", {})
    enabled = {
        motor_id: bool(motor_config.get(motor_id, {}).get("enabled", False))
        for motor_id in ("RA", "DEC", "FOCUS", "AUX1", "AUX2")
    }
    state = TelescopeState.with_default_channels(enabled)
    state.mount_type = mount_type
    state.__post_init__()
    return state
