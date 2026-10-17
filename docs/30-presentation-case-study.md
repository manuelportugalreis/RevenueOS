# RevenueOS: an evidence-led revenue operations portfolio

## The problem

A B2B SaaS inbound team needs to prioritize leads, understand pipeline health and prepare accurate outreach. A CRM export alone does not provide trustworthy metrics or source-backed recommendations. Adding a model before controlling data, evidence and permissions can accelerate incorrect decisions.

RevenueOS demonstrates the complete engineering path from synthetic CRM data to SQL metrics, transparent priorities, approved knowledge, cited recommendations and human review. There is no client company or actual business pilot.

## Architecture and decisions

Python/FastAPI, PostgreSQL and React/TypeScript form a modular monolith. PostgreSQL handles transactional snapshots, analytics, full-text retrieval, sessions and audit, keeping infrastructure small. Deterministic scoring is explainable; synthetic outcomes cannot justify a trained conversion classifier. Templates isolate retrieval and policy errors before spending on live models. Bounded read tools control authority, while an explicit reviewer approves an immutable draft version. The application cannot deliver it externally.

The [architecture](22-architecture-current.md) shows the flows. The [implementation guide](28-improvements-guide.md) explains choices, simpler alternatives and operating instructions.

## What the evidence supports

- 207 Python/PostgreSQL tests and two local Chromium journeys passed; the browser used a native restricted database login.
- Four template arms scored 66, 85, 99 and 99 successful authored tasks out of 100. The focused direct and bounded variants had equal quality; orchestration added latency and audit controls.
- A grounded but inappropriate completion remains. Cases were previously exposed and authored within the project; independent labels and a new holdout are absent.
- Batched scoring used four client SQL statements instead of 3,001 for 1,000 synthetic leads, preserving score explanations.
- Local isolated backup/restore preserved row fingerprints. Post-restore grants and PUBLIC revokes were reapplied and tested with a non-owner login.
- Rework and missingness can invalidate an attractive business scenario. All human times are scripted; real participants, measured savings and realized ROI remain absent.

These are recorded local observations. The public repository's Actions run supplies separate hosted CI evidence. Source hashes and raw attempts make the diagnostic inspectable; [the report](29-improvements-verification.md) records uncertainty, failure cases and remaining risks.

## What I would explain in an interview

The strongest outcome is a defensible boundary between what was measured and what remains assumed. Improving evidence selection mattered more than adding agent orchestration. Authentication, RLS and immutable review protect different boundaries; none substitutes for the others. Model cost reservations preserve uncertainty after interrupted requests. Software milliseconds cannot be translated into rep productivity or revenue uplift without a human study.

The next quality milestone is independent review and newly authored unseen tasks. A future authorized business pilot would measure total preparation, review and rework effort, task quality, actual costs and mature outcomes. Until then, this is a complete synthetic demonstration with explicit production gaps.

Use [the five-minute walkthrough](26-interview-demo.md) to present it. If services are unavailable, use the current recorded screenshots and raw attempts rather than pretending to run a live system.
