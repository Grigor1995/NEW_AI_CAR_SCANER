# Risk register

| Risk | Current mitigation / remaining gate |
|---|---|
| Incorrect or unsafe ECU write | allowlist plus locked executor; verified profiles and authorized bench acceptance required |
| False measurement or diagnosis | strict response/PID checks, explicit quality/provenance, no invented confidence |
| Public identity exposure | loopback-only host; TLS/MFA/abuse review required before public deployment |
| Unverified platform claims | Linux evidence only; native Windows/Android/iOS packaging NOT RUN |
| Mobile permissions/background restrictions | serial deliberately unavailable; background scanning not implemented |
| Update compromise | real signature primitive; no execution/download until pinned-key signed installer design |
| Lost old work | Git history, archive branch, verified bundle and filesystem copy outside active repo |
| Incomplete product phases | explicit status matrix, no fabricated providers/stats/payments |
| Data leakage/retention | owner queries and owner-only DB/report files; full deletion/backup/privacy lifecycle pending |
| License/data accuracy | no reused/unauthorized OEM diagram/fitment data; licensed integration blocked |
