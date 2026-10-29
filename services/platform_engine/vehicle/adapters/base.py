from abc import ABC, abstractmethod
from vehicle.devices.models import DeviceDescriptor

class DiagnosticAdapter(ABC):
    @property
    @abstractmethod
    def descriptor(self) -> DeviceDescriptor: ...

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def health_check(self) -> dict: ...
