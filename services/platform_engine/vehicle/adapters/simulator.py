from vehicle.adapters.base import DiagnosticAdapter
from vehicle.devices.models import DeviceDescriptor, DeviceStatus, DeviceCapabilities

class VciSimulatorAdapter(DiagnosticAdapter):
    def __init__(self, device_id='sim-vci-001'):
        self._descriptor = DeviceDescriptor(device_id, 'Simulator', 'Professional VCI Simulator', '1.0', 'CAN/ISO-TP/UDS', 'simulator', DeviceCapabilities(True, True, True, True, True), DeviceStatus.DISCONNECTED)
    @property
    def descriptor(self): return self._descriptor
    async def connect(self): self._descriptor.status = DeviceStatus.CONNECTED
    async def disconnect(self): self._descriptor.status = DeviceStatus.DISCONNECTED
    async def health_check(self): return {'device_id': self.descriptor.device_id, 'status': self.descriptor.status.value, 'latency_ms': 1.0, 'packet_loss': 0.0}
