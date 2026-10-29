"""Windows J2534 DLL loader seam. No vendor DLL is bundled or required."""
import ctypes
from pathlib import Path
from vehicle.j2534.interface import J2534PassThru

class J2534Windows(J2534PassThru):
    def __init__(self, dll_path: str):
        self.dll_path = Path(dll_path)
        self.dll = None
        self.channel = None
    def open(self):
        if not self.dll_path.exists():
            raise FileNotFoundError(self.dll_path)
        self.dll = ctypes.WinDLL(str(self.dll_path))
    def close(self):
        self.dll = None
        self.channel = None
    def connect(self, protocol_id: int, flags: int = 0):
        if self.dll is None: raise RuntimeError('J2534 DLL is not open')
        raise NotImplementedError('Vendor-specific PassThruConnect binding must be configured')
    def disconnect(self): self.channel = None
    def send(self, messages, timeout_ms=1000):
        raise NotImplementedError('Vendor-specific PassThruWriteMsgs binding must be configured')
    def receive(self, max_messages=1, timeout_ms=1000):
        raise NotImplementedError('Vendor-specific PassThruReadMsgs binding must be configured')
