# Notifications — PLANNED / UNAVAILABLE

INotificationSender is a small domain contract only; no email/SMS/push adapter is configured, no contact has been verified, and no messages are sent. Settings show unavailable provider state. Future implementation needs consent, verified destinations, language/quiet hours, delivery outbox, retries, deduplication, throttles/cooldowns, redaction and delivery audit.

Provider credentials must be supplied through secure environment settings after inspecting actual bindings; do not hardcode keys or request values in chat. Simulator/provider-contract tests must remain separate from sandbox/live delivery evidence.
