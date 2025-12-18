import pytest

from pcispace import config
from pcispace.errors import ValidationError


def test_config_read_write(sysfs_root, make_device):
    config_bytes = bytearray(64)
    config_bytes[4:8] = b"\x11\x22\x33\x44"
    make_device(bdf="0000:00:05.0", config_bytes=config_bytes)

    addr = "0000:00:05.0"
    value = config.read_u32(addr, 4, sysfs_root=str(sysfs_root))
    assert value == 0x44332211

    config.write_u16(addr, 2, 0xABCD, sysfs_root=str(sysfs_root))
    assert config.read_u16(addr, 2, sysfs_root=str(sysfs_root)) == 0xABCD

    config.write_u64(addr, 8, 0x1122334455667788, sysfs_root=str(sysfs_root))
    assert config.read_u64(addr, 8, sysfs_root=str(sysfs_root)) == 0x1122334455667788


def test_config_alignment(sysfs_root, make_device):
    make_device(bdf="0000:00:06.0")
    addr = "0000:00:06.0"
    with pytest.raises(ValidationError):
        config.read_u16(addr, 1, sysfs_root=str(sysfs_root))
    with pytest.raises(ValidationError):
        config.write_u32(addr, 2, 0x1234, sysfs_root=str(sysfs_root))
