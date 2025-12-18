import pytest

from pypcie.bar import PciBar
from pypcie.errors import AlignmentError, OutOfRangeError
from pypcie.sysfs import Sysfs


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
    sysfs = Sysfs(root=str(sysfs_root))
    pci_bar = PciBar(sysfs, addr, 0)
    with pci_bar.open():
        value = pci_bar.read_u32(4)
        assert value == 0x07060504

        pci_bar.write_u16(2, 0xBEEF)
        assert pci_bar.read_u16(2) == 0xBEEF

        pci_bar.write_u64(8, 0x1122334455667788)
        assert pci_bar.read_u64(8) == 0x1122334455667788

        with pytest.raises(OutOfRangeError):
            pci_bar.read_u32(256)


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
    sysfs = Sysfs(root=str(sysfs_root))
    pci_bar = PciBar(sysfs, addr, 1)
    with pci_bar.open():
        assert pci_bar.read_u8(1) == 1
        pci_bar.write_u8(1, 0xAA)
        assert pci_bar.read_u8(1) == 0xAA


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

    sysfs = Sysfs(root=str(sysfs_root))
    pci_bar = PciBar(sysfs, "0000:00:09.0", 0)
    with pci_bar.open():
        with pytest.raises(AlignmentError):
            pci_bar.read_u32(2)
