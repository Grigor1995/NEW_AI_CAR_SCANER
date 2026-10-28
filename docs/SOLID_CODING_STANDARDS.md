# SOLID coding standards

Single responsibility: protocol decoding, write validation, transport, orchestration, identity persistence and QML presentation are separate modules. Device connection/read/write/decoder/notification contracts are segregated under core/interfaces. High-level protocol/safety/rules code accepts values or interfaces rather than UI/SQL drivers. RAII owns connections and cryptographic contexts. No payments or provider dependencies are forced into diagnostics.

Extension contracts must retain deadline, availability, provenance and error semantics. A new transport must pass fragmentation, timeout, disconnect and read-only tests. A new decoder may not transform wrong-service/truncated bytes into plausible numbers. Future writers must accept operation-specific permits and must never expose arbitrary ECU bytes. The current QtElm is a concrete adapter, not an implementation of every abstract core contract: a fully injected transport executor is a remaining refactor before adding advanced hardware.

Use scripts/test/source_contracts.py, local clang-format, compiler warnings, CTest, ASan/UBSan and GCC coverage. Tests should exercise contracts and negative authorization branches, not merely mirror methods.
