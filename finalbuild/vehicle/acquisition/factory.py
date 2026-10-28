from __future__ import annotations
from typing import Any
from vehicle.obd.client import GenericObdClient
from vehicle.obd.transport import DiagnosticTransport
from vehicle.obd.adapters.ble import ObdBleTransport
from vehicle.obd.adapters.tcp_wifi import ObdWifiTransport
from vehicle.obd.adapters.usb_serial import ObdUsbSerialTransport
from .sources import ObdPollingSource


def build_obd_transport(adapter: str, config: dict[str, Any]) -> DiagnosticTransport:
    adapter = adapter.lower()
    if adapter == 'ble':
        return ObdBleTransport(config['address'], config['tx_uuid'], config['rx_uuid'])
    if adapter == 'wifi':
        if config.get('native_tcp') is True:
            from vehicle.obd.adapters.native_tcp import NativeObdWifiTransport
            return NativeObdWifiTransport(config['host'], int(config.get('port', 35000)))
        return ObdWifiTransport(config['host'], int(config.get('port', 35000)))
    if adapter == 'usb':
        return ObdUsbSerialTransport(config['port'], int(config.get('baudrate', 115200)))
    raise ValueError(f'Unsupported OBD adapter: {adapter}')


def build_obd_source(adapter: str, config: dict[str, Any], pids: list[int] | None = None) -> ObdPollingSource:
    return ObdPollingSource(GenericObdClient(build_obd_transport(adapter, config)), pids)
