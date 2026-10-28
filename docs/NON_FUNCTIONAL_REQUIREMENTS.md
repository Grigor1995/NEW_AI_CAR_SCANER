# Non-functional requirements

Domain code is C++20 without Qt dependencies; Qt adapters own networking and UI. Socket work is asynchronous; password derivation runs off the GUI thread. Response buffers are capped at 64 KiB, request JSON at 16 KiB, adapter commands are allowlisted and operations have bounded deadlines. Use RAII for device/cryptographic ownership and scoped SQL connections.

Initial targets: local protocol processing p95 under 90 ms, responsive UI without hardware blocking, and >=90% meaningful critical-core line coverage. Measurements must identify workload, compiler, hardware, percentiles and exclusions. No vehicle polling or production latency guarantee is inferred from local tests. Cross-platform packaging, load/battery tests, distributed abuse protection, accessibility certification, storage lifecycle and live PostgreSQL remain release gates.
