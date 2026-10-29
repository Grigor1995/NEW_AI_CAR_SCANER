from __future__ import annotations
from vehicle.obd.client import GenericObdClient

class ObdDiagnosticService:
    def __init__(self, client: GenericObdClient): self.client=client
    async def identify_vehicle(self):
        return {"vin": await self.client.read_vin(), "dtcs": await self.client.read_dtcs()}
    async def snapshot(self):
        return await self.client.read_standard_live_data()
