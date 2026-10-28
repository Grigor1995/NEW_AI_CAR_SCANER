# Performance methodology

Separate domain parsing/rules latency from physical polling, network wait, AI inference, GUI startup and memory/battery use. The protocol benchmark uses repeated fixed RPM reply decoding and records p50/p95/p99 in microseconds on the current compiler/host. It is not an OBD polling or production SLA. Initial domain target is p95 <90 ms where feasible.

CTest timeout/fragmentation integration checks show the event loop can service loopback signals while adapters wait. Password work is off the GUI thread; local HTTP password hashing is synchronous and needs concurrency/load hardening before remote deployment. ASan/UBSan and GCC line/branch coverage are separate builds. Native battery, full UI interaction latency, multi-client API load and real device timing are NOT RUN.
