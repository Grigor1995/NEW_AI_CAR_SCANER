from vehicle.devices.registry import DeviceRegistry
from vehicle.devices.models import DeviceDescriptor

def test_registry_register_and_lookup():
    r=DeviceRegistry(); d=DeviceDescriptor('x','Test','VCI'); r.register(d)
    assert r.get('x') is d and len(r.list()) == 1
