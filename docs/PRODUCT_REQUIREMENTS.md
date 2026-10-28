# CAR DIAGNOSTIC ANALYSIS SYSTEM
## MASTER DEVELOPMENT PROMPT — VERSION 3.0
### Production-Grade Cross-Platform Automotive Diagnostic Ecosystem

# 1. YOUR ROLE AND PRIMARY OBJECTIVE

Act as a multidisciplinary team of:

- Principal Software Architect
- Senior C++20/23 Engineer
- Qt 6 / QML Cross-Platform Engineer
- Microservices and Macroservices Architect
- Automotive ECU / OBD / UDS Protocol Engineer
- AI/ML and RAG Architect
- Backend and Database Architect
- UI/UX Designer
- Application Security Engineer
- QA Automation Architect
- Technical Documentation Engineer

Build a complete, high-performance **CAR DIAGNOSTIC ANALYSIS SYSTEM** from zero.

Target platforms:

- Windows Desktop
- Android
- iOS

Use one shared C++ diagnostic core and a unified Qt/QML visual design system.

The application must provide:

- Real automotive diagnostics
- OBD Read/Write capabilities
- ECU communication
- Live vehicle telemetry
- AI-based fault analysis
- Automated vehicle monitoring
- Email/SMS notifications
- Service-center management
- Professional repair documentation
- Wiring diagrams
- Automotive marketplace
- Platform administration
- Online software updates
- Multilingual and configurable units
- Future-ready payment architecture

## CRITICAL PROJECT RULES

1. Do not reuse previous source code.
2. Delete the old application implementation from the confirmed repository.
3. Preserve `.git` and Git history.
4. Do not delete unrelated files or external resources.
5. Create a completely new system architecture.
6. Do not implement CI/CD pipelines.
7. Build and test locally.
8. Use modern C++ as the primary programming language.
9. Use SOLID and Clean Architecture.
10. Implement domain-oriented Macroservices with clear boundaries.
11. Prepare services for future Microservice extraction.
12. Use the exact visual design defined below.
13. Create the canonical application icon.
14. Implement all three primary application modes.
15. Integrate MARKET as a separate merchant portal.
16. Prepare payment architecture, but DO NOT implement payment processing now.
17. Implement real OBD Read/Write with explicit authorization and safety controls.
18. Support online application updates.
19. Create an interactive system architecture dashboard.
20. Produce comprehensive project and API documentation.

Do not use mock functionality as a substitute for production implementation without clearly identifying it.

---

# 2. SOFTWARE ENGINEERING — SOLID STANDARDS

ALL CODE MUST FOLLOW SOLID PRINCIPLES.

## S — Single Responsibility Principle

Each class, interface and module must have a clearly defined responsibility.

For example:

- OBDConnectionManager
- OBDProtocolDetector
- VehicleTelemetryService
- DiagnosticSessionManager
- FaultAnalysisService
- NotificationScheduler
- UserAuthorizationService
- VehicleRepository
- MarketplaceCatalogService

Avoid classes that simultaneously handle UI, database, network and business logic.

## O — Open/Closed Principle

Design components that can be extended through interfaces without modifying their stable core.

Examples:

- Add new OBD protocols without rewriting connection management.
- Add new AI providers without rewriting diagnostic workflows.
- Add new notification providers without changing alert rules.
- Add new payment providers later without redesigning marketplace domain models.

## L — Liskov Substitution Principle

Every implementation must respect the contracts of its interfaces.

Different OBD adapters, AI providers and notification providers must expose predictable behavior and consistent failure semantics.

## I — Interface Segregation Principle

Use small, focused interfaces.

Examples:

- IOBDReader
- IOBDWriter
- IDeviceConnection
- IProtocolDecoder
- ILiveDataProvider
- IDiagnosticAnalyzer
- INotificationSender
- IVehicleRepository
- IUpdateProvider

Do not force implementations to depend on unsupported capabilities.

## D — Dependency Inversion Principle

High-level domain logic must not depend on database drivers, Qt widgets, HTTP clients or hardware-specific libraries.

Use constructor-based dependency injection and interface contracts.

Avoid global mutable state and tightly coupled singleton architectures.

## Additional Coding Standards

- Clean Architecture
- Domain-Driven Design where appropriate
- DRY
- KISS
- Strong typing
- RAII
- Smart pointers and clear ownership rules
- Const correctness
- Explicit error handling
- Structured logging
- Thread safety
- Asynchronous operations
- Reusable components
- Unit-testable classes
- No hardcoded secrets
- No duplicated business logic
- No unnecessary platform-specific forks

Use static analysis, sanitizers and formatting tools locally.

---

# 3. MACROSERVICES / SERVICE-ORIENTED ARCHITECTURE

Implement a modular, domain-oriented Macroservice Architecture.

A Macroservice is a coarse-grained service responsible for a meaningful business domain.

Avoid creating dozens of tiny services prematurely.

Service boundaries must be documented and enforceable.

## Core Services

### 1. Identity & Access Service

Responsibilities:

- Authentication
- Authorization
- Roles
- Permissions
- User identity
- Organization membership
- Access tokens
- Consent

### 2. Vehicle Management Service

Responsibilities:

- Vehicle catalog
- Vehicle registration
- VIN information
- Engine and model mapping
- Vehicle ownership
- Compatibility references

### 3. Diagnostic Service

Responsibilities:

- Diagnostic sessions
- OBD communication orchestration
- DTCs
- Live data
- Diagnostic history
- Vehicle health
- Read/Write operation authorization

### 4. AI Analysis Service

Responsibilities:

- Symptom analysis
- Rule engine
- ML models
- RAG knowledge retrieval
- Diagnostic hypotheses
- Test recommendations
- Confidence updates

### 5. Monitoring & Notification Service

Responsibilities:

- Diagnostic schedules
- Scheduled scan orchestration
- Email
- SMS
- Push notifications
- Alert thresholds
- Delivery tracking

### 6. Customer / Workshop Service

Responsibilities:

- Service-center accounts
- Workshop staff
- Connected vehicle owners
- Professional diagnostics
- Work orders
- Repair history

### 7. Marketplace Service

Responsibilities:

- Merchant accounts
- Products
- Stock
- Vehicle compatibility
- Pricing
- Discounts
- Promotions

### 8. Administration Service

Responsibilities:

- Platform management
- System statistics
- Account moderation
- Service monitoring
- Audit records
- Feature administration

### 9. Update Management Service

Responsibilities:

- Application version tracking
- Update metadata
- Compatibility checks
- Release manifests
- Windows update delivery
- Android/iOS store update coordination
- Update integrity validation

### 10. Future Billing & Payment Service

Status: PLANNED — NOT IMPLEMENTED.

Reserve architectural boundaries for future:

- Payment providers
- Orders
- Invoices
- Transaction status
- Subscription billing
- Refunds
- Payment audit events

DO NOT integrate payment gateways, collect card information, or create active payment flows now.

## Service Communication

Support appropriate combinations of:

- REST APIs
- WebSocket
- Internal service interfaces
- Asynchronous domain events
- Message queues where justified

Use versioned API contracts, correlation IDs, idempotent operations and explicit failure handling.

Avoid tight synchronous dependency chains.

A service may initially be deployed as part of a modular backend process.

Independent deployment must be introduced only when needed.

---

# 4. TECHNOLOGY STACK

Primary language: C++20/23.

Recommended technologies:

- Qt 6
- Qt Quick / QML
- CMake
- Drogon C++ Web Framework
- PostgreSQL
- SQLite for offline storage
- GoogleTest
- Qt Test
- OpenAPI
- REST and WebSocket
- llama.cpp-compatible AI integration
- Structured logging
- Modern cryptographic libraries

Support:

- Windows Desktop
- Android
- iOS

Use appropriate platform abstraction layers for hardware, storage, permissions and updates.

Do not claim a single binary will run unchanged on all platforms. Build separate platform artifacts from shared source code.

## Performance Priorities

- Fast application startup
- Responsive UI
- Low-latency telemetry processing
- Efficient ECU polling
- Low memory usage
- Non-blocking AI operations
- Background-task lifecycle management
- Battery-efficient monitoring
- Efficient database access

Set measurable performance targets and report p50, p95 and p99 where appropriate.

---

# 5. UI DESIGN — EXACT DESIGN SYSTEM

Design name:

**NEO AUTOMOTIVE DIAGNOSTIC**

The application must look like premium, professional, futuristic automotive diagnostic software.

## Colors

| UI Token | Color |
|---|---|
| Primary background | #070D18 |
| Secondary background | #0D1726 |
| Card background | #122136 |
| Elevated surface | #192B43 |
| Neon blue | #00BFFF |
| Cyan highlight | #29DFFF |
| Secondary blue | #126EFF |
| Main text | #EDF7FF |
| Secondary text | #9CB5CC |
| Border | #25415C |
| Success | #20D79A |
| Warning | #FFB547 |
| Error | #FF596D |

## UI Components

- Premium dark dashboard
- Clean automotive telemetry cards
- Interactive gauges
- Real-time diagnostic charts
- Professional data tables
- Subtle blue borders
- 12–16 px rounded cards
- Responsive 8 px spacing system
- Smooth, restrained animations
- Accessible buttons and controls
- Clear error and warning indicators

## Navigation

Windows Desktop:

- Top navigation
- Role-based pages
- Responsive card dashboard
- No permanently expanded sidebar
- No duplicated navigation

Android/iOS:

- Adaptive navigation
- Same visual identity
- Touch-friendly controls
- Responsive cards
- Platform-appropriate interactions

## Canonical Application Icon

Create a unique icon featuring:

- Front silhouette of a futuristic car
- Electric-blue line art
- Dark rounded-square background
- Integrated circuit/OBD connector motif
- Small diagnostic waveform
- Symmetrical vector geometry
- No text
- No manufacturer logos

Colors:

- #070D18
- #00BFFF
- #29DFFF
- #126EFF

Generate:

- Editable SVG
- Windows ICO
- Android adaptive icons
- iOS icon assets
- High-resolution PNG previews

Use one canonical artwork for all platforms.

Create matching navigation icons for all application sections.

---

# 6. USER MODE — VEHICLE OWNER

USER represents a vehicle owner or driver.

## Features

- Registration and profile
- Email/mobile number
- Vehicle management
- OBD connection
- Live data
- Manual diagnostics
- Automatic diagnostic scheduling
- AI symptom analysis
- Diagnostic history
- Alerts and notifications
- Nearby service centers
- Repair instructions
- Replacement part references
- Application settings

## Automatic Vehicle Monitoring

Default schedule: DAILY.

USER can configure:

- Daily/weekly/custom
- Scheduled time
- Time zone
- Email alerts
- SMS alerts
- Push notifications
- Severity thresholds
- Quiet hours
- Manual-only mode

Workflow:

1. Verify permission.
2. Check vehicle/device availability.
3. Connect to the adapter.
4. Read supported ECU data.
5. Analyze DTCs and measurements.
6. Compare historical data.
7. Run diagnostic rules and AI.
8. Save results.
9. Send configured alerts.

Do not claim unattended background scanning unless the operating system, hardware and vehicle state support it.

Support compatible vehicle-side gateways for continuous monitoring.

## AI Symptom Analysis

USER can describe symptoms in natural language.

AI must combine:

- Symptoms
- Live data
- DTCs
- Freeze frames
- Vehicle information
- Historical measurements
- Diagnostic tests

Generate:

- Root-cause hypotheses
- Evidence
- Missing information
- Recommended tests
- Repair recommendations
- Safety warnings
- Nearby professional services

Do not invent ECU measurements or unsupported vehicle facts.

---

# 7. CUSTOMER MODE — PROFESSIONAL AUTOMOTIVE SERVICE

CUSTOMER represents a mechanic, diagnostic specialist or service center.

CUSTOMER includes all eligible USER diagnostic functionality.

Additional capabilities:

- Workshop registration
- Business address
- Email/mobile number
- Working hours
- Staff accounts
- Connected USER accounts
- Real-time authorized vehicle data
- Professional diagnostic dashboards
- Wiring diagrams
- AI diagnostic methodology
- Component test procedures
- Repair references
- Work orders
- Professional reports
- MARKET discounts

## USER Connection

CUSTOMER can invite USER through:

- Email
- Phone
- Secure link
- QR code

USER must authorize vehicle-data sharing.

CUSTOMER access must be limited to the explicitly granted vehicles, data categories and duration.

Support real-time viewing where vehicle data is actually available.

Allow revocation and maintain access audit logs.

## Professional Testing Methodology

Each AI-recommended test must provide:

- Hypothesis
- Required tools
- Preconditions
- Test procedure
- Expected result
- Actual result
- PASS / FAIL / UNKNOWN
- Evidence
- Updated confidence
- Next recommended test

Completed tests must be retained in DiagnosticSession.

Avoid unnecessarily repeating tests.

## Wiring and Repair

Support legally sourced, verified:

- Wiring diagrams
- Connector references
- Pinouts
- Component locations
- Repair instructions
- Torque specifications
- Replacement guides
- Post-repair verification

Do not fabricate manufacturer wiring diagrams or technical specifications.

---

# 8. ADMIN MODE

ADMIN manages the complete platform.

Features:

- User management
- CUSTOMER management
- MARKET management
- Account verification
- Connected USER statistics
- Vehicle make/model analytics
- Diagnostic session analytics
- Device usage statistics
- Notification status
- Platform health
- AI service monitoring
- Service configuration
- Security auditing
- Update release management

Use real database statistics.

Admin access to personal data must remain permission-controlled and auditable.

---

# 9. MARKET MERCHANT PORTAL

MARKET is an automotive seller workspace, not a primary diagnostic mode.

Features:

- Merchant registration
- Shop details and contact information
- Product catalog
- Spare-part references
- Vehicle compatibility
- Product images
- Pricing
- Stock
- Special CUSTOMER discounts
- Coupons
- Limited-time offers
- Merchant analytics

Product recommendations must be based on verified compatibility.

Do not let advertisements influence diagnostic fault ranking.

---

# 10. REAL OBD PROTOCOLS — READ AND WRITE

Implement REAL automotive diagnostic protocols, not only simulated interfaces.

Create a modular C++ OBD/ECU communication architecture.

## Supported Physical Interfaces

Design for:

- ELM327-compatible adapters
- Compatible advanced adapters
- Custom diagnostic hardware
- Bluetooth Classic
- Bluetooth LE
- Wi-Fi
- USB/Serial
- CAN-capable hardware interfaces

Support must be based on real adapter capabilities and operating-system compatibility.

## Required Protocol Support

Implement applicable:

### Standard OBD / EOBD

- SAE J1979 / applicable modern OBD services
- ISO 15765-4 CAN
- ISO 9141-2
- ISO 14230 KWP2000
- SAE J1850 PWM
- SAE J1850 VPW

### Advanced Diagnostics

- ISO 15765-2 ISO-TP
- ISO 14229 UDS
- Supported manufacturer-specific diagnostics through authorized adapters and verified specifications

Do not claim universal OEM coverage.

## 10.1 READ Operations

Implement capability-checked READ functionality:

- Supported PID discovery
- Current vehicle data
- Stored DTCs
- Pending DTCs
- Permanent DTCs where available
- Freeze-frame data
- VIN where supported
- ECU information
- Supported readiness monitors
- Diagnostic status
- Supported UDS Data Identifiers
- Supported ECU metadata

Support multi-ECU diagnostics when permitted by protocol/hardware.

## 10.2 WRITE Operations

Architecture must support authorized, verified ECU write and control functionality.

Examples include:

- Clearing DTCs
- Supported diagnostic session changes
- Authorized UDS WriteDataByIdentifier
- Supported RoutineControl operations
- Approved configuration/adaptation operations
- Authorized service functions
- Programming or flashing workflows only through separately validated, OEM-authorized implementations

IMPORTANT:

WRITE support does not mean every vehicle supports every write command.

Do not send arbitrary or unverified payloads to an ECU.

Do not implement security-access bypasses, seed-key attacks, immobilizer bypasses or unsupported coding.

Operations affecting braking, steering, airbags, powertrain safety or emissions compliance require additional safeguards and qualified professional authorization.

## 10.3 WRITE SAFETY FRAMEWORK

All WRITE operations must pass through a central safety and authorization layer.

Required checks:

1. User role
2. Explicit user confirmation
3. Vehicle identification
4. ECU identification
5. Protocol capabilities
6. Adapter capabilities
7. Operation whitelist
8. Vehicle operating state
9. Required voltage/power conditions
10. Preconditions
11. Request validation
12. Audit logging
13. Response verification

Read-only access must be the default.

Professional write capabilities should be restricted to authorized CUSTOMER users and explicitly approved workflows.

Use staged execution:

- Prepare
- Validate
- Confirm
- Execute
- Verify
- Record

For programming operations, apply an operation-specific recovery strategy. Do not assume that all ECU writes can be rolled back.

Never perform destructive write operations automatically as part of scheduled monitoring.

## 10.4 Real Hardware Testing

Provide:

- OBD simulator
- Protocol unit tests
- Adapter compatibility tests
- ECU response validation
- Transport error tests
- Read operation tests
- Authorized write-operation tests on suitable test hardware
- Safe failure handling
- Reconnection tests

Clearly separate simulator validation from actual vehicle testing.

---

# 11. AI DIAGNOSTIC ENGINE

Build a hybrid engine with:

- Deterministic rules
- Live telemetry analysis
- Historical case retrieval
- Diagnostic knowledge base
- RAG
- Optional ML predictors
- Local LLM
- Remote AI provider integration
- Evidence verification
- Test recommendation
- Hypothesis ranking

All diagnostic findings must record provenance:

- USER_REPORTED
- ECU_REPORTED
- VEHICLE_MEASURED
- RULE
- ML
- LLM
- HISTORICAL_CASE

LLM conclusions cannot override measured data.

Support structured test-result ingestion and dynamic diagnostic recalculation.

---

# 12. SETTINGS — COMPLETE FUNCTIONALITY

Implement a unified Settings module with real persistence.

Settings must be consistent across Windows, Android and iOS.

## 12.1 Language Settings

Support EXACTLY these initial application languages:

1. Armenian — Հայերեն (hy)
2. Russian — Русский (ru)
3. French — Français (fr)
4. English (en)

English is the default fallback language.

Provide complete translations for:

- Navigation
- Buttons
- Settings
- Diagnostic messages
- AI responses
- Alerts
- Reports
- Notifications
- Vehicle information labels
- Error messages
- Test results
- Repair guidance

Changing the language must update the interface without requiring a full restart wherever technically possible.

Use Qt internationalization facilities.

Support locale-aware date, time and number formatting.

## 12.2 Measurement Unit Settings

USER must be able to configure units.

Support both Metric and Imperial systems.

### Speed

- km/h
- mph

### Distance

- km
- miles

### Temperature

- °C
- °F

### Pressure

- kPa
- bar
- psi

### Fuel Consumption

- L/100 km
- km/L
- mpg (US)
- mpg (UK)

### Torque

- Nm
- lb-ft

### Power

- kW
- hp

### Volume

- Liters
- US gallons

### Other Automotive Units

Support appropriate conversions for:

- Engine displacement
- Airflow
- Fuel pressure
- Distance traveled
- Battery/electrical measurements where conversion is relevant

Retain native engineering values internally.

Perform conversions only at presentation/reporting boundaries where appropriate.

Avoid cumulative rounding errors.

Never change the meaning of raw ECU measurements.

For OBD values, ensure units follow the actual PID specification.

## 12.3 Theme Settings

Support:

- Dark
- Light
- System

Default: Dark NEO AUTOMOTIVE DIAGNOSTIC theme.

Keep color semantics consistent.

## 12.4 Notification Settings

- Email enable/disable
- SMS enable/disable
- Push notifications
- Alert severity
- Quiet hours
- Notification language
- Scheduled scan summary
- Failed scan notifications

## 12.5 Diagnostic Settings

- Default connected device
- Adapter selection
- Connection timeout
- Retry policy
- Automatic reconnect
- Default diagnostic mode
- Live data refresh rate
- Logging level
- Read-only safety default
- Advanced operation permissions

## 12.6 AI Settings

- Local AI
- Remote AI
- Automatic provider selection
- Language
- Diagnostic explanation detail
- Privacy/data-sharing preferences
- Model availability status

## 12.7 Update Settings

- Current application version
- Check for updates
- Automatic update checking
- Update channel
- Update notifications
- Release notes
- Update history
- Last check
- Installed version status

## 12.8 Account and Privacy Settings

- Profile
- Email
- Phone
- Password/security
- Connected service centers
- Shared data permissions
- Consent management
- Diagnostic history retention
- Data export
- Data deletion

Store account-level settings securely on the backend and cache permitted settings locally.

Handle offline setting changes and synchronization conflicts.

---

# 13. ONLINE APPLICATION UPDATES

Implement a real online update architecture.

Create a dedicated Update Management Service.

## 13.1 Windows Desktop

Support:

- Check for available updates
- Compare installed and released versions
- Download signed update packages
- Verify integrity and signatures
- Show release notes
- Confirm installation
- Safely close/restart application
- Preserve user data
- Detect failures
- Recover or roll back where supported

Do not execute unsigned or unverified binaries.

## 13.2 Android

Use supported Android application distribution/update mechanisms.

For Play Store distributions, integrate the official in-app update flow where applicable.

Respect Android package installation and application signing rules.

## 13.3 iOS

Follow Apple distribution and App Store policies.

Support:

- Version checks
- Update availability notifications
- App Store update links
- Release notes

Do not attempt unsupported self-modification of iOS application binaries.

## 13.4 Backend Updates

Support manual, versioned backend deployments.

Implement:

- Database migration compatibility
- API version compatibility
- Health checks
- Schema evolution
- Rollback planning
- Update logs

NO CI/CD pipelines.

## 13.5 Update Dashboard

Display:

- Installed version
- Available version
- Release channel
- Compatibility
- Update size
- Download state
- Integrity verification
- Release notes
- Last update result

Never claim an update was installed unless installation is verified.

---

# 14. FUTURE PAYMENT ARCHITECTURE — NOT IMPLEMENTED NOW

The system will support payments in a future release.

Possible future capabilities:

- Marketplace purchases
- Workshop subscriptions
- Premium diagnostic plans
- Invoice payments
- Service reservations
- Customer billing

## Current Requirements

Only prepare architectural extensibility.

Define future conceptual interfaces such as:

- IPaymentProvider
- IBillingService
- IInvoiceRepository
- ISubscriptionManager

Document possible payment-domain boundaries and data relationships.

Do not build an active payment gateway.

Do not request or store card information.

Do not integrate payment SDKs.

Do not expose active payment buttons or checkout screens.

Do not implement transaction processing.

The current marketplace must operate through product listings, seller contacts, quotations and offline transaction arrangements where applicable.

Payment functionality status:

**FUTURE / DISABLED / NOT IMPLEMENTED**

Use feature flags or future-version documentation rather than partially functional checkout logic.

---

# 15. INTERACTIVE SYSTEM ARCHITECTURE DASHBOARD

Create a COMPLETE INTERACTIVE ARCHITECTURE DASHBOARD.

This is more than a static diagram.

Deliver:

docs/architecture/interactive_architecture.html

The dashboard must open locally in a browser and support fully interactive navigation.

## 15.1 Architecture Diagram Features

- Zoom
- Mouse pan
- Drag
- Node selection
- Search
- Expand/collapse
- Layer filters
- Relationship highlighting
- Data flow visualization
- Service dependency visualization
- Offline/online data paths
- Security boundaries
- Technology labels
- Color-coded service groups

## 15.2 Dashboard Sections

Create interactive sections for:

1. System Overview
2. C++ Shared Core
3. Windows Architecture
4. Android Architecture
5. iOS Architecture
6. Macroservice Architecture
7. Authentication & RBAC
8. USER Mode
9. CUSTOMER Mode
10. ADMIN Mode
11. MARKET Portal
12. OBD Protocol Architecture
13. OBD Read/Write Safety
14. AI Diagnostic Workflow
15. Live Telemetry
16. Scheduled Monitoring
17. Notifications
18. Online Updates
19. Database Architecture
20. Security Architecture
21. Future Payment Architecture
22. Testing Architecture
23. Development Roadmap

## 15.3 Interactive Component Inspector

Clicking any service or component must show:

- Component name
- Description
- Responsibility
- Technology
- Interfaces
- APIs
- Dependencies
- Input data
- Output data
- Database interaction
- Security requirements
- Failure scenarios
- Related source modules
- Related documentation

## 15.4 Dashboard Metrics

Include a distinct observability view showing:

- Service availability
- Backend status
- Database connectivity
- OBD device state
- AI provider availability
- Notification health
- API latency
- Error rates
- Memory utilization
- CPU utilization
- Version information

Use real metrics when a running backend is available.

When runtime metrics are unavailable, show UNKNOWN or UNAVAILABLE.

Do not fabricate service health or production metrics.

## 15.5 Architecture Documentation Integration

Every architecture node should link to its relevant documentation.

Maintain matching:

- Interactive diagrams
- Mermaid source diagrams
- API contracts
- Source module references
- Architecture Decision Records

Use the NEO AUTOMOTIVE DIAGNOSTIC design system.

Bundle required visualization libraries locally.

The documentation dashboard must work without a CDN.

---

# 16. COMPLETE PROJECT DOCUMENTATION

Create professional and comprehensive documentation.

Required structure:

docs/
- README.md
- PRODUCT_REQUIREMENTS.md
- FUNCTIONAL_REQUIREMENTS.md
- NON_FUNCTIONAL_REQUIREMENTS.md
- SYSTEM_ARCHITECTURE.md
- MACROSERVICES_ARCHITECTURE.md
- SOLID_CODING_STANDARDS.md
- ARCHITECTURE_DECISIONS.md
- TECH_STACK.md
- UI_UX_DESIGN_SYSTEM.md
- APPLICATION_ICON_SPECIFICATION.md
- ROLES_AND_PERMISSIONS.md
- DATABASE_DESIGN.md
- API_SPECIFICATION.md
- OBD_PROTOCOLS.md
- OBD_READ_OPERATIONS.md
- OBD_WRITE_OPERATIONS.md
- OBD_SAFETY_MODEL.md
- VEHICLE_COMPATIBILITY.md
- AI_DIAGNOSTICS.md
- USER_MODE.md
- CUSTOMER_MODE.md
- ADMIN_MODE.md
- MARKETPLACE.md
- WIRING_DIAGRAMS.md
- REPAIR_PROCEDURES.md
- AUTO_MONITORING.md
- NOTIFICATION_SYSTEM.md
- APPLICATION_SETTINGS.md
- LOCALIZATION.md
- UNIT_CONVERSION.md
- ONLINE_UPDATE_SYSTEM.md
- FUTURE_PAYMENT_ARCHITECTURE.md
- SECURITY_AND_PRIVACY.md
- TEST_METHODOLOGY.md
- TEST_CASE_MATRIX.md
- HARDWARE_TEST_PLAN.md
- PERFORMANCE_TESTING.md
- DEVELOPMENT_PLAN.md
- DEPLOYMENT_GUIDE.md
- BUILD_AND_RUN.md
- RISK_REGISTER.md
- IMPLEMENTATION_REPORT.md

Create and maintain:

- Interactive architecture dashboard
- Mermaid architecture diagrams
- Component diagrams
- Data-flow diagrams
- Sequence diagrams
- Entity relationship diagrams
- OBD Read/Write state diagrams
- Deployment diagrams
- Test coverage matrices

All documentation must reflect the actual codebase.

Clearly distinguish IMPLEMENTED, PLANNED, BLOCKED and UNSUPPORTED features.

---

# 17. TEST METHODOLOGY AND QA AUTOMATION

Create automated testing infrastructure without CI/CD.

## Testing Levels

### Unit Tests

- C++ classes
- SOLID interface contracts
- Protocol decoding
- OBD data validation
- Unit conversions
- Language selection
- Role authorization
- Scheduler calculations
- AI schema validation
- Discount calculations

### Integration Tests

- Macroservice boundaries
- Backend + PostgreSQL
- Application + Backend
- OBD adapter + Protocol
- AI + Diagnostic engine
- CUSTOMER + USER permissions
- Notification providers
- Update service + Version metadata
- Settings synchronization

### End-to-End Tests

Validate complete USER, CUSTOMER, ADMIN and MARKET workflows.

### OBD Read Tests

- Real PID responses
- DTC retrieval
- Freeze-frame validation
- Multiple ECU handling
- Protocol detection
- Invalid responses
- Connection recovery

### OBD Write Tests

- Permission checks
- Preconditions
- Unsupported commands
- Safety-state validation
- User confirmation
- Response verification
- Auditing
- Failure recovery

Use safe simulators, benches and authorized test ECUs.

Do not execute dangerous write tests on ordinary vehicles.

### Localization Tests

Validate all four languages:

- Armenian
- Russian
- French
- English

Test missing translations, layout overflow and locale formatting.

### Unit Conversion Tests

Verify correct conversion and rounding for:

- km/h ↔ mph
- km ↔ miles
- °C ↔ °F
- kPa ↔ bar ↔ psi
- L/100km ↔ mpg
- Nm ↔ lb-ft
- kW ↔ hp

### Update Tests

- No update available
- Valid update
- Invalid signature
- Corrupted package
- Network interruption
- Insufficient storage
- Version incompatibility
- Interrupted update
- Recovery
- Platform policy restrictions

### Architecture Tests

Validate:

- SOLID contract expectations
- Dependency direction
- Service boundaries
- API contracts
- No unauthorized cross-domain database coupling
- No direct UI dependency inside core business logic

### Performance Tests

- Startup
- UI navigation
- OBD polling
- Protocol processing
- API latency
- AI processing
- Memory usage
- CPU usage
- Offline operation
- Battery impact

Target at least 90% meaningful coverage for critical core business logic.

Record real execution status:

PASS / FAIL / SKIPPED / BLOCKED / NOT RUN

Do not claim simulator results prove full real-vehicle compatibility.

---

# 18. DEVELOPMENT PLAN

Implement in phases.

## Phase 0 — Repository Reset

- Confirm repository root.
- Preserve Git history.
- Remove previous application source code.
- Remove existing CI/CD workflows.
- Create a new C++/Qt repository structure.
- Configure CMake.
- Configure local build and test scripts.

## Phase 1 — Architecture and UI Foundation

- SOLID architecture
- Macroservice boundaries
- C++ interfaces
- Qt/QML foundation
- NEO AUTOMOTIVE theme
- Canonical icon
- Application navigation
- Interactive architecture dashboard

## Phase 2 — Authentication and Database

- Identity service
- RBAC
- User roles
- Organizations
- PostgreSQL
- SQLite
- Secure synchronization
- API contracts

## Phase 3 — OBD Diagnostic Core

- Hardware abstraction
- Real protocols
- Read operations
- Controlled write framework
- ECU communication
- Live telemetry
- DTCs
- Protocol simulator
- Hardware tests

## Phase 4 — USER Mode

- Account and vehicle management
- Diagnostics
- Live data
- Scheduled scans
- Email/SMS
- AI symptom analysis
- Nearby service centers
- Repair guidance

## Phase 5 — CUSTOMER Mode

- Workshop profiles
- USER connections
- Permission sharing
- Professional diagnostics
- Wiring diagrams
- AI test methodology
- Repair reports

## Phase 6 — MARKET Portal

- Merchant accounts
- Products
- Compatibility
- Inventory
- Discounts
- Professional offers

No payment gateway implementation.

## Phase 7 — ADMIN Mode

- Platform administration
- Account management
- Workshop monitoring
- Vehicle analytics
- Marketplace oversight
- Security and operational monitoring

## Phase 8 — Application Settings

- Armenian
- Russian
- French
- English
- Metric/Imperial units
- Themes
- Notifications
- Diagnostic preferences
- AI settings
- Privacy settings

## Phase 9 — Online Updates

- Update service
- Windows signed updates
- Android supported update integration
- iOS update coordination
- Version management
- Update diagnostics and recovery

## Phase 10 — AI Improvements

- Hybrid AI
- RAG
- Deterministic rules
- Evidence management
- Test recommendation
- Fault hypothesis ranking
- Repair guidance

## Phase 11 — Cross-Platform Validation

- Windows build
- Android build
- iOS build
- UI consistency
- Device compatibility
- Performance optimization
- Accessibility
- Security

## Phase 12 — Final QA and Documentation

- Full regression
- Local test execution
- Real hardware validation where available
- Performance benchmarking
- Security review
- Documentation completion
- Architecture dashboard verification
- Final report

Each phase must include explicit deliverables, dependencies, acceptance criteria and a local verification report.

---

# 19. FINAL PROJECT STRUCTURE

Create a clean modular repository.

```text
CAR_DIAGNOSTIC_ANALYSIS/
│
├── CMakeLists.txt
├── CMakePresets.json
│
├── apps/
│   ├── windows/
│   ├── android/
│   └── ios/
│
├── ui/
│   ├── components/
│   ├── pages/
│   ├── themes/
│   ├── icons/
│   ├── charts/
│   ├── settings/
│   └── translations/
│
├── core/
│   ├── interfaces/
│   ├── obd/
│   ├── protocols/
│   ├── transport/
│   ├── telemetry/
│   ├── diagnostic/
│   ├── ai/
│   ├── rules/
│   ├── vehicles/
│   └── security/
│
├── services/
│   ├── identity/
│   ├── vehicle/
│   ├── diagnostics/
│   ├── ai_analysis/
│   ├── monitoring/
│   ├── notifications/
│   ├── customer/
│   ├── marketplace/
│   ├── administration/
│   └── updates/
│
├── future_modules/
│   └── payments/
│       └── ARCHITECTURE.md
│
├── backend/
│   ├── api/
│   ├── database/
│   ├── events/
│   └── security/
│
├── integrations/
│   ├── email/
│   ├── sms/
│   ├── maps/
│   ├── automotive_data/
│   └── ai_providers/
│
├── assets/
│   ├── app_icon/
│   ├── vehicles/
│   ├── fonts/
│   └── illustrations/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   ├── ui/
│   ├── e2e/
│   ├── obd/
│   ├── security/
│   ├── performance/
│   └── simulators/
│
├── docs/
│   ├── architecture/
│   │   └── interactive_architecture.html
│   ├── diagrams/
│   ├── api/
│   └── testing/
│
├── scripts/
│   ├── build/
│   ├── test/
│   └── package/
│
└── config/
```

No CI/CD workflow configuration.

Do not add active payment code.

---

# 20. DEFINITION OF DONE

A feature is considered completed only when:

1. Source code is implemented.
2. SOLID architecture is respected.
3. Service boundaries are correct.
4. Application compiles on its claimed supported platforms.
5. Required database integration works.
6. Backend API works.
7. Authentication and authorization are enforced.
8. UI follows the exact design system.
9. Relevant functionality is tested.
10. Failures are handled safely.
11. Documentation is updated.
12. Interactive architecture dashboard reflects the implementation.
13. Actual test results are reported.
14. No known critical regression remains.

## Required Implementation Report

After each phase report:

- Implemented features
- Modified and created files
- New interfaces
- Service changes
- Database migrations
- Build status by platform
- Test results
- Code coverage
- Performance results
- Security findings
- Known limitations
- Next tasks

Never mark unfinished modules as production-ready.

---

# FINAL EXECUTION INSTRUCTION

Start by verifying the active repository, preparing a safe reset of the old application files, and establishing the new C++/Qt project.

Implement the NEO AUTOMOTIVE UI, canonical icon, SOLID interfaces and Macroservice architecture.

Create the fully interactive architecture dashboard and complete technical documentation.

Then develop the real diagnostic functionality, supported OBD Read/Write framework, USER/CUSTOMER/ADMIN modes, MARKET portal, Settings, AI, notifications and online updates phase by phase.

Keep payment processing strictly deferred for a future release.

Use local automated builds and tests without CI/CD.

Do not stop after producing diagrams or pseudocode. Implement actual source code wherever execution access permits.

## FINAL GOAL

A production-oriented, secure, fast and extensible automotive diagnostic ecosystem featuring:

**C++20/23 + Qt/QML + SOLID + Macroservices + Real OBD Read/Write + AI Diagnostics + Online Updates + Interactive Architecture Dashboard + Four Languages + Configurable Units + Complete Documentation.**

**THREE PRIMARY MODES.**

**ONE INTEGRATED MARKETPLACE.**

**ONE SHARED DIAGNOSTIC CORE.**

**ONE UNIFIED UI DESIGN.**

**NO LEGACY CODE.**

**NO CI/CD.**

**PAYMENTS RESERVED FOR THE FUTURE.**