"""PCIe link control helpers."""

import time

from . import config
from .capability import find_pcie_capability
from .errors import ResourceNotFoundError, ValueRangeError
from .types import validate_u16

PCI_EXP_FLAGS = 0x02
PCI_EXP_LNKCTL = 0x10
PCI_EXP_LNKCTL_LD = 0x0010
PCI_EXP_LNKCTL_RL = 0x0020
PCI_EXP_LNKSTA = 0x12
PCI_EXP_LNKSTA_CLS = 0x000F
PCI_EXP_LNKSTA_NLW = 0x03F0
PCI_EXP_LNKSTA_NLW_SHIFT = 4
PCI_EXP_LNKSTA_LT = 0x0800
PCI_EXP_LNKSTA_DLLLA = 0x2000
PCI_EXP_LNKCTL2 = 0x30
PCI_EXP_LNKCTL2_TLS = 0x000F
PCI_BRIDGE_CONTROL = 0x3E
PCI_BRIDGE_CTL_BUS_RESET = 0x0040
PCI_HEADER_TYPE = 0x0E
PCI_HEADER_TYPE_MASK = 0x7F
PCI_HEADER_TYPE_BRIDGE = 0x01

_LINK_SPEED_TO_TLS = {
    2.5: 0x1,
    5.0: 0x2,
    8.0: 0x3,
    16.0: 0x4,
    32.0: 0x5,
    64.0: 0x6,
}
_TLS_TO_LINK_SPEED = {value: key for key, value in _LINK_SPEED_TO_TLS.items()}


def _pcie_cap_base(address, sysfs_root=None):
    base = find_pcie_capability(address, sysfs_root=sysfs_root)
    if not base:
        raise ResourceNotFoundError("PCIe capability not found")
    return base


def _pcie_cap_version(address, base, sysfs_root=None):
    flags = config.read_u16(address, base + PCI_EXP_FLAGS, sysfs_root=sysfs_root)
    return flags & 0xF


def _update_link_control(address, mask, enable, sysfs_root=None):
    base = _pcie_cap_base(address, sysfs_root=sysfs_root)
    value = config.read_u16(address, base + PCI_EXP_LNKCTL, sysfs_root=sysfs_root)
    if enable:
        value |= mask
    else:
        value &= ~mask
    config.write_u16(address, base + PCI_EXP_LNKCTL, value, sysfs_root=sysfs_root)
    return value


def link_disable(address, sysfs_root=None):
    """Disable the PCIe link by setting the Link Disable bit."""
    return _update_link_control(address, PCI_EXP_LNKCTL_LD, True, sysfs_root=sysfs_root)


def link_enable(address, sysfs_root=None):
    """Enable the PCIe link by clearing the Link Disable bit."""
    return _update_link_control(address, PCI_EXP_LNKCTL_LD, False, sysfs_root=sysfs_root)


def retrain_link(address, sysfs_root=None, clear_after=False):
    """Request link retraining by setting the Retrain Link bit."""
    value = _update_link_control(address, PCI_EXP_LNKCTL_RL, True, sysfs_root=sysfs_root)
    if clear_after:
        value = _update_link_control(
            address, PCI_EXP_LNKCTL_RL, False, sysfs_root=sysfs_root
        )
    return value


def _normalize_target_speed(speed):
    if isinstance(speed, str):
        try:
            if "." in speed:
                speed = float(speed)
            else:
                speed = int(speed, 0)
        except ValueError:
            raise ValueRangeError("invalid target link speed: %r" % speed)
    if isinstance(speed, float) and speed.is_integer():
        speed = int(speed)
    if speed in _LINK_SPEED_TO_TLS:
        return _LINK_SPEED_TO_TLS[speed]
    if isinstance(speed, int) and speed in _TLS_TO_LINK_SPEED:
        return speed
    raise ValueRangeError("unsupported target link speed: %r" % speed)


def set_target_link_speed(address, speed, retrain=True, sysfs_root=None):
    """Set Target Link Speed (LNKCTL2) and optionally retrain."""
    base = _pcie_cap_base(address, sysfs_root=sysfs_root)
    if _pcie_cap_version(address, base, sysfs_root=sysfs_root) < 2:
        raise ValueRangeError("link control 2 not supported by PCIe capability")
    tls = _normalize_target_speed(speed)
    value = config.read_u16(address, base + PCI_EXP_LNKCTL2, sysfs_root=sysfs_root)
    value = (value & ~PCI_EXP_LNKCTL2_TLS) | tls
    config.write_u16(address, base + PCI_EXP_LNKCTL2, value, sysfs_root=sysfs_root)
    if retrain:
        retrain_link(address, sysfs_root=sysfs_root)
    return value


def read_link_status(address, sysfs_root=None):
    """Return decoded Link Status fields."""
    base = _pcie_cap_base(address, sysfs_root=sysfs_root)
    status = config.read_u16(address, base + PCI_EXP_LNKSTA, sysfs_root=sysfs_root)
    speed_code = status & PCI_EXP_LNKSTA_CLS
    width = (status & PCI_EXP_LNKSTA_NLW) >> PCI_EXP_LNKSTA_NLW_SHIFT
    return {
        "speed_code": speed_code,
        "speed_gtps": _TLS_TO_LINK_SPEED.get(speed_code),
        "width": width,
        "training": bool(status & PCI_EXP_LNKSTA_LT),
        "dll_link_active": bool(status & PCI_EXP_LNKSTA_DLLLA),
    }


def wait_for_link_training(address, timeout_s=1.0, poll_s=0.01, sysfs_root=None):
    """Wait until the Link Training bit clears; return True if it does."""
    timeout_s = float(timeout_s)
    poll_s = float(poll_s)
    deadline = time.monotonic() + timeout_s
    base = _pcie_cap_base(address, sysfs_root=sysfs_root)
    while time.monotonic() < deadline:
        status = config.read_u16(address, base + PCI_EXP_LNKSTA, sysfs_root=sysfs_root)
        if not (status & PCI_EXP_LNKSTA_LT):
            return True
        time.sleep(poll_s)
    return False


def link_hot_reset(address, sysfs_root=None, delay_s=0.002):
    """Trigger a hot reset via the secondary bus reset bit on bridges."""
    hdr = config.read_u8(address, PCI_HEADER_TYPE, sysfs_root=sysfs_root)
    if (hdr & PCI_HEADER_TYPE_MASK) != PCI_HEADER_TYPE_BRIDGE:
        raise ValueRangeError("secondary bus reset requires a bridge device")
    ctrl = config.read_u16(address, PCI_BRIDGE_CONTROL, sysfs_root=sysfs_root)
    config.write_u16(
        address,
        PCI_BRIDGE_CONTROL,
        ctrl | PCI_BRIDGE_CTL_BUS_RESET,
        sysfs_root=sysfs_root,
    )
    if delay_s:
        time.sleep(float(delay_s))
    config.write_u16(
        address,
        PCI_BRIDGE_CONTROL,
        ctrl & ~PCI_BRIDGE_CTL_BUS_RESET,
        sysfs_root=sysfs_root,
    )


def set_link_control_bits(address, mask, enable=True, sysfs_root=None):
    """Generic helper to set or clear Link Control bits."""
    mask = validate_u16(mask)
    return _update_link_control(address, mask, enable, sysfs_root=sysfs_root)


__all__ = [
    "link_disable",
    "link_enable",
    "link_hot_reset",
    "read_link_status",
    "retrain_link",
    "set_link_control_bits",
    "set_target_link_speed",
    "wait_for_link_training",
]
