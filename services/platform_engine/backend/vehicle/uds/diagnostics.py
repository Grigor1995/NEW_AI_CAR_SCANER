from dataclasses import dataclass

@dataclass
class UdsIdentity:
    vin: str|None=None
    software_version: str|None=None
    hardware_version: str|None=None
@dataclass
class UdsDtcRecord:
    code: str
    raw_dtc: int
    status_byte: int
    confirmed: bool

class UdsDiagnosticSession:
    def __init__(self, client): self.client=client
    async def identify_ecu(self):
        return UdsIdentity(vin="SIMULATORVIN0000001",software_version="SIM-ECU-1.0",hardware_version="SIM-HW-1.0")
    async def read_dtcs(self):
        return []
