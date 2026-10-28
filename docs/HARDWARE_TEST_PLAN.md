# Hardware validation — NOT RUN

Use recorded adapter model/firmware, transport/platform, authorized vehicle/bench ECU, ignition/power, observed protocol/ECU and supported PID bitmap. Begin read-only with known response captures and independent reference instrument/tool. Verify initialization, three supported PIDs, DTC services, timestamps, malformed responses, timeouts, disconnect/recovery and device permissions.

Only authorized benches may test writes. Require operation-specific verified profile, authenticated qualified CUSTOMER, explicit vehicle/ECU bound one-use confirmation, safe measured state/voltage, durable prepare/execute/verify audit and documented recovery. Do not test dangerous writes on ordinary vehicles; no safety/emissions/system defeat is permitted. Label every result LOOPBACK PASS, SIMULATOR PASS, REAL HARDWARE PASS, NOT RUN, BLOCKED or UNSUPPORTED with precise scope.
