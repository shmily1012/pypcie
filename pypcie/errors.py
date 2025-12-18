"""Custom exceptions for pypcie."""


class PciSpaceError(Exception):
    """Base exception for pypcie."""


class PciError(PciSpaceError):
    """Deprecated compatibility alias for PciSpaceError."""


class DeviceNotFoundError(PciError):
    """Requested PCI device does not exist."""


class PermissionDeniedError(PciError):
    """Operation not permitted due to permissions."""


class AlignmentError(PciError):
    """Offset or access is not properly aligned."""


class OutOfRangeError(PciError):
    """Offset or index is outside the allowed range."""


class ResourceNotFoundError(PciError):
    """Required sysfs resource is missing."""


class MultipleDevicesFoundError(PciError):
    """Multiple devices matched a query that requires one."""


class SysfsFormatError(PciError):
    """Unexpected or invalid sysfs formatting."""


class ValueRangeError(PciError):
    """Value is out of range for the requested width."""


class PciAddressError(ValueRangeError):
    """Deprecated compatibility alias for address validation errors."""


class SysfsError(PciSpaceError):
    """Deprecated compatibility alias for sysfs access errors."""


class ValidationError(PciSpaceError):
    """Deprecated compatibility alias for input validation errors."""


class PermissionDenied(PermissionDeniedError):
    """Deprecated compatibility alias for PermissionDeniedError."""


class ConfigError(PciError):
    """Deprecated compatibility alias for config space errors."""


class BarError(PciError):
    """Deprecated compatibility alias for BAR access errors."""


__all__ = [
    "AlignmentError",
    "BarError",
    "ConfigError",
    "DeviceNotFoundError",
    "MultipleDevicesFoundError",
    "OutOfRangeError",
    "PciAddressError",
    "PciError",
    "PciSpaceError",
    "PermissionDenied",
    "PermissionDeniedError",
    "ResourceNotFoundError",
    "SysfsError",
    "SysfsFormatError",
    "ValidationError",
    "ValueRangeError",
]
