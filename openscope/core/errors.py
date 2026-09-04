class OpenScopeError(Exception):
    """Base exception for expected OpenScope errors."""


class ConfigurationError(OpenScopeError, ValueError):
    """Raised when configuration or a command value is invalid."""


class DeviceError(OpenScopeError):
    """Raised when a device cannot execute a command."""
