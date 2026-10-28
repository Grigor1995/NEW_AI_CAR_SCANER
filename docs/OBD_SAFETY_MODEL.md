# Write safety and authorization

Read-only is enforced by the transport command allowlist. The independent safety predicate requires CUSTOMER (ADMIN does not bypass), explicit consent and confirmation, nonempty authenticated actor and verified vehicle/ECU, adapter/ECU clear capability, whitelisted operation, ignition on, engine off, stationary vehicle, measured voltage 12–15 V, observed state <=5 seconds old and not in the future, plus durable audit availability. Every missing prerequisite is separately denied in tests.

These conservative fixture values are not a universal OEM procedure or approved profile. The application has no qualified hardware-profile trust source and therefore exposes no write executor. No ECU write is scheduled or performed. A verified bench workflow and professionally authorized profiles are external prerequisites before enabling any operation; arbitrary firmware updates are not permitted by this policy.
