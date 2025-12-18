"""Device wrapper for PCI access."""

import os

from . import bar as bar_access
from . import config as config_access
from .errors import ResourceNotFoundError
from .sysfs import Sysfs
from .types import PciAddress


class _ConfigAccessor(object):
    def __init__(self, device):
        self._device = device

    def read(self, width, offset):
        return config_access.read(
            self._device.address, offset, width, sysfs_root=self._device.sysfs.root
        )

    def write(self, width, offset, value):
        config_access.write(
            self._device.address,
            offset,
            width,
            value,
            sysfs_root=self._device.sysfs.root,
        )


class PciDevice(object):
    """Represents a PCI device in sysfs."""

    def __init__(self, sysfs, addr):
        self.sysfs = sysfs or Sysfs()
        self._address = PciAddress.parse(addr)
        self._config = _ConfigAccessor(self)

    @property
    def address(self):
        return self._address

    @property
    def vendor_id(self):
        path = os.path.join(self.sysfs.device_dir(self._address), "vendor")
        return self.sysfs.read_hex_attr(path)

    @property
    def device_id(self):
        path = os.path.join(self.sysfs.device_dir(self._address), "device")
        return self.sysfs.read_hex_attr(path)

    @property
    def class_code(self):
        path = os.path.join(self.sysfs.device_dir(self._address), "class")
        try:
            return self.sysfs.read_hex_attr(path)
        except ResourceNotFoundError:
            return None

    @property
    def config(self):
        return self._config

    def bar(self, index):
        return bar_access.PciBar(self.sysfs, self._address, index)

    def cfg_read(self, width, offset):
        return config_access.read(
            self._address, offset, width, sysfs_root=self.sysfs.root
        )

    def cfg_write(self, width, offset, value):
        config_access.write(
            self._address, offset, width, value, sysfs_root=self.sysfs.root
        )

    def cfgrd8(self, offset):
        return self.cfg_read(1, offset)

    def cfgrd16(self, offset):
        return self.cfg_read(2, offset)

    def cfgrd32(self, offset):
        return self.cfg_read(4, offset)

    def cfgwr8(self, offset, value):
        self.cfg_write(1, offset, value)

    def cfgwr16(self, offset, value):
        self.cfg_write(2, offset, value)

    def cfgwr32(self, offset, value):
        self.cfg_write(4, offset, value)

    def bar_read(self, index, width, offset):
        return bar_access.read(
            self._address, index, offset, width, sysfs_root=self.sysfs.root
        )

    def bar_write(self, index, width, offset, value):
        bar_access.write(
            self._address, index, offset, width, value, sysfs_root=self.sysfs.root
        )

    def memrd8(self, index, offset):
        return self.bar_read(index, 1, offset)

    def memrd16(self, index, offset):
        return self.bar_read(index, 2, offset)

    def memrd32(self, index, offset):
        return self.bar_read(index, 4, offset)

    def memrd64(self, index, offset):
        return self.bar_read(index, 8, offset)

    def memwr8(self, index, offset, value):
        self.bar_write(index, 1, offset, value)

    def memwr16(self, index, offset, value):
        self.bar_write(index, 2, offset, value)

    def memwr32(self, index, offset, value):
        self.bar_write(index, 4, offset, value)

    def memwr64(self, index, offset, value):
        self.bar_write(index, 8, offset, value)

    def __repr__(self):
        return "PciDevice(%s)" % self._address.bdf

    def __str__(self):
        return self._address.bdf


Device = PciDevice


__all__ = ["Device", "PciDevice"]
