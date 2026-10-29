from vehicle.adapters.base import DiagnosticAdapter
from vehicle.devices.models import DeviceDescriptor, DeviceStatus
from vehicle.j2534.interface import J2534PassThru

class J2534Adapter(DiagnosticAdapter):
    def __init__(self, descriptor: DeviceDescriptor, passthru: J2534PassThru):
        self._descriptor, self.passthru = descriptor, passthru
    @property
    def descriptor(self): return self._descriptor
    async def connect(self):
        self.passthru.open(); self._descriptor.status = DeviceStatus.CONNECTED
    async def disconnect(self):
        self.passthru.disconnect(); self.passthru.close(); self._descriptor.status = DeviceStatus.DISCONNECTED
    async def health_check(self):
        return {'device_id': self.descriptor.device_id, 'status': self.descriptor.status.value, 'j2534': True}
