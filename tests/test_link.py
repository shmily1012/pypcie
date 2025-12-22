import pytest

from pypcie import config, link
from pypcie.errors import ValueRangeError


def _make_pcie_device(
    make_device,
    bdf,
    config_bytes=None,
    header_type=0x00,
    pcie_version=None,
    lnksta=None,
):
    if config_bytes is None:
        config_bytes = bytearray(256)
    config_bytes[0x06:0x08] = (0x0010).to_bytes(2, "little")
    config_bytes[0x0E] = header_type
    config_bytes[0x34] = 0x50
    config_bytes[0x50] = 0x10
    config_bytes[0x51] = 0x00
    if pcie_version is not None:
        config_bytes[0x52:0x54] = int(pcie_version).to_bytes(2, "little")
    if lnksta is not None:
        config_bytes[0x62:0x64] = int(lnksta).to_bytes(2, "little")
    make_device(bdf=bdf, config_bytes=config_bytes)
    return config_bytes


def test_link_disable_enable(sysfs_root, make_device):
    _make_pcie_device(make_device, "0000:00:10.0")
    addr = "0000:00:10.0"

    link.link_disable(addr, sysfs_root=str(sysfs_root))
    value = config.read_u16(addr, 0x60, sysfs_root=str(sysfs_root))
    assert value & 0x0010

    link.link_enable(addr, sysfs_root=str(sysfs_root))
    value = config.read_u16(addr, 0x60, sysfs_root=str(sysfs_root))
    assert not (value & 0x0010)


def test_retrain_link(sysfs_root, make_device):
    _make_pcie_device(make_device, "0000:00:11.0")
    addr = "0000:00:11.0"

    link.retrain_link(addr, sysfs_root=str(sysfs_root))
    value = config.read_u16(addr, 0x60, sysfs_root=str(sysfs_root))
    assert value & 0x0020


def test_set_target_link_speed(sysfs_root, make_device):
    config_bytes = bytearray(256)
    _make_pcie_device(
        make_device, "0000:00:12.0", config_bytes=config_bytes, pcie_version=0x0002
    )
    addr = "0000:00:12.0"

    link.set_target_link_speed(addr, 8.0, retrain=False, sysfs_root=str(sysfs_root))
    value = config.read_u16(addr, 0x80, sysfs_root=str(sysfs_root))
    assert (value & 0x000F) == 0x3

    link.set_target_link_speed(addr, 2, retrain=True, sysfs_root=str(sysfs_root))
    value = config.read_u16(addr, 0x80, sysfs_root=str(sysfs_root))
    assert (value & 0x000F) == 0x2
    lnkctl = config.read_u16(addr, 0x60, sysfs_root=str(sysfs_root))
    assert lnkctl & 0x0020


def test_link_status(sysfs_root, make_device):
    config_bytes = bytearray(256)
    _make_pcie_device(
        make_device, "0000:00:13.0", config_bytes=config_bytes, lnksta=0x0043
    )
    addr = "0000:00:13.0"

    status = link.read_link_status(addr, sysfs_root=str(sysfs_root))
    assert status["speed_code"] == 0x3
    assert status["speed_gtps"] == 8.0
    assert status["width"] == 0x4


def test_link_hot_reset_requires_bridge(sysfs_root, make_device):
    _make_pcie_device(make_device, "0000:00:14.0")
    addr = "0000:00:14.0"
    with pytest.raises(ValueRangeError):
        link.link_hot_reset(addr, sysfs_root=str(sysfs_root), delay_s=0)


def test_link_hot_reset_bridge(sysfs_root, make_device):
    config_bytes = bytearray(256)
    _make_pcie_device(
        make_device, "0000:00:15.0", config_bytes=config_bytes, header_type=0x01
    )
    addr = "0000:00:15.0"

    link.link_hot_reset(addr, sysfs_root=str(sysfs_root), delay_s=0)
    value = config.read_u16(addr, 0x3E, sysfs_root=str(sysfs_root))
    assert not (value & 0x0040)
