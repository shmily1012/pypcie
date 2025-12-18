"""PCI config space access using pread/pwrite."""

import os
import struct

from .errors import (
    AlignmentError,
    OutOfRangeError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValueRangeError,
)
from .sysfs import Sysfs


def _config_path(address, sysfs_root=None):
    sysfs = Sysfs(root=sysfs_root) if sysfs_root else Sysfs()
    return sysfs.config_path(address)


def _open_fd(path, flags):
    try:
        return os.open(path, flags)
    except FileNotFoundError as exc:
        raise ResourceNotFoundError(str(exc))
    except PermissionError as exc:
        raise PermissionDeniedError(str(exc))
    except OSError as exc:
        raise ResourceNotFoundError(str(exc))


def _config_size(fd):
    try:
        return os.fstat(fd).st_size
    except OSError as exc:
        raise ResourceNotFoundError(str(exc))


def _validate_offset(offset):
    if not isinstance(offset, int) or isinstance(offset, bool):
        raise OutOfRangeError("offset must be an integer")
    if offset < 0:
        raise OutOfRangeError("offset must be non-negative")


def _validate_alignment(offset, width):
    if width == 2 and offset % 2 != 0:
        raise AlignmentError("u16 offset must be 2-byte aligned")
    if width == 4 and offset % 4 != 0:
        raise AlignmentError("u32 offset must be 4-byte aligned")
    if width == 8 and offset % 8 != 0:
        raise AlignmentError("u64 offset must be 8-byte aligned")


def _validate_bounds(offset, width, size):
    if offset + width > size:
        raise OutOfRangeError("config access out of range")


def _validate_value(value, width):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueRangeError("value must be an integer")
    max_value = (1 << (width * 8)) - 1
    if not (0 <= value <= max_value):
        raise ValueRangeError("value out of range")


def _read_bytes(address, offset, width, sysfs_root=None):
    path = _config_path(address, sysfs_root)
    fd = _open_fd(path, os.O_RDONLY)
    try:
        size = _config_size(fd)
        _validate_bounds(offset, width, size)
        data = os.pread(fd, width, offset)
    finally:
        os.close(fd)
    if len(data) != width:
        raise OutOfRangeError("short read from config")
    return data


def _write_bytes(address, offset, data, sysfs_root=None):
    path = _config_path(address, sysfs_root)
    fd = _open_fd(path, os.O_RDWR)
    try:
        size = _config_size(fd)
        _validate_bounds(offset, len(data), size)
        written = os.pwrite(fd, data, offset)
    finally:
        os.close(fd)
    if written != len(data):
        raise OutOfRangeError("short write to config")


def read(address, offset, width, sysfs_root=None):
    _validate_offset(offset)
    if width not in (1, 2, 4, 8):
        raise ValueRangeError("width must be 1, 2, 4, or 8")
    _validate_alignment(offset, width)
    if width == 8:
        return read_u64(address, offset, sysfs_root=sysfs_root)
    data = _read_bytes(address, offset, width, sysfs_root=sysfs_root)
    fmt = {1: "<B", 2: "<H", 4: "<I"}[width]
    return struct.unpack(fmt, data)[0]


def write(address, offset, width, value, sysfs_root=None):
    _validate_offset(offset)
    if width not in (1, 2, 4, 8):
        raise ValueRangeError("width must be 1, 2, 4, or 8")
    _validate_alignment(offset, width)
    if width == 8:
        write_u64(address, offset, value, sysfs_root=sysfs_root)
        return
    _validate_value(value, width)
    fmt = {1: "<B", 2: "<H", 4: "<I"}[width]
    data = struct.pack(fmt, value)
    _write_bytes(address, offset, data, sysfs_root=sysfs_root)


def read_u8(address, offset, sysfs_root=None):
    return read(address, offset, 1, sysfs_root=sysfs_root)


def read_u16(address, offset, sysfs_root=None):
    return read(address, offset, 2, sysfs_root=sysfs_root)


def read_u32(address, offset, sysfs_root=None):
    return read(address, offset, 4, sysfs_root=sysfs_root)


def read_u64(address, offset, sysfs_root=None):
    _validate_offset(offset)
    _validate_alignment(offset, 8)
    low = read_u32(address, offset, sysfs_root=sysfs_root)
    high = read_u32(address, offset + 4, sysfs_root=sysfs_root)
    return (high << 32) | low


def write_u8(address, offset, value, sysfs_root=None):
    write(address, offset, 1, value, sysfs_root=sysfs_root)


def write_u16(address, offset, value, sysfs_root=None):
    write(address, offset, 2, value, sysfs_root=sysfs_root)


def write_u32(address, offset, value, sysfs_root=None):
    write(address, offset, 4, value, sysfs_root=sysfs_root)


def write_u64(address, offset, value, sysfs_root=None):
    _validate_offset(offset)
    _validate_alignment(offset, 8)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueRangeError("value must be an integer")
    if not (0 <= value <= 0xFFFFFFFFFFFFFFFF):
        raise ValueRangeError("value out of range")
    low = value & 0xFFFFFFFF
    high = (value >> 32) & 0xFFFFFFFF
    write_u32(address, offset, low, sysfs_root=sysfs_root)
    write_u32(address, offset + 4, high, sysfs_root=sysfs_root)


__all__ = [
    "read",
    "read_u8",
    "read_u16",
    "read_u32",
    "read_u64",
    "write",
    "write_u8",
    "write_u16",
    "write_u32",
    "write_u64",
]
