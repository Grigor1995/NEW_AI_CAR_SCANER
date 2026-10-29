from vehicle.adapters.base import DiagnosticAdapter
from vehicle.devices.models import DeviceDescriptor, DeviceStatus

class VendorSdkAdapter(DiagnosticAdapter):
    """Generic vendor SDK seam. Real SDKs are injected, never embedded in the domain."""
    def __init__(self, descriptor: DeviceDescriptor, sdk=None):
        self._descriptor = descriptor
        self.sdk = sdk
    @property
    def descriptor(self): return self._descriptor
    async def connect(self):
        if self.sdk and hasattr(self.sdk, 'connect'):
            result = self.sdk.connect()
            if hasattr(result, '__await__'): await result
        self._descriptor.status = DeviceStatus.CONNECTED
    async def disconnect(self):
        if self.sdk and hasattr(self.sdk, 'disconnect'):
            result = self.sdk.disconnect()
            if hasattr(result, '__await__'): await result
        self._descriptor.status = DeviceStatus.DISCONNECTED
    async def health_check(self):
        if self.sdk and hasattr(self.sdk, 'health_check'):
            result = self.sdk.health_check()
            if hasattr(result, '__await__'): result = await result
            return result
        return {'device_id': self.descriptor.device_id, 'status': self.descriptor.status.value}
