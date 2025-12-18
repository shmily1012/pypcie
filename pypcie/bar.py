"""PCI BAR access helpers."""

import mmap
import os
import struct

from .errors import AlignmentError, OutOfRangeError, PermissionDeniedError, ValueRangeError
from .sysfs import Sysfs, parse_resource_file
from .types import PciAddress

IORESOURCE_IO = 0x00000100


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


def _validate_value(value, width):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueRangeError("value must be an integer")
    max_value = (1 << (width * 8)) - 1
    if not (0 <= value <= max_value):
        raise ValueRangeError("value out of range")


class PciBar(object):
    """Access a PCI BAR resource."""

    def __init__(self, sysfs, addr, index):
        self.sysfs = sysfs or Sysfs()
        self.address = PciAddress.parse(addr)
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            raise OutOfRangeError("bar index must be a non-negative integer")
        self.index = index
        self._fd = None
        self._mmap = None
        self._readonly = False
        self._length = None
        self._start, self._end, self._flags, self._size = self._resource_entry()
        self._io_port = bool(self._flags & IORESOURCE_IO)

    def _resource_entry(self):
        entries = parse_resource_file(self.address, root=self.sysfs.root)
        if self.index >= len(entries):
            raise OutOfRangeError("BAR index out of range")
        start, end, flags = entries[self.index]
        if start == 0 and end == 0:
            size = 0
        elif end < start:
            size = 0
        else:
            size = end - start + 1
        return start, end, flags, size

    @property
    def is_io(self):
        return self._io_port

    @property
    def length(self):
        if self._length is not None:
            return self._length
        return self._size or 4096

    def open(self, readonly=False, length=None):
        if self._fd is not None or self._mmap is not None:
            return self
        if length is None:
            length = self._size or 4096
        if length <= 0:
            raise OutOfRangeError("length must be positive")
        self._length = length
        self._readonly = bool(readonly)
        path = self.sysfs.resource_path(self.address, self.index)
        flags = os.O_RDONLY if readonly else os.O_RDWR
        try:
            self._fd = os.open(path, flags)
        except PermissionError as exc:
            raise PermissionDeniedError(str(exc))
        except OSError as exc:
            raise OutOfRangeError(str(exc))
        if not self._io_port:
            access = mmap.ACCESS_READ if readonly else mmap.ACCESS_WRITE
            try:
                self._mmap = mmap.mmap(self._fd, length, access=access)
            except (OSError, ValueError) as exc:
                os.close(self._fd)
                self._fd = None
                raise OutOfRangeError(str(exc))
        return self

    def close(self):
        if self._mmap is not None:
            self._mmap.close()
            self._mmap = None
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def _ensure_open(self, readonly=False):
        if self._fd is None and self._mmap is None:
            self.open(readonly=readonly)
        elif readonly is False and self._readonly:
            self.close()
            self.open(readonly=False)

    def _check_bounds(self, offset, length):
        if offset + length > self.length:
            raise OutOfRangeError("BAR access out of range")

    def read_bytes(self, offset, length):
        _validate_offset(offset)
        if not isinstance(length, int) or isinstance(length, bool) or length < 0:
            raise OutOfRangeError("length must be non-negative")
        self._ensure_open(readonly=True)
        self._check_bounds(offset, length)
        if self._io_port:
            data = os.pread(self._fd, length, offset)
        else:
            data = self._mmap[offset : offset + length]
        if len(data) != length:
            raise OutOfRangeError("short read from BAR")
        return data

    def write_bytes(self, offset, data):
        _validate_offset(offset)
        if not isinstance(data, (bytes, bytearray)):
            raise ValueRangeError("data must be bytes")
        self._ensure_open(readonly=False)
        self._check_bounds(offset, len(data))
        if self._io_port:
            written = os.pwrite(self._fd, data, offset)
            if written != len(data):
                raise OutOfRangeError("short write to BAR")
        else:
            self._mmap[offset : offset + len(data)] = data

    def read_u8(self, offset):
        data = self.read_bytes(offset, 1)
        return struct.unpack("<B", data)[0]

    def read_u16(self, offset):
        _validate_alignment(offset, 2)
        data = self.read_bytes(offset, 2)
        return struct.unpack("<H", data)[0]

    def read_u32(self, offset):
        _validate_alignment(offset, 4)
        data = self.read_bytes(offset, 4)
        return struct.unpack("<I", data)[0]

    def read_u64(self, offset):
        _validate_alignment(offset, 8)
        self._check_bounds(offset, 8)
        low = self.read_u32(offset)
        high = self.read_u32(offset + 4)
        return (high << 32) | low

    def write_u8(self, offset, value):
        _validate_value(value, 1)
        self.write_bytes(offset, struct.pack("<B", value))

    def write_u16(self, offset, value):
        _validate_alignment(offset, 2)
        _validate_value(value, 2)
        self.write_bytes(offset, struct.pack("<H", value))

    def write_u32(self, offset, value):
        _validate_alignment(offset, 4)
        _validate_value(value, 4)
        self.write_bytes(offset, struct.pack("<I", value))

    def write_u64(self, offset, value):
        _validate_alignment(offset, 8)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueRangeError("value must be an integer")
        if not (0 <= value <= 0xFFFFFFFFFFFFFFFF):
            raise ValueRangeError("value out of range")
        self._check_bounds(offset, 8)
        low = value & 0xFFFFFFFF
        high = (value >> 32) & 0xFFFFFFFF
        self.write_u32(offset, low)
        self.write_u32(offset + 4, high)


def _get_sysfs(sysfs_root):
    return Sysfs(root=sysfs_root) if sysfs_root else Sysfs()


def read(address, bar, offset, width, sysfs_root=None):
    if width not in (1, 2, 4, 8):
        raise ValueRangeError("width must be 1, 2, 4, or 8")
    pci_bar = PciBar(_get_sysfs(sysfs_root), address, bar)
    with pci_bar.open(readonly=True):
        if width == 1:
            return pci_bar.read_u8(offset)
        if width == 2:
            return pci_bar.read_u16(offset)
        if width == 4:
            return pci_bar.read_u32(offset)
        return pci_bar.read_u64(offset)


def write(address, bar, offset, width, value, sysfs_root=None):
    if width not in (1, 2, 4, 8):
        raise ValueRangeError("width must be 1, 2, 4, or 8")
    pci_bar = PciBar(_get_sysfs(sysfs_root), address, bar)
    with pci_bar.open(readonly=False):
        if width == 1:
            pci_bar.write_u8(offset, value)
        elif width == 2:
            pci_bar.write_u16(offset, value)
        elif width == 4:
            pci_bar.write_u32(offset, value)
        else:
            pci_bar.write_u64(offset, value)


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


__all__ = [
    "PciBar",
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
