"""PCI device discovery helpers."""

import os
import re

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

_PCI_DOMAIN_DIR_RE = re.compile(r"^pci[0-9a-fA-F]{4}:[0-9a-fA-F]{2}$")


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


def _extract_bdfs_from_path(path):
    resolved = os.path.realpath(path)
    if not os.path.exists(resolved):
        raise ResourceNotFoundError("unresolvable sysfs path: %s" % path)
    parts = [part for part in resolved.split(os.sep) if part]
    domain_idx = None
    for idx, part in enumerate(parts):
        if _PCI_DOMAIN_DIR_RE.match(part):
            domain_idx = idx
            break
    search_parts = parts[domain_idx + 1 :] if domain_idx is not None else parts
    chain = []
    for part in search_parts:
        try:
            chain.append(PciAddress.parse(part))
        except Exception:
            continue
    return chain


def find_root_port(addr, sysfs=None):
    """Return the root-complex port PciAddress for a given endpoint BDF."""
    if sysfs is None:
        sysfs = Sysfs()
    address = PciAddress.parse(addr)
    device_path = sysfs.device_dir(address)
    if not os.path.lexists(device_path):
        raise DeviceNotFoundError("device not found: %s" % address.bdf)
    chain = _extract_bdfs_from_path(device_path)
    if not chain:
        raise SysfsFormatError("no PCI root port found for %s" % address.bdf)
    return chain[0]


def build_device_tree(sysfs=None):
    """Return (roots, children) describing PCI topology derived from sysfs."""
    if sysfs is None:
        sysfs = Sysfs()
    children = {}
    roots = []
    seen_edges = set()
    for addr in list_devices(sysfs=sysfs):
        device_path = sysfs.device_dir(addr)
        if not os.path.lexists(device_path):
            continue
        try:
            chain = _extract_bdfs_from_path(device_path)
        except ResourceNotFoundError:
            continue
        if not chain:
            continue
        if chain[0] not in roots:
            roots.append(chain[0])
        for parent, child in zip(chain, chain[1:]):
            edge = (parent, child)
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            children.setdefault(parent, []).append(child)
    roots = sorted(roots, key=lambda a: a.bdf)
    for key in list(children.keys()):
        children[key] = sorted(children[key], key=lambda a: a.bdf)
    return roots, children


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
