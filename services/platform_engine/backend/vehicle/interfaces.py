from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
@dataclass
class DeviceCapabilities:
    obd: bool=False; can: bool=False; can_fd: bool=False; uds: bool=False; j2534: bool=False; ble: bool=False; wifi: bool=False; usb: bool=False
class DiagnosticAdapter(ABC):
    @abstractmethod
    async def connect(self)->None: ...
    @abstractmethod
    async def disconnect(self)->None: ...
    @abstractmethod
    def capabilities(self)->DeviceCapabilities: ...
class VehicleInterface(ABC):
    @abstractmethod
    async def read_vin(self)->str|None: ...
    @abstractmethod
    async def read_dtcs(self)->list[str]: ...
class ObdInterface(VehicleInterface):
    @abstractmethod
    async def read_pid(self,pid:int)->Any: ...
class CanInterface(ABC):
    @abstractmethod
    async def send(self,arbitration_id:int,data:bytes)->None: ...
    @abstractmethod
    async def receive(self,timeout_ms:int=1000)->dict|None: ...
class UdsInterface(ABC):
    @abstractmethod
    async def diagnostic_session_control(self,session_type:int)->bytes: ...
