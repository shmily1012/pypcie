"""Command-line interface for pypcie."""

import argparse
import os
import sys

from . import bar as bar_access
from . import link as link_access
from . import config as config_access
from .discover import build_device_tree, find_by_id, find_root_port
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


def _resolve_link_target(args):
    if getattr(args, "port_bdf", None) is not None:
        return args.port_bdf
    if getattr(args, "endpoint", False):
        return args.bdf
    return find_root_port(args.bdf, sysfs=_get_sysfs(args))


def _should_display(node, children, matched, cache):
    if matched is None:
        return True
    if node in cache:
        return cache[node]
    if node in matched:
        cache[node] = True
        return True
    for child in children.get(node, []):
        if _should_display(child, children, matched, cache):
            cache[node] = True
            return True
    cache[node] = False
    return False


def _render_tree(sysfs, vendor=None, device=None):
    roots, children = build_device_tree(sysfs=sysfs)
    matched = None
    if vendor is not None or device is not None:
        matched = set(find_by_id(vendor, device, sysfs=sysfs))
    root_set = set(roots)
    cache = {}
    lines = []

    def render(node, prefix, has_parent, is_last):
        display_children = [
            child
            for child in children.get(node, [])
            if _should_display(child, children, matched, cache)
        ]
        role = "RC" if node in root_set else ("SW" if display_children else "EP")
        connector = ""
        if has_parent:
            connector = "\\-- " if is_last else "|-- "
        lines.append(prefix + connector + "[%s] %s" % (role, node.bdf))
        child_prefix = prefix
        if has_parent:
            child_prefix += "    " if is_last else "|   "
        for idx, child in enumerate(display_children):
            render(child, child_prefix, True, idx == len(display_children) - 1)

    for idx, root in enumerate(roots):
        if not _should_display(root, children, matched, cache):
            continue
        render(root, "", False, idx == len(roots) - 1)
    return lines


def _cmd_list(args):
    sysfs = _get_sysfs(args)
    tree_lines = _render_tree(sysfs, vendor=args.vendor, device=args.device)
    for line in tree_lines:
        print(line)
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


def _cmd_link_disable(args):
    target = _resolve_link_target(args)
    link_access.link_disable(target, sysfs_root=args.sysfs_root)
    return 0


def _cmd_link_enable(args):
    target = _resolve_link_target(args)
    link_access.link_enable(target, sysfs_root=args.sysfs_root)
    return 0


def _cmd_link_retrain(args):
    target = _resolve_link_target(args)
    link_access.retrain_link(
        target, sysfs_root=args.sysfs_root, clear_after=args.clear_after
    )
    return 0


def _cmd_link_status(args):
    target = _resolve_link_target(args)
    status = link_access.read_link_status(target, sysfs_root=args.sysfs_root)
    speed = status["speed_gtps"]
    if speed is None:
        speed_text = "unknown(0x%x)" % status["speed_code"]
    else:
        speed_text = "%sGT/s" % speed
    print(
        "speed=%s width=x%d training=%d dll_link_active=%d"
        % (
            speed_text,
            status["width"],
            int(status["training"]),
            int(status["dll_link_active"]),
        )
    )
    return 0


def _cmd_link_set_speed(args):
    target = _resolve_link_target(args)
    link_access.set_target_link_speed(
        target,
        args.speed,
        retrain=not args.no_retrain,
        sysfs_root=args.sysfs_root,
    )
    return 0


def _cmd_link_hot_reset(args):
    target = _resolve_link_target(args)
    delay_s = args.delay_ms / 1000.0 if args.delay_ms is not None else 0.002
    link_access.link_hot_reset(target, sysfs_root=args.sysfs_root, delay_s=delay_s)
    return 0


def _cmd_link_wait(args):
    target = _resolve_link_target(args)
    ok = link_access.wait_for_link_training(
        target,
        timeout_s=args.timeout,
        poll_s=args.poll,
        sysfs_root=args.sysfs_root,
    )
    if ok:
        return 0
    print("error: link training did not complete before timeout", file=sys.stderr)
    return 1


def _cmd_link_control(args):
    target = _resolve_link_target(args)
    link_access.set_link_control_bits(
        target,
        args.mask,
        enable=not args.disable,
        sysfs_root=args.sysfs_root,
    )
    return 0


def _add_link_target_args(parser):
    parser.add_argument("--bdf", required=True, type=_parse_address)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--endpoint",
        action="store_true",
        help="operate on the endpoint BDF instead of the upstream root port",
    )
    group.add_argument(
        "--port-bdf",
        type=_parse_address,
        help="override target port BDF (root/downstream port)",
    )


def build_parser():
    parser = argparse.ArgumentParser(prog="pypcie")
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

    link_disable = subparsers.add_parser("link-disable", help="disable PCIe link")
    _add_link_target_args(link_disable)

    link_enable = subparsers.add_parser("link-enable", help="enable PCIe link")
    _add_link_target_args(link_enable)

    link_retrain = subparsers.add_parser("link-retrain", help="retrain PCIe link")
    _add_link_target_args(link_retrain)
    link_retrain.add_argument(
        "--clear-after",
        action="store_true",
        help="clear retrain bit after setting it",
    )

    link_status = subparsers.add_parser("link-status", help="read PCIe link status")
    _add_link_target_args(link_status)

    link_set_speed = subparsers.add_parser(
        "link-set-speed", help="set target PCIe link speed"
    )
    _add_link_target_args(link_set_speed)
    link_set_speed.add_argument(
        "--speed",
        required=True,
        help="target speed (2.5/5/8/16/32/64 or TLS code)",
    )
    link_set_speed.add_argument(
        "--no-retrain",
        action="store_true",
        help="do not request retraining after setting speed",
    )

    link_hot_reset = subparsers.add_parser(
        "link-hot-reset", help="toggle secondary bus reset on bridges"
    )
    _add_link_target_args(link_hot_reset)
    link_hot_reset.add_argument(
        "--delay-ms",
        type=lambda v: _parse_non_negative(v, "delay-ms"),
        default=2,
        help="delay between assert/deassert (milliseconds)",
    )

    link_wait = subparsers.add_parser(
        "link-wait", help="wait for PCIe link training to complete"
    )
    _add_link_target_args(link_wait)
    link_wait.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="timeout in seconds (default: 1.0)",
    )
    link_wait.add_argument(
        "--poll",
        type=float,
        default=0.01,
        help="poll interval in seconds (default: 0.01)",
    )

    link_control = subparsers.add_parser(
        "link-control", help="set or clear PCIe link control bits"
    )
    _add_link_target_args(link_control)
    link_control.add_argument(
        "--mask",
        required=True,
        type=lambda v: _parse_int(v, "mask"),
        help="bit mask to set/clear (hex or int)",
    )
    link_control.add_argument(
        "--disable",
        action="store_true",
        help="clear mask bits instead of setting",
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
        if args.command == "link-disable":
            return _cmd_link_disable(args)
        if args.command == "link-enable":
            return _cmd_link_enable(args)
        if args.command == "link-retrain":
            return _cmd_link_retrain(args)
        if args.command == "link-status":
            return _cmd_link_status(args)
        if args.command == "link-set-speed":
            return _cmd_link_set_speed(args)
        if args.command == "link-hot-reset":
            return _cmd_link_hot_reset(args)
        if args.command == "link-wait":
            return _cmd_link_wait(args)
        if args.command == "link-control":
            return _cmd_link_control(args)
    except PciError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
