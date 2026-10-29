from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class DeviceStatus(str, Enum):
    DISCONNECTED = 'disconnected'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    ERROR = 'error'

@dataclass(frozen=True)
class DeviceCapabilities:
    obd: bool = False
    can: bool = False
    can_fd: bool = False
    uds: bool = False
    j2534: bool = False
    ble: bool = False
    wifi: bool = False
    usb: bool = False

@dataclass
class DeviceDescriptor:
    device_id: str
    manufacturer: str
    model: str
    firmware_version: str | None = None
    protocol: str | None = None
    connection_type: str | None = None
    capabilities: DeviceCapabilities = field(default_factory=DeviceCapabilities)
    status: DeviceStatus = DeviceStatus.DISCONNECTED
    metadata: dict[str, Any] = field(default_factory=dict)
