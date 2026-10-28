# Test matrix

| Area | Local coverage | External / remaining |
|---|---|---|
| Protocols | valid/wrong PID, truncation, hex errors, multi-ECU DTC, ISO-TP sequence/size, bitmap | real firmware, raw CAN, full protocol matrix |
| Safety | every missing role/confirmation/ID/capability/state/voltage/freshness/audit prerequisite denied | trusted profiles, one-use executor, bench verification |
| Identity | salts/hash, credentials, owner scope, token/logout, persisted restart, role escalation denial | MFA/recovery, distributed abuse and sharing consent |
| Settings | field whitelist, invalid locale, persistence, source-catalog parity, runtime switch | conflict sync, all advanced preferences |
| UI | pages instantiated, locale/theme/units, narrow render and actual screenshot | native touch/accessibility and all task E2Es |
| Updates | version ordering, real signature and tamper rejection | signed feed/package/install/recovery |
| Monitoring | unavailable/ignition/OS eligibility => deferred | actual scheduler/background jobs |
| Commerce/providers | no active payment or fabricated service claims | all real merchant/notification/licensed-provider workflows |

Exact outcomes and limitations are in IMPLEMENTATION_REPORT.md and testing/current-results.json.
