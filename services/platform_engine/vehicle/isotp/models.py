from __future__ import annotations
from enum import Enum

class IsoTpError(Exception): pass
class IsoTpTimeout(IsoTpError): pass
class IsoTpProtocolError(IsoTpError): pass

class FlowStatus(int, Enum):
    CTS = 0
    WAIT = 1
    OVERFLOW = 2
