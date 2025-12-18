import pytest

from pypcie.discover import (
    find_by_id,
    find_one_by_id,
    get_device_info,
    list_devices,
)
from pypcie.errors import DeviceNotFoundError, MultipleDevicesFoundError
from pypcie.sysfs import Sysfs


def test_list_devices(sysfs_root, make_device):
    make_device(bdf="0000:00:01.0", vendor=0x1111, device=0x2222)
    make_device(bdf="0000:00:02.0", vendor=0x3333, device=0x4444)

    sysfs = Sysfs(root=str(sysfs_root))
    devices = list_devices(sysfs=sysfs)
    bdfs = sorted([dev.bdf for dev in devices])
    assert bdfs == ["0000:00:01.0", "0000:00:02.0"]


def test_get_device_info(sysfs_root, make_device):
    make_device(
        bdf="0000:00:03.0",
        vendor=0x8086,
        device=0x1234,
        resource_entries=[(0, 0, 0)] * 6,
    )
    dev_path = sysfs_root / "0000:00:03.0"
    (dev_path / "subsystem_vendor").write_text("0x1af4\n")
    (dev_path / "subsystem_device").write_text("0x1000\n")
    (dev_path / "class").write_text("0x010802\n")

    sysfs = Sysfs(root=str(sysfs_root))
    info = get_device_info("0000:00:03.0", sysfs=sysfs)
    assert info["vendor"] == 0x8086
    assert info["device"] == 0x1234
    assert info["subsystem_vendor"] == 0x1AF4
    assert info["subsystem_device"] == 0x1000
    assert info["class"] == 0x010802


def test_find_by_id(sysfs_root, make_device):
    make_device(bdf="0000:00:04.0", vendor=0x8086, device=0x1234)
    make_device(bdf="0000:00:05.0", vendor=0x1234, device=0x5678)
    make_device(bdf="0000:00:06.0", vendor=0x8086, device=0x9999)

    sysfs = Sysfs(root=str(sysfs_root))
    devices = find_by_id(0x8086, sysfs=sysfs)
    assert sorted([dev.bdf for dev in devices]) == ["0000:00:04.0", "0000:00:06.0"]

    devices = find_by_id("0x1234", "0x5678", sysfs=sysfs)
    assert [dev.bdf for dev in devices] == ["0000:00:05.0"]


def test_find_one_by_id(sysfs_root, make_device):
    make_device(bdf="0000:00:07.0", vendor=0x8086, device=0x1234)
    make_device(bdf="0000:00:08.0", vendor=0x8086, device=0x1234)

    sysfs = Sysfs(root=str(sysfs_root))
    with pytest.raises(MultipleDevicesFoundError):
        find_one_by_id(0x8086, 0x1234, sysfs=sysfs)

    with pytest.raises(DeviceNotFoundError):
        find_one_by_id(0xDEAD, 0xBEEF, sysfs=sysfs)
