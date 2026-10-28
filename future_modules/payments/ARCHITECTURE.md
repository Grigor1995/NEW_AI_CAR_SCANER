# Future billing and payments — NOT IMPLEMENTED / DISABLED

Reserve an independently owned billing domain for future invoices, orders,
subscriptions, refunds and provider adapters. Conceptual contracts are
IPaymentProvider, IBillingService, IInvoiceRepository and ISubscriptionManager.
They are documentation only: no compiled interface, provider SDK, active API,
checkout button, card-data field or transaction processing exists in V3.

Future integrations must accept provider tokens rather than card details,
validate signed provider webhooks, make state transitions idempotent and retain
financial audit events. Marketplace quotations and seller contact workflows
must remain independent of diagnostic hypothesis ranking. A future ADR and
privacy/security review must precede enabling any payment capability.
