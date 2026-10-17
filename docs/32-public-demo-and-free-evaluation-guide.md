# Public demonstration and a zero-budget model experiment

This increment addresses accessibility and the missing model comparison separately. The public site is an **interactive replay**, not an authenticated hosted FastAPI/PostgreSQL application. The actual free-tier comparison has now executed: 14 model calls, 14/24 model-arm task successes versus 17/24 for the template, with nine validation failures and no demonstrated uplift. See [the measured report](33-live-model-comparison-report.md). Independent human review remains unperformed.

## Open the public replay

Canonical project URL: https://manuelportugalreis.github.io/RevenueOS/. GitHub may redirect project Pages to the owner's existing custom domain, https://manuelportugalreis.com/RevenueOS/. Only this project's subpath is published; the existing personal site is not replaced.

The public build reuses the React dashboard and recorded synthetic API responses in `data/dashboard/public-replay.json`. It automatically opens without a password. The banner identifies every interaction as recorded/simulated. Use **Start guided walkthrough**, replay the configuration-checklist recommendation, inspect the exact citation, open Approvals, and simulate a decision. Reset clears browser-local state. Other visitors have independent state. There is no database connection, model call, credential, persistent approval or send endpoint in this build. Unknown questions/lead combinations fail rather than inventing a response. Dates and expiry values are recorded historical facts, not current authorization.

`scripts/capture_public_replay.py` regenerates the recording against the running loopback synthetic API. It authenticates the demo personas, captures actual KPI/recommendation/citation/action responses, and excludes existing shared-demo queue history and cost ledger. It never exports session cookies, password hashes or CSRF tokens. The injection fixture records an abstained workflow; the replay does not fabricate a reviewable draft for it. The API intentionally refuses opening that abstained recommendation as reviewable.

```powershell
# Run the synthetic API helper first, using REVENUEOS_DEMO_PASSWORD from your environment.
./.venv/Scripts/python scripts/capture_public_replay.py
npm.cmd run build:showcase --prefix frontend
npm.cmd run test:showcase --prefix frontend
```

The showcase build uses `/RevenueOS/` as its asset base and an isolated output folder. `npm run build` still produces the authenticated full-stack frontend, with replay behavior removed. GitHub Actions runs the complete Python suite, both production/public builds, Docker build, actual backend browser journeys and replay journeys before Pages deployment. A failed verification prevents deployment. The public tests assert no `/api` or provider requests, citation inspection, temporary approval, reset, visitor isolation, unknown-query rejection, mobile layout and automated accessibility.

Why this hosting choice: the existing public GitHub repository can host static assets without a paid backend. A simpler alternative is screenshots; a fuller alternative is a separately funded and hardened FastAPI/PostgreSQL deployment. The public replay solves zero-install exploration but does **not** satisfy a claim of hosted backend authentication or live inference. See [GitHub's Pages workflow requirements](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## What the prospective baseline found

Before writing 24 new questions, the focused evidence policy and the corrected extractive prompt were frozen. The original provider payload omitted the user's query; `extractive_sales_v2` now supplies it and explicitly requires answering it. The same strict schema, original passages and validator apply to both arms. The policy itself was not tuned after seeing the new results. This experiment tests whether a model improves evidence selection/refusal under the current restrictive output contract; it does not test creative outreach writing.

The first new template-only run passed **17/24** authored tasks: eight relevant completions among nine answerable tasks, one false abstention, nine correct abstentions among 15 refusal tasks and six inappropriate completions. There were no technical failures or unsupported quotations. No model was called. This is a different, harder authored set; do not compare its percentage directly with 99/100 as a controlled effect. Both remain project-authored diagnostics, not independent labels or a hidden predictive test. Raw attempts, prompt/schema hashes and source hashes are under `outputs/prospective/template-final/` (the initial run remains in `template-only/`). Retain the failures instead of tuning this run away.

## Configure the free API without sharing a key

Annotation caveat: the expected-refusal labels are provisional. Some yes/no questions may admit a valid, grounded negative answer (for example, a passage explicitly denying a guarantee). An extractive completion can therefore disagree with an authored refusal label without being false. The 17/24 result and six inappropriate-completion counts are conditional on this conservative rubric, not adjudicated human error rates. Preserve the original labels/results and resolve such disagreements through blinded independent review; do not silently relabel this run to improve its score.

The owner requires **zero monetary spend** and explicitly confirmed Free Tier with no linked billing before live calls. The initial 2.5 Flash-Lite request returned HTTP 404 (unavailable to new users); that failed run and its single halted transport attempt are preserved. A separate minimal diagnostic confirmed the provider recommended 3.5 Flash-Lite, which was also present in the authenticated catalog and official free pricing. This is an explicit availability correction, not an automatic model fallback or tuning against task results. The optional adapter targets `gemini-3.5-flash-lite` through the official Developer API. At inspection, [Google's pricing page](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite) lists free-tier input/output and separate paid-tier prices. Availability, account eligibility and quotas are not guaranteed. Unpaid-service data may be used to improve Google products; this project transmits approved synthetic material only. Request shape follows [generateContent](https://ai.google.dev/api/generate-content) and its JSON-schema generation settings. Provider schema compliance is not evidence of factual relevance.

1. Create/use a Google AI Studio project on the **Free Tier with no billing attached**. Do not enable billing, upgrade plans or use a paid project for this experiment.
2. Create a key in that project. Store it in an ignored local `.env` file or the process environment. Never paste it into chat, Git, the browser build or public Pages.
3. Explicitly attest the account state with `REVENUEOS_FREE_TIER_CONFIRMED=1`. The code cannot inspect billing entitlement from the key; this flag is an operator attestation, not API verification. If that state is uncertain, leave the adapter disabled.

Ignored `.env` content (replace the placeholder locally):

```dotenv
GEMINI_API_KEY=replace-locally-never-commit
REVENUEOS_FREE_TIER_CONFIRMED=1
```

For the synthetic organization/current dataset from the data guide:

```powershell
$env:DATABASE_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/revenueos_web_demo'
./.venv/Scripts/python -m revenueos.prospective --organization ORG_UUID --dataset DATASET_UUID --output outputs/prospective/new-free-run --live-free --env-file .env
```

The optional env-file reader reads **only** the two Gemini fields, and never logs their values. Set DATABASE_URL separately; use an already seeded synthetic database and steward membership. Without `--live-free`, only the template arm executes. Without the key and attestation, live mode fails before database access. No OpenAI key, SDK dependency, paid fallback, external tool or endpoint override is used.

Calls are paced at 15-second intervals, capped at 24 for this dataset, with one attempt per task. Provider transport failures halt subsequent calls; remaining assigned model tasks count as technical failures rather than being discarded. Unknown usage remains unknown in the ledger. The shared budget is configured to zero with an explicitly attested free price card; **that ledger cannot prevent charges if an operator falsely attests a paid account**. Invoices remain null until actually observed. This is why disabling billing at the provider, not merely configuring a local zero price, is required.

## Compare honestly and collect independent review

Each arm sees the same lead, approved corpus, scope, evidence time and validator. Upstream policy may abstain before calling a model; inspect actual transport calls and the subset reaching inference. All assigned tasks and failures remain in denominators. Raw outputs, known/unknown token accounting and family-level descriptive intervals are preserved. A free provider refusing quota is a reliability result, not an acceptable abstention or quality success.

The output contains shuffled `independent-review-blank.csv` and a separate `coordinator-key.csv`. Give two independent reviewers the blank packet and approved corpus, withholding arm names and automated scores. Rate relevance/grounding 0–2, record actual review/edit seconds, preserve disagreements and adjudicate before opening the key. Empty cells are missing observations, not zero effort. No review, recruitment, message or human time-saving claim has been fabricated. Model-minus-template value and realized ROI remain unproven until evidence exists.

For a new unseen test after this diagnostic, have someone outside implementation author/label the tasks, freeze all configuration before execution, and do not modify that test after seeing results. Keep v0.1.0 and the current failed baseline as historical evidence.
