window.ARCHITECTURE_DATA = {
  "layers": [
    "Native UI",
    "Identity",
    "Workspaces",
    "C++ native transport",
    "Device transport",
    "DiagnosticSession",
    "AI / rules",
    "Backend",
    "Storage",
    "Scheduler",
    "Notifications",
    "Repair providers",
    "Marketplace",
    "External providers",
    "Observability"
  ],
  "nodes": [
    {
      "id": "windows",
      "layer": "Native UI",
      "title": "Windows Desktop",
      "technology": "PySide6 / Python",
      "responsibility": "Existing themed diagnostic workstation",
      "io": "Local API + telemetry -> native panels",
      "api": "/api/v1 (local mode)",
      "security": "User process; no role granted by UI",
      "failure": "Show connection/error state, preserve local diagnosis",
      "status": "EXISTING",
      "dependencies": [
        "backend",
        "transport"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "android",
      "layer": "Native UI",
      "title": "Android",
      "technology": "Kotlin / Compose",
      "responsibility": "Native diagnostic UI and device bridge",
      "io": "Backend contracts -> native screens",
      "api": "Existing Retrofit DiagnosticApi",
      "security": "OS Bluetooth/USB permissions",
      "failure": "Stop polling on disconnect; show unsupported data",
      "status": "EXISTING",
      "dependencies": [
        "backend",
        "transport"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "ios",
      "layer": "Native UI",
      "title": "iOS",
      "technology": "Swift / SwiftUI",
      "responsibility": "Native diagnostic UI and BLE/Wi-Fi bridge",
      "io": "Backend contracts -> native screens",
      "api": "Existing DiagnosticAPI",
      "security": "iOS permission/background boundary",
      "failure": "No universal Classic/USB or unattended scan claim",
      "status": "EXISTING",
      "dependencies": [
        "backend",
        "transport"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "identity",
      "layer": "Identity",
      "title": "Accounts + RBAC",
      "technology": "FastAPI / SQLAlchemy",
      "responsibility": "Account sessions, server roles and allowed workspaces",
      "io": "Bearer token -> current account + permissions",
      "api": "/api/v2/ecosystem/auth/*, /me",
      "security": "Opaque token hashes; role checked from DB",
      "failure": "Deny expired/revoked/inactive sessions",
      "status": "FOUNDATION",
      "dependencies": [
        "user",
        "customer",
        "admin",
        "marketrole",
        "storage"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "user",
      "layer": "Workspaces",
      "title": "USER",
      "technology": "Shared API contract",
      "responsibility": "Vehicle-owner primary mode",
      "io": "Owned profile + evidence -> personal workspace",
      "api": "/vehicles",
      "security": "Ownership checked server-side",
      "failure": "Foreign resources not disclosed",
      "status": "FOUNDATION",
      "dependencies": [
        "consent",
        "location"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "customer",
      "layer": "Workspaces",
      "title": "CUSTOMER",
      "technology": "Existing staff Role + durable membership",
      "responsibility": "Professional primary mode",
      "io": "Active center membership + owner consent -> scoped reads",
      "api": "/service-centers/*",
      "security": "Staff role is not platform ADMIN",
      "failure": "No grant before explicit owner approval",
      "status": "FOUNDATION",
      "dependencies": [
        "consent",
        "market"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "admin",
      "layer": "Workspaces",
      "title": "ADMIN",
      "technology": "Role contract; UI planned",
      "responsibility": "Platform primary mode",
      "io": "Assigned platform role -> authorized admin tools",
      "api": "/workspace (selection only)",
      "security": "No implicit private vehicle bypass",
      "failure": "Admin management/analytics not yet implemented",
      "status": "PLANNED",
      "dependencies": [],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "marketrole",
      "layer": "Workspaces",
      "title": "MARKET portal",
      "technology": "Merchant role; portal planned",
      "responsibility": "Seller role attached to a primary workspace",
      "io": "Approved merchant identity -> seller portal",
      "api": "No product endpoints in foundation",
      "security": "Never a fourth diagnostic mode",
      "failure": "Deny as primary mode; future merchant approval",
      "status": "PLANNED",
      "dependencies": [
        "market"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "cpp",
      "layer": "C++ native transport",
      "title": "Opt-in C++ TCP transport",
      "technology": "C++20 / pybind11; Linux loopback tested",
      "responsibility": "Bounded TCP connect, write, prompt framing and deadlines; existing Python diagnostic logic retained",
      "io": "Existing GenericObdClient -> trusted IPv4 ELM TCP adapter",
      "api": "NativeObdWifiTransport; native_tcp=true in Wi-Fi connection config",
      "security": "Read-only command allowlist; no TLS; authorized trusted local adapter only",
      "failure": "Explicit errors, timeout/disconnect cleanup; cancellation drains worker before close",
      "status": "IMPLEMENTED",
      "dependencies": [
        "transport"
      ],
      "docs": "../../native/obd/README.md"
    },
    {
      "id": "transport",
      "layer": "Device transport",
      "title": "Native / local transports",
      "technology": "Python, Kotlin, Swift",
      "responsibility": "ELM/custom adapter discovery and byte transport",
      "io": "Bluetooth/BLE/Wi-Fi/USB -> replies",
      "api": "/api/v1/devices (local)",
      "security": "Platform and hardware capability constraints",
      "failure": "Timeout, reconnect, unsupported/invalid statuses",
      "status": "EXISTING",
      "dependencies": [
        "obd"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "obd",
      "layer": "Device transport",
      "title": "OBD / ISO-TP / UDS",
      "technology": "Existing Python vehicle + obd modules",
      "responsibility": "Capability-driven protocol decoding",
      "io": "Actual supported responses -> normalized readings",
      "api": "Existing OBD plan/discovery APIs",
      "security": "Read-only policy; simulator provenance distinct",
      "failure": "Reject malformed/unsupported data",
      "status": "EXISTING",
      "dependencies": [
        "session"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "session",
      "layer": "DiagnosticSession",
      "title": "DiagnosticSession",
      "technology": "Pydantic / shared domain",
      "responsibility": "One evidence/test/history aggregate for all clients",
      "io": "Symptoms + DTC + readings + outcomes -> updated session",
      "api": "Existing session/test APIs; scoped wrapper later",
      "security": "New identity must scope access before exposure",
      "failure": "Preserve history; never invent ECU readings",
      "status": "EXISTING",
      "dependencies": [
        "reasoning",
        "repair"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "reasoning",
      "layer": "AI / rules",
      "title": "Rules + AI / RAG / ML",
      "technology": "Python deterministic engine + provider adapters",
      "responsibility": "Evidence ranking, retrieval and test recalculation",
      "io": "Verified evidence -> hypotheses + safe next tests",
      "api": "Existing analyze / decision / knowledge APIs",
      "security": "LLM output cannot become factual measurement",
      "failure": "Deterministic fallback; honest provider availability",
      "status": "EXISTING",
      "dependencies": [
        "session",
        "cpp"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "backend",
      "layer": "Backend",
      "title": "FastAPI backend",
      "technology": "Python / asynchronous transports",
      "responsibility": "Shared diagnostic orchestration and API boundaries",
      "io": "Native requests -> shared services",
      "api": "/health, /api/v1, /api/v2/ecosystem",
      "security": "Feature-enabled mode blocks anonymous legacy API bypass",
      "failure": "DB not ready -> explicit failure, not fake persistence",
      "status": "EXISTING",
      "dependencies": [
        "identity",
        "session",
        "storage",
        "observability"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "storage",
      "layer": "Storage",
      "title": "PostgreSQL / local SQLite",
      "technology": "SQLAlchemy / Alembic foundation",
      "responsibility": "Existing snapshots/catalog + new account/consent state",
      "io": "Transactions -> durable rows",
      "api": "Explicit additive migrations",
      "security": "FK ownership and scoped repository access",
      "failure": "No silent production fallback; backups required",
      "status": "EXISTING",
      "dependencies": [],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "consent",
      "layer": "Storage",
      "title": "Ownership + consent",
      "technology": "Durable scoped grants",
      "responsibility": "Explicit time-limited workshop sharing",
      "io": "Owner accept/revoke -> currently allowed reads",
      "api": "/invitations/*/accept, /consents",
      "security": "Per-vehicle scope/expiry; recheck every read",
      "failure": "Revoked/expired membership or grant denies access",
      "status": "FOUNDATION",
      "dependencies": [
        "storage"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "scheduler",
      "layer": "Scheduler",
      "title": "Eligible scan scheduler",
      "technology": "Provider/gateway design only",
      "responsibility": "Future daily/weekly/manual eligible jobs",
      "io": "Consent + hardware availability -> scan run",
      "api": "No scheduling endpoint yet",
      "security": "Never assume ignition ON or background access",
      "failure": "Deferred/missed/failed distinct from completed",
      "status": "PLANNED",
      "dependencies": [
        "transport",
        "notifications"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "notifications",
      "layer": "Notifications",
      "title": "Email / SMS outbox",
      "technology": "Provider design only",
      "responsibility": "Future consented verified alert delivery",
      "io": "Eligible event -> retryable delivery attempt",
      "api": "No delivery endpoint yet",
      "security": "Verified destination, rate limit and redaction",
      "failure": "Queued is not delivered; no provider configured",
      "status": "PLANNED",
      "dependencies": [],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "repair",
      "layer": "Repair providers",
      "title": "Licensed repair data",
      "technology": "External authorized provider boundary",
      "responsibility": "Future wiring, references and repair guidance",
      "io": "Verified vehicle fitment -> licensed reference",
      "api": "No repair-provider API yet",
      "security": "License and source provenance required",
      "failure": "Never fabricate torque, pinouts or diagrams",
      "status": "PLANNED",
      "dependencies": [],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "market",
      "layer": "Marketplace",
      "title": "Products / offers / fitment",
      "technology": "Future catalog + eligibility service",
      "responsibility": "Merchant listings, verified fitment, exact pricing",
      "io": "Vehicle/OEM references -> eligible labeled offers",
      "api": "No marketplace API yet",
      "security": "Paid offers cannot influence fault ranking",
      "failure": "Unknown fitment stays unknown",
      "status": "PLANNED",
      "dependencies": [
        "storage"
      ],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "location",
      "layer": "External providers",
      "title": "Service / location providers",
      "technology": "Future opted-in location/provider adapters",
      "responsibility": "Find relevant verified automotive specialists",
      "io": "User-approved city/location -> sourced center list",
      "api": "No location-provider integration yet",
      "security": "Explicit location consent; minimal data sharing",
      "failure": "No fabricated locations/ratings",
      "status": "PLANNED",
      "dependencies": [],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    },
    {
      "id": "observability",
      "layer": "Observability",
      "title": "Audit / metrics / traces",
      "technology": "Existing observability + foundation audit",
      "responsibility": "Record real events without sensitive payloads",
      "io": "Actions + timing -> auditable operational facts",
      "api": "Existing local observability; new audit store",
      "security": "No raw password/token/contact logging",
      "failure": "No fabricated production statistics",
      "status": "EXISTING",
      "dependencies": [],
      "docs": "../SYSTEM_ARCHITECTURE.md"
    }
  ],
  "edges": [
    {
      "id": "0",
      "source": "windows",
      "target": "backend",
      "label": "local HTTP API",
      "path": "offline"
    },
    {
      "id": "1",
      "source": "android",
      "target": "backend",
      "label": "native API contract",
      "path": "online"
    },
    {
      "id": "2",
      "source": "ios",
      "target": "backend",
      "label": "native API contract",
      "path": "online"
    },
    {
      "id": "3",
      "source": "backend",
      "target": "identity",
      "label": "v2 authorization",
      "path": "both"
    },
    {
      "id": "4",
      "source": "identity",
      "target": "user",
      "label": "authorized mode",
      "path": "both"
    },
    {
      "id": "5",
      "source": "identity",
      "target": "customer",
      "label": "authorized mode + staff",
      "path": "both"
    },
    {
      "id": "6",
      "source": "identity",
      "target": "admin",
      "label": "assigned mode only",
      "path": "both"
    },
    {
      "id": "7",
      "source": "identity",
      "target": "marketrole",
      "label": "portal role, not mode",
      "path": "both"
    },
    {
      "id": "8",
      "source": "customer",
      "target": "consent",
      "label": "request / check sharing",
      "path": "both"
    },
    {
      "id": "9",
      "source": "user",
      "target": "consent",
      "label": "explicit accept / revoke",
      "path": "both"
    },
    {
      "id": "10",
      "source": "consent",
      "target": "storage",
      "label": "grant transaction / current checks",
      "path": "both"
    },
    {
      "id": "11",
      "source": "backend",
      "target": "session",
      "label": "shared domain operations",
      "path": "both"
    },
    {
      "id": "12",
      "source": "transport",
      "target": "obd",
      "label": "actual adapter replies",
      "path": "offline"
    },
    {
      "id": "13",
      "source": "obd",
      "target": "session",
      "label": "supported readings + provenance",
      "path": "offline"
    },
    {
      "id": "14",
      "source": "session",
      "target": "reasoning",
      "label": "evidence / test outcomes",
      "path": "offline"
    },
    {
      "id": "15",
      "source": "reasoning",
      "target": "session",
      "label": "rank / recalculate",
      "path": "offline"
    },
    {
      "id": "16",
      "source": "backend",
      "target": "storage",
      "label": "snapshots / account records",
      "path": "both"
    },
    {
      "id": "17",
      "source": "android",
      "target": "transport",
      "label": "native transport bridge",
      "path": "offline"
    },
    {
      "id": "18",
      "source": "ios",
      "target": "transport",
      "label": "native BLE/Wi-Fi bridge",
      "path": "offline"
    },
    {
      "id": "19",
      "source": "windows",
      "target": "transport",
      "label": "local server transport",
      "path": "offline"
    },
    {
      "id": "20",
      "source": "scheduler",
      "target": "transport",
      "label": "eligible gateway scan (future)",
      "path": "both"
    },
    {
      "id": "21",
      "source": "scheduler",
      "target": "notifications",
      "label": "eligible alert event (future)",
      "path": "online"
    },
    {
      "id": "22",
      "source": "session",
      "target": "repair",
      "label": "verified reference request (future)",
      "path": "online"
    },
    {
      "id": "23",
      "source": "customer",
      "target": "market",
      "label": "eligible offers (future)",
      "path": "online"
    },
    {
      "id": "24",
      "source": "marketrole",
      "target": "market",
      "label": "merchant management (future)",
      "path": "online"
    },
    {
      "id": "25",
      "source": "market",
      "target": "storage",
      "label": "verified fitment / price (future)",
      "path": "online"
    },
    {
      "id": "26",
      "source": "user",
      "target": "location",
      "label": "opted-in discovery (future)",
      "path": "online"
    },
    {
      "id": "27",
      "source": "transport",
      "target": "cpp",
      "label": "optional native_tcp socket backend",
      "path": "offline"
    },
    {
      "id": "28",
      "source": "backend",
      "target": "observability",
      "label": "real request events / timing",
      "path": "both"
    },
    {
      "id": "29",
      "source": "identity",
      "target": "storage",
      "label": "token hash / role lookup",
      "path": "both"
    }
  ],
  "views": {
    "High-Level Architecture": [
      "windows",
      "android",
      "ios",
      "identity",
      "user",
      "customer",
      "admin",
      "marketrole",
      "cpp",
      "transport",
      "obd",
      "session",
      "reasoning",
      "backend",
      "storage",
      "consent",
      "scheduler",
      "notifications",
      "repair",
      "market",
      "location",
      "observability"
    ],
    "USER Diagnostic Flow": [
      "windows",
      "android",
      "ios",
      "identity",
      "user",
      "transport",
      "obd",
      "session",
      "reasoning",
      "backend",
      "storage",
      "consent"
    ],
    "CUSTOMER Diagnostic Flow": [
      "customer",
      "identity",
      "consent",
      "session",
      "reasoning",
      "repair",
      "backend",
      "storage"
    ],
    "Automated OBD Monitoring": [
      "identity",
      "user",
      "consent",
      "scheduler",
      "transport",
      "obd",
      "session",
      "reasoning",
      "notifications",
      "storage"
    ],
    "AI Diagnostic Decision Flow": [
      "session",
      "obd",
      "reasoning",
      "backend",
      "repair",
      "observability"
    ],
    "Notifications": [
      "identity",
      "user",
      "consent",
      "scheduler",
      "notifications",
      "storage",
      "observability"
    ],
    "Marketplace": [
      "identity",
      "customer",
      "marketrole",
      "market",
      "storage",
      "repair",
      "observability"
    ],
    "Admin and Permission Management": [
      "identity",
      "admin",
      "customer",
      "marketrole",
      "consent",
      "backend",
      "storage",
      "observability"
    ],
    "Offline/Online Synchronization": [
      "windows",
      "android",
      "ios",
      "backend",
      "storage",
      "session",
      "transport",
      "reasoning",
      "identity"
    ],
    "Cross-Platform Integration": [
      "windows",
      "android",
      "ios",
      "backend",
      "transport",
      "obd",
      "session",
      "reasoning",
      "cpp",
      "storage"
    ]
  },
  "descriptions": {
    "High-Level Architecture": "Existing modules, the first account/consent foundation and explicitly planned integrations. No C++ core or complete ecosystem is claimed.",
    "USER Diagnostic Flow": "Existing local diagnostic workflow plus new owned-profile APIs; authenticated diagnostic-session adapters and native login UI are next.",
    "CUSTOMER Diagnostic Flow": "Foundation implements staff-scoped vehicle-profile sharing. Full authenticated professional diagnostics, work orders and licensed guides are planned.",
    "Automated OBD Monitoring": "Scheduler and unattended scans are PLANNED. Availability/ignition/OS restrictions must defer unperformed scans, never mark them successful.",
    "AI Diagnostic Decision Flow": "Existing evidence-driven deterministic/AI modules; shared canonical session and test recalculation. LLMs cannot invent readings.",
    "Notifications": "Email/SMS/outbox and verified delivery are PLANNED; no external provider is configured or executed here.",
    "Marketplace": "Merchant role contract is defined. Products, stock, discounts, verified compatibility and seller portal are PLANNED.",
    "Admin and Permission Management": "Foundation checks assigned modes and current DB roles. Admin management, MFA and production analytics are PLANNED.",
    "Offline/Online Synchronization": "Existing local/shared backend topology. A cross-device synchronization queue and conflict handling are PLANNED, not implemented.",
    "Cross-Platform Integration": "Existing native UIs/transports and shared Python backend. Native authenticated workspace UI and any measured C++ extraction are later milestones."
  }
};
