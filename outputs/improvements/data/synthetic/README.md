# Synthetic CRM fixtures

Every entity and outcome here is fictitious. Email/domain values use reserved `.example` domains. These datasets contain no customer evidence and cannot establish scoring accuracy, revenue lift, or ROI.

- `golden/`: fixed hand-computable edge fixture: 35 input rows, 28 accepted, six quarantined, one exact duplicate. Expected accepted counts: accounts 2, leads 8, opportunities 4, interactions 6, opportunity links 2, stage events 1, outcomes 5.
- `demo/`: seed 42, 1,000 leads, as-of 2026-10-01T00:00:00Z. Includes sparse attributes/outcomes, suppression, automated contact, recent leads, multiple currencies, and independently simulated qualification flags.

Regenerate using `python -m revenueos.cli synthetic data/synthetic/golden --golden` and `python -m revenueos.cli synthetic data/synthetic/demo --seed 42 --leads 1000`. File bytes are deterministic for the same generator/version/arguments. Generator tests compare repeated outputs. SHA256SUMS records the checked-in CSV/manifest bytes.

Golden metric cohort: [2026-08-01, 2026-10-01) UTC. Eligible inbound leads 6; test/internal excluded 1; deleted excluded 1; human responses 3; no recorded response 3; response hours [2,4,1], median 2, p90 3.6. Mature complete qualification cohort 3, qualified 1; immature 1, missing/incomplete mature outcomes 2. Wins 1 / closed 2. Open pipeline EUR 4000.20 and USD 3000.10. The malformed opportunity and its dependent link are quarantined; duplicate L1 does not increase any denominator.
