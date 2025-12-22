from pypcie import capability


def test_find_pci_capability(sysfs_root, make_device):
    config_bytes = bytearray(256)
    config_bytes[0x06:0x08] = (0x0010).to_bytes(2, "little")
    config_bytes[0x0E] = 0x00
    config_bytes[0x34] = 0x50
    config_bytes[0x50] = 0x01
    config_bytes[0x51] = 0x60
    config_bytes[0x60] = 0x10
    config_bytes[0x61] = 0x00
    make_device(bdf="0000:00:01.0", config_bytes=config_bytes)

    addr = "0000:00:01.0"
    assert (
        capability.find_pci_capability(addr, 0x01, sysfs_root=str(sysfs_root))
        == 0x50
    )
    assert (
        capability.find_pci_capability(addr, 0x10, sysfs_root=str(sysfs_root))
        == 0x60
    )
    assert capability.find_pcie_capability(addr, sysfs_root=str(sysfs_root)) == 0x60
    assert (
        capability.find_pci_capability(addr, 0x05, sysfs_root=str(sysfs_root))
        == 0
    )


def test_find_ext_capability(sysfs_root, make_device):
    config_bytes = bytearray(0x1000)
    header_one = (0x200 << 20) | (1 << 16) | 0x0010
    header_two = (0x000 << 20) | (1 << 16) | 0x0001
    config_bytes[0x100:0x104] = header_one.to_bytes(4, "little")
    config_bytes[0x200:0x204] = header_two.to_bytes(4, "little")
    make_device(bdf="0000:00:02.0", config_bytes=config_bytes)

    addr = "0000:00:02.0"
    assert (
        capability.find_ext_capability(addr, 0x0001, sysfs_root=str(sysfs_root))
        == 0x200
    )
    assert (
        capability.find_pcie_ext_capability(addr, 0x0001, sysfs_root=str(sysfs_root))
        == 0x200
    )
    assert (
        capability.find_ext_capability(addr, 0x1234, sysfs_root=str(sysfs_root))
        == 0
    )


def test_find_ext_capability_short_config(sysfs_root, make_device):
    make_device(bdf="0000:00:03.0", config_bytes=bytearray(256))
    addr = "0000:00:03.0"
    assert capability.find_ext_capability(addr, 0x0001, sysfs_root=str(sysfs_root)) == 0
