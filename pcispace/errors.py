"""Custom exceptions for pcispace."""


class PciError(Exception):
    """Base exception for pcispace."""


class PciAddressError(PciError):
    """Invalid PCI address format or range."""


class SysfsError(PciError):
    """Issues accessing sysfs."""


class ValidationError(PciError):
    """Invalid user input (alignment, range, width)."""


class PermissionDenied(PciError):
    """Operation not permitted due to permissions."""


class ConfigError(PciError):
    """Access or parsing error for PCI config space."""


class BarError(PciError):
    """Access or parsing error for PCI BAR resources."""
