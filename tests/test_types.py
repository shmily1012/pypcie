import pytest

from pcispace.types import PciAddress
from pcispace.errors import PciAddressError


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


def test_pci_address_invalid():
    with pytest.raises(PciAddressError):
        PciAddress.parse("not-a-bdf")
