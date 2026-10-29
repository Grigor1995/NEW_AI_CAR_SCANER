from vehicle.devices.models import DeviceDescriptor, DeviceStatus

class DeviceRegistry:
    def __init__(self): self._devices = {}
    def register(self, descriptor: DeviceDescriptor): self._devices[descriptor.device_id] = descriptor
    def remove(self, device_id: str): self._devices.pop(device_id, None)
    def get(self, device_id: str): return self._devices.get(device_id)
    def list(self): return list(self._devices.values())
    def connected(self): return [d for d in self._devices.values() if d.status == DeviceStatus.CONNECTED]
