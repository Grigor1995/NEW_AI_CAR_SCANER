window.CDA_ARCHITECTURE = {
  "nodes": [
    {
      "id": "ui",
      "title": "Shared Qt/QML client",
      "group": "Clients",
      "status": "IMPLEMENTED",
      "technology": "C++20 / Qt 6.8 QML",
      "responsibility": "Responsive UI, live preferences and local account/diagnostic commands",
      "interfaces": "AppModel invokables",
      "APIs": "AppModel invokables",
      "dependencies": [
        "identity",
        "diagnostics",
        "settings"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "apps/shared; ui",
      "documentation": "../UI_UX_DESIGN_SYSTEM.md"
    },
    {
      "id": "windows",
      "title": "Windows desktop",
      "group": "Clients",
      "status": "BLOCKED",
      "technology": "Platform-specific Qt kit",
      "responsibility": "Build the shared UI as a separate native artifact",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [
        "ui"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Native build/signing not executed on this Linux host",
      "source": "apps/windows",
      "documentation": "../BUILD_AND_RUN.md"
    },
    {
      "id": "android",
      "title": "Android client",
      "group": "Clients",
      "status": "BLOCKED",
      "technology": "Platform-specific Qt kit",
      "responsibility": "Build the shared UI as a separate native artifact",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [
        "ui"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Native build/signing not executed on this Linux host",
      "source": "apps/android",
      "documentation": "../BUILD_AND_RUN.md"
    },
    {
      "id": "ios",
      "title": "iOS client",
      "group": "Clients",
      "status": "BLOCKED",
      "technology": "Platform-specific Qt kit",
      "responsibility": "Build the shared UI as a separate native artifact",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [
        "ui"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Native build/signing not executed on this Linux host",
      "source": "apps/ios",
      "documentation": "../BUILD_AND_RUN.md"
    },
    {
      "id": "core",
      "title": "Shared C++ domain",
      "group": "Core",
      "status": "IMPLEMENTED",
      "technology": "C++20; OpenSSL",
      "responsibility": "Protocol decoding, units, safety, evidence and crypto without Qt UI/SQL",
      "interfaces": "IObdReader / IObdWriter / IProtocolDecoder",
      "APIs": "IObdReader / IObdWriter / IProtocolDecoder",
      "dependencies": [
        "protocols",
        "safety",
        "rules"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "core",
      "documentation": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "identity",
      "title": "Identity & access",
      "group": "Macroservices",
      "status": "PARTIAL",
      "technology": "Qt SQL / OpenSSL",
      "responsibility": "Local accounts, roles, expiry, password/token hashes",
      "interfaces": "POST accounts/sessions; GET me",
      "APIs": "POST accounts/sessions; GET me",
      "dependencies": [
        "storage"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "services/identity",
      "documentation": "../ROLES_AND_PERMISSIONS.md"
    },
    {
      "id": "user",
      "title": "USER mode",
      "group": "Workspaces",
      "status": "PARTIAL",
      "technology": "Assigned roles; Qt shell",
      "responsibility": "Owner workflow",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [
        "identity"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "apps/shared; services/identity",
      "documentation": "../USER_MODE.md"
    },
    {
      "id": "customer",
      "title": "CUSTOMER mode",
      "group": "Workspaces",
      "status": "PLANNED",
      "technology": "Assigned roles; Qt shell",
      "responsibility": "Role shell only; professional business workflows not implemented",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [
        "identity"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "apps/shared; services/identity",
      "documentation": "../CUSTOMER_MODE.md"
    },
    {
      "id": "admin",
      "title": "ADMIN mode",
      "group": "Workspaces",
      "status": "PLANNED",
      "technology": "Assigned roles; Qt shell",
      "responsibility": "Role shell only; professional business workflows not implemented",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [
        "identity"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "apps/shared; services/identity",
      "documentation": "../ADMIN_MODE.md"
    },
    {
      "id": "market",
      "title": "MARKET portal",
      "group": "Macroservices",
      "status": "PLANNED",
      "technology": "Future C++ domain",
      "responsibility": "Verified merchant listings/fitment/quotes; never fourth diagnostic mode",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [
        "identity",
        "vehicle"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "services/marketplace",
      "documentation": "../MARKETPLACE.md"
    },
    {
      "id": "vehicle",
      "title": "Vehicle management",
      "group": "Macroservices",
      "status": "PARTIAL",
      "technology": "Qt SQL",
      "responsibility": "Private manually entered profiles; no OEM identity verification",
      "interfaces": "GET/POST vehicles",
      "APIs": "GET/POST vehicles",
      "dependencies": [
        "storage"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "services/identity/Store",
      "documentation": "../VEHICLE_COMPATIBILITY.md"
    },
    {
      "id": "diagnostics",
      "title": "Diagnostic orchestration",
      "group": "Macroservices",
      "status": "PARTIAL",
      "technology": "Qt asynchronous controller",
      "responsibility": "Initialize ELM, discover supported PIDs, poll and read DTCs",
      "interfaces": "DiagnosticController",
      "APIs": "DiagnosticController",
      "dependencies": [
        "transport",
        "protocols",
        "session"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "services/diagnostics",
      "documentation": "../OBD_READ_OPERATIONS.md"
    },
    {
      "id": "transport",
      "title": "TCP / desktop serial",
      "group": "Adapters",
      "status": "PARTIAL",
      "technology": "Qt Network / SerialPort",
      "responsibility": "Bounded asynchronous I/O; real sockets tested on loopback only",
      "interfaces": "QtElm",
      "APIs": "QtElm",
      "dependencies": [
        "device"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Read-only allowlist; trusted local adapter, no TCP TLS",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "core/transport",
      "documentation": "../OBD_PROTOCOLS.md"
    },
    {
      "id": "device",
      "title": "Vehicle / ECU hardware",
      "group": "Adapters",
      "status": "BLOCKED",
      "technology": "ELM-compatible physical adapter",
      "responsibility": "Actual vehicle bus interaction requires authorized hardware",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "No real adapter attached or certified",
      "source": "External adapter / ECU",
      "documentation": "../HARDWARE_TEST_PLAN.md"
    },
    {
      "id": "protocols",
      "title": "ELM / CAN / ISO-TP",
      "group": "Core",
      "status": "PARTIAL",
      "technology": "Pure C++",
      "responsibility": "Validate frame structure, requested service/PID, DTCs, bitmap",
      "interfaces": "parseElm / decodePid / troubleCodes",
      "APIs": "parseElm / decodePid / troubleCodes",
      "dependencies": [],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "core/protocols",
      "documentation": "../OBD_PROTOCOLS.md"
    },
    {
      "id": "safety",
      "title": "Read/write safety",
      "group": "Core",
      "status": "PARTIAL",
      "technology": "Pure C++ predicate",
      "responsibility": "Deny writes unless every required prerequisite is satisfied; executor locked",
      "interfaces": "validateWrite",
      "APIs": "validateWrite",
      "dependencies": [],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "CUSTOMER + verified IDs/state/capabilities/consent/audit; no arbitrary ECU bytes",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "core/security/write_policy",
      "documentation": "../OBD_SAFETY_MODEL.md"
    },
    {
      "id": "session",
      "title": "Diagnostic evidence",
      "group": "Core",
      "status": "PARTIAL",
      "technology": "C++ value model",
      "responsibility": "Retain evidence, DTCs and completed test results",
      "interfaces": "DiagnosticSession",
      "APIs": "DiagnosticSession",
      "dependencies": [
        "rules"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "core/ai/evidence.hpp",
      "documentation": "../AI_DIAGNOSTICS.md"
    },
    {
      "id": "rules",
      "title": "AI / deterministic rules",
      "group": "Macroservices",
      "status": "PARTIAL",
      "technology": "C++ rule slice",
      "responsibility": "P0302 evidence ranking and test recalculation; no LLM provider",
      "interfaces": "analyze",
      "APIs": "analyze",
      "dependencies": [],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "No invented probabilities or authority over measurements",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "core/ai",
      "documentation": "../AI_DIAGNOSTICS.md"
    },
    {
      "id": "telemetry",
      "title": "Telemetry & units",
      "group": "Core",
      "status": "PARTIAL",
      "technology": "C++ engineering values",
      "responsibility": "Quality/timestamp/provenance and boundary-only conversions",
      "interfaces": "Measurement / convert",
      "APIs": "Measurement / convert",
      "dependencies": [
        "protocols"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "core/telemetry; services/diagnostics",
      "documentation": "../UNIT_CONVERSION.md"
    },
    {
      "id": "monitoring",
      "title": "Scheduled monitoring",
      "group": "Macroservices",
      "status": "PLANNED",
      "technology": "Eligibility predicate only",
      "responsibility": "Future daily scheduling with device/ignition/OS eligibility",
      "interfaces": "eligibleScan only; no scheduler",
      "APIs": "eligibleScan only; no scheduler",
      "dependencies": [
        "diagnostics"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "services/monitoring",
      "documentation": "../AUTO_MONITORING.md"
    },
    {
      "id": "notifications",
      "title": "Email / SMS / push",
      "group": "Adapters",
      "status": "PLANNED",
      "technology": "Future providers",
      "responsibility": "Consented verified delivery, retries/deduplication/audit",
      "interfaces": "INotificationSender",
      "APIs": "INotificationSender",
      "dependencies": [],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "UNAVAILABLE; no provider configured",
      "source": "integrations/email; integrations/sms",
      "documentation": "../NOTIFICATION_SYSTEM.md"
    },
    {
      "id": "updates",
      "title": "Online update service",
      "group": "Macroservices",
      "status": "PARTIAL",
      "technology": "OpenSSL Ed25519 / version parser",
      "responsibility": "Verify signatures/versions; feed/download/install not implemented",
      "interfaces": "verifyEd25519 / newerVersion",
      "APIs": "verifyEd25519 / newerVersion",
      "dependencies": [],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "services/updates; core/security",
      "documentation": "../ONLINE_UPDATE_SYSTEM.md"
    },
    {
      "id": "storage",
      "title": "SQLite / PostgreSQL",
      "group": "Persistence",
      "status": "PARTIAL",
      "technology": "SQLite implemented; PostgreSQL planned",
      "responsibility": "Local identity/profile/settings/audit persistence",
      "interfaces": "Store; schema version 1",
      "APIs": "Store; schema version 1",
      "dependencies": [],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "services/identity; backend/database",
      "documentation": "../DATABASE_DESIGN.md"
    },
    {
      "id": "settings",
      "title": "Persistent settings",
      "group": "Core",
      "status": "PARTIAL",
      "technology": "QSettings / SQLite / Qt Linguist",
      "responsibility": "Four languages, two unit systems, three themes; no cross-device sync",
      "interfaces": "GET/PUT settings",
      "APIs": "GET/PUT settings",
      "dependencies": [
        "storage"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "apps/shared/app_model; ui/translations",
      "documentation": "../APPLICATION_SETTINGS.md"
    },
    {
      "id": "repair",
      "title": "Licensed repair / wiring",
      "group": "Adapters",
      "status": "BLOCKED",
      "technology": "Future licensed provider",
      "responsibility": "Verified procedures and circuit references only",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "No licensed data configured; never fabricate diagrams",
      "source": "integrations/automotive_data",
      "documentation": "../WIRING_DIAGRAMS.md"
    },
    {
      "id": "backend",
      "title": "C++ HTTP host",
      "group": "Macroservices",
      "status": "PARTIAL",
      "technology": "Qt HttpServer",
      "responsibility": "Versioned loopback APIs; no remote public deployment",
      "interfaces": "/api/v1/*",
      "APIs": "/api/v1/*",
      "dependencies": [
        "identity",
        "vehicle",
        "settings"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "backend/api",
      "documentation": "../API_SPECIFICATION.md"
    },
    {
      "id": "payments",
      "title": "Future payments",
      "group": "Future",
      "status": "DISABLED",
      "technology": "Documentation only",
      "responsibility": "Reserve domain boundary; no code, provider, checkout or cards",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Not compiled or exposed; payments NOT IMPLEMENTED",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "future_modules/payments/ARCHITECTURE.md",
      "documentation": "../FUTURE_PAYMENT_ARCHITECTURE.md"
    },
    {
      "id": "testing",
      "title": "Local QA & contracts",
      "group": "Quality",
      "status": "IMPLEMENTED",
      "technology": "CTest / Qt Test / ASan / Python QA",
      "responsibility": "Compile/runtime/HTTP/UI/catalog/safety validation; no CI/CD",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "tests; scripts/test",
      "documentation": "../TEST_METHODOLOGY.md"
    },
    {
      "id": "roadmap",
      "title": "Development roadmap",
      "group": "Quality",
      "status": "IMPLEMENTED",
      "technology": "Phased acceptance gates",
      "responsibility": "Separate current milestone, external blockers and future delivery",
      "interfaces": "No public endpoint",
      "APIs": "No public endpoint",
      "dependencies": [],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "docs",
      "documentation": "../DEVELOPMENT_PLAN.md"
    },
    {
      "id": "observability",
      "title": "Runtime observations",
      "group": "Quality",
      "status": "PARTIAL",
      "technology": "Local health API / browser fetch",
      "responsibility": "Actual host observations; unavailable CPU/memory/provider metrics remain UNKNOWN",
      "interfaces": "GET /api/v1/health",
      "APIs": "GET /api/v1/health",
      "dependencies": [
        "backend"
      ],
      "input": "Validated requests, observed evidence or configuration",
      "output": "Typed result and explicit implementation status",
      "database": "Only through domain-owned repository; no implicit cross-account access",
      "security": "Scope credentials and capabilities to the authenticated actor",
      "failure": "Explicit unavailable/error state; no fabricated success",
      "source": "backend/api; dashboard",
      "documentation": "../PERFORMANCE_TESTING.md"
    },
    {
      "id": "platform_engine",
      "title": "Source diagnostic companion",
      "group": "Migration",
      "status": "IMPLEMENTED",
      "technology": "Python / FastAPI + native C ABI",
      "responsibility": "135 retained source API operations: reasoning, RAG, vehicle catalog, reports, telemetry and optional consent boundary",
      "interfaces": "Local HTTP / C ABI",
      "APIs": "/api/v1/migration/runtime",
      "dependencies": [
        "native_engine"
      ],
      "input": "Validated requests / timestamped samples",
      "output": "Typed diagnostic results with provenance",
      "database": "Separate SQLite by default; configured SQLAlchemy database respected",
      "security": "Loopback only; separate accounts/session IDs; provider-dependent calls need configuration",
      "failure": "Explicit errors; no physical hardware certification",
      "source": "services/platform_engine",
      "documentation": "../migration/README.md"
    },
    {
      "id": "native_engine",
      "title": "Native telemetry/PID kernels",
      "group": "Migration",
      "status": "IMPLEMENTED",
      "technology": "C++20 / Qt Core shared library",
      "responsibility": "Packed-array telemetry statistics and ten PID snapshot scalings called by companion",
      "interfaces": "Local HTTP / C ABI",
      "APIs": "cda_stats_binary; cda_engine_json",
      "dependencies": [
        "core"
      ],
      "input": "Validated requests / timestamped samples",
      "output": "Typed diagnostic results with provenance",
      "database": "No owned database",
      "security": "Bounded C ABI; thread-local JSON result; explicit observable Python fallback",
      "failure": "Explicit errors; no physical hardware certification",
      "source": "native/engine; services/platform_engine/native_acceleration.py",
      "documentation": "../migration/README.md"
    }
  ],
  "edges": [
    {
      "from": "ui",
      "to": "identity",
      "label": "local sign-in and role checks",
      "path": "offline"
    },
    {
      "from": "identity",
      "to": "storage",
      "label": "credential hashes and current token checks",
      "path": "offline"
    },
    {
      "from": "ui",
      "to": "diagnostics",
      "label": "explicit authorized connection/read",
      "path": "offline"
    },
    {
      "from": "diagnostics",
      "to": "transport",
      "label": "bounded command exchange",
      "path": "offline"
    },
    {
      "from": "transport",
      "to": "device",
      "label": "actual adapter bytes; hardware NOT RUN",
      "path": "offline"
    },
    {
      "from": "device",
      "to": "protocols",
      "label": "observed ECU response",
      "path": "offline"
    },
    {
      "from": "protocols",
      "to": "telemetry",
      "label": "validated engineering measurement",
      "path": "offline"
    },
    {
      "from": "diagnostics",
      "to": "session",
      "label": "observed DTC/evidence",
      "path": "offline"
    },
    {
      "from": "session",
      "to": "rules",
      "label": "evidence-ranked hypotheses",
      "path": "offline"
    },
    {
      "from": "ui",
      "to": "settings",
      "label": "local preference changes",
      "path": "offline"
    },
    {
      "from": "settings",
      "to": "storage",
      "label": "explicit account save",
      "path": "offline"
    },
    {
      "from": "diagnostics",
      "to": "safety",
      "label": "future write prepare; executor currently locked",
      "path": "offline"
    },
    {
      "from": "monitoring",
      "to": "diagnostics",
      "label": "future eligible scan; no scheduled execution",
      "path": "offline"
    },
    {
      "from": "windows",
      "to": "ui",
      "label": "shared source; native build blocked",
      "path": "offline"
    },
    {
      "from": "android",
      "to": "ui",
      "label": "shared source; native SDK required",
      "path": "offline"
    },
    {
      "from": "ios",
      "to": "ui",
      "label": "shared source; Xcode required",
      "path": "offline"
    },
    {
      "from": "testing",
      "to": "core",
      "label": "runtime and negative contracts",
      "path": "offline"
    },
    {
      "from": "backend",
      "to": "identity",
      "label": "versioned credential API",
      "path": "online"
    },
    {
      "from": "backend",
      "to": "vehicle",
      "label": "owner-scoped profile API",
      "path": "online"
    },
    {
      "from": "backend",
      "to": "settings",
      "label": "account settings API",
      "path": "online"
    },
    {
      "from": "monitoring",
      "to": "notifications",
      "label": "future delivery after actual completion",
      "path": "online"
    },
    {
      "from": "rules",
      "to": "repair",
      "label": "future licensed reference retrieval",
      "path": "online"
    },
    {
      "from": "market",
      "to": "vehicle",
      "label": "future verified fitment",
      "path": "online"
    },
    {
      "from": "observability",
      "to": "backend",
      "label": "actual health when same-origin available",
      "path": "online"
    },
    {
      "from": "ui",
      "to": "platform_engine",
      "label": "Qt async loopback diagnostic API",
      "path": "offline"
    },
    {
      "from": "platform_engine",
      "to": "native_engine",
      "label": "ctypes packed-array statistics / PID JSON ABI",
      "path": "offline"
    },
    {
      "from": "native_engine",
      "to": "core",
      "label": "Shared C++ PID definitions",
      "path": "offline"
    }
  ],
  "views": [
    {
      "id": "overview",
      "title": "System Overview",
      "nodes": [
        "*"
      ],
      "description": "System Overview: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "core",
      "title": "C++ Shared Core",
      "nodes": [
        "core",
        "protocols",
        "safety",
        "rules",
        "telemetry",
        "session",
        "platform_engine",
        "native_engine"
      ],
      "description": "C++ Shared Core: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "windows",
      "title": "Windows Architecture",
      "nodes": [
        "windows",
        "ui",
        "core",
        "transport",
        "storage"
      ],
      "description": "Windows Architecture: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "android",
      "title": "Android Architecture",
      "nodes": [
        "android",
        "ui",
        "core",
        "transport",
        "settings"
      ],
      "description": "Android Architecture: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "ios",
      "title": "iOS Architecture",
      "nodes": [
        "ios",
        "ui",
        "core",
        "settings"
      ],
      "description": "iOS Architecture: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "macroservices",
      "title": "Macroservice Architecture",
      "nodes": [
        "identity",
        "market",
        "vehicle",
        "diagnostics",
        "rules",
        "monitoring",
        "updates",
        "backend"
      ],
      "description": "Macroservice Architecture: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "identity",
      "title": "Authentication & RBAC",
      "nodes": [
        "identity",
        "user",
        "customer",
        "admin",
        "market",
        "storage"
      ],
      "description": "Authentication & RBAC: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "user",
      "title": "USER Mode",
      "nodes": [
        "user",
        "ui",
        "vehicle",
        "diagnostics",
        "rules"
      ],
      "description": "USER Mode: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "customer",
      "title": "CUSTOMER Mode",
      "nodes": [
        "customer",
        "identity",
        "diagnostics",
        "repair"
      ],
      "description": "CUSTOMER Mode: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "admin",
      "title": "ADMIN Mode",
      "nodes": [
        "admin",
        "identity",
        "backend",
        "updates",
        "observability"
      ],
      "description": "ADMIN Mode: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "market",
      "title": "MARKET Portal",
      "nodes": [
        "market",
        "vehicle",
        "identity",
        "payments"
      ],
      "description": "MARKET Portal: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "protocols",
      "title": "OBD Protocol Architecture",
      "nodes": [
        "diagnostics",
        "transport",
        "device",
        "protocols",
        "telemetry"
      ],
      "description": "OBD Protocol Architecture: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "safety",
      "title": "OBD Read/Write Safety",
      "nodes": [
        "diagnostics",
        "safety",
        "transport",
        "device",
        "identity"
      ],
      "description": "OBD Read/Write Safety: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "rules",
      "title": "AI Diagnostic Workflow",
      "nodes": [
        "session",
        "rules",
        "repair",
        "telemetry"
      ],
      "description": "AI Diagnostic Workflow: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "telemetry",
      "title": "Live Telemetry",
      "nodes": [
        "device",
        "protocols",
        "telemetry",
        "ui",
        "platform_engine",
        "native_engine"
      ],
      "description": "Live Telemetry: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "monitoring",
      "title": "Scheduled Monitoring",
      "nodes": [
        "monitoring",
        "diagnostics",
        "device",
        "notifications"
      ],
      "description": "Scheduled Monitoring: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "notifications",
      "title": "Notifications",
      "nodes": [
        "notifications",
        "monitoring",
        "identity"
      ],
      "description": "Notifications: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "updates",
      "title": "Online Updates",
      "nodes": [
        "updates",
        "windows",
        "android",
        "ios",
        "backend"
      ],
      "description": "Online Updates: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "storage",
      "title": "Database Architecture",
      "nodes": [
        "storage",
        "identity",
        "vehicle",
        "settings"
      ],
      "description": "Database Architecture: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "security",
      "title": "Security Architecture",
      "nodes": [
        "identity",
        "safety",
        "storage",
        "backend"
      ],
      "description": "Security Architecture: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "payments",
      "title": "Future Payment Architecture",
      "nodes": [
        "payments",
        "market"
      ],
      "description": "Future Payment Architecture: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "testing",
      "title": "Testing Architecture",
      "nodes": [
        "testing",
        "core",
        "transport",
        "backend",
        "ui"
      ],
      "description": "Testing Architecture: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "roadmap",
      "title": "Development Roadmap",
      "nodes": [
        "roadmap",
        "testing",
        "device",
        "updates",
        "market"
      ],
      "description": "Development Roadmap: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    },
    {
      "id": "observability",
      "title": "Runtime Observability",
      "nodes": [
        "observability",
        "backend",
        "storage",
        "device",
        "notifications"
      ],
      "description": "Runtime Observability: inspect each node\u2019s exact implementation status, security boundary and current limitations."
    }
  ]
};
