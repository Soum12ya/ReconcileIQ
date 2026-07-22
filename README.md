# ReconcileIQ

**An agentic AI system for automated Accounts Payable invoice reconciliation.**

ReconcileIQ replaces the manual 3-way-match, vendor-chase, and re-key workflow that AP teams run on every discrepant invoice with a multi-agent pipeline: a router that classifies each case, a planner that resolves the trivial ones instantly and reasons through the ambiguous ones with real PO/contract data, a policy gate that keeps every external action auditable, an async agent that handles vendor back-and-forth without blocking anything, and a human approval step that keeps a person in control of every dollar that gets posted.

It was built as a hands-on capstone to demonstrate four things end to end: **harness engineering**, **loop engineering**, **evals**, and **human-in-the-loop design** — not as slide-deck concepts, but as a working system with real bugs found and fixed along the way.

---

## Table of contents

- [Problem statement](#problem-statement)
- [Demo](#demo)
- [Workflow](#workflow)
- [Performance](#performance)
- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [API reference](#api-reference)
- [The UI](#the-ui)
- [Testing](#testing)
- [The LLM Ops loop](#the-llm-ops-loop)
- [Deployment](#deployment)
- [What's built vs. what's a known simplification](#whats-built-vs-whats-a-known-simplification)
- [Roadmap / build phases](#roadmap--build-phases)

---

## Problem statement

Accounts Payable teams process invoices by manually performing 3-way matching (Purchase Order ↔ Goods Receipt ↔ Invoice), chasing discrepancies with vendors via email or portal, and re-keying approved invoices into the ERP. This causes:

- **Delayed collections** — multi-day email threads per discrepancy
- **High cost-to-process** — large manual teams doing repetitive, low-judgment work
- **Inconsistent resolution quality** — outcomes depend on which staff member handles a case
- **No systematic learning** — the same mistakes recur with no feedback loop

ReconcileIQ automates triage, investigation, vendor communication, and re-keying, while keeping exactly one human decision point (final approval) and adding a capability the manual process never had: a system that measurably improves its own accuracy over time.

---

## Demo

**Live dashboard**
<table>
  <tr>
    <td><img width="480" alt="demo_ui_test_01" src="https://github.com/user-attachments/assets/a6464316-d033-43c5-a09f-1e11dfd88673" /></td>
    <td><img width="480" alt="demo_ui_test_02" src="https://github.com/user-attachments/assets/a2fd0f08-9cf8-43ec-b1f5-875a1309e7e2" /></td>
  </tr>
</table>

*Left: a price-variance case routed and awaiting resolution. Right: a case resolved and closed. The queue on the left is color-coded by status; the detail panel on the right shows the full reasoning trail with context-aware actions.*

**Demo video**

Watch the demo - 
*~2 minute walkthrough: a clean-match invoice auto-resolving, a price-variance case going through the router and policy gate, a triage case resolved manually and approved, and the async vendor loop surviving a worker restart.*

> Replace the paths above with your actual screenshot/video files once captured — see [Testing](#testing) for the exact payloads used to generate each state shown in the video.

---

## Workflow

<img width="780" height="720" alt="ap_agent_combined_system_design" src="https://github.com/user-attachments/assets/448e8668-b545-4b7c-acbc-d265e1cb8bbd" />

*Gateway → Router Agent → Reconciliation Planner (deterministic rule or agentic RAG-backed reasoning) → Policy & Guardrails Gate → Vendor Query Agent (async) or Human Triage → Human Approval → Posted & Closed. The Status Agent and LLM Ops Loop run alongside the pipeline rather than inside it — see [Architecture](#architecture) for the full breakdown.*

---

## Performance

Measured with `python -m infra.load_test` against the real router agent (not mocked) on 20 sequential invoice submissions:

| Metric | Value |
|---|---|
| p50 latency | **1.56s** |
| p95 latency | **1.95s** |
| Max latency | 30.79s |

The p50/p95 numbers reflect the router's LLM classification call, which is the dominant cost on the sync path. The max outlier is a known bottleneck — see [Known simplifications](#whats-built-vs-whats-a-known-simplification) for the honest read on why, and what a production fix would look like (prompt caching or a faster model). Cases that hit the **deterministic rule path** (no LLM call at all) resolve in well under 100ms, not reflected in the table above since the load test intentionally targeted the router-bound path.

---

## How it works

1. **Gateway** — every invoice passes auth, a PII scan, and a dedupe check before anything else happens.
2. **Router agent** — a cheap LLM call classifies the case (`clean_match`, `price_variance`, `duplicate_invoice`, `missing_po`, `tax_mismatch`, `needs_human_triage`) with a confidence score.
3. **Reconciliation planner** — checks a **deterministic rule** first (e.g. rounding variance under $50 auto-resolves with zero LLM calls); only genuinely ambiguous cases fall through to full **agentic reasoning**, which retrieves the real PO from Postgres and the relevant contract clause via RAG over a pgvector store.
4. **Policy & guardrails gate** — before any external action (vendor email, ERP write), a single checkpoint verifies it's within policy (e.g. dollar-amount thresholds). Anything that fails routes to human triage instead of proceeding.
5. **Vendor query agent** — sends the discrepancy query and suspends in a durable, queue-backed wait state that survives process restarts, resuming automatically when the vendor replies.
6. **Human triage / manual resolve** — a case blocked by policy can be resolved directly by a human entering a corrected total, moving it into the approval path — the human's number overrides the system's own calculation.
7. **Human approval** — nothing posts to the ERP without an explicit approve click. Idempotency keys prevent double-posting on retries.
8. **Status agent** — a read-only endpoint answers "what's the status of invoice X" from shared case state at any time, independent of the pipeline.
9. **LLM Ops loop** — every agent run is traced (Langfuse). An eval suite scores classification accuracy against a golden dataset; a deliberately-introduced prompt regression was caught by this suite (accuracy dropped from 2/2 to 0/2), diagnosed, fixed, and re-verified — proving the loop catches real regressions, not just measuring a static score.

---

## Architecture

```
Gateway → Router Agent → Reconciliation Planner → Policy & Guardrails Gate
                                                          │
                              ┌───────────────────────────┴──────────────┐
                              ▼                                          ▼
                    Vendor Query Agent (async)                  Needs Human Triage
                              │                                          │
                              ▼                                          ▼
                      Human Approval  ◄─────────────────────  Manual Resolve
                              │
                              ▼
                      Posted & Closed

Status Agent — reads shared case state independently, at any point above.

LLM Ops Loop (continuous, offline) — Trace → Eval & Observe → Diagnose → Gate → Release
    every router/planner run is traced; eval failures are diagnosed and gated
    before a fixed prompt is considered released.
```

---

## Tech stack

| Layer | Choice |
|---|---|
| API | FastAPI |
| Database | PostgreSQL + pgvector |
| Queue | Redis |
| LLM | OpenAI (`gpt-4o-mini` for routing/classification) |
| Tracing | Langfuse |
| Frontend | Flask + vanilla JS (HITL review dashboard) |
| ORM | SQLAlchemy |
| Containerization | Docker / Docker Compose |
| Deployment | Render |

---

## Project structure

```
ap-invoice-agent/
├── app/
│   ├── main.py                        # FastAPI app: all API routes
│   ├── gateway/
│   │   ├── dedupe.py                  # duplicate invoice detection
│   │   └── pii_scanner.py             # basic PII flagging
│   ├── harness/
│   │   ├── db.py                      # SQLAlchemy engine/session
│   │   ├── async_wait_loop.py         # background worker, consumes vendor_reply_queue
│   │   └── resolve_case.py            # shared resolution logic (used by worker and sync fallback)
│   ├── agents/
│   │   └── router_agent.py            # LLM classification call, traced via Langfuse
│   ├── deterministic_rules/
│   │   └── rounding_variance.py       # zero-LLM fast path for small variances
│   ├── policy_guardrails/
│   │   └── policy_gate.py             # single checkpoint for all external actions
│   ├── tools/
│   │   ├── claims_db_tool.py          # PO retrieval
│   │   └── vector_db_tool.py          # embeddings + RAG over contract clauses
│   └── schemas/
│       ├── case_state.py              # CaseState model (the pipeline's source of truth)
│       ├── purchase_order.py
│       └── contract_clause.py
│
├── evals/
│   └── golden_datasets/
│       └── phase2_invoices.json
│
├── infra/
│   ├── init_db.py                     # creates all tables
│   ├── seed_data.py                   # seeds a test PO + contract clause
│   ├── check_timeouts.py              # escalates cases with no vendor reply
│   ├── load_test.py                   # measures p50/p95/max latency
│   ├── consolidate_memory.py          # episodic → semantic memory demo
│   └── demo_scenario.py               # scripted end-to-end demo run
│
├── ui/
│   ├── app.py                         # Flask proxy + server
│   ├── templates/
│   │   ├── base.html
│   │   └── index.html                 # the HITL review dashboard
│   └── static/
│       └── style.css
│
├── docker-compose.yml                 # local Postgres (pgvector) + Redis
├── requirements.txt
└── .env.example
```

---

## Getting started

### Prerequisites
- Python 3.11+
- Docker + Docker Compose
- An OpenAI API key

### Setup

```bash
git clone <your-repo-url> ap-invoice-agent
cd ap-invoice-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # fill in DATABASE_URL, REDIS_URL, OPENAI_API_KEY

docker compose up -d
docker exec -it $(docker compose ps -q postgres) psql -U ap_agent -d ap_agent -c "CREATE EXTENSION IF NOT EXISTS vector;"

python -m infra.init_db
python -m infra.seed_data
```

### Run it

```bash
# terminal 1 — API
uvicorn app.main:app --reload --port 8000

# terminal 2 — background worker
python -m app.harness.async_wait_loop

# terminal 3 — UI
python ui/app.py
```

Open `http://localhost:5000` for the review dashboard, or hit the API directly at `http://localhost:8000`.

---

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | Postgres connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `OPENAI_API_KEY` | Yes | Used by the router agent |
| `ROUTER_MODEL` | No | Defaults to `gpt-4o-mini` |
| `POLICY_APPROVAL_THRESHOLD_USD` | No | Defaults to `1000` — amounts above this require human triage before vendor contact |
| `VENDOR_REPLY_TIMEOUT_DAYS` | No | Used by `infra/check_timeouts.py` |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` | No | Enables tracing |
| `API_BASE` | UI only | Where the Flask UI finds the FastAPI backend |

---

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/invoices` | Submit an invoice; runs the full gateway → router → planner → policy gate pipeline |
| `GET` | `/cases` | List recent cases |
| `GET` | `/cases/{case_id}` | Full detail for one case |
| `GET` | `/status/{invoice_id}` | Status agent — independent read by invoice ID |
| `POST` | `/cases/{case_id}/approve` | Human approval — posts and closes a `pending_approval` case |
| `POST` | `/cases/{case_id}/reject` | Rejects a case |
| `POST` | `/cases/{case_id}/manual-resolve` | Human enters a corrected total for a `needs_human_triage` case, moving it to `pending_approval` |
| `POST` | `/simulate-vendor-reply/{case_id}` | Testing endpoint — simulates a vendor confirming a discrepancy |

Example:
```bash
curl -X POST http://localhost:8000/invoices -H "Content-Type: application/json" \
  -d '{"invoice_id": "INV-001", "vendor": "Meridian Office Supplies", "total": 9100.00,
       "po_number": "PO-40921", "sku": "DSK-220", "unit_price": 310.00, "qty": 20}'
```

---

## The UI

A dark-mode HITL review dashboard: live stat cards (cases today, pending approval, auto-resolved %), a case queue color-coded by status, and a detail panel showing the case's full reasoning trail with context-appropriate actions — **Approve/Reject** for cases awaiting a decision, **Resolve manually** for cases blocked by the policy gate.

---

## Testing

Sample payloads covering every branch of the pipeline:

```json
// Clean match — deterministic, zero LLM calls
{"invoice_id": "T1", "vendor": "Meridian Office Supplies", "total": 5900.00, "po_number": "PO-40921", "sku": "DSK-220", "unit_price": 295.00, "qty": 20}

// Price variance, within policy threshold — reaches the vendor queue
{"invoice_id": "T2", "vendor": "Meridian Office Supplies", "total": 900.00, "po_number": "PO-40921", "sku": "DSK-220", "unit_price": 45.00, "qty": 20}

// Price variance, over policy threshold — blocked at the gate, needs human triage
{"invoice_id": "T3", "vendor": "Meridian Office Supplies", "total": 9100.00, "po_number": "PO-40921", "sku": "DSK-220", "unit_price": 310.00, "qty": 20}

// Missing PO
{"invoice_id": "T4", "vendor": "Meridian Office Supplies", "total": 750.00}
```

Load test:
```bash
python -m infra.load_test
```
See [Performance](#performance) for full measured results.

Durability test (proves the async loop survives a crash):
1. Submit an invoice, confirm it reaches `routed`.
2. Kill the worker process mid-wait.
3. Restart it.
4. Simulate the vendor reply.
5. Confirm the case still resolves correctly — state lived in Postgres, not the worker's memory.

---

## The LLM Ops loop

Every router agent call is traced via Langfuse (`@observe`). The eval suite (`evals/golden_datasets/phase2_invoices.json`) was used to catch a **deliberately introduced regression**: a forced-override instruction dropped accuracy from `2/2` to `0/2`. The diagnosis was immediate (the override ignored case-specific evidence entirely), the prompt was reverted, and the fix was verified by re-running the eval before being considered "released" — a genuine trigger → detect → diagnose → gate → release cycle, not a simulated one.

---

## Deployment

coming soon !!

---

## What's built vs. what's a known simplification

Being direct about this matters more than pretending everything is production-perfect:

- **PII scanning** is a basic regex stub, not a production-grade classifier.
- **Policy gate** checks a single dollar threshold; a real system would check RBAC/capability tokens against an actual policy document via RAG.
- **Memory consolidation** (episodic → semantic) is demonstrated as a standalone script, not a scheduled background job.
- **LLM Ops diagnose/gate/release** were proven as a real, manually-executed cycle (with actual before/after eval scores) rather than fully automated standalone modules — the loop is real, the automation around it is partial.
- **Router latency** (up to ~30s observed on outliers) is the main obstacle to a sub-2s p95 target in a production deployment; caching or a faster model would be the next step.

---

## Roadmap / build phases

- [x] Phase 0 — Foundation, gateway (dedupe + PII)
- [x] Phase 1 — Router agent + deterministic path
- [x] Phase 2 — Agentic planner with real PO retrieval + RAG
- [x] Phase 3 — Policy & guardrails gate, status agent
- [x] Phase 4 — Async vendor loop, proven durable across worker restarts
- [x] Phase 5 — LLM Ops loop, proven with a real caught-and-fixed regression
- [x] Phase 6 — Load testing, HITL dashboard, manual-resolve path
- [ ] Full automation of diagnose/gate/release as standalone modules
- [ ] Production-grade PII/RBAC
- [ ] Scheduled memory consolidation

---

## License

MIT (or your preference).
