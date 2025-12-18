"""Device wrapper for PCI access."""

import os

from . import bar as bar_access
from . import config as config_access
from .errors import SysfsError
from .sysfs import device_path, read_hex_file
from .types import PciAddress


class Device(object):
    """Represents a PCI device in sysfs."""

    def __init__(self, address, sysfs_root=None):
        self.address = PciAddress.parse(address)
        self.sysfs_root = sysfs_root

    @property
    def bdf(self):
        return self.address.bdf

    @property
    def path(self):
        return device_path(self.address, self.sysfs_root)

    def vendor_id(self):
        return read_hex_file(os.path.join(self.path, "vendor"))

    def device_id(self):
        return read_hex_file(os.path.join(self.path, "device"))

    def read_config(self, offset, width):
        return config_access.read(self.address, offset, width, sysfs_root=self.sysfs_root)

    def write_config(self, offset, width, value):
        config_access.write(self.address, offset, width, value, sysfs_root=self.sysfs_root)

    def read_bar(self, bar, offset, width):
        return bar_access.read(self.address, bar, offset, width, sysfs_root=self.sysfs_root)

    def write_bar(self, bar, offset, width, value):
        bar_access.write(self.address, bar, offset, width, value, sysfs_root=self.sysfs_root)

    def exists(self):
        return os.path.isdir(self.path)

    def __repr__(self):
        return "Device(%s)" % self.bdf

    def __str__(self):
        return self.bdf
