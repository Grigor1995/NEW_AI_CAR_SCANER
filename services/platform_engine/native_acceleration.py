"""C++ kernels with an explicit, observable Python fallback.

No Python objects cross the ABI; ctypes releases the GIL during each native call.
"""
import ctypes
import json
import os
from pathlib import Path

_library = None
_installed = False
_error = None
_dll_directories = []


def load():
    global _library, _error
    if _library is not None:
        return _library
    if os.name == 'nt' and not _dll_directories:
        qt_bin = Path(os.getenv('CDA_QT_BIN', 'C:/msys64/ucrt64/bin'))
        if qt_bin.is_dir():
            _dll_directories.append(os.add_dll_directory(str(qt_bin)))
    root = Path(__file__).resolve().parents[2]
    configured = os.getenv('CDA_ENGINE_LIBRARY')
    paths = [Path(configured)] if configured else [root / 'build/dev' / name for name in
        ('cda_engine.dll', 'libcda_engine.dll', 'libcda_engine.so', 'libcda_engine.dylib')]
    for path in paths:
        if path.is_file():
            try:
                library = ctypes.CDLL(str(path.resolve()))
                library.cda_engine_json.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
                library.cda_engine_json.restype = ctypes.c_char_p
                library.cda_stats_binary.argtypes = [ctypes.POINTER(ctypes.c_int64),
                    ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_double), ctypes.c_size_t,
                    ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_int64)]
                library.cda_stats_binary.restype = ctypes.c_int
                _library = library
                _error = None
                return library
            except (OSError, AttributeError) as exc:
                _error = str(exc)
    _error = _error or 'Native library not built; Python fallback active'
    return None


def invoke(operation, payload):
    library = load()
    if library is None:
        raise RuntimeError(_error)
    result = json.loads(library.cda_engine_json(operation.encode(), json.dumps(payload, allow_nan=False).encode()))
    if 'error' in result:
        raise ValueError(result['error'])
    return result


def install():
    global _installed
    if _installed:
        return True
    if load() is None:
        return False
    from telemetry import analysis
    from telemetry.models import SignalStats
    from obd import decoding
    original_snapshot = decoding.decode_snapshot

    def compute_stats(session_id, pid, samples):
        # Retain source behavior for nonfinite inputs rather than fabricating statistics.
        import math
        if len(samples) > 1000000 or any(not math.isfinite(s.value) for s in samples):
            return original_stats(session_id, pid, samples)
        return fast_stats(session_id, pid, samples)

    def decode_snapshot(responses):
        normalized = {key.upper().replace(' ', ''): value for key, value in responses.items()}
        result = invoke('decode_snapshot', normalized)
        if result['errors']:
            # Preserve source-specific malformed/missing-frame diagnostics exactly.
            return original_snapshot(responses)
        # Protocol negotiation remains source-identical, including error semantics.
        result['protocol'] = None
        if 'ATDPN' in normalized:
            try:
                from obd.protocols import detected_protocol
                result['protocol'] = detected_protocol(normalized['ATDPN'])
            except ValueError as exc:
                result['errors']['ATDPN'] = str(exc)
        # Preserve the source unit spelling.
        for pid in decoding.PIDS:
            result['units'][pid.key] = pid.unit
        return result

    original_stats = analysis.compute_stats
    analysis.compute_stats = compute_stats
    decoding.decode_snapshot = decode_snapshot
    _installed = True
    return True


def status():
    return {'available': load() is not None, 'kernels': ['decode_snapshot', 'compute_stats'] if _library else [],
            'error': _error}


def pytest_configure(config):
    """Opt-in test plugin: run source contracts with the native kernels installed."""
    if not install():
        raise RuntimeError('Native parity tests require a built cda_engine library')


def fast_stats(session_id, pid, samples):
    from telemetry.models import SignalStats
    xs = [s for s in samples if s.quality != 'INVALID']
    count = len(xs)
    times = (ctypes.c_int64 * count)(*(s.timestamp_ms for s in xs))
    sequence = (ctypes.c_int64 * count)(*(s.sequence or -1 for s in xs))
    values = (ctypes.c_double * count)(*(s.value for s in xs))
    output = (ctypes.c_double * 9)()
    bounds = (ctypes.c_int64 * 2)()
    status_code = load().cda_stats_binary(times, sequence, values, count, output, bounds)
    if status_code:
        raise ValueError(f'Native statistics failed: {status_code}')
    if not count:
        return SignalStats(session_id=session_id, pid=pid, count=0)
    return SignalStats(session_id=session_id, pid=pid, count=count, start_ms=bounds[0], end_ms=bounds[1],
        duration_ms=int(output[8]), min_value=output[0], max_value=output[1], mean=output[2],
        stddev=output[3], mean_abs_delta=output[4], max_abs_delta=output[5],
        slope_per_second=output[6] if output[8]>0 else None,
        sample_rate_hz=output[7] if output[8]>0 else None)
