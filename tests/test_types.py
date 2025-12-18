import pytest

from pypcie.errors import SysfsFormatError, ValueRangeError
from pypcie.types import (
    PciAddress,
    validate_u16,
    validate_u32,
    validate_u64,
    validate_u8,
    validate_width,
)


def test_pci_address_parse_full():
    addr = PciAddress.parse("0000:00:1f.6")
    assert addr.domain == 0
    assert addr.bus == 0
    assert addr.device == 0x1F
    assert addr.function == 6
    assert str(addr) == "0000:00:1f.6"


def test_pci_address_parse_short_domain():
    addr = PciAddress.parse("02:00.0")
    assert addr.domain == 0
    assert addr.bus == 2
    assert addr.device == 0
    assert addr.function == 0
    assert addr.bdf == "0000:02:00.0"


def test_pci_address_invalid_format():
    with pytest.raises(SysfsFormatError):
        PciAddress.parse("not-a-bdf")


def test_pci_address_range_validation():
    with pytest.raises(ValueRangeError):
        PciAddress(0x10000, 0, 0, 0)
    with pytest.raises(ValueRangeError):
        PciAddress(0, 0x100, 0, 0)
    with pytest.raises(ValueRangeError):
        PciAddress(0, 0, 0x20, 0)
    with pytest.raises(ValueRangeError):
        PciAddress(0, 0, 0, 0x8)


def test_validate_width():
    for width in (1, 2, 4, 8):
        assert validate_width(width) == width
    with pytest.raises(ValueRangeError):
        validate_width(3)


def test_validate_value_ranges():
    assert validate_u8(0) == 0
    assert validate_u8(0xFF) == 0xFF
    with pytest.raises(ValueRangeError):
        validate_u8(0x100)

    assert validate_u16(0xFFFF) == 0xFFFF
    with pytest.raises(ValueRangeError):
        validate_u16(-1)

    assert validate_u32(0xFFFFFFFF) == 0xFFFFFFFF
    with pytest.raises(ValueRangeError):
        validate_u32(1 << 32)

    assert validate_u64(0xFFFFFFFFFFFFFFFF) == 0xFFFFFFFFFFFFFFFF
    with pytest.raises(ValueRangeError):
        validate_u64(1 << 64)
