import pytest
from vehicle.can.models import CanFrame

def test_classic_can_frame():
    f=CanFrame(0x7E0,b'\x01\x02')
    assert f.dlc==2

def test_invalid_id():
    with pytest.raises(ValueError): CanFrame(0x800,b'')
