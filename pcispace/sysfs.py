"""Helpers for interacting with sysfs."""

import os

from .errors import (
    OutOfRangeError,
    PermissionDeniedError,
    ResourceNotFoundError,
    SysfsFormatError,
)
from .types import PciAddress

DEFAULT_SYSFS_ROOT = "/sys/bus/pci/devices"


class Sysfs(object):
    """Access sysfs entries for PCI devices."""

    def __init__(self, root=None):
        self.root = root or DEFAULT_SYSFS_ROOT

    def device_dir(self, addr):
        address = PciAddress.parse(addr)
        return os.path.join(self.root, address.bdf)

    def config_path(self, addr):
        return os.path.join(self.device_dir(addr), "config")

    def resource_path(self, addr, bar_index):
        if not isinstance(bar_index, int) or isinstance(bar_index, bool):
            raise OutOfRangeError("bar_index must be an integer")
        if bar_index < 0:
            raise OutOfRangeError("bar_index must be non-negative")
        return os.path.join(self.device_dir(addr), "resource%d" % bar_index)

    def read_hex_attr(self, path):
        try:
            with open(path, "r") as handle:
                value = handle.read().strip()
        except FileNotFoundError as exc:
            raise ResourceNotFoundError(str(exc))
        except PermissionError as exc:
            raise PermissionDeniedError(str(exc))
        except OSError as exc:
            raise ResourceNotFoundError(str(exc))
        if not value:
            raise SysfsFormatError("empty value in %s" % path)
        try:
            return int(value, 16)
        except ValueError:
            raise SysfsFormatError("invalid hex value in %s" % path)


def sysfs_root(root=None):
    return root or DEFAULT_SYSFS_ROOT


def device_path(address, root=None):
    return Sysfs(root).device_dir(address)


def read_hex_file(path):
    return Sysfs().read_hex_attr(path)


def list_device_bdfs(root=None):
    base = sysfs_root(root)
    try:
        entries = os.listdir(base)
    except FileNotFoundError as exc:
        raise ResourceNotFoundError(str(exc))
    except PermissionError as exc:
        raise PermissionDeniedError(str(exc))
    except OSError as exc:
        raise ResourceNotFoundError(str(exc))
    bdfs = []
    for entry in entries:
        try:
            bdfs.append(PciAddress.parse(entry))
        except Exception:
            continue
    return bdfs


def parse_resource_file(address, root=None):
    """Return list of (start, end, flags) tuples for each BAR."""
    path = os.path.join(device_path(address, root), "resource")
    try:
        with open(path, "r") as handle:
            lines = [line.strip() for line in handle if line.strip()]
    except FileNotFoundError as exc:
        raise ResourceNotFoundError(str(exc))
    except PermissionError as exc:
        raise PermissionDeniedError(str(exc))
    except OSError as exc:
        raise ResourceNotFoundError(str(exc))
    entries = []
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            start = int(parts[0], 16)
            end = int(parts[1], 16)
            flags = int(parts[2], 16)
        except ValueError:
            raise SysfsFormatError("invalid resource line: %r" % line)
        entries.append((start, end, flags))
    return entries
