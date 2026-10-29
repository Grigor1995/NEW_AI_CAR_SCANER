"""Adapter-injected ELM read-only protocol detection; no vehicle needed."""
import pytest
from vehicle.protocol.elm327_probe import (
    discover_elm_obd_protocol, is_obd_mode_01_supported_pids_reply,
)


@pytest.mark.parametrize("message", [
    "41 00 BE 1F A8 13",
    "7E8 06 41 00 BE 1F A8 13",
    "SEARCHING...\r41 00 00 00 00 00\r>",
])
def test_valid_pid_supported_reply(message):
    assert is_obd_mode_01_supported_pids_reply(message)


@pytest.mark.parametrize("message", ["NO DATA", "0100", "41 01 12 20", ""])
def test_malformed_or_nonobd_reply_is_rejected(message):
    assert not is_obd_mode_01_supported_pids_reply(message)


@pytest.mark.asyncio
async def test_real_read_only_elm_protocol_handshake_verifies_response():
    seen = []
    responses = {
        "ATSP0": "OK", "0100": "41 00 98 3B 80 13",
        "ATDPN": "A6",
    }
    async def transport(cmd):
        seen.append(cmd)
        return responses[cmd]
    result = await discover_elm_obd_protocol(transport)
    assert seen == ["ATSP0", "0100", "ATDPN"]
    assert result["status"] == "ecu_observed"
    assert result["protocol_id"] == "iso15765_4_can11_500"
    assert result["confirmed_ecu_communication"]
    assert not any(c in seen for c in ("04", "2E", "31", "34"))


@pytest.mark.asyncio
async def test_adapter_alone_does_not_confirm_obd_support():
    async def transport(command):
        return {"ATSP0": "OK", "0100": "NO DATA", "ATDPN": "A6"}[command]
    result = await discover_elm_obd_protocol(transport)
    assert result["status"] == "adapter_only"
    assert not result["confirmed_ecu_communication"]


@pytest.mark.asyncio
async def test_probe_error_is_structured_and_not_claimed_supported():
    async def transport(command):
        raise TimeoutError("adapter timeout")
    result = await discover_elm_obd_protocol(transport)
    assert result["status"] == "error"
    assert result["protocol_id"] is None
    assert result["commands"] == []


def test_partial_obd_header_is_not_measured_communication():
    assert not is_obd_mode_01_supported_pids_reply("41 00 BE")
    assert not is_obd_mode_01_supported_pids_reply("7E8 06 41 00")


@pytest.mark.asyncio
async def test_partial_mode_01_reply_never_proves_ecu_protocol():
    async def command(code):
        return {"ATSP0":"OK","0100":"41 00 BE","ATDPN":"A6"}[code]
    result = await discover_elm_obd_protocol(command)
    assert result["status"] == "adapter_only"
    assert result["confirmed_ecu_communication"] is False
