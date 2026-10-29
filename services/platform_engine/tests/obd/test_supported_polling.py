import pytest
from fastapi.testclient import TestClient
from obd.decoding import supported_polling_plan
from vehicle.obd.client import GenericObdClient
from vehicle.obd.adapters.simulator import SimulatorTransport
from vehicle.acquisition.sources import ObdPollingSource


def bitmap(*pids):
    mask = sum(1 << (32-pid) for pid in pids)
    return f"4100{mask:08X}"


def test_bitmap_bit_positions_and_catalog_intersection():
    plan = supported_polling_plan({"01 00": bitmap(1, 5, 12, 13, 32)})
    assert plan["supported_pids"] == [1, 5, 12, 13, 32]
    assert plan["commands"] == ["010C", "010D", "0105"]
    assert "0110" in plan["unsupported_commands"]
    assert plan["capabilities_observed"] and plan["read_only"]
    assert "0120" not in plan["commands"]  # No implemented live channel needs page two.


def test_multiple_ecu_bitmaps_are_combined_without_concatenation():
    raw = "7E8 06 " + " ".join(bytes.fromhex(bitmap(12)).hex()[i:i+2] for i in range(0,12,2))
    raw += "\r18DAF110 06 " + " ".join(bytes.fromhex(bitmap(13)).hex()[i:i+2] for i in range(0,12,2))
    assert supported_polling_plan({"0100": raw})["commands"] == ["010C", "010D"]


@pytest.mark.parametrize("raw", ["NO DATA", "?", "41000010", "410D00100000", "430000100000", "4100GG000000", "410000100000FF"])
def test_invalid_capabilities_never_fall_back_to_all_pids(raw):
    with pytest.raises(ValueError):
        supported_polling_plan({"0100": raw})


def test_zero_bitmap_is_valid_but_does_not_invent_live_channels():
    assert supported_polling_plan({"0100": bitmap()})["commands"] == []


def test_api_accepts_observed_capabilities_and_rejects_bad_frames():
    from api.main import app
    with TestClient(app) as client:
        response = client.post("/api/v1/obd/plan", json={"responses": {"0100": bitmap(12)}})
        assert response.status_code == 200
        assert response.json()["commands"] == ["010C"]
        assert client.post("/api/v1/obd/plan", json={"responses": {"0100": "NO DATA"}}).status_code == 422
        assert client.post("/api/v1/obd/plan", json={"responses": {"0100": "A"*9000}}).status_code == 422


class TracedTransport(SimulatorTransport):
    def __init__(self, responses):
        super().__init__(responses)
        self.commands = []

    async def write(self, data):
        self.commands.append(data.decode().strip())
        await super().write(data)


@pytest.mark.asyncio
async def test_local_reader_polls_only_supported_pids_and_refreshes_on_reconnect():
    transport = TracedTransport({"0100":bitmap(12), "010C":"410C1F40", "0105":"41057B"})
    client = GenericObdClient(transport)
    try:
        await client.connect()
        first = await client.read_standard_live_data()
        second = await client.read_standard_live_data()
        assert first["rpm"] == second["rpm"] == 2000
        assert first["coolant_c"] is None
        assert transport.commands.count("0100") == 1
        assert transport.commands.count("010C") == 2
        assert "0105" not in transport.commands
        await client.disconnect()
        transport.responses["0100"] = bitmap(5)
        await client.connect()
        start = len(transport.commands)
        changed = await client.read_standard_live_data()
        assert changed["coolant_c"] == 83
        assert changed["rpm"] is None
        assert transport.commands[start:] == ["0105"]
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_acquisition_filters_requested_channels_and_closes_empty_plan():
    transport = TracedTransport({"0100":bitmap(12), "010C":"410C1F40"})
    source = ObdPollingSource(GenericObdClient(transport))
    await source.connect()
    assert source.pids == [12]
    await source.disconnect()
    transport.responses["0100"] = bitmap()
    with pytest.raises(ValueError, match="no supported channels"):
        await source.connect()
    assert not transport.connected


@pytest.mark.asyncio
async def test_direct_device_reader_does_not_report_empty_success():
    client = GenericObdClient(SimulatorTransport({"0100":bitmap()}))
    await client.connect()
    try:
        with pytest.raises(ValueError, match="no supported live channels"):
            await client.read_standard_live_data()
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_bad_initial_capability_can_be_retried_after_ecu_wakes_up():
    transport = TracedTransport({"0100":"NO DATA", "010C":"410C1F40"})
    client = GenericObdClient(transport)
    await client.connect()
    try:
        with pytest.raises(ValueError):
            await client.read_standard_live_data()
        transport.responses["0100"] = bitmap(12)
        assert (await client.read_standard_live_data())["rpm"] == 2000
        assert transport.commands.count("0100") == 2
    finally:
        await client.disconnect()
