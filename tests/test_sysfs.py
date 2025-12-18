import os

import pytest

from pcispace.errors import OutOfRangeError, ResourceNotFoundError, SysfsFormatError
from pcispace.sysfs import Sysfs


def test_sysfs_paths(sysfs_root, make_device):
    make_device(bdf="0000:00:01.0")
    sysfs = Sysfs(root=str(sysfs_root))

    device_dir = sysfs.device_dir("0000:00:01.0")
    assert device_dir == os.path.join(str(sysfs_root), "0000:00:01.0")
    assert sysfs.config_path("0000:00:01.0") == os.path.join(device_dir, "config")
    assert sysfs.resource_path("0000:00:01.0", 2) == os.path.join(device_dir, "resource2")


def test_sysfs_read_hex_attr(sysfs_root, make_device):
    make_device(bdf="0000:00:02.0", vendor=0x1A2B, device=0x3C4D)
    sysfs = Sysfs(root=str(sysfs_root))

    vendor_path = os.path.join(str(sysfs_root), "0000:00:02.0", "vendor")
    assert sysfs.read_hex_attr(vendor_path) == 0x1A2B

    missing_path = os.path.join(str(sysfs_root), "0000:00:02.0", "missing")
    with pytest.raises(ResourceNotFoundError):
        sysfs.read_hex_attr(missing_path)

    bad_path = os.path.join(str(sysfs_root), "0000:00:02.0", "bad")
    with open(bad_path, "w") as handle:
        handle.write("not-hex\n")
    with pytest.raises(SysfsFormatError):
        sysfs.read_hex_attr(bad_path)


def test_sysfs_resource_path_validation(sysfs_root):
    sysfs = Sysfs(root=str(sysfs_root))
    with pytest.raises(OutOfRangeError):
        sysfs.resource_path("0000:00:00.0", -1)
