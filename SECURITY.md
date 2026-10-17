# Security policy

RevenueOS is a synthetic portfolio demonstration. Do not upload real CRM records, credentials or customer documents. External messaging is unavailable and live model transport remains disabled by default. Fixture passwords in tests/CI are disposable public examples; they must never be used for hosted systems.

Report a vulnerability through this repository's **Security → Report a vulnerability** feature. Do not include secrets, personal records or exploit details in a public issue. If private reporting is unavailable, open a minimal issue requesting a private contact without sensitive details. This portfolio has no guaranteed response time or production support commitment.

The current trust boundaries and remaining gaps are documented in [the security design](docs/05-security-governance.md), [runtime/recovery guide](docs/28-improvements-guide.md) and [executed verification](docs/29-improvements-verification.md). Database administrators and the application process remain trusted. Passing fixture tests is not a universal security proof.
