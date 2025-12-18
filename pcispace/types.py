"""Core types for pcispace."""

import re

from .errors import PciAddressError

_BDF_RE = re.compile(
    r"^(?:(?P<domain>[0-9a-fA-F]{4}):)?"
    r"(?P<bus>[0-9a-fA-F]{2}):"
    r"(?P<device>[0-9a-fA-F]{2})\."
    r"(?P<function>[0-7])$"
)


class PciAddress(object):
    """Represents a PCI domain:bus:device.function address."""

    __slots__ = ("domain", "bus", "device", "function")

    def __init__(self, domain, bus, device, function):
        self.domain = int(domain)
        self.bus = int(bus)
        self.device = int(device)
        self.function = int(function)
        self._validate()

    def _validate(self):
        if not (0 <= self.domain <= 0xFFFF):
            raise PciAddressError("domain out of range")
        if not (0 <= self.bus <= 0xFF):
            raise PciAddressError("bus out of range")
        if not (0 <= self.device <= 0x1F):
            raise PciAddressError("device out of range")
        if not (0 <= self.function <= 0x7):
            raise PciAddressError("function out of range")

    @classmethod
    def parse(cls, text):
        """Parse a BDF string like '0000:00:1f.6' or '00:1f.6'."""
        if isinstance(text, cls):
            return text
        if not isinstance(text, str):
            raise PciAddressError("address must be a string")
        match = _BDF_RE.match(text.strip())
        if not match:
            raise PciAddressError("invalid PCI address: %r" % (text,))
        domain = match.group("domain")
        if domain is None:
            domain = "0000"
        return cls(
            int(domain, 16),
            int(match.group("bus"), 16),
            int(match.group("device"), 16),
            int(match.group("function"), 16),
        )

    @property
    def bdf(self):
        return "%04x:%02x:%02x.%x" % (
            self.domain,
            self.bus,
            self.device,
            self.function,
        )

    def __str__(self):
        return self.bdf

    def __repr__(self):
        return "PciAddress(%r)" % self.bdf

    def __eq__(self, other):
        if not isinstance(other, PciAddress):
            try:
                other = PciAddress.parse(other)
            except Exception:
                return False
        return (
            self.domain == other.domain
            and self.bus == other.bus
            and self.device == other.device
            and self.function == other.function
        )

    def __hash__(self):
        return hash((self.domain, self.bus, self.device, self.function))
