import pytest
from vehicle.obd.protocols.elm327 import ELM327Protocol, OBDProtocolError

def test_rpm_decode(): assert ELM327Protocol.rpm(bytes([0x0B,0xB8])) == 750.0

def test_coolant_decode(): assert ELM327Protocol.coolant_c(bytes([90])) == 50.0

def test_dtc_decode(): assert ELM327Protocol.dtc_codes(bytes.fromhex('43 03 02 00 00')) == ['P0302']

def test_no_data():
    with pytest.raises(OBDProtocolError): ELM327Protocol.parse_hex_payload('010C','NO DATA')
