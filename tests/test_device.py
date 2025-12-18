from pypcie.device import PciDevice
from pypcie.discover import find_by_id
from pypcie.sysfs import Sysfs


def test_pcidevice_config_and_bar(sysfs_root, make_device):
    config_bytes = bytearray(64)
    config_bytes[0:4] = b"\x01\x02\x03\x04"
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
        bdf="0000:00:0a.0",
        vendor=0x1234,
        device=0x5678,
        config_bytes=config_bytes,
        resource_entries=resource_entries,
        resource_files={0: data},
    )

    sysfs = Sysfs(root=str(sysfs_root))
    addresses = find_by_id(0x1234, 0x5678, sysfs=sysfs)
    assert [addr.bdf for addr in addresses] == ["0000:00:0a.0"]

    dev = PciDevice(sysfs, addresses[0])
    assert dev.vendor_id == 0x1234
    assert dev.device_id == 0x5678
    assert dev.class_code is None

    assert dev.cfg_read(4, 0) == 0x04030201
    dev.cfg_write(2, 2, 0xBEEF)
    assert dev.cfg_read(2, 2) == 0xBEEF

    assert dev.bar_read(0, 4, 4) == 0x07060504
    dev.bar_write(0, 2, 2, 0xABCD)
    assert dev.bar_read(0, 2, 2) == 0xABCD

    bar = dev.bar(0)
    with bar.open():
        bar.write_u8(0, 0x5A)
        assert bar.read_u8(0) == 0x5A
