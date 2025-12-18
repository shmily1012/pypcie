"""Core types and validation helpers for pypcie."""

import re

from .errors import SysfsFormatError, ValueRangeError

_BDF_RE = re.compile(
    r"^(?:(?P<domain>[0-9a-fA-F]{4}):)?"
    r"(?P<bus>[0-9a-fA-F]{2}):"
    r"(?P<device>[0-9a-fA-F]{2})\."
    r"(?P<function>[0-7])$"
)


def validate_width(width):
    """Validate access width in bytes (1/2/4/8)."""
    if not isinstance(width, int) or isinstance(width, bool):
        raise ValueRangeError("width must be an integer")
    if width not in (1, 2, 4, 8):
        raise ValueRangeError("width must be 1, 2, 4, or 8 bytes")
    return width


def _validate_value_range(value, bits, name):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueRangeError("%s must be an integer" % name)
    max_value = (1 << bits) - 1
    if not (0 <= value <= max_value):
        raise ValueRangeError("%s out of range" % name)
    return value


def validate_u8(value):
    return _validate_value_range(value, 8, "u8")


def validate_u16(value):
    return _validate_value_range(value, 16, "u16")


def validate_u32(value):
    return _validate_value_range(value, 32, "u32")


def validate_u64(value):
    return _validate_value_range(value, 64, "u64")


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
            raise ValueRangeError("domain out of range")
        if not (0 <= self.bus <= 0xFF):
            raise ValueRangeError("bus out of range")
        if not (0 <= self.device <= 0x1F):
            raise ValueRangeError("device out of range")
        if not (0 <= self.function <= 0x7):
            raise ValueRangeError("function out of range")

    @classmethod
    def parse(cls, text):
        """Parse a BDF string like '0000:00:1f.6' or '00:1f.6'."""
        if isinstance(text, cls):
            return text
        if not isinstance(text, str):
            raise SysfsFormatError("address must be a string")
        match = _BDF_RE.match(text.strip())
        if not match:
            raise SysfsFormatError("invalid PCI address: %r" % (text,))
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


__all__ = [
    "PciAddress",
    "validate_u8",
    "validate_u16",
    "validate_u32",
    "validate_u64",
    "validate_width",
]
