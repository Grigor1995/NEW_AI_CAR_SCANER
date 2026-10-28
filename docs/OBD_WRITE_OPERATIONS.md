# OBD write operations — LOCKED

No application, backend or scheduler can send ECU write commands in this milestone. The pure validateWrite policy models only the candidate clear_dtcs operation and rejects all others. Standard clear-DTC execution is not wired to QtElm. UDS writes, RoutineControl, coding/adaptation and flashing are unsupported.

A future operation-specific executor must bind a short-lived one-use permit to the exact authenticated actor, verified vehicle/ECU/adapter, request bytes and current state; prepare/validate/confirm/execute/verify/record with durable audit at every transition. Confirmation cannot be a reusable boolean from a remote client. The current WriteContext is a policy-test value, not proof that hardware has been validated. No security access bypass, seed-key attack or safety/emissions defeat is included. Real write validation requires authorized bench ECUs and documented recovery.
