# OBD and hardware connectivity

Existing modules: `backend/device`, `backend/vehicle`, `backend/obd` and native
mobile bridges. ELM codes 0–9 describe generic adapter-selected protocols;
heavy-duty/UDS/DoIP support is explicit and capability-dependent. CAN-FD,
OBDonUDS, WWH-OBD and arbitrary OEM diagnostics are not universal implemented
support. Reuse current retry/reconnect, supported-PID planning and simulator.

Desktop supports serial/USB plus supported wireless adapters. Android uses
permission-aware Classic/BLE/Wi-Fi/USB. iOS supports implemented BLE/Wi-Fi;
generic Classic SPP/USB cannot be assumed. Custom hardware needs an actual
adapter implementation and capability negotiation. Default reads only; ECU
writes require a separate supported safety/authorization design. New identity
work cannot imply permission to run arbitrary ECU commands.

Hardware acceptance: record adapter/firmware, vehicle, ignition, protocol,
capability bitmaps, command/response timing, disconnect and recovery. Label
SIMULATOR PASS, REAL HARDWARE PASS, NOT EXECUTED, BLOCKED or UNSUPPORTED.
No real-vehicle test was performed for this branch. See existing
`finalbuild/docs/obd/REAL_OBD_AUDIT.md` and `SUPPORTED_PID_POLLING.md`.

## C++ TCP milestone

`native/obd` and `vehicle/obd/adapters/native_tcp.py` implement optional C++20
Wi-Fi TCP I/O behind the existing transport interface. Enable explicitly with
`native_tcp: true`; default transport is unchanged. Linux loopback validation
is not physical adapter coverage. Windows/mobile bindings, USB/BLE, UDS
addressing and native protocol decoding remain outside this milestone.
See [build instructions and safety limits](../native/obd/README.md).
