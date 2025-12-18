"""PCI device discovery helpers."""

import os

from .errors import (
    DeviceNotFoundError,
    MultipleDevicesFoundError,
    PermissionDeniedError,
    ResourceNotFoundError,
    SysfsFormatError,
    ValueRangeError,
)
from .sysfs import Sysfs
from .types import PciAddress


def _parse_id(value, name):
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = int(value, 0)
        except ValueError:
            raise ValueRangeError("invalid %s: %r" % (name, value))
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueRangeError("invalid %s: %r" % (name, value))
    if not (0 <= value <= 0xFFFF):
        raise ValueRangeError("%s out of range" % name)
    return value


def list_devices(sysfs=None):
    """Return PciAddress entries for all devices in sysfs."""
    if sysfs is None:
        sysfs = Sysfs()
    try:
        entries = os.listdir(sysfs.root)
    except FileNotFoundError as exc:
        raise ResourceNotFoundError(str(exc))
    except PermissionError as exc:
        raise PermissionDeniedError(str(exc))
    devices = []
    for entry in entries:
        try:
            devices.append(PciAddress.parse(entry))
        except Exception:
            continue
    return devices


def get_device_info(addr, sysfs=None):
    """Return a dict of available sysfs attributes for a device."""
    if sysfs is None:
        sysfs = Sysfs()
    base = sysfs.device_dir(addr)
    mapping = {
        "vendor": "vendor",
        "device": "device",
        "subsystem_vendor": "subsystem_vendor",
        "subsystem_device": "subsystem_device",
        "class": "class",
    }
    info = {}
    for key, filename in mapping.items():
        path = os.path.join(base, filename)
        try:
            info[key] = sysfs.read_hex_attr(path)
        except ResourceNotFoundError:
            continue
    return info


def find_by_id(vendor_id, device_id=None, sysfs=None):
    """Return PciAddress entries matching vendor/device ids."""
    if sysfs is None:
        sysfs = Sysfs()
    vendor_id = _parse_id(vendor_id, "vendor_id")
    device_id = _parse_id(device_id, "device_id")
    matches = []
    for addr in list_devices(sysfs=sysfs):
        base = sysfs.device_dir(addr)
        try:
            vendor = sysfs.read_hex_attr(os.path.join(base, "vendor"))
            device = sysfs.read_hex_attr(os.path.join(base, "device"))
        except ResourceNotFoundError:
            continue
        except (PermissionDeniedError, SysfsFormatError):
            continue
        if vendor_id is not None and vendor != vendor_id:
            continue
        if device_id is not None and device != device_id:
            continue
        matches.append(addr)
    return matches


def find_one_by_id(vendor_id, device_id=None, sysfs=None):
    matches = find_by_id(vendor_id, device_id, sysfs=sysfs)
    if not matches:
        raise DeviceNotFoundError("no devices found")
    if len(matches) > 1:
        raise MultipleDevicesFoundError("multiple devices found")
    return matches[0]


def find_devices(vendor_id=None, device_id=None, sysfs=None):
    """Compatibility alias for find_by_id."""
    if vendor_id is None and device_id is None:
        return list_devices(sysfs=sysfs)
    return find_by_id(vendor_id, device_id, sysfs=sysfs)
