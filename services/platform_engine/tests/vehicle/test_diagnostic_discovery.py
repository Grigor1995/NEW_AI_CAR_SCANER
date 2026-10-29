import pytest
from vehicle.diagnostic_discovery import collect, identify, responding_modules, vin_from_response

VIN = 'WDD2110801A123456'
VIN_RAW = '49 02 01 ' + ' '.join(f'{b:02X}' for b in VIN.encode())


def test_vin_and_responder_parsing_require_correct_complete_services():
    assert vin_from_response(VIN_RAW) == VIN
    assert vin_from_response('41 00 ' + VIN_RAW) is None
    assert vin_from_response('NO DATA') is None
    modules = responding_modules('7E8 06 41 00 BE 3E B8 13\r7E9 06 41 00 00 00 00 01')
    assert [m['address'] for m in modules] == ['7E8', '7E9']
    assert responding_modules('7E8064100BE3EB813')[0]['address'] == '7E8'
    assert responding_modules('18DAF110064100BE3EB813')[0]['address'] == '18DAF110'
    assert responding_modules('7E8 02 41 00') == []
    assert responding_modules('7E8 06 43 00 BE 3E B8 13') == []
    assert responding_modules('41 00 BE 3E B8 13')[0]['address'] is None


@pytest.mark.asyncio
async def test_vin_is_first_and_headers_restore_on_failure():
    seen = []
    async def command(step):
        seen.append(step)
        if step == '0100': raise RuntimeError('timeout')
        return 'OK'
    with pytest.raises(RuntimeError): await collect(command)
    assert seen == ['0902', 'ATH1', '0100', 'ATH0']


@pytest.mark.asyncio
async def test_lookup_failure_keeps_measured_modules(monkeypatch):
    def offline(vin): raise OSError('offline')
    monkeypatch.setattr('vehicle.diagnostic_discovery.nhtsa_decode_vin', offline)
    result = await identify({'0902': VIN_RAW, '0100': '7E8 06 41 00 BE 3E B8 13'})
    assert result['vin'] == VIN
    assert result['identification_status'] == 'lookup_unavailable'
    assert result['modules'][0]['observed'] is True
    assert result['vehicle'] is None


@pytest.mark.asyncio
async def test_simulation_never_looks_up_real_vehicle(monkeypatch):
    def forbidden(vin): raise AssertionError('Must not send synthetic VIN')
    monkeypatch.setattr('vehicle.diagnostic_discovery.nhtsa_decode_vin', forbidden)
    assert (await identify({'0902': VIN_RAW}, simulated=True))['identification_status'] == 'simulated'


@pytest.mark.asyncio
async def test_complete_vin_identification_and_29_bit_responder(monkeypatch):
    monkeypatch.setattr('vehicle.diagnostic_discovery.nhtsa_decode_vin',
                        lambda vin: {'make': 'Mercedes-Benz', 'model': 'E-Class', 'error_code': '0'})
    result = await identify({'0902': VIN_RAW, '0100': '18DAF110 06 41 00 BE 3E B8 13'})
    assert result['identification_status'] == 'identified'
    assert result['modules'][0]['address'] == '18DAF110'
    assert result['scope'] == 'generic_obd_responders_only'


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,expected", [("A6", "can-11-500"), ("A7", "can-29-500"), ("3", "iso9141-2"), ("A0", None), ("?", None)])
async def test_protocol_autodetection_requires_positive_ecu_reply(mode, expected):
    responses = {"0100": "41 00 BE 3E B8 13", "ATDPN": mode}
    result = await identify(responses)
    assert (result["protocol"]["id"] if result["protocol"] else None) == expected
    result = await identify({"0100": "NO DATA", "ATDPN": mode})
    assert result["protocol"] is None
    result = await identify(responses, simulated=True)
    assert result["protocol"] is None
