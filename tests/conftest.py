import os

import pytest


@pytest.fixture
def sysfs_root(tmp_path):
    root = tmp_path / "sys"
    devices = root / "bus" / "pci" / "devices"
    devices.mkdir(parents=True)
    return root


def create_device(
    sysfs_root,
    bdf,
    vendor=0x1234,
    device=0x5678,
    config_size=256,
    config_bytes=None,
    resource_entries=None,
    resource_files=None,
):
    dev_path = sysfs_root / "bus" / "pci" / "devices" / bdf
    dev_path.mkdir(parents=True)

    (dev_path / "vendor").write_text("0x%04x\n" % vendor)
    (dev_path / "device").write_text("0x%04x\n" % device)

    if config_bytes is None:
        config_bytes = bytes([0] * config_size)
    else:
        config_bytes = bytes(config_bytes)
    config_path = dev_path / "config"
    with open(str(config_path), "wb") as handle:
        handle.write(config_bytes)

    if resource_entries is None:
        resource_entries = [(0, 0, 0)] * 6
    resource_path = dev_path / "resource"
    with open(str(resource_path), "w") as handle:
        for start, end, flags in resource_entries:
            handle.write("0x%016x 0x%016x 0x%016x\n" % (start, end, flags))

    if resource_files:
        for bar, data in resource_files.items():
            res_path = dev_path / ("resource%d" % bar)
            with open(str(res_path), "wb") as handle:
                handle.write(bytes(data))

    return dev_path


@pytest.fixture
def make_device(sysfs_root):
    def _make(**kwargs):
        return create_device(sysfs_root, **kwargs)

    return _make
