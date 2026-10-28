# Optional native OBD TCP transport

This C++20/pybind11 milestone handles TCP socket ownership, nonblocking connect,
partial writes, bounded prompt-delimited reads, deadlines and cleanup. Existing
`GenericObdClient`, PID/DTC parser, DiagnosticSession and UI remain authoritative.
No performance improvement or physical hardware certification is claimed.

Build from the repository root (Python 3.12 and GCC 14 tested):

```sh
python -m pip install cmake==4.4.4 pybind11==3.1.0
python -m cmake -S native/obd -B .build-tools/obd \
  -Dpybind11_DIR="$(python -m pybind11 --cmakedir)" \
  -DPython_EXECUTABLE="$(command -v python)" -DCMAKE_BUILD_TYPE=Release
python -m cmake --build .build-tools/obd -j 2
PYTHONPATH="$PWD/.build-tools/obd" python -m pytest finalbuild/tests/obd/test_native_tcp.py -q
```

Add `.build-tools/obd` to the launch process's PYTHONPATH and set
`native_tcp: true` in an existing Wi-Fi acquisition/device connection config.
Default false preserves the original Python transport. If enabled without a
built extension, connection fails explicitly rather than silently falling back.
No new UI or duplicate diagnostic engine is added.

Current platform boundary: Linux validated, POSIX APIs used; macOS untested.
Windows compilation, Android JNI and iOS integration remain future milestones.
Use existing transports on those platforms. Numeric IPv4 only; no DNS/IPv6.
BLE, USB, custom VCI and UDS addressing are not implemented by this extension.
The allowlist permits existing generic ELM setup and read services 01/03/07/09/0A,
ATRV and ATDPN. ECU writes, DTC clear and custom header/UDS commands are rejected.
Unsupported commands do not imply unsupported vehicle capability globally.

Use only with an explicitly authorized, trusted local adapter. These plain TCP
adapters supply no TLS/authentication; never expose them to the public Internet.
In managed cloud environments external adapters also require configured network
access; loopback tests do not prove access to a user's vehicle.

Calls run off the asyncio/UI thread and release the Python GIL. A transport has
one owning async wrapper; the existing client serializes complete commands.
Cancellation waits for the bounded in-flight call before closing (typically the
configured read timeout, at most 120 s). This favors safe ownership over immediate
abort; interruptible cancellation and cross-platform transport abstraction remain
follow-up work. Do not call the low-level extension concurrently directly.

Test outcomes in the current implementation report distinguish loopback from
hardware tests. Benchmarks must separate socket round trips from parsing and
vehicle polling before any acceleration claim.
