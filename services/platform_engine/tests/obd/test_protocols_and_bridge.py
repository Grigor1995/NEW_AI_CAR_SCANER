import asyncio

import pytest
from fastapi.testclient import TestClient
from obd.protocols import PROTOCOLS, initialization, detected_protocol
from obd.decoding import decode_snapshot
from vehicle.obd.protocols.elm327 import ELM327Protocol, OBDProtocolError
from vehicle.obd.client import GenericObdClient
from vehicle.obd.adapters.simulator import SimulatorTransport


@pytest.mark.parametrize('code', list('0123456789'))
def test_adapter_protocol_selection_is_backend_owned(code):
    protocol = next(p for p in PROTOCOLS if p.elm_code == code)
    assert initialization(protocol.id)[-1] == 'ATSP'+code
    assert 'ATH0' in initialization(protocol.id)


@pytest.mark.parametrize('code', list('123456789'))
def test_actual_adapter_detection_accepts_auto_prefix(code):
    actual = detected_protocol('A'+code+'>')
    assert actual['automatic'] and actual['observed']
    assert actual['elm_code'] == code


@pytest.mark.parametrize('protocol', ['doip', 'can-fd', 'wwh-obd', 'j1939', 'oem-diagnostics', 'not-a-protocol'])
def test_unimplemented_family_is_not_silently_sent_to_adapter(protocol):
    with pytest.raises(ValueError): initialization(protocol)


@pytest.mark.parametrize('raw', ['0', 'A0', 'NO DATA', 'OK', 'A6 GARBAGE'])
def test_unknown_adapter_protocol_does_not_claim_compatibility(raw):
    with pytest.raises(ValueError): detected_protocol(raw)


@pytest.mark.parametrize('raw', ['41 0C 1A F8', '410c1af8', '010C\rSEARCHING...\r410C1AF8>',
                                  '7E8 04 41 0C 1A F8 00 00 00', '18DAF110 04 41 0C 1A F8 00 00 00'])
def test_rpm_compact_echo_can_and_extended_headers(raw):
    result = decode_snapshot({'010C':raw})
    assert result['values']['rpm'] == 1726


@pytest.mark.parametrize('raw', ['42 0C 1A F8', '41 0D 1A F8', '41 0C GG GG', '41 0C 1A', 'NO DATA', '7E8 06 41 0C 1A'])
def test_bad_wrong_service_and_truncated_frames_never_become_numbers(raw):
    assert decode_snapshot({'010C': raw})['values']['rpm'] is None


def test_backend_scales_all_ten_pid_values_and_preserves_errors():
    frames = {'010C':'410C1AF8','010D':'410D32','0105':'41057B','0104':'410480',
              '010F':'410F50','0110':'411001F4','010B':'410B64','0111':'411180','0106':'410680','0107':'4107A0','ATDPN':'A6'}
    result = decode_snapshot(frames)
    assert result['values'] == pytest.approx(dict(rpm=1726,speed_kmh=50,coolant_c=83,engine_load_percent=128*100/255,
                      intake_air_c=40,maf_gps=5,map_kpa=100,throttle_percent=128*100/255,
                      short_fuel_trim_percent=0,long_fuel_trim_percent=25))
    assert result['protocol']['id'] == 'can-11-500'
    assert not result['hardware_verified']


def test_isotp_frames_reassemble_vin_and_validate_sequence():
    raw = '7E8 10 14 49 02 01 57 44 42\r7E8 21 32 31 31 30 30 30 30\r7E8 22 30 30 30 30 30 30 31'
    data = ELM327Protocol.payloads('0902', raw)[0]
    assert data == bytes.fromhex('49 02 01') + b'WDB21100000000001'
    with pytest.raises(OBDProtocolError): ELM327Protocol.payloads('0902', raw.replace('7E8 21', '7E8 23'))


def test_multiple_ecus_are_not_concatenated_and_dtcs_are_merged():
    raw = '7E8 03 43 03 02 00 00 00\r7E9 03 43 01 71 00 00 00'
    async def scenario():
        client = GenericObdClient(SimulatorTransport({'03': raw}))
        await client.transport.connect()
        return await client.read_dtcs()
    assert asyncio.run(scenario()) == ['P0302','P0171']


def test_supported_pid_pages_follow_actual_bitmaps():
    async def scenario():
        client = GenericObdClient(SimulatorTransport({'0100':'410080000001','0120':'412080000000'}))
        await client.transport.connect()
        return await client.supported_pids()
    assert asyncio.run(scenario()) == [1,32,33]


def test_bridge_api_plan_validation_and_telemetry_ingestion(monkeypatch):
    import api.main as main
    from api.state import sessions
    from api.telemetry_routes import service
    from diagnostic.models import DiagnosticSession
    session = DiagnosticSession()
    key = str(session.session_id)
    sessions[key] = session
    with TestClient(main.app) as client:
        plan = client.get('/api/v1/obd/plan').json()
        assert plan['read_only'] and '010C' in plan['commands']
        assert client.get('/api/v1/obd/plan?protocol_id=doip').status_code == 422
        response = client.post('/api/v1/obd/decode', json={'session_id':key,'responses':{'010C':'410C1AF8'}})
        assert response.status_code == 200
        assert response.json()['accepted_samples'] == 1
        samples = service.samples(session.session_id)
        assert samples[-1].pid == 'rpm' and samples[-1].value == 1726
        assert samples[-1].source == 'NATIVE_OBD_BRIDGE'
        assert client.post('/api/v1/obd/decode',json={'session_id':'missing','responses':{}}).status_code == 404
        assert client.post('/api/v1/obd/decode',json={'responses':{'010C':'A'*9000}}).status_code == 422
    del sessions[key]


def test_real_tcp_transport_is_used_by_backend_device_facade():
    from device.manager import VCIConnectionManager
    async def scenario():
        commands = []
        async def adapter(reader, writer):
            try:
                while data := await reader.readuntil(b'\r'):
                    command = data.decode().strip(); commands.append(command)
                    reply = {'010C':'410C1AF8','0100':'4100BE1FA813','ATDPN':'A6'}.get(command,'OK')
                    writer.write((reply+'>').encode()); await writer.drain()
            except (asyncio.IncompleteReadError, ConnectionError): pass
            finally:
                writer.close(); await writer.wait_closed()
        server = await asyncio.start_server(adapter,'127.0.0.1',0)
        manager = VCIConnectionManager()
        try:
            port = server.sockets[0].getsockname()[1]
            descriptor = await manager.probe_wifi('127.0.0.1',port,1)
            await manager.connect(descriptor.device_id,{'protocol_id':'can-11-500'})
            values = await manager.read_live_data(descriptor.device_id)
            assert values['rpm'] == 1726
            assert 'ATSP6' in commands
            observed = await manager._physical().connected_obd(descriptor.device_id).protocol_status()
            assert observed['id'] == 'can-11-500'
        finally:
            await manager.shutdown(); server.close(); await server.wait_closed()
    asyncio.run(scenario())


@pytest.mark.parametrize('mode,header', [(3,'43'),(7,'47'),(10,'4A')])
def test_stored_pending_and_permanent_dtc_services(mode,header):
    async def scenario():
        transport = SimulatorTransport({f'{mode:02X}':header+'0302'})
        client = GenericObdClient(transport)
        await transport.connect()
        return await client.read_dtcs(mode)
    assert asyncio.run(scenario()) == ['P0302']


@pytest.mark.parametrize('raw',['7E804410C1AF8','18DAF11004410C1AF8'])
def test_compact_can_headers(raw):
    assert decode_snapshot({'010C':raw})['values']['rpm'] == 1726


def test_server_acquisition_collects_actual_values_and_stops_on_transport_error():
    from uuid import uuid4
    from acquisition.service import AcquisitionApiService
    from acquisition.models import AcquisitionStartRequest
    class Device:
        calls = 0
        async def read_live_data(self, device_id):
            self.calls += 1
            if self.calls == 1:return {'rpm':1234.5}
            raise ConnectionError('adapter disconnected')
    async def scenario():
        service = AcquisitionApiService()
        sid = uuid4()
        await service.start_device(sid,AcquisitionStartRequest(adapter='wifi',pids=[12],poll_interval_ms=20),Device(),'wifi:local')
        for _ in range(100):
            if service.status(sid).state == 'ERROR':break
            await asyncio.sleep(0.005)
        records = service.snapshot(sid)
        assert len(records) == 1 and records[0].numeric_value == 1234.5
        assert records[0].metadata['adapter'] == 'wifi'
        assert service.status(sid).state == 'ERROR'
        assert service.status(sid).stats['errors'] == 1
        await service.shutdown()
    asyncio.run(scenario())


def test_native_bridge_and_server_acquisition_do_not_mix_sources():
    from uuid import uuid4
    from acquisition.service import AcquisitionApiService
    from acquisition.models import AcquisitionStartRequest
    class Device:
        async def read_live_data(self, device_id):return {'rpm':1234.5}
    async def scenario():
        service = AcquisitionApiService(); sid = uuid4()
        await service.start_device(sid,AcquisitionStartRequest(adapter='wifi'),Device(),'device')
        try:
            with pytest.raises(ValueError):service.append_bridge(sid,decode_snapshot({'010C':'410C0000'}))
        finally:await service.shutdown()
    asyncio.run(scenario())


def test_timeout_disconnects_transport_instead_of_consuming_late_frame():
    class TimeoutTransport(SimulatorTransport):
        async def read_until(self, *args, **kwargs):raise TimeoutError('adapter stalled')
    async def scenario():
        transport = TimeoutTransport()
        await transport.connect()
        client = GenericObdClient(transport)
        with pytest.raises(TimeoutError):await client.command('010C')
        assert not transport.connected
    asyncio.run(scenario())


def test_public_protocol_registry_and_detected_response_errors():
    import api.main as main
    with TestClient(main.app) as client:
        protocols = client.get('/api/v1/obd/protocols').json()['protocols']
        assert any(p['id']=='doip' and p['status']=='read_only_tcp_routing_and_uds_22_19' for p in protocols)
        assert client.get('/api/v1/obd/detected-protocol',params={'raw':'A6'}).json()['id']=='can-11-500'
        assert client.get('/api/v1/obd/detected-protocol',params={'raw':'UNKNOWN'}).status_code==422
        result = client.post('/api/v1/obd/decode',json={'responses':{'ATDPN':'UNKNOWN'}}).json()
        assert result['protocol'] is None and 'ATDPN' in result['errors']


def test_simulator_history_cannot_be_relabelled_as_real_measurements():
    from uuid import uuid4
    from api.telemetry_routes import service as telemetry
    from telemetry.models import TelemetrySample
    from acquisition.service import AcquisitionApiService
    from acquisition.models import AcquisitionStartRequest
    sid=uuid4()
    telemetry.append([TelemetrySample(session_id=sid,timestamp_ms=1,pid='rpm',value=750,source='SIMULATOR')])
    async def scenario():
        with pytest.raises(ValueError,match='new session'):
            await AcquisitionApiService().start_device(sid,AcquisitionStartRequest(adapter='wifi'),None,'device')
    asyncio.run(scenario())


def test_bound_acquisition_resolves_device_transport_in_backend(monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4
    import api.acquisition_routes as routes
    import api.state as state
    from diagnostic.models import DiagnosticSession
    from acquisition.models import AcquisitionStartRequest
    sid=str(uuid4()); state.sessions[sid]=DiagnosticSession(connected_device_id='wifi:car')
    descriptor=SimpleNamespace(connection_type='Wi-Fi',status=SimpleNamespace(value='connected'))
    manager=SimpleNamespace(status=lambda device:descriptor)
    monkeypatch.setattr(state,'vci_manager',manager)
    calls=[]
    async def start_device(session_id,request,device_manager,device_id):
        calls.append((request.adapter,device_id)); return 'started'
    monkeypatch.setattr(routes.service,'start_device',start_device)
    async def scenario():
        assert await routes.start_acquisition(sid,AcquisitionStartRequest(adapter='bound'))=='started'
    try:asyncio.run(scenario())
    finally:del state.sessions[sid]
    assert calls==[('wifi','wifi:car')]
