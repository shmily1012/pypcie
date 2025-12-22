"""pypcie package."""

__version__ = "0.1.0"

from .bar import read as read_bar, write as write_bar
from .capability import (
    find_ext_capability,
    find_pci_capability,
    find_pcie_capability,
    find_pcie_ext_capability,
)
from .config import read as read_config, write as write_config
from .device import Device, PciDevice
from .discover import find_devices, list_devices
from .errors import (
    AlignmentError,
    BarError,
    ConfigError,
    DeviceNotFoundError,
    MultipleDevicesFoundError,
    OutOfRangeError,
    PciAddressError,
    PciError,
    PciSpaceError,
    PermissionDenied,
    PermissionDeniedError,
    ResourceNotFoundError,
    SysfsError,
    SysfsFormatError,
    ValidationError,
    ValueRangeError,
)
from .types import PciAddress

__all__ = [
    "__version__",
    "BarError",
    "ConfigError",
    "Device",
    "DeviceNotFoundError",
    "PciDevice",
    "AlignmentError",
    "MultipleDevicesFoundError",
    "OutOfRangeError",
    "PciAddress",
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
    "find_devices",
    "find_ext_capability",
    "find_pci_capability",
    "find_pcie_capability",
    "find_pcie_ext_capability",
    "list_devices",
    "read_bar",
    "read_config",
    "write_bar",
    "write_config",
]
