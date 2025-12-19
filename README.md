# pypcie

## Overview

pypcie is a small Python 3.6+ library and CLI for working with PCI devices via
Linux sysfs. It provides:

- PCI BDF parsing (`0000:03:00.0`)
- Device discovery by vendor/device ID
- Config space read/write (u8/u16/u32/u64)
- BAR access with mmap for MMIO and file I/O for I/O port BARs
- A CLI for quick inspection and scripting

## Requirements and permissions

- Linux with `/sys/bus/pci/devices` available
- Python 3.6+
- Most reads work as an unprivileged user, but writes often require root or
  CAP_SYS_ADMIN / CAP_SYS_RAWIO depending on kernel and device policy.
- Even reads may be restricted for some devices.

## Installation

```bash
pip install pypcie
```

Editable install for development:

```bash
pip install -e .
```

## Python usage examples

Discovery:

```python
from pypcie.discover import list_devices, find_by_id, find_root_port
from pypcie.sysfs import Sysfs

sysfs = Sysfs()
for addr in list_devices(sysfs=sysfs):
    print(addr.bdf)

matches = find_by_id(0x8086, 0x1234, sysfs=sysfs)
print([addr.bdf for addr in matches])

root_port = find_root_port("0000:02:00.0", sysfs=sysfs)
print(root_port.bdf)
```

Config read/write:

```python
from pypcie import config

bdf = "0000:03:00.0"
value = config.read_u32(bdf, 0x10)
print(hex(value))

config.write_u16(bdf, 0x04, 0x0007)
```

BAR read/write:

```python
from pypcie import bar

bdf = "0000:03:00.0"
value = bar.read_u32(bdf, 0, 0x100)
print(hex(value))

bar.write_u32(bdf, 0, 0x104, 0xdeadbeef)
```

Device wrapper:

```python
from pypcie.device import PciDevice
from pypcie.sysfs import Sysfs

sysfs = Sysfs()
device = PciDevice(sysfs, "0000:03:00.0")
print(hex(device.vendor_id))
print(hex(device.device_id))

value = device.cfg_read(4, 0x10)
print(hex(value))

bar0 = device.bar(0)
with bar0.open():
    print(hex(bar0.read_u32(0x100)))
```

## CLI examples

List devices:

```bash
pypcie list
# [RC] 0000:00:00.0
# \-- [EP] 0000:03:00.0
```

Filter by vendor/device:

```bash
pypcie list --vendor 0x8086
# [RC] 0000:00:1f.6
# [RC] 0000:00:1f.2

pypcie find --vendor 0x8086 --device 0x1234
# 0000:03:00.0
```

`pypcie list` renders a simple ASCII tree: root-complex ports are tagged `[RC]`,
intermediate bridges/switches `[SW]`, and leaves `[EP]`.

Config access:

```bash
pypcie cfg-read --bdf 0000:03:00.0 --offset 0x10 --width 32
# 0x00000007

pypcie cfg-write --bdf 0000:03:00.0 --offset 0x04 --width 16 --value 0x0007
```

BAR access:

```bash
pypcie bar-read --bdf 0000:03:00.0 --bar 0 --offset 0x100 --width 32
# 0xdeadbeef

pypcie bar-write --bdf 0000:03:00.0 --bar 0 --offset 0x104 --width 32 --value 0x00000001
```

Config dump:

```bash
pypcie dump-config --bdf 0000:03:00.0 --start 0 --len 64
# 0000: 86 80 34 12 07 00 10 00 01 00 00 00 00 00 00 00
# 0010: ...
```

Use `--sysfs-root` to point to a custom sysfs tree (useful for tests).

## Safety warnings

Writing to config space or BARs can crash hardware, lock up the system, or
corrupt data. Only write when you understand the device behavior and have a
recovery plan. Use read-only operations whenever possible.

## Testing

```bash
pytest -q
```

## License

MIT
