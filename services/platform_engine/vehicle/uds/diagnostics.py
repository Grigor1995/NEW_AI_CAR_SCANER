from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .client import UdsClient
from .decoder import UdsDtcRecord, parse_dtc_information


@dataclass(frozen=True)
class EcuIdentity:
    vin: str | None = None
    software_version: str | None = None
    hardware_version: str | None = None
    extra_dids: dict[int, bytes] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'vin': self.vin,
            'software_version': self.software_version,
            'hardware_version': self.hardware_version,
            'extra_dids': {f'0x{k:04X}': v.hex() for k, v in self.extra_dids.items()},
        }


class UdsDiagnosticSession:
    """Read-only UDS diagnostic facade for ECU identification and DTC capture."""

    VIN_DID = 0xF190
    SOFTWARE_VERSION_DID = 0xF187
    HARDWARE_VERSION_DID = 0xF191

    def __init__(self, client: UdsClient, *, identity_dids: dict[str, int] | None = None):
        self.client = client
        dids = identity_dids or {}
        self.vin_did = dids.get('vin', self.VIN_DID)
        self.software_version_did = dids.get('software_version', self.SOFTWARE_VERSION_DID)
        self.hardware_version_did = dids.get('hardware_version', self.HARDWARE_VERSION_DID)

    async def identify_ecu(self) -> EcuIdentity:
        values: dict[str, bytes | None] = {'vin': None, 'software_version': None, 'hardware_version': None}
        for name, did in (
            ('vin', self.vin_did),
            ('software_version', self.software_version_did),
            ('hardware_version', self.hardware_version_did),
        ):
            try:
                values[name] = await self.client.read_data_by_identifier(did)
            except Exception:
                # Identity is best-effort; one unsupported DID must not hide the others.
                values[name] = None

        def text(raw: bytes | None) -> str | None:
            if raw is None:
                return None
            value = bytes(x for x in raw if 32 <= x <= 126).decode('ascii', errors='ignore').strip()
            return value or None

        return EcuIdentity(
            vin=text(values['vin']),
            software_version=text(values['software_version']),
            hardware_version=text(values['hardware_version']),
        )

    async def read_dtcs(self, subfunction: int = 0x02) -> list[UdsDtcRecord]:
        payload = await self.client.read_dtc_information(subfunction)
        return parse_dtc_information(payload)

    @property
    def supports_clear_dtc(self) -> bool:
        # Service 0x14 is intentionally excluded from MVP/Phase 16 safety scope.
        return False
