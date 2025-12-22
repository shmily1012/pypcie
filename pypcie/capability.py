"""PCI capability discovery helpers."""

import os

from . import config
from .errors import PermissionDeniedError, ResourceNotFoundError
from .sysfs import Sysfs
from .types import validate_u16, validate_u8

PCI_STATUS = 0x06
PCI_STATUS_CAP_LIST = 0x10
PCI_HEADER_TYPE = 0x0E
PCI_HEADER_TYPE_MASK = 0x7F
PCI_HEADER_TYPE_NORMAL = 0x00
PCI_HEADER_TYPE_BRIDGE = 0x01
PCI_HEADER_TYPE_CARDBUS = 0x02
PCI_CAPABILITY_LIST = 0x34
PCI_CB_CAPABILITY_LIST = 0x14
PCI_CAP_ID_EXP = 0x10
PCI_STD_HEADER_SIZEOF = 0x40
PCI_FIND_CAP_TTL = 48
PCI_CFG_SPACE_SIZE = 0x100


def _config_size(address, sysfs_root=None):
    sysfs = Sysfs(root=sysfs_root) if sysfs_root else Sysfs()
    path = sysfs.config_path(address)
    try:
        return os.stat(path).st_size
    except FileNotFoundError as exc:
        raise ResourceNotFoundError(str(exc))
    except PermissionError as exc:
        raise PermissionDeniedError(str(exc))
    except OSError as exc:
        raise ResourceNotFoundError(str(exc))


def _cap_list_start(address, sysfs_root=None):
    status = config.read_u16(address, PCI_STATUS, sysfs_root=sysfs_root)
    if not (status & PCI_STATUS_CAP_LIST):
        return 0
    hdr_type = config.read_u8(address, PCI_HEADER_TYPE, sysfs_root=sysfs_root)
    hdr_type &= PCI_HEADER_TYPE_MASK
    if hdr_type in (PCI_HEADER_TYPE_NORMAL, PCI_HEADER_TYPE_BRIDGE):
        return PCI_CAPABILITY_LIST
    if hdr_type == PCI_HEADER_TYPE_CARDBUS:
        return PCI_CB_CAPABILITY_LIST
    return 0


def find_pci_capability(address, cap_id, sysfs_root=None):
    """Return the offset of a standard PCI capability, or 0 if not found."""
    cap_id = validate_u8(cap_id)
    start = _cap_list_start(address, sysfs_root=sysfs_root)
    if not start:
        return 0
    pos = config.read_u8(address, start, sysfs_root=sysfs_root)
    ttl = PCI_FIND_CAP_TTL
    while ttl > 0:
        ttl -= 1
        if pos < PCI_STD_HEADER_SIZEOF:
            break
        pos &= 0xFC
        ent = config.read_u16(address, pos, sysfs_root=sysfs_root)
        ent_id = ent & 0xFF
        if ent_id == 0xFF:
            break
        if ent_id == cap_id:
            return pos
        pos = (ent >> 8) & 0xFF
    return 0


def find_pcie_capability(address, sysfs_root=None):
    """Return the offset of the PCI Express capability, or 0 if not found."""
    return find_pci_capability(address, PCI_CAP_ID_EXP, sysfs_root=sysfs_root)


def find_ext_capability(address, cap_id, sysfs_root=None):
    """Return the offset of a PCIe extended capability, or 0 if not found."""
    cap_id = validate_u16(cap_id)
    config_size = _config_size(address, sysfs_root=sysfs_root)
    if config_size <= PCI_CFG_SPACE_SIZE:
        return 0
    pos = PCI_CFG_SPACE_SIZE
    ttl = max(1, (config_size - PCI_CFG_SPACE_SIZE) // 8)
    while ttl > 0 and pos >= PCI_CFG_SPACE_SIZE:
        ttl -= 1
        if pos + 4 > config_size:
            break
        header = config.read_u32(address, pos, sysfs_root=sysfs_root)
        if header in (0, 0xFFFFFFFF):
            break
        if (header & 0xFFFF) == cap_id:
            return pos
        next_pos = (header >> 20) & 0xFFF
        if next_pos == 0 or next_pos == pos or next_pos < PCI_CFG_SPACE_SIZE:
            break
        pos = next_pos
    return 0


def find_pcie_ext_capability(address, cap_id, sysfs_root=None):
    """Alias for find_ext_capability for PCIe extended capability IDs."""
    return find_ext_capability(address, cap_id, sysfs_root=sysfs_root)


__all__ = [
    "find_ext_capability",
    "find_pci_capability",
    "find_pcie_capability",
    "find_pcie_ext_capability",
]
