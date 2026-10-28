# Implemented local API v1

See api/openapi.json for current typed request/response contracts. The C++ backend binds 127.0.0.1 only. No TLS/public deployment is provided.

| Path | Methods | Authorization |
|---|---|---|
| /api/v1/health | GET | public local health |
| /api/v1/capabilities | GET | public implementation-status metadata |
| /api/v1/accounts | POST | local registration; USER only |
| /api/v1/sessions | POST | password login; opaque expiring token |
| /api/v1/sessions/current | DELETE | bearer; revoke current token |
| /api/v1/me | GET | bearer |
| /api/v1/vehicles | GET, POST | bearer; owner scope |
| /api/v1/settings | GET, PUT | bearer; account scope |

Responses distinguish 401 auth failure, 422 invalid data, 429 bounded local auth throttle and 500 redacted operational errors. JSON body limit is 16 KiB after HTTP parsing; connection-level body/concurrency limits remain public-host hardening work. No remote device/write/payment endpoints exist. Correlation IDs and idempotency tokens are planned before extracting network macroservices.
