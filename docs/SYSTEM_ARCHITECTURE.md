# System architecture

The 2026-10-29 functionality migration adds a local source-compatible companion
at port 8001. PlatformClient uses asynchronous Qt HTTP for diagnostic sessions,
evidence, hypotheses, guided tests and knowledge APIs. The companion preserves
Python reasoning/business/driver services and calls cda_engine through a typed C
ABI for telemetry statistics and JSON ABI for PID snapshots.
[Exact boundaries and limitations](migration/README.md).
The following native V3 boundaries remain separate from that companion.

The modular runtime consists of a pure C++ domain library (cda_core), Qt adapters and local application services (cda_services), a shared QML client (car_diagnostic), and a loopback C++ HTTP host (cda_backend). Core interfaces and data do not depend on QML, SQL, HTTP or device drivers. Constructors own dependencies; no global mutable service registry exists.

Application -> identity/vehicle service -> scoped SQLite repository; application -> diagnostic controller -> asynchronous Qt transport -> authorized ELM adapter -> protocol decoder -> measurement/DTC model. Rules consume evidence and retain explicit provenance. Native engineering values are converted only for presentation. Qt adapters live under core/transport but are linked into cda_services, not cda_core.

The desktop client currently uses an in-process local Store with its own app-data database. The standalone backend uses a separately specified SQLite file. They are NOT synchronized and the client does not claim remote API integration. PostgreSQL and authenticated remote synchronization are planned. Three primary role modes are USER/CUSTOMER/ADMIN; MARKET is a separate merchant capability. Role assignment exists; complete professional/admin workflows do not.

No real ECU write executor, background scheduler, notification delivery, remote AI/RAG, repair provider, merchant commerce or installer is active. The dashboard distinguishes these proposals from implemented slices.
