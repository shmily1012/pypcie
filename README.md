# pcispace

pcispace is a lightweight Python 3.6+ library for PCI device discovery and
configuration access via sysfs. It provides helpers for parsing PCI BDF
addresses, scanning devices, reading/writing config space, and accessing BARs
using mmap with a file-based fallback for I/O resources.

## Features

- Parse and format PCI addresses (`0000:00:1f.6` or `00:1f.6`)
- Discover devices by vendor/device ID
- Read/write PCI config space (u8/u16/u32, u64 via two u32)
- Read/write BAR resources (MMIO mmap with I/O port fallback)
- CLI tool for basic inspection and access

## Installation

```bash
python setup.py install
```

## CLI

```bash
pcispace list
pcispace find --vendor 0x8086 --device 0x1234
pcispace cfg-read 0000:00:1f.6 0x0 16
pcispace cfg-write 0000:00:1f.6 0x4 32 0x12345678
pcispace bar-read 0000:00:1f.6 0 0x0 32
pcispace bar-write 0000:00:1f.6 0 0x4 16 0xabcd
pcispace dump-config 0000:00:1f.6
```

Use `--sysfs-root` to point at a custom sysfs tree for testing.

## Testing

```bash
pytest -q
```
