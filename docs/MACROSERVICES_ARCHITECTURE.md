# Domain macroservice boundaries

| Service | Owner / interface boundary | Current implementation |
|---|---|---|
| Identity & access | accounts, roles, tokens, consent policy | services/identity/Store; consent sharing PLANNED |
| Vehicle management | owner profiles, catalog/VIN references | Store vehicle slice; extraction to its own repository PLANNED |
| Diagnostics | sessions, measurements, command orchestration | services/diagnostics; no cross-tenant remote device API |
| AI analysis | evidence, hypotheses, tests and provider orchestration | core/ai deterministic slice; RAG/LLM PLANNED |
| Monitoring/notifications | scan eligibility, schedules, delivery outbox | eligibility policy only; delivery PLANNED |
| Customer/workshop | organizations, staff, owner-approved scopes | PLANNED |
| Marketplace | merchants, listings, fitment, quotes | PLANNED; payments excluded |
| Administration | controlled assignments, audit and metrics | local operator provisioning only |
| Updates | release metadata, verification, platform delivery | crypto/version primitives only |
| Future billing | future provider/order/invoice separation | documentation only |

Deploy coarse domains in one process initially. Extract independently only with concrete scaling/security ownership needs. The current Store combines small identity and owner-profile persistence; splitting repository contracts is required before independent service extraction. Do not describe these folders as deployed services. Future versioned events need correlation IDs, transactional outbox, idempotency and schema compatibility; no queue exists now.
