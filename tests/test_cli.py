import subprocess
import sys
from pathlib import Path


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
