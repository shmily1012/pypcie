"""PCI config space access."""

import os
import struct

from .errors import ConfigError, PermissionDenied, ValidationError
from .sysfs import device_path
from .types import PciAddress


def _config_path(address, sysfs_root=None):
    addr = PciAddress.parse(address)
    return os.path.join(device_path(addr, sysfs_root), "config")


def _validate_width(width):
    if width not in (1, 2, 4, 8):
        raise ValidationError("width must be 1, 2, 4, or 8")


def _validate_alignment(offset, width):
    if offset < 0:
        raise ValidationError("offset must be non-negative")
    if width in (1, 2, 4) and offset % width != 0:
        raise ValidationError("offset must be aligned to width")
    if width == 8 and offset % 4 != 0:
        raise ValidationError("offset must be 4-byte aligned for u64")


def _config_size(path):
    try:
        return os.stat(path).st_size
    except PermissionError as exc:
        raise PermissionDenied(str(exc))
    except OSError as exc:
        raise ConfigError(str(exc))


def _read_bytes(path, offset, size):
    try:
        with open(path, "rb") as handle:
            handle.seek(offset)
            data = handle.read(size)
    except PermissionError as exc:
        raise PermissionDenied(str(exc))
    except OSError as exc:
        raise ConfigError(str(exc))
    if len(data) != size:
        raise ConfigError("short read from config space")
    return data


def _write_bytes(path, offset, data):
    try:
        with open(path, "r+b") as handle:
            handle.seek(offset)
            handle.write(data)
    except PermissionError as exc:
        raise PermissionDenied(str(exc))
    except OSError as exc:
        raise ConfigError(str(exc))


def read(address, offset, width, sysfs_root=None):
    _validate_width(width)
    _validate_alignment(offset, width)
    path = _config_path(address, sysfs_root)
    size = _config_size(path)
    if offset + width > size:
        raise ValidationError("config read out of range")
    if width == 8:
        low = read_u32(address, offset, sysfs_root=sysfs_root)
        high = read_u32(address, offset + 4, sysfs_root=sysfs_root)
        return (high << 32) | low
    data = _read_bytes(path, offset, width)
    fmt = {1: "<B", 2: "<H", 4: "<I"}[width]
    return struct.unpack(fmt, data)[0]


def write(address, offset, width, value, sysfs_root=None):
    _validate_width(width)
    _validate_alignment(offset, width)
    path = _config_path(address, sysfs_root)
    size = _config_size(path)
    if offset + width > size:
        raise ValidationError("config write out of range")
    max_value = (1 << (width * 8)) - 1
    if not (0 <= value <= max_value):
        raise ValidationError("value out of range")
    if width == 8:
        low = value & 0xFFFFFFFF
        high = (value >> 32) & 0xFFFFFFFF
        write_u32(address, offset, low, sysfs_root=sysfs_root)
        write_u32(address, offset + 4, high, sysfs_root=sysfs_root)
        return
    fmt = {1: "<B", 2: "<H", 4: "<I"}[width]
    data = struct.pack(fmt, value)
    _write_bytes(path, offset, data)


def read_u8(address, offset, sysfs_root=None):
    return read(address, offset, 1, sysfs_root=sysfs_root)


def read_u16(address, offset, sysfs_root=None):
    return read(address, offset, 2, sysfs_root=sysfs_root)


def read_u32(address, offset, sysfs_root=None):
    return read(address, offset, 4, sysfs_root=sysfs_root)


def read_u64(address, offset, sysfs_root=None):
    return read(address, offset, 8, sysfs_root=sysfs_root)


def write_u8(address, offset, value, sysfs_root=None):
    write(address, offset, 1, value, sysfs_root=sysfs_root)


def write_u16(address, offset, value, sysfs_root=None):
    write(address, offset, 2, value, sysfs_root=sysfs_root)


def write_u32(address, offset, value, sysfs_root=None):
    write(address, offset, 4, value, sysfs_root=sysfs_root)


def write_u64(address, offset, value, sysfs_root=None):
    write(address, offset, 8, value, sysfs_root=sysfs_root)
