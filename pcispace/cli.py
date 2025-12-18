"""Command-line interface for pcispace."""

import argparse
import os
import sys

from . import bar as bar_access
from . import config as config_access
from .discover import find_by_id, list_devices
from .errors import (
    OutOfRangeError,
    PciError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValueRangeError,
)
from .sysfs import Sysfs
from .types import PciAddress


def _parse_int(value, name):
    try:
        return int(value, 0)
    except ValueError:
        raise ValueRangeError("invalid %s: %r" % (name, value))


def _parse_width_bytes(value):
    width = _parse_int(value, "width")
    if width <= 0:
        raise ValueRangeError("width must be positive")
    if width in (1, 2, 4, 8):
        return width
    if width in (8, 16, 32, 64):
        return width // 8
    raise ValueRangeError("width must be 8/16/32/64 bits or 1/2/4/8 bytes")


def _parse_non_negative(value, name):
    number = _parse_int(value, name)
    if number < 0:
        raise ValueRangeError("%s must be non-negative" % name)
    return number


def _parse_address(value):
    return PciAddress.parse(value)


def _get_sysfs(args):
    return Sysfs(root=args.sysfs_root) if args.sysfs_root else Sysfs()


def _cmd_list(args):
    sysfs = _get_sysfs(args)
    if args.vendor is None and args.device is None:
        devices = list_devices(sysfs=sysfs)
    else:
        devices = find_by_id(args.vendor, args.device, sysfs=sysfs)
    for dev in devices:
        print(dev.bdf)
    return 0


def _cmd_find(args):
    if args.vendor is None:
        raise ValueRangeError("find requires --vendor")
    sysfs = _get_sysfs(args)
    for dev in find_by_id(args.vendor, args.device, sysfs=sysfs):
        print(dev.bdf)
    return 0


def _cmd_cfg_read(args):
    value = config_access.read(
        args.bdf, args.offset, args.width, sysfs_root=args.sysfs_root
    )
    print("0x%0*x" % (args.width * 2, value))
    return 0


def _cmd_cfg_write(args):
    config_access.write(
        args.bdf, args.offset, args.width, args.value, sysfs_root=args.sysfs_root
    )
    return 0


def _cmd_bar_read(args):
    value = bar_access.read(
        args.bdf, args.bar, args.offset, args.width, sysfs_root=args.sysfs_root
    )
    print("0x%0*x" % (args.width * 2, value))
    return 0


def _cmd_bar_write(args):
    bar_access.write(
        args.bdf,
        args.bar,
        args.offset,
        args.width,
        args.value,
        sysfs_root=args.sysfs_root,
    )
    return 0


def _cmd_dump_config(args):
    sysfs = _get_sysfs(args)
    path = sysfs.config_path(args.bdf)
    start = args.start
    length = args.length
    if start < 0:
        raise OutOfRangeError("start must be non-negative")
    if length < 0:
        raise OutOfRangeError("length must be non-negative")
    try:
        fd = os.open(path, os.O_RDONLY)
    except FileNotFoundError as exc:
        raise ResourceNotFoundError(str(exc))
    except PermissionError as exc:
        raise PermissionDeniedError(str(exc))
    try:
        size = os.fstat(fd).st_size
        if start >= size:
            raise OutOfRangeError("start beyond config size")
        if start + length > size:
            length = size - start
        data = os.pread(fd, length, start)
    finally:
        os.close(fd)
    for row in range(0, len(data), 16):
        chunk = data[row : row + 16]
        hex_bytes = " ".join("%02x" % b for b in chunk)
        print("%04x: %s" % (start + row, hex_bytes))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="pcispace")
    parser.add_argument(
        "-r",
        "--sysfs-root",
        default=None,
        help="sysfs devices root (default: /sys/bus/pci/devices)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list PCI devices")
    list_parser.add_argument("--vendor", help="vendor id (hex or int)")
    list_parser.add_argument("--device", help="device id (hex or int)")

    find = subparsers.add_parser("find", help="find devices by vendor/device id")
    find.add_argument("--vendor", required=True, help="vendor id (hex or int)")
    find.add_argument("--device", help="device id (hex or int)")

    cfg_read = subparsers.add_parser("cfg-read", help="read config space")
    cfg_read.add_argument("--bdf", required=True, type=_parse_address)
    cfg_read.add_argument("--offset", required=True, type=lambda v: _parse_non_negative(v, "offset"))
    cfg_read.add_argument("--width", required=True, type=_parse_width_bytes)

    cfg_write = subparsers.add_parser("cfg-write", help="write config space")
    cfg_write.add_argument("--bdf", required=True, type=_parse_address)
    cfg_write.add_argument("--offset", required=True, type=lambda v: _parse_non_negative(v, "offset"))
    cfg_write.add_argument("--width", required=True, type=_parse_width_bytes)
    cfg_write.add_argument("--value", required=True, type=lambda v: _parse_int(v, "value"))

    bar_read = subparsers.add_parser("bar-read", help="read BAR space")
    bar_read.add_argument("--bdf", required=True, type=_parse_address)
    bar_read.add_argument("--bar", required=True, type=lambda v: _parse_non_negative(v, "bar"))
    bar_read.add_argument("--offset", required=True, type=lambda v: _parse_non_negative(v, "offset"))
    bar_read.add_argument("--width", required=True, type=_parse_width_bytes)

    bar_write = subparsers.add_parser("bar-write", help="write BAR space")
    bar_write.add_argument("--bdf", required=True, type=_parse_address)
    bar_write.add_argument("--bar", required=True, type=lambda v: _parse_non_negative(v, "bar"))
    bar_write.add_argument("--offset", required=True, type=lambda v: _parse_non_negative(v, "offset"))
    bar_write.add_argument("--width", required=True, type=_parse_width_bytes)
    bar_write.add_argument("--value", required=True, type=lambda v: _parse_int(v, "value"))

    dump_cfg = subparsers.add_parser("dump-config", help="dump config space")
    dump_cfg.add_argument("--bdf", required=True, type=_parse_address)
    dump_cfg.add_argument("--start", default=0, type=lambda v: _parse_non_negative(v, "start"))
    dump_cfg.add_argument(
        "--len",
        dest="length",
        default=256,
        type=lambda v: _parse_non_negative(v, "len"),
    )

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
        print("error: %s" % exc, file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
