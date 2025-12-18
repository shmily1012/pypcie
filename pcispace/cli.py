"""Command-line interface for pcispace."""

import argparse
import os
import sys

from . import bar as bar_access
from . import config as config_access
from .discover import find_devices, list_devices
from .errors import PciError, ValidationError
from .sysfs import device_path
from .types import PciAddress


def _parse_int(value, name):
    try:
        return int(value, 0)
    except ValueError:
        raise ValidationError("invalid %s: %r" % (name, value))


def _parse_width(value):
    width = _parse_int(value, "width")
    if width in (1, 2, 4, 8):
        return width
    if width in (8, 16, 32, 64):
        return width // 8
    raise ValidationError("width must be 1,2,4,8 bytes or 8,16,32,64 bits")


def _parse_bar(value):
    bar = _parse_int(value, "bar")
    if bar < 0:
        raise ValidationError("bar must be non-negative")
    return bar


def _parse_address(value):
    return PciAddress.parse(value)


def _cmd_list(args):
    for dev in list_devices(sysfs_root=args.sysfs_root):
        print(dev.bdf)
    return 0


def _cmd_find(args):
    if args.vendor is None and args.device is None:
        raise ValidationError("find requires --vendor or --device")
    for dev in find_devices(args.vendor, args.device, sysfs_root=args.sysfs_root):
        print(dev.bdf)
    return 0


def _cmd_cfg_read(args):
    value = config_access.read(args.address, args.offset, args.width, sysfs_root=args.sysfs_root)
    print("0x%0*x" % (args.width * 2, value))
    return 0


def _cmd_cfg_write(args):
    config_access.write(args.address, args.offset, args.width, args.value, sysfs_root=args.sysfs_root)
    return 0


def _cmd_bar_read(args):
    value = bar_access.read(args.address, args.bar, args.offset, args.width, sysfs_root=args.sysfs_root)
    print("0x%0*x" % (args.width * 2, value))
    return 0


def _cmd_bar_write(args):
    bar_access.write(args.address, args.bar, args.offset, args.width, args.value, sysfs_root=args.sysfs_root)
    return 0


def _cmd_dump_config(args):
    addr = args.address
    path = device_path(addr, args.sysfs_root)
    config_path = path + "/config"
    try:
        size = os.stat(config_path).st_size
    except Exception:
        size = 256
    data = bytearray()
    offset = 0
    while offset < size:
        chunk = config_access.read(addr, offset, 1, sysfs_root=args.sysfs_root)
        data.append(chunk)
        offset += 1
    for row in range(0, len(data), 16):
        slice_ = data[row : row + 16]
        hex_bytes = " ".join("%02x" % b for b in slice_)
        print("%04x: %s" % (row, hex_bytes))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="pcispace")
    parser.add_argument("-r", "--sysfs-root", default=None, help="override sysfs root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="list PCI devices")

    find = subparsers.add_parser("find", help="find devices by vendor/device id")
    find.add_argument("--vendor", "-v", help="vendor id (hex or int)")
    find.add_argument("--device", "-d", help="device id (hex or int)")

    cfg_read = subparsers.add_parser("cfg-read", help="read config space")
    cfg_read.add_argument("address", type=_parse_address)
    cfg_read.add_argument("offset", type=lambda v: _parse_int(v, "offset"))
    cfg_read.add_argument("width", type=_parse_width)

    cfg_write = subparsers.add_parser("cfg-write", help="write config space")
    cfg_write.add_argument("address", type=_parse_address)
    cfg_write.add_argument("offset", type=lambda v: _parse_int(v, "offset"))
    cfg_write.add_argument("width", type=_parse_width)
    cfg_write.add_argument("value", type=lambda v: _parse_int(v, "value"))

    bar_read = subparsers.add_parser("bar-read", help="read BAR space")
    bar_read.add_argument("address", type=_parse_address)
    bar_read.add_argument("bar", type=_parse_bar)
    bar_read.add_argument("offset", type=lambda v: _parse_int(v, "offset"))
    bar_read.add_argument("width", type=_parse_width)

    bar_write = subparsers.add_parser("bar-write", help="write BAR space")
    bar_write.add_argument("address", type=_parse_address)
    bar_write.add_argument("bar", type=_parse_bar)
    bar_write.add_argument("offset", type=lambda v: _parse_int(v, "offset"))
    bar_write.add_argument("width", type=_parse_width)
    bar_write.add_argument("value", type=lambda v: _parse_int(v, "value"))

    dump_cfg = subparsers.add_parser("dump-config", help="dump config space")
    dump_cfg.add_argument("address", type=_parse_address)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            return _cmd_list(args)
        if args.command == "find":
            return _cmd_find(args)
        if args.command == "cfg-read":
            return _cmd_cfg_read(args)
        if args.command == "cfg-write":
            return _cmd_cfg_write(args)
        if args.command == "bar-read":
            return _cmd_bar_read(args)
        if args.command == "bar-write":
            return _cmd_bar_write(args)
        if args.command == "dump-config":
            return _cmd_dump_config(args)
    except PciError as exc:
        parser.error(str(exc))
    return 1


if __name__ == "__main__":
    sys.exit(main())
