# AI-CAR-SCANER functionality migration

The user's 2026-10-29 request authorizes restoring the source functionality while
retaining the reference Qt launcher and moving appropriate work to C++.
This extends the earlier from-zero V3 scope. It is a hybrid migration: the UI,
TCP/serial OBD acquisition, ten PID decoders and telemetry statistics run in C++;
existing reasoning/RAG/business services remain Python in a local companion.
A complete C++ rewrite, custom forms for every endpoint, and mobile packaging are
not claimed.

## Repository analysis and provenance

Audited all 975 tracked files on main, enumerated 263 runtime Python modules and
compared nine remote branch references. [Full audit](full-repository-audit.json)
records file Git objects, module symbols and branch deltas.
[Module analysis](MODULE_ANALYSIS.md) lists runtime classes/functions.

Source main: `a71c547b4b58f88f9c09f7f25d86931b79131bd2`.
Additive ecosystem source: `540e00f07b8f60c2788c8d12dea1200817669afb`.
The other remote branches are recorded for analysis; their divergent UI/build
changes are not merged over the requested reference interface.
[Import manifest](source-inventory.json) records source hashes and all 135 API
operations (119 main + 16 ecosystem). Hashes identify imported baselines; the
requirements file additionally includes Windows timezone data. Two imported
files have whitespace-only cleanup, recorded in the manifest.
Old desktop/mobile apps, old launchers, old installers and CI workflows are not
restored. Vehicle portraits and their original reference metadata are retained.

## Functionality mapping

| Source capability | Destination and behavior | Current execution |
|---|---|---|
| Desktop launcher | Existing C++/QML reference UI preserved | Native Linux rendered tests |
| TCP/USB ELM polling | Qt async TCP/desktop serial, PID bitmap discovery across ECUs | C++ integration tests; no physical adapter |
| RPM/speed/coolant/load/IAT/MAF/MAP/throttle/STFT/LTFT | Ten C++ PID definitions; source snapshot ABI uses same scalings | Differential source tests |
| Bluetooth/BLE/J2534/UDS/DoIP/J1939/J1587/ISO-TP | Source vehicle/device drivers and passive decoders retained in companion; original adapter/profile restrictions retained | Source software contracts; physical drivers unverified |
| Sessions, vehicles, symptoms, DTC and evidence CRUD | Source v1 API on companion; native Qt common session forms and API operation selector | HTTP + Qt network workflow |
| Reasoning, hypotheses and test-result feedback | Original diagnostic/intelligence engines; native display of hypotheses/recommended tests and PASS/FAIL/INCOMPLETE actions | Source tests + Qt session analysis |
| Guided decision plans | Original information-gain/risk/prerequisite decision service | Source and HTTP tests |
| Telemetry capture, events, evidence | Source acquisition/event pipeline; C++ packed-array statistics kernel | Source contracts with native kernel installed |
| AI teaching and local lexical retrieval | Source knowledge store; Qt index/search forms; rich file ingestion via local API docs | HTTP + Qt search tests |
| RAG embeddings, pgvector, reranking, ingestion | Source implementations retained | Unit contracts; live PostgreSQL/pgvector not configured |
| Local llama-server/OpenAI-compatible providers | Source HTTP adapters and context/grounding/budget pipeline | Software contracts; no model/provider deployment claimed |
| ECU discovery/multibus/multi-ECU | Source API and network/acquisition modules | Source tests + passive frame HTTP fixture |
| Vehicle catalogue and images | 70 generation references, 199 named engine options, original portraits | API/image tests; not VIN fitment certification |
| JSON/PDF diagnostic reports | Source private reports and Unicode PDF renderer; V3 native JSON report preserved | Real HTTP JSON/PDF checks |
| Professional roles, organization audit/reporting | Source professional_platform service | Source software contracts |
| Accounts/ownership/consent/service centers | Optional ecosystem branch, separate migration and API boundary | 34 SQLite/API tests |
| Existing V3 local accounts/settings | C++ Store stays scoped to its local database; four UI locales | Existing CTest and UI checks |
| Payments, notification delivery, native installers | No new implementation or deployment asserted | Not validated |

## Windows: use the existing UCRT64 build

Close the running application first. In MSYS2 UCRT64:

```bash
cd /c/Users/grigorg/Projects/NEW_AI_CAR_SCANER_V3
git pull --ff-only
cmake --build --preset dev
ctest --preset dev
```

Install official Windows CPython 3.12+ with its `py` launcher. The companion does
not need PySide6. Its Python runtime must be Windows CPython, rather than the
MSYS2 Python distribution, so binary dependencies can use Windows wheels.

```bash
py -3 --version
bash scripts/build/setup_platform_engine.sh
./.engine-venv/Scripts/python.exe scripts/run_platform_engine.py --local-database
```

Keep that terminal running. In a second UCRT64 terminal:

```bash
cd /c/Users/grigorg/Projects/NEW_AI_CAR_SCANER_V3
./build/dev/car_diagnostic.exe
```

Open **Application → Diagnostic platform**, or **Guided Tests / Teach AI /
ECU Network**. Create a diagnostic session, add observed symptoms/reported DTCs,
then analyze. Native adapter readings can be attached only when actually valid
and connected. Source API operations remain available through the operation
selector. **API documentation / file upload** opens the local service's schema
and multipart upload interface. A source operation may need its documented
parameters, credentials, provider or adapter.

The default native library is discovered under `build/dev`. On Windows the
binding adds `C:/msys64/ucrt64/bin` to the DLL search directories. Set
`CDA_QT_BIN` for a different Qt/toolchain bin directory, or `CDA_ENGINE_LIBRARY`
for a different library path. Verify **Check service** reports native available.
Python fallback is explicitly reported if a native library cannot load.

Windows instructions are provided for the user's installed toolchain; the changes
were compiled/executed on Linux here. Windows and Android builds were not run.
An Android device cannot reach the desktop companion using its own loopback
address. LAN/TLS/authenticated remote transport and an Android native package
remain separate work.

## Cloud Linux and repeatable checks

```bash
source /workspace/toolchains/env.sh
cmake --preset dev
cmake --build --preset dev
bash scripts/build/setup_platform_engine.sh
bash scripts/test/platform_engine.sh
.engine-venv/bin/python scripts/run_platform_engine.py
```

With that server running, in another terminal:

```bash
source /workspace/toolchains/env.sh
.engine-venv/bin/python scripts/test/platform_engine_http.py
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  ./build/dev/car_diagnostic --platform-self-test /tmp/platform-workspace.png
```

Normal companion defaults to `local/platform-engine.sqlite`. Existing DATABASE_URL
is respected unless `--local-database` is explicitly selected. That flag changes
only the launched process, chooses the normal local SQLite file and never moves
or deletes PostgreSQL data. Use it when an activated environment inherits an
unavailable PostgreSQL URL. Session/profile persistence uses the selected DB. Some source components,
such as the simple local knowledge store, still have source-original in-memory
lifetimes; do not infer universal durability from SQLite session persistence.

Optional ecosystem mode uses `local/platform-ecosystem.sqlite` by default, runs
its additive Alembic migration and enables the source consent boundary:

```bash
.engine-venv/bin/python scripts/run_platform_engine.py --ecosystem
```

Stop the normal companion before reusing its port. Ecosystem mode intentionally
changes which legacy APIs are exposed; it is not a switch that merges accounts
or silently grants ownership to existing diagnostic sessions. Use its own
`/api/v2/ecosystem` endpoints and login token. The API documentation supports
its bearer authorization.

## Measured validation and remaining limits

[evidence](evidence/) includes actual Linux runs:

- 339 source diagnostic/AI/OBD/telemetry/security tests passed, one pgvector
  integration placeholder skipped; repeated with native kernels installed.
- 34 additional ecosystem DB/API tests passed; combined run 373 passed, one skipped.
- 17 ABI/differential tests cover all ten PID scalings, sorted/out-of-order and
  invalid telemetry, zero/one/many samples, and failure containment.
- Two existing CTest executables passed; existing UI regression 18 checks passed.
- Native Qt→HTTP workflow 10 checks and HTTP workflow 22 checks passed. The HTTP
  workflow verifies all 135 source API operations are registered in live OpenAPI.
  Registration is not proof that each provider-dependent operation succeeds.
- Packed C++ statistics including Python marshalling measured about 2.1–3.6×
  faster than the original Python statistics on this Linux machine at 100,
  5,000 and 50,000 samples (median of seven runs). This is not an application-wide
  or hardware OBD speed claim.

Imported historical tests for old packaging/mobile presentation are retained as
source evidence; they are outside the selected runtime suite and can require
files from the original repository. No live PostgreSQL/pgvector, physical vehicle,
Bluetooth/J2534 hardware, AI model, Windows execution, or Android/iOS deployment
was certified. V3 native ECU writes remain locked; original source driver safety
and read-only restrictions are retained.
