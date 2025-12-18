"""PCI BAR access."""

import mmap
import os
import struct

from .errors import BarError, PermissionDenied, ValidationError
from .sysfs import device_path, parse_resource_file
from .types import PciAddress

IORESOURCE_IO = 0x00000100


def _resource_entry(address, bar, sysfs_root=None):
    entries = parse_resource_file(address, sysfs_root)
    if bar < 0 or bar >= len(entries):
        raise ValidationError("BAR index out of range")
    start, end, flags = entries[bar]
    if start == 0 and end == 0:
        size = 0
    elif end < start:
        size = 0
    else:
        size = end - start + 1
    return start, end, flags, size


def _resource_path(address, bar, sysfs_root=None):
    addr = PciAddress.parse(address)
    return os.path.join(device_path(addr, sysfs_root), "resource%d" % bar)


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


def _validate_range(offset, width, size):
    if size and offset + width > size:
        raise ValidationError("BAR access out of range")


def _read_file(path, offset, size):
    try:
        with open(path, "rb") as handle:
            handle.seek(offset)
            data = handle.read(size)
    except PermissionError as exc:
        raise PermissionDenied(str(exc))
    except OSError as exc:
        raise BarError(str(exc))
    if len(data) != size:
        raise BarError("short read from BAR")
    return data


def _write_file(path, offset, data):
    try:
        with open(path, "r+b") as handle:
            handle.seek(offset)
            handle.write(data)
    except PermissionError as exc:
        raise PermissionDenied(str(exc))
    except OSError as exc:
        raise BarError(str(exc))


def _read_mmio(path, offset, width, size):
    try:
        with open(path, "rb") as handle:
            mm = mmap.mmap(handle.fileno(), size, access=mmap.ACCESS_READ)
            try:
                mm.seek(offset)
                data = mm.read(width)
            finally:
                mm.close()
    except (OSError, ValueError) as exc:
        raise BarError(str(exc))
    if len(data) != width:
        raise BarError("short read from BAR")
    return data


def _write_mmio(path, offset, data, size):
    try:
        with open(path, "r+b") as handle:
            mm = mmap.mmap(handle.fileno(), size, access=mmap.ACCESS_WRITE)
            try:
                mm.seek(offset)
                mm.write(data)
            finally:
                mm.close()
    except (OSError, ValueError) as exc:
        raise BarError(str(exc))


def _read_raw(address, bar, offset, width, sysfs_root=None):
    _validate_width(width)
    _validate_alignment(offset, width)
    _, _, flags, size = _resource_entry(address, bar, sysfs_root)
    if size == 0:
        raise BarError("BAR size is zero")
    _validate_range(offset, width, size)
    path = _resource_path(address, bar, sysfs_root)
    if flags & IORESOURCE_IO:
        return _read_file(path, offset, width)
    try:
        return _read_mmio(path, offset, width, size)
    except BarError:
        return _read_file(path, offset, width)


def _write_raw(address, bar, offset, width, data, sysfs_root=None):
    _validate_width(width)
    _validate_alignment(offset, width)
    _, _, flags, size = _resource_entry(address, bar, sysfs_root)
    if size == 0:
        raise BarError("BAR size is zero")
    _validate_range(offset, width, size)
    path = _resource_path(address, bar, sysfs_root)
    if flags & IORESOURCE_IO:
        _write_file(path, offset, data)
        return
    try:
        _write_mmio(path, offset, data, size)
    except BarError:
        _write_file(path, offset, data)


def read(address, bar, offset, width, sysfs_root=None):
    _validate_width(width)
    _validate_alignment(offset, width)
    if width == 8:
        low = read_u32(address, bar, offset, sysfs_root=sysfs_root)
        high = read_u32(address, bar, offset + 4, sysfs_root=sysfs_root)
        return (high << 32) | low
    data = _read_raw(address, bar, offset, width, sysfs_root)
    fmt = {1: "<B", 2: "<H", 4: "<I"}[width]
    return struct.unpack(fmt, data)[0]


def write(address, bar, offset, width, value, sysfs_root=None):
    _validate_width(width)
    _validate_alignment(offset, width)
    if width == 8:
        max_value = (1 << 64) - 1
    else:
        max_value = (1 << (width * 8)) - 1
    if not (0 <= value <= max_value):
        raise ValidationError("value out of range")
    if width == 8:
        low = value & 0xFFFFFFFF
        high = (value >> 32) & 0xFFFFFFFF
        write_u32(address, bar, offset, low, sysfs_root=sysfs_root)
        write_u32(address, bar, offset + 4, high, sysfs_root=sysfs_root)
        return
    fmt = {1: "<B", 2: "<H", 4: "<I"}[width]
    data = struct.pack(fmt, value)
    _write_raw(address, bar, offset, width, data, sysfs_root)


def read_u8(address, bar, offset, sysfs_root=None):
    return read(address, bar, offset, 1, sysfs_root=sysfs_root)


def read_u16(address, bar, offset, sysfs_root=None):
    return read(address, bar, offset, 2, sysfs_root=sysfs_root)


def read_u32(address, bar, offset, sysfs_root=None):
    return read(address, bar, offset, 4, sysfs_root=sysfs_root)


def read_u64(address, bar, offset, sysfs_root=None):
    return read(address, bar, offset, 8, sysfs_root=sysfs_root)


def write_u8(address, bar, offset, value, sysfs_root=None):
    write(address, bar, offset, 1, value, sysfs_root=sysfs_root)


def write_u16(address, bar, offset, value, sysfs_root=None):
    write(address, bar, offset, 2, value, sysfs_root=sysfs_root)


def write_u32(address, bar, offset, value, sysfs_root=None):
    write(address, bar, offset, 4, value, sysfs_root=sysfs_root)


def write_u64(address, bar, offset, value, sysfs_root=None):
    write(address, bar, offset, 8, value, sysfs_root=sysfs_root)
