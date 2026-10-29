from dataclasses import dataclass
@dataclass(frozen=True)
class ObdPid:
    pid:int; name:str; unit:str; description:str
STANDARD_PIDS=(
 ObdPid(0x05,'coolant_c','°C','Engine coolant temperature'),
 ObdPid(0x0C,'rpm','rpm','Engine speed'),
 ObdPid(0x0D,'speed_kmh','km/h','Vehicle speed'),
 ObdPid(0x11,'throttle_percent','%','Throttle position'),
)
