import pytest

from pcispace import bar
from pcispace.errors import ValidationError


def test_bar_mmio_read_write(sysfs_root, make_device):
    resource_entries = [
        (0x1000, 0x10FF, 0x00000200),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
    ]
    data = bytes(range(256))
    make_device(
        bdf="0000:00:07.0",
        resource_entries=resource_entries,
        resource_files={0: data},
    )

    addr = "0000:00:07.0"
    value = bar.read_u32(addr, 0, 4, sysfs_root=str(sysfs_root))
    assert value == 0x07060504

    bar.write_u16(addr, 0, 2, 0xBEEF, sysfs_root=str(sysfs_root))
    assert bar.read_u16(addr, 0, 2, sysfs_root=str(sysfs_root)) == 0xBEEF


def test_bar_io_fallback(sysfs_root, make_device):
    resource_entries = [
        (0, 0, 0),
        (0x20, 0x2F, 0x00000100),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
    ]
    data = bytes(range(16))
    make_device(
        bdf="0000:00:08.0",
        resource_entries=resource_entries,
        resource_files={1: data},
    )

    addr = "0000:00:08.0"
    assert bar.read_u8(addr, 1, 1, sysfs_root=str(sysfs_root)) == 1
    bar.write_u8(addr, 1, 1, 0xAA, sysfs_root=str(sysfs_root))
    assert bar.read_u8(addr, 1, 1, sysfs_root=str(sysfs_root)) == 0xAA


def test_bar_alignment(sysfs_root, make_device):
    resource_entries = [
        (0x1000, 0x10FF, 0x00000200),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
    ]
    data = bytes(range(256))
    make_device(
        bdf="0000:00:09.0",
        resource_entries=resource_entries,
        resource_files={0: data},
    )

    with pytest.raises(ValidationError):
        bar.read_u32("0000:00:09.0", 0, 2, sysfs_root=str(sysfs_root))
