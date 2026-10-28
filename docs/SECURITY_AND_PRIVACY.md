# Security and privacy

Local identity uses OpenSSL scrypt (N=16384,r=8,p=1,16-byte salt,32-byte derived key) with bounded UTF-8 password length, secure random opaque session credentials and persisted SHA-256 token hashes. SQLite checks current active accounts and session expiry for each authenticated request. New users receive USER only; local operator provisioning is explicit. Profile queries are owner-scoped and use bound SQL parameters. JSON inputs/settings are bounded/whitelisted and errors omit credential values.

Current host is loopback-only with a coarse in-process auth throttle, not an internet-hardened identity provider. Password recovery, verified contacts, MFA, distributed rate limiting, TLS termination, full audit coverage, account deletion/retention/export, keychain storage, CSRF/origin deployment review and denial-of-service hardening remain required. The UI's local auth store is not remote SSO or tenant sharing. Plain local adapter TCP has no encryption/authentication; only authorized trusted adapters should be used. Reports may contain private diagnostics and are written owner-only; contact/location data must not be leaked.

Writes are transport-locked. No security access bypass, unsafe OEM payload, unrestricted LLM action or automatic write is exposed. No physical safety certification or penetration test is claimed.
