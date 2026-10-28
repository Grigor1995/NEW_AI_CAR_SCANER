# OBD read operations

On connection the controller sends bounded initialization commands, requests the supported PID bitmap and polls only supported RPM(0C), speed(0D), coolant(05). Stored DTC service 03 is available on explicit request. Shared parser supports DTC response service selection; pending/permanent/freeze-frame/VIN UI orchestration is not complete. The live view retains at most 60 actual samples per measurement for traces and clears them on disconnect/reconnect. No synthetic trace points are generated.

Raw read allowlist permits standard read families and setup but never arbitrary UDS/header/write payloads.

Measurement quality is valid/unavailable/unsupported/stale/invalid; numeric values are absent when invalid. Original units, UTC timestamp and VEHICLE_MEASURED provenance are retained. Disconnect clears values and faults rather than presenting them as live. Values are live responses from a socket, but physical hardware validation is NOT RUN. Generic source and protocol compatibility require an actual adapter/vehicle matrix.
