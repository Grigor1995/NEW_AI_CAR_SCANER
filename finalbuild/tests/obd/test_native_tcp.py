"""Actual loopback sockets, never physical-hardware certification."""
import asyncio
from contextlib import suppress
import pytest

pytest.importorskip('_obd_native', reason='optional C++ extension not built')
from vehicle.obd.adapters.native_tcp import NativeObdWifiTransport
from vehicle.obd.client import GenericObdClient
from vehicle.obd.transport import TransportError
from vehicle.acquisition.factory import build_obd_transport


@pytest.mark.asyncio
async def test_existing_client_initializes_and_decodes_native_socket():
    commands = []

    async def adapter(reader, writer):
        try:
            while data := await reader.readuntil(b'\r'):
                command = data.decode().strip()
                commands.append(command)
                reply = {'ATZ': b'ELM327', '0100': b'410008180000',
                         '010C': b'410C1AF8', '03': b'430302'}.get(command, b'OK')
                writer.write(reply[:2])
                await writer.drain()
                await asyncio.sleep(0.001)
                writer.write(reply[2:] + b'\r>')
                await writer.drain()
        except asyncio.IncompleteReadError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(adapter, '127.0.0.1', 0)
    async with server:
        transport = build_obd_transport('wifi', {'host': '127.0.0.1',
            'port': server.sockets[0].getsockname()[1], 'native_tcp': True})
        assert isinstance(transport, NativeObdWifiTransport)
        client = GenericObdClient(transport)
        try:
            await client.connect()
            assert transport.connected
            raw = await client.command('010C')
            assert raw == '410C1AF8'
            assert client.protocol.rpm(client.protocol.parse_pid(12, raw)) == 1726
            assert await client.read_dtcs() == ['P0302']
        finally:
            await client.disconnect()
        assert not transport.connected
        assert commands[:7] == ['ATZ', 'ATE0', 'ATL0', 'ATS0', 'ATH0', 'ATCAF1', 'ATSP0']


@pytest.mark.asyncio
@pytest.mark.parametrize('command', [b'04\r', b'ATSH7E0\r', b'2E123400\r', b'010C\r04\r', b'010C', b'01GG\r', b' ' * 65 + b'010C\r'])
async def test_modifying_or_malformed_commands_never_reach_socket(command):
    received = []
    finished = asyncio.Event()

    async def adapter(reader, writer):
        received.append(await reader.read())
        writer.close()
        await writer.wait_closed()
        finished.set()

    server = await asyncio.start_server(adapter, '127.0.0.1', 0)
    async with server:
        transport = NativeObdWifiTransport('127.0.0.1', server.sockets[0].getsockname()[1])
        await transport.connect()
        with pytest.raises(TransportError):
            await transport.write(command)
        await asyncio.wait_for(finished.wait(), 1)
        assert received == [b'']
        assert not transport.connected


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['timeout', 'disconnect', 'overflow', 'cancel'])
async def test_failure_closes_connection_and_does_not_block_event_loop(kind):
    finished = asyncio.Event()
    async def adapter(reader, writer):
        try:
            if kind == 'disconnect':
                return
            if kind == 'overflow':
                writer.write(b'A' * 70000)
                await writer.drain()
            with suppress(ConnectionResetError):
                await reader.read()
        finally:
            writer.close()
            with suppress(ConnectionResetError):
                await writer.wait_closed()
            finished.set()
    server = await asyncio.start_server(adapter, '127.0.0.1', 0)
    async with server:
        transport = NativeObdWifiTransport('127.0.0.1', server.sockets[0].getsockname()[1])
        await transport.connect()
        task = asyncio.create_task(transport.read_until(timeout=0.06))
        await asyncio.sleep(0.005)
        if kind == 'cancel':
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            expected = {"timeout": "timeout", "disconnect": "disconnected", "overflow": "64 KiB"}[kind]
            with pytest.raises(TransportError, match=expected):
                await task
        assert not transport.connected
        await transport.disconnect()
        await asyncio.wait_for(finished.wait(), 1)


@pytest.mark.asyncio
async def test_coalesced_responses_preserve_trailing_frame():
    async def adapter(reader, writer):
        writer.write(b'first>second>')
        await writer.drain()
        await reader.read()
        writer.close()
        await writer.wait_closed()
    server = await asyncio.start_server(adapter, '127.0.0.1', 0)
    async with server:
        transport = NativeObdWifiTransport('127.0.0.1', server.sockets[0].getsockname()[1])
        await transport.connect()
        assert await transport.read_until() == b'first>'
        assert await transport.read_until() == b'second>'
        await transport.disconnect()


@pytest.mark.asyncio
@pytest.mark.parametrize('host,port', [('localhost', 35000), ('127.0.0.1', 0), ('127.0.0.1', 65536)])
async def test_invalid_address_is_rejected(host, port):
    transport = NativeObdWifiTransport(host, port)
    with pytest.raises(TransportError):
        await transport.connect()
    assert not transport.connected


@pytest.mark.asyncio
async def test_disconnected_read_and_write_fail():
    transport = NativeObdWifiTransport('127.0.0.1')
    with pytest.raises(TransportError):
        await transport.read_until()
    with pytest.raises(TransportError):
        await transport.write(b'010C\r')


@pytest.mark.asyncio
async def test_reconnect_clears_buffer_and_invalid_deadline_fails_closed():
    count = 0
    async def adapter(reader, writer):
        nonlocal count
        count += 1
        writer.write(b'first>stale>' if count == 1 else b'new>')
        await writer.drain()
        await reader.read()
        writer.close()
        await writer.wait_closed()
    server = await asyncio.start_server(adapter, '127.0.0.1', 0)
    async with server:
        transport = NativeObdWifiTransport('127.0.0.1', server.sockets[0].getsockname()[1])
        await transport.connect()
        assert await transport.read_until() == b'first>'
        await transport.disconnect()
        await transport.connect()
        assert await transport.read_until() == b'new>'
        with pytest.raises(TransportError, match='Timeout'):
            await transport.read_until(timeout=float('nan'))
        assert not transport.connected


@pytest.mark.asyncio
async def test_connection_refused_is_not_connected():
    server = await asyncio.start_server(lambda r, w: None, '127.0.0.1', 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()
    transport = NativeObdWifiTransport('127.0.0.1', port)
    with pytest.raises(TransportError):
        await transport.connect()
    assert not transport.connected
