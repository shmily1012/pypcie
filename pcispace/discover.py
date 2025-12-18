"""PCI device discovery helpers."""

import os

from .errors import ValidationError
from .sysfs import device_path, list_device_bdfs, read_hex_file
from .device import Device


def _parse_id(value, name):
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            raise ValidationError("invalid %s: %r" % (name, value))
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError("invalid %s: %r" % (name, value))


def list_devices(sysfs_root=None):
    """Return Device objects for all devices in sysfs."""
    return [Device(addr, sysfs_root=sysfs_root) for addr in list_device_bdfs(sysfs_root)]


def find_devices(vendor_id=None, device_id=None, sysfs_root=None):
    """Find devices matching vendor_id and/or device_id."""
    vendor_id = _parse_id(vendor_id, "vendor_id")
    device_id = _parse_id(device_id, "device_id")
    devices = []
    for addr in list_device_bdfs(sysfs_root):
        base = device_path(addr, sysfs_root)
        try:
            vendor = read_hex_file(os.path.join(base, "vendor"))
            device = read_hex_file(os.path.join(base, "device"))
        except Exception:
            continue
        if vendor_id is not None and vendor != vendor_id:
            continue
        if device_id is not None and device != device_id:
            continue
        devices.append(Device(addr, sysfs_root=sysfs_root))
    return devices
