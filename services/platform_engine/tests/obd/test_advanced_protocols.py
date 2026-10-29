"""Loopback TCP wire fixtures, not physical vehicle compatibility evidence."""
import asyncio
import struct

import pytest
from fastapi import HTTPException
from vehicle.doip.client import DoipClient
from obd.j1939 import decode_diagnostic_frame
from api.advanced_obd_routes import DoipRead, J1939Frame, read_doip, decode_j1939


def packet(kind, payload=b''):
    return struct.pack('!BBHI', 2, 253, kind, len(payload)) + payload


async def receive(reader):
    _, _, kind, size = struct.unpack('!BBHI', await reader.readexactly(8))
    return kind, await reader.readexactly(size)


@pytest.mark.asyncio
@pytest.mark.parametrize('service', ['vin', 'dtcs', 'mismatch', 'negative', 'nack', 'routing_rejected', 'bad_header', 'oversized', 'timeout'])
async def test_doip_real_tcp_routing_and_read_only_exchange(service):
    seen = []
    finished = asyncio.Event()

    async def gateway(reader, writer):
        try:
            kind, body = await receive(reader)
            seen.append((kind, body))
            activation = struct.pack('!HHB4x', 0x0E00, 1, 0 if service == 'routing_rejected' else 0x10)
            writer.write(packet(6, activation)); await writer.drain()
            if service == 'routing_rejected': return
            kind, body = await receive(reader); seen.append((kind, body))
            assert body[:4] == b'\x0E\x00\x00\x01'
            request = body[4:]
            if service == 'timeout':
                await reader.read()
                return
            if service == 'bad_header': writer.write(b'\x02\x00\x80\x01\x00\x00\x00\x05')
            elif service == 'oversized': writer.write(struct.pack('!BBHI', 2, 253, 0x8001, 65537))
            elif service == 'nack': writer.write(packet(0x8003, b'\x00\x01\x0E\x00\x02'))
            else:
                addresses = b'\x00\x01\x0E\x00'
                writer.write(packet(7)); await writer.drain()
                assert await receive(reader) == (8, b'\x0E\x00')
                writer.write(packet(0x8002, addresses + b'\x00'))
                writer.write(packet(0x8001, addresses + bytes((127, request[0], 120))))
                if service == 'negative': response = b'\x7F\x22\x31'
                elif service == 'mismatch': response = b'\x62\xF1\x91WRONG'
                elif service == 'dtcs': response = b'\x59\x02\xFF\x03\x02\x00\x08'
                else: response = b'\x62\xF1\x90WDBUF56X06B123456'
                frame = packet(0x8001, addresses + response)
                writer.write(frame[:5]); await writer.drain()
                writer.write(frame[5:])
            await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close(); await writer.wait_closed(); finished.set()

    server = await asyncio.start_server(gateway, '127.0.0.1', 0)
    port = server.sockets[0].getsockname()[1]
    try:
        request = DoipRead(host='127.0.0.1', port=port, source_address=0x0E00, target_address=1,
                           timeout=0.2 if service == 'timeout' else 2,
                           **({'dtc_status_mask': 255} if service == 'dtcs' else {'did': 0xF190}))
        if service in {'vin', 'dtcs'}:
            result = await read_doip(request)
            assert result['read_only'] and not result['hardware_verified']
            assert result['response_hex'].startswith('5902' if service == 'dtcs' else '62F190')
        else:
            with pytest.raises(HTTPException) as error: await read_doip(request)
            assert error.value.status_code == 502
        assert seen[0] == (5, b'\x0E\x00\x00\x00\x00\x00\x00')
        assert all(frame[0] in (5, 0x8001) for frame in seen)
        await asyncio.wait_for(finished.wait(), 2)
    finally:
        server.close(); await server.wait_closed()


@pytest.mark.asyncio
@pytest.mark.parametrize('payload', [b'\x04', b'\x2E\xF1\x90', b'\x31\x01\x00', b'\x10\x03', b'\x19', b'\x22\x01'])
async def test_doip_rejects_write_or_unimplemented_services_before_network(payload):
    client = DoipClient('invalid.invalid', source_address=0x0E00, target_address=1)
    with pytest.raises(ValueError): await client.read(payload)
    assert client.writer is None


@pytest.mark.asyncio
@pytest.mark.parametrize('kwargs', [{}, {'did':1,'dtc_status_mask':255}])
async def test_api_requires_exactly_one_read_operation(kwargs):
    with pytest.raises(HTTPException) as error:
        await read_doip(DoipRead(host='invalid.invalid',source_address=0x0E00,target_address=1,**kwargs))
    assert error.value.status_code == 422


@pytest.mark.parametrize('pgn', [0xFECA, 0xFECB])
def test_j1939_single_frame_dm_capture_preserves_spn_fmi_lamps_and_source(pgn):
    spn, fmi, occurrence = 123456, 5, 12
    payload = bytes((0x40, 0xFF, spn & 255, (spn >> 8) & 255,
                     ((spn >> 11) & 224) | fmi, occurrence, 255, 255))
    result = decode_j1939(J1939Frame(arbitration_id=0x18000000 | (pgn << 8) | 0x80, data=payload.hex()))
    assert result['pgn'] == pgn and result['source_address'] == 128
    assert result['lamp_status'] == 0x40 and not result['hardware_verified']
    assert result['dtcs'][0]['spn'] == spn
    assert result['dtcs'][0]['fmi'] == fmi
    assert result['dtcs'][0]['occurrence_count'] == occurrence


@pytest.mark.parametrize('identifier,data', [(0x18F00480,'0000000000000000'),(0x18FECA80,'000001'),(0x18FECA80,'0000010203040001'),(0x18FECA80,'bad!')])
def test_j1939_wrong_pgn_truncation_and_invalid_padding_rejected(identifier, data):
    with pytest.raises(HTTPException) as error:
        decode_j1939(J1939Frame(arbitration_id=identifier, data=data))
    assert error.value.status_code == 422


def test_j1939_legacy_conversion_never_fabricates_modern_spn():
    result = decode_diagnostic_frame(0x18FECA80,b'\x00\x00\x01\x02\x03\x80')
    assert result['dtcs'][0]['spn'] is None
    assert result['dtcs'][0]['status'] == 'legacy_conversion_requires_profile'


def bam_frames():
    from api.advanced_obd_routes import J1939Frame
    data = b'\x40\xFF' + b'\x01\x02\x03\x04' + b'\x05\x06\x07\x08'
    header = b'\x20\x0A\x00\x02\xFF\xCA\xFE\x00'
    return [J1939Frame(arbitration_id=0x18ECFF80,data=header.hex()),
            J1939Frame(arbitration_id=0x18EBFF80,data=(b'\x01'+data[:7]).hex()),
            J1939Frame(arbitration_id=0x18EBFF80,data=(b'\x02'+data[7:]+b'\xFF'*4).hex())]


def test_complete_j1939_bam_capture_decodes_multiple_dtcs():
    from api.advanced_obd_routes import J1939Capture, decode_j1939_bam
    result = decode_j1939_bam(J1939Capture(frames=bam_frames()))
    assert result['transport'] == 'TP.BAM' and result['kind'] == 'DM1'
    assert len(result['dtcs']) == 2 and result['source_address'] == 128
    assert [x['raw'] for x in result['dtcs']] == ['01020304','05060708']


@pytest.mark.parametrize('issue', ['missing','sequence','source','padding','control','unsupported_pgn'])
def test_j1939_bam_capture_rejects_corruption(issue):
    from api.advanced_obd_routes import J1939Capture, decode_j1939_bam
    frames = bam_frames()
    if issue == 'missing': frames.pop()
    elif issue == 'sequence': frames[2].data = '03'+frames[2].data[2:]
    elif issue == 'source': frames[1].arbitration_id += 1
    elif issue == 'padding': frames[2].data = frames[2].data[:-2]+'00'
    elif issue == 'control': frames[0].data = '10'+frames[0].data[2:]
    elif issue == 'unsupported_pgn': frames[0].data = frames[0].data[:-6]+'04F000'
    with pytest.raises(HTTPException) as error:
        decode_j1939_bam(J1939Capture(frames=frames))
    assert error.value.status_code == 422


def j1708_packet(data):
    return bytes(data)+bytes(((-sum(data)) & 255,))


def test_j1587_valid_checksum_fixed_variable_and_extended_parameters():
    from api.advanced_obd_routes import decode_j1708, J1708Packet
    packet = j1708_packet([128, 84, 80, 190, 0, 40, 194, 2, 3, 4, 255, 84, 25])
    result = decode_j1708(J1708Packet(data=packet.hex()))
    assert result['checksum_valid'] and result['mid'] == 128
    assert result['parameters'] == [{'pid':84,'raw_hex':'50'}, {'pid':190,'raw_hex':'0028'},
                                    {'pid':194,'raw_hex':'0304'}, {'pid':340,'raw_hex':'19'}]
    assert not result['hardware_verified']


@pytest.mark.parametrize('data', [b'\x80\x54\x00\x00',j1708_packet([127,84,2]),
    j1708_packet([128,190,2]),j1708_packet([128,194,5,2]),j1708_packet([128,254,0]),
    j1708_packet([128,84,2,255]),j1708_packet([128,84,2,194]),j1708_packet([128,194,0]),b'\x80'*22])
def test_j1587_invalid_checksum_lengths_and_reserved_ids_rejected(data):
    from api.advanced_obd_routes import decode_j1708, J1708Packet
    with pytest.raises(HTTPException) as error:
        decode_j1708(J1708Packet(data=data.hex()))
    assert error.value.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['vin','dtc','extended','wrong_did','negative','adapter_rejected','kline','bad_bitmap','bad_width'])
async def test_addressed_elm_uds_restores_generic_polling_over_real_tcp(mode):
    from vehicle.obd.client import GenericObdClient
    from vehicle.obd.adapters.tcp_wifi import ObdWifiTransport
    commands = []
    finished = asyncio.Event()

    async def adapter(reader, writer):
        try:
            while raw := await reader.readuntil(b'\r'):
                command = raw.decode().strip()
                commands.append(command)
                if command == '0100': response = '4100BE' if mode == 'bad_bitmap' else '4100BE1FA813'
                elif command == 'ATDPN': response = 'A3' if mode == 'kline' else 'A7' if mode == 'extended' else 'A6'
                elif command.startswith('ATSH') and mode == 'adapter_rejected': response = '?'
                elif command == '22F190':
                    response = ('62F19100' if mode == 'wrong_did' else '7F2231' if mode == 'negative'
                                else '62F1905744425546353658303642313233343536')
                elif command == '1902FF': response = '5902FF03020008'
                elif command == '010C': response = '410C1AF8'
                else: response = command+'\rOK' if command == 'ATE0' else 'OK'
                writer.write((response+'>').encode()); await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError): pass
        finally:
            writer.close(); await writer.wait_closed(); finished.set()

    server = await asyncio.start_server(adapter,'127.0.0.1',0)
    transport = ObdWifiTransport('127.0.0.1',server.sockets[0].getsockname()[1])
    client = GenericObdClient(transport,protocol_id='can-29-500' if mode == 'extended' else 'can-11-500')
    try:
        await client.connect()
        command = b'\x19\x02\xFF' if mode == 'dtc' else b'\x22\xF1\x90'
        if mode in {'vin','dtc','extended'}:
            response = await client.read_uds(0x18DA10F1 if mode == 'extended' else 0x7E0,
                                             0x18DAF110 if mode == 'extended' else 0x7E8,command)
            assert response.startswith(b'\x59\x02' if mode == 'dtc' else b'\x62\xF1\x90')
        else:
            with pytest.raises(ValueError):
                await client.read_uds(0x1000 if mode == 'bad_width' else 0x7E0,0x7E8,command)
        if mode not in {'bad_bitmap','kline','bad_width'}:
            assert commands.count('ATSP7' if mode == 'extended' else 'ATSP6') == 2
            assert commands[-1] == '0100'
            assert ('ATSH18DA10F1' if mode == 'extended' else 'ATSH7E0') in commands
        assert await client.read_pid(12) == bytes.fromhex('1AF8')
    finally:
        await client.disconnect(); server.close(); await server.wait_closed()
        await asyncio.wait_for(finished.wait(),2)


@pytest.mark.asyncio
async def test_elm_uds_api_is_read_only_and_rejects_simulator(monkeypatch):
    from types import SimpleNamespace
    import api.state as state
    from api.advanced_obd_routes import ElmUdsRead, read_elm_uds
    monkeypatch.setattr(state,'vci_manager',SimpleNamespace(status=lambda _:SimpleNamespace(connection_type='simulator')))
    with pytest.raises(HTTPException) as error:
        await read_elm_uds(ElmUdsRead(device_id='simulator-vci',request_id=0x7E0,response_id=0x7E8,did=0xF190))
    assert error.value.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize('facade',[False,True])
async def test_elm_uds_api_supports_both_physical_manager_shapes(monkeypatch,facade):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    import api.state as state
    from api.advanced_obd_routes import ElmUdsRead, read_elm_uds
    read = AsyncMock(return_value=b'\x62\xF1\x90VIN')
    physical = SimpleNamespace(connected_obd=lambda _:SimpleNamespace(read_uds=read))
    manager = SimpleNamespace(_physical=lambda:physical) if facade else physical
    manager.status = lambda _:SimpleNamespace(connection_type='Wi-Fi')
    monkeypatch.setattr(state,'vci_manager',manager)
    result = await read_elm_uds(ElmUdsRead(device_id='wifi:adapter',request_id=0x7E0,response_id=0x7E8,did=0xF190))
    assert result['read_only'] and result['response_hex'] == '62F19056494E'
    read.assert_awaited_once_with(0x7E0,0x7E8,b'\x22\xF1\x90')


@pytest.mark.asyncio
async def test_generic_pid_polling_cannot_interleave_addressed_uds_configuration():
    from vehicle.obd.adapters.simulator import SimulatorTransport
    from vehicle.obd.client import GenericObdClient
    configured = asyncio.Event()
    commands = []

    class AdapterFixture(SimulatorTransport):
        async def write(self, data):
            await super().write(data)
            commands.append(self.last_command)
            if self.last_command.startswith('ATSH'):
                configured.set()
                await asyncio.sleep(0)

        async def read_until(self, terminator=b'>', timeout=2):
            response = {'0100':'4100BE1FA813','ATDPN':'A6','010C':'410C1AF8',
                        '22F190':'62F19056494E'}.get(self.last_command,'OK')
            return (response+'>').encode()

    transport = AdapterFixture()
    await transport.connect()
    client = GenericObdClient(transport,protocol_id='can-11-500')
    uds = asyncio.create_task(client.read_uds(0x7E0,0x7E8,b'\x22\xF1\x90'))
    await configured.wait()
    pid = asyncio.create_task(client.read_pid(12))
    response, value = await asyncio.gather(uds,pid)
    assert response == b'\x62\xF1\x90VIN' and value == b'\x1A\xF8'
    assert commands[-2:] == ['0100','010C']
    assert commands.index('22F190') < commands.index('ATZ') < commands.index('010C')


@pytest.mark.parametrize('status,confirmed',[(0,False),(1,False),(4,False),(8,True),(0x28,True),(0x80,False),(9,True)])
def test_uds_confirmed_dtc_uses_confirmed_status_bit(status,confirmed):
    from vehicle.uds.decoder import UdsDtcRecord
    assert UdsDtcRecord(0x030200,'P030200',status).confirmed is confirmed
