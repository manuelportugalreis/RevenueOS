# Synthetic intelligence fixtures

All documents, policies, labels, identities, prices, token counts and outcomes used here are synthetic. They are not business approvals, independently annotated benchmarks, provider pricing, or real customer evidence.

- `corpus.json`: 19 versioned text documents, including scope, lifecycle, conflict and injection examples.
- `cases.json`: 100 lexical variants across 20 agent-authored families; 60 development cases/12 families and 40 test cases/eight families. Families never cross splits. These are knowledge cases, not a predictive business holdout.
- `failure_cases.json`: 15 provider/policy/cost fault scenarios exercised by the automated tests.
- `SHA256SUMS`: exact fixture file hashes.

Regenerate with `python scripts/build_intelligence_fixtures.py --output DIRECTORY`. The fixture builder does not use a model or network. Fixed retrieval time is 2026-10-16T12:00:00Z; synthetic document approval time is 2026-09-01. Revocation always denies access, including historical views. The synthetic reader only has team scope.

See the intelligence guide and verification report in docs for observed results, failed quality gates, and interpretation limits. Do not treat five lexical variants as five independent business examples. Scripted provider outputs copy the template intentionally, so they cannot demonstrate LLM improvement.
