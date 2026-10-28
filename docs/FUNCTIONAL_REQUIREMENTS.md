# Functional requirements and current coverage

| Domain | Current behavior | Status |
|---|---|---|
| Identity | Local SQLite accounts, scrypt passwords, expiring opaque bearer sessions, roles | IMPLEMENTED local slice |
| Vehicles | Private owner-scoped manual profiles; VIN syntax validation, not OEM verification | PARTIAL |
| OBD | C++ asynchronous TCP/desktop serial ELM setup, supported bitmap, RPM/speed/coolant, stored DTCs | PARTIAL; loopback tested |
| Read/write safety | Read allowlist; independent all-preconditions write policy; ECU writes not exposed | PARTIAL; writes LOCKED |
| UI | Shared QML, responsive main menu, account, vehicles, live data, rules, JSON report, preferences | IMPLEMENTED foundation |
| Roles | USER/CUSTOMER/ADMIN assignments; operator CLI provisioning; MARKET separate | PARTIAL; professional/admin workflows PLANNED |
| Languages/units | EN/HY/RU/FR catalogs, runtime switch; engineering conversions | IMPLEMENTED current screens |
| Updates | Version comparator and real Ed25519 verification primitives | PARTIAL; feed/install PLANNED |
| Notifications/market/repair | Labeled unavailable pages and architecture boundaries | PLANNED, not functional substitutes |
| Payments | Documentation boundary only; no compiled/payment code | DISABLED / NOT IMPLEMENTED |
