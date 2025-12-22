import subprocess
import sys
from pathlib import Path

from pypcie import config


def _run_cli(args, cwd):
    cmd = [sys.executable, "-m", "pypcie.cli"] + args
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def test_cli_list_and_find(sysfs_root, make_device):
    make_device(bdf="0000:00:0b.0", vendor=0x1234, device=0x5678)
    make_device(bdf="0000:00:0c.0", vendor=0xABCD, device=0x1111)
    repo_root = Path(__file__).resolve().parents[1]

    result = _run_cli(["--sysfs-root", str(sysfs_root), "list"], cwd=str(repo_root))
    assert result.returncode == 0
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert lines == ["[RC] 0000:00:0b.0", "[RC] 0000:00:0c.0"]

    result = _run_cli(
        ["--sysfs-root", str(sysfs_root), "list", "--vendor", "0x1234"],
        cwd=str(repo_root),
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "[RC] 0000:00:0b.0"

    result = _run_cli(
        ["--sysfs-root", str(sysfs_root), "find", "--vendor", "0xabcd"],
        cwd=str(repo_root),
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0000:00:0c.0"


def test_cli_list_tree_view(sysfs_root):
    sys_root = sysfs_root.parents[2]
    devices_root = sys_root / "devices" / "pci0000:00"
    rp_bdf = "0000:00:1c.0"
    switch_bdf = "0000:01:00.0"
    endpoint_bdf = "0000:02:00.0"

    endpoint_real = devices_root / rp_bdf / switch_bdf / endpoint_bdf
    endpoint_real.mkdir(parents=True)
    rp_real = devices_root / rp_bdf
    switch_real = devices_root / rp_bdf / switch_bdf
    for path in (rp_real, switch_real, endpoint_real):
        (path / "vendor").write_text("0x8086\n")
        (path / "device").write_text("0x1234\n")

    (sysfs_root / rp_bdf).symlink_to(rp_real)
    (sysfs_root / switch_bdf).symlink_to(switch_real)
    (sysfs_root / endpoint_bdf).symlink_to(endpoint_real)

    repo_root = Path(__file__).resolve().parents[1]
    result = _run_cli(["--sysfs-root", str(sysfs_root), "list"], cwd=str(repo_root))
    assert result.returncode == 0
    lines = [line.rstrip() for line in result.stdout.splitlines() if line.strip()]
    assert lines == [
        "[RC] 0000:00:1c.0",
        "\\-- [SW] 0000:01:00.0",
        "    \\-- [EP] 0000:02:00.0",
    ]


def test_cli_cfg_bar_dump(sysfs_root, make_device):
    config_bytes = bytes(range(64))
    resource_entries = [
        (0x1000, 0x10FF, 0x00000200),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
    ]
    bar_data = bytes(range(256))
    make_device(
        bdf="0000:00:0d.0",
        vendor=0x8086,
        device=0x1234,
        config_bytes=config_bytes,
        resource_entries=resource_entries,
        resource_files={0: bar_data},
    )
    repo_root = Path(__file__).resolve().parents[1]
    base = ["--sysfs-root", str(sysfs_root)]

    result = _run_cli(
        base
        + [
            "cfg-read",
            "--bdf",
            "0000:00:0d.0",
            "--offset",
            "0x0",
            "--width",
            "32",
        ],
        cwd=str(repo_root),
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0x03020100"

    result = _run_cli(
        base
        + [
            "cfg-write",
            "--bdf",
            "0000:00:0d.0",
            "--offset",
            "0x2",
            "--width",
            "16",
            "--value",
            "0xbeef",
        ],
        cwd=str(repo_root),
    )
    assert result.returncode == 0

    result = _run_cli(
        base
        + [
            "cfg-read",
            "--bdf",
            "0000:00:0d.0",
            "--offset",
            "0x2",
            "--width",
            "16",
        ],
        cwd=str(repo_root),
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0xbeef"

    result = _run_cli(
        base
        + [
            "bar-read",
            "--bdf",
            "0000:00:0d.0",
            "--bar",
            "0",
            "--offset",
            "0x4",
            "--width",
            "32",
        ],
        cwd=str(repo_root),
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0x07060504"

    result = _run_cli(
        base
        + [
            "bar-write",
            "--bdf",
            "0000:00:0d.0",
            "--bar",
            "0",
            "--offset",
            "0x2",
            "--width",
            "16",
            "--value",
            "0xabcd",
        ],
        cwd=str(repo_root),
    )
    assert result.returncode == 0

    result = _run_cli(
        base
        + [
            "bar-read",
            "--bdf",
            "0000:00:0d.0",
            "--bar",
            "0",
            "--offset",
            "0x2",
            "--width",
            "16",
        ],
        cwd=str(repo_root),
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0xabcd"

    result = _run_cli(
        base + ["dump-config", "--bdf", "0000:00:0d.0", "--start", "0", "--len", "16"],
        cwd=str(repo_root),
    )
    assert result.returncode == 0
    first_line = result.stdout.splitlines()[0]
    assert first_line == "0000: 00 01 ef be 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f"


def test_cli_link_ops(sysfs_root, make_device):
    config_bytes = bytearray(256)
    config_bytes[0x06:0x08] = (0x0010).to_bytes(2, "little")
    config_bytes[0x0E] = 0x00
    config_bytes[0x34] = 0x50
    config_bytes[0x50] = 0x10
    config_bytes[0x51] = 0x00
    config_bytes[0x52:0x54] = (0x0002).to_bytes(2, "little")
    config_bytes[0x62:0x64] = (0x0043).to_bytes(2, "little")
    make_device(bdf="0000:00:0e.0", config_bytes=config_bytes)

    bridge_bytes = bytearray(256)
    bridge_bytes[0x0E] = 0x01
    make_device(bdf="0000:00:0f.0", config_bytes=bridge_bytes)

    repo_root = Path(__file__).resolve().parents[1]
    base = ["--sysfs-root", str(sysfs_root)]

    result = _run_cli(
        base + ["link-status", "--bdf", "0000:00:0e.0"], cwd=str(repo_root)
    )
    assert result.returncode == 0
    assert (
        result.stdout.strip()
        == "speed=8.0GT/s width=x4 training=0 dll_link_active=0"
    )

    result = _run_cli(
        base + ["link-disable", "--bdf", "0000:00:0e.0"], cwd=str(repo_root)
    )
    assert result.returncode == 0
    value = config.read_u16("0000:00:0e.0", 0x60, sysfs_root=str(sysfs_root))
    assert value & 0x0010

    result = _run_cli(
        base
        + ["link-set-speed", "--bdf", "0000:00:0e.0", "--speed", "8.0", "--no-retrain"],
        cwd=str(repo_root),
    )
    assert result.returncode == 0
    value = config.read_u16("0000:00:0e.0", 0x80, sysfs_root=str(sysfs_root))
    assert (value & 0x000F) == 0x3

    result = _run_cli(
        base + ["link-hot-reset", "--bdf", "0000:00:0f.0", "--delay-ms", "0"],
        cwd=str(repo_root),
    )
    assert result.returncode == 0


def test_cli_link_uses_root_port(sysfs_root):
    sys_root = sysfs_root.parents[2]
    devices_root = sys_root / "devices" / "pci0000:00"
    rp_bdf = "0000:00:1c.0"
    ep_bdf = "0000:01:00.0"

    rp_real = devices_root / rp_bdf
    ep_real = devices_root / rp_bdf / ep_bdf
    rp_real.mkdir(parents=True)
    ep_real.mkdir(parents=True)

    rp_config = bytearray(256)
    rp_config[0x06:0x08] = (0x0010).to_bytes(2, "little")
    rp_config[0x0E] = 0x01
    rp_config[0x34] = 0x50
    rp_config[0x50] = 0x10
    rp_config[0x51] = 0x00
    rp_config[0x62:0x64] = (0x0012).to_bytes(2, "little")
    (rp_real / "vendor").write_text("0x8086\n")
    (rp_real / "device").write_text("0x1234\n")
    with open(str(rp_real / "config"), "wb") as handle:
        handle.write(rp_config)

    ep_config = bytearray(256)
    (ep_real / "vendor").write_text("0x1234\n")
    (ep_real / "device").write_text("0x5678\n")
    with open(str(ep_real / "config"), "wb") as handle:
        handle.write(ep_config)

    (sysfs_root / rp_bdf).symlink_to(rp_real)
    (sysfs_root / ep_bdf).symlink_to(ep_real)

    repo_root = Path(__file__).resolve().parents[1]
    result = _run_cli(
        ["--sysfs-root", str(sysfs_root), "link-status", "--bdf", ep_bdf],
        cwd=str(repo_root),
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "speed=5.0GT/s width=x1 training=0 dll_link_active=0"
