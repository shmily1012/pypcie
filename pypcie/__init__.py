"""pypcie package."""

__version__ = "0.1.0"

from .bar import read as read_bar, write as write_bar
from .capability import (
    find_ext_capability,
    find_pci_capability,
    find_pcie_capability,
    find_pcie_ext_capability,
)
from .link import (
    link_disable,
    link_enable,
    link_hot_reset,
    read_link_status,
    retrain_link,
    set_link_control_bits,
    set_target_link_speed,
    wait_for_link_training,
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
    "link_disable",
    "link_enable",
    "link_hot_reset",
    "list_devices",
    "read_link_status",
    "read_bar",
    "read_config",
    "retrain_link",
    "set_link_control_bits",
    "set_target_link_speed",
    "wait_for_link_training",
    "write_bar",
    "write_config",
]
