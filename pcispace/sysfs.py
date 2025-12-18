"""Helpers for interacting with sysfs."""

import os

from .errors import PermissionDenied, SysfsError
from .types import PciAddress

DEFAULT_SYSFS_ROOT = "/sys"


def sysfs_root(root=None):
    return root or DEFAULT_SYSFS_ROOT


def pci_devices_path(root=None):
    return os.path.join(sysfs_root(root), "bus", "pci", "devices")


def device_path(address, root=None):
    addr = PciAddress.parse(address)
    return os.path.join(pci_devices_path(root), addr.bdf)


def read_hex_file(path):
    try:
        with open(path, "r") as handle:
            value = handle.read().strip()
    except PermissionError as exc:
        raise PermissionDenied(str(exc))
    except OSError as exc:
        raise SysfsError(str(exc))
    if not value:
        raise SysfsError("empty value in %s" % path)
    return int(value, 16)


def list_device_bdfs(root=None):
    base = pci_devices_path(root)
    try:
        entries = os.listdir(base)
    except PermissionError as exc:
        raise PermissionDenied(str(exc))
    except OSError as exc:
        raise SysfsError(str(exc))
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
    except PermissionError as exc:
        raise PermissionDenied(str(exc))
    except OSError as exc:
        raise SysfsError(str(exc))
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
            continue
        entries.append((start, end, flags))
    return entries
