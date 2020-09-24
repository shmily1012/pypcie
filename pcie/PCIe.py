import os

#######################################
_U32 = 4
_U16 = 2
_U8 = 1
#######################################


class PCIe():
    def __init__(self, domain: int, bus: int, device: int, function: int):
        self.domain = domain
        self.bus = bus
        self.device = device
        self.function = function

    def _getPcieConfigPath(self) -> str:
        path = r'/proc/bus/pci/'
        if domain != 0x0:
            if domain < 0x1000:
                path += f'{domain:0>4x}'+r':'
            else:
                path += f'{domain:x}'+r':'
        path += f'{bus:0>2x}' + r'/'+f'{device:0>2x}.{function:x}'
        return path

    def _read(self, dataType: int, offset: int) -> int:
        assert offset % dataType == 0, f"read - {offset=:X}h must be align with {dataType}."
        path = self._getPcieConfigPath()
        try:
            f = os.open(path, os.O_RDONLY)
        except FileNotFoundError:
            if dataType == _U8:
                return 0xFF
            elif dataType == _U16:
                return 0xFFFF
            elif dataType == _U32:
                return 0xFFFFFFFF
            else:
                Warning(f"[{dataType=:}] is invalid.", 5)
        value = os.pread(f, dataType, offset)
        os.close(f)
        return int.from_bytes(value, byteorder='little')

    def _write(self, dataType: int, offset: int, value: int) -> bool:
        '''
        return status
        If DNF, return False; otherwise, return True
        '''
        assert offset % dataType == 0, f"write - {offset=:X}h must be align with {dataType}."
        value_b = value.to_bytes(length=dataType, byteorder='little')
        path = self._getPcieConfigPath()
        try:
            f = os.open(path, os.O_WRONLY)
        except FileNotFoundError:
            return False
        n = os.pwrite(f, value_b, offset)
        os.close(f)
        return True

    def configRead32(self, offset: int):
        return self._read(_U32, offset)

    def configRead16(self, offset: int):
        return self._read(_U16, offset)

    def configRead8(self, offset: int):
        return self._read(_U8, offset)

    def configWrite32(self, offset: int, value: int):
        return self._write(_U32, offset, value)

    def configWrite16(self, offset: int, value: int):
        return self._write(_U16, offset, value)

    def configWrite8(self, offset: int, value: int):
        return self._write(_U8, offset, value)


if __name__ == "__main__":
    pcie = PCIe(0x0, 0x1, 0x0, 0x0)
    pcie._read(0x2, 0x1)
