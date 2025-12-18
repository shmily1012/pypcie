from pcispace.discover import find_devices, list_devices


def test_list_devices(sysfs_root, make_device):
    make_device(bdf="0000:00:01.0", vendor=0x1111, device=0x2222)
    make_device(bdf="0000:00:02.0", vendor=0x3333, device=0x4444)
    devices = list_devices(sysfs_root=str(sysfs_root))
    bdfs = sorted([dev.bdf for dev in devices])
    assert bdfs == ["0000:00:01.0", "0000:00:02.0"]


def test_find_devices(sysfs_root, make_device):
    make_device(bdf="0000:00:03.0", vendor=0x8086, device=0x1234)
    make_device(bdf="0000:00:04.0", vendor=0x1234, device=0x5678)

    devices = find_devices(0x8086, None, sysfs_root=str(sysfs_root))
    assert [dev.bdf for dev in devices] == ["0000:00:03.0"]

    devices = find_devices("0x1234", "0x5678", sysfs_root=str(sysfs_root))
    assert [dev.bdf for dev in devices] == ["0000:00:04.0"]
