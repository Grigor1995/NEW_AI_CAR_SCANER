"""Differential checks of the compiled C++ ABI against the imported source."""
import importlib.util
import random
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / 'services/platform_engine'
sys.path[:0] = [str(ENGINE), str(ENGINE/'backend')]
from native_acceleration import invoke, load, fast_stats
from telemetry.analysis import compute_stats
from telemetry.models import TelemetrySample
from obd.decoding import decode_snapshot, PIDS
import pytest


def test_native_library_required():
    assert load() is not None, 'Build cda_engine before native contract tests'


@pytest.mark.parametrize('count', [0, 1, 2, 10, 1000])
def test_stats_match_source_with_out_of_order_invalid_and_equal_timestamps(count):
    rng = random.Random(42 + count)
    session = uuid4()
    samples = [TelemetrySample(session_id=session, timestamp_ms=rng.randrange(0, 50)*100,
        sequence=i, pid='rpm', value=rng.uniform(500, 7000),
        quality='INVALID' if i % 7 == 0 else 'GOOD') for i in range(count)]
    expected = compute_stats(session, 'rpm', samples).model_dump(mode='json')
    packed = fast_stats(session, 'rpm', samples).model_dump(mode='json')
    result = invoke('compute_stats', {'session_id':str(session), 'pid':'rpm',
        'samples':[s.model_dump(mode='json') for s in samples]})
    from telemetry.models import SignalStats
    actual = SignalStats.model_validate(result).model_dump(mode='json')
    for key in expected:
        if isinstance(expected[key], float):
            assert packed[key] == pytest.approx(expected[key], rel=1e-10, abs=1e-9)
            assert actual[key] == pytest.approx(expected[key], rel=1e-10, abs=1e-9)
        else:
            assert actual[key] == expected[key]
            assert packed[key] == expected[key]


@pytest.mark.parametrize('pid', PIDS)
def test_all_ten_pid_scalings_match_source(pid):
    for value in (0, 1, (1 << (8*pid.length))-1):
        responses={pid.command: '41'+pid.command[2:]+value.to_bytes(pid.length,'big').hex()+'>'}
        actual=invoke('decode_snapshot',responses)
        expected=decode_snapshot(responses)
        assert actual['values'] == expected['values']
        assert set(actual['errors']) == set(expected['errors'])


def test_invalid_native_input_is_contained():
    with pytest.raises(ValueError,match='Unknown native operation'):
        invoke('bad_operation',{})
