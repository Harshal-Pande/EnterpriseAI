# Architectural & Technical Decision Records

This log documents every architectural, database, orchestration, and API decision made during the Enterprise AI Mesh backend overhaul, adhering to section 2.4 of the Master Prompt.

---

## Decision D-01: Canonical Orchestration Pipeline
* **Date:** 2026-10-15 (Phase P0)
* **Context:** The codebase contained two orchestration implementations: `app/orchestration/governed.py` (10-phase pipeline) and `app/orchestration/graph.py` (LangGraph experiment).
* **Options Evaluated:**
  1. *LangGraph (`app/orchestration/graph.py`):* Experimental graph traversal; not wired into FastAPI routes.
  2. *Governed Orchestrator (`app/orchestration/governed.py`):* Production-tested 10-phase pipeline directly called by `app/api/orchestration.py`, with full Pydantic contracts and database persistence.
* **Choice:** Option 2 (`GovernedOrchestrator` in `app/orchestration/governed.py`).
* **Reason:** Directly fulfills the requirements of the redesigned frontend Case File stepper, has 100% test coverage, and avoids divergent execution paths.
* **Cost of being wrong:** Low. If LangGraph is ever needed, it can be re-introduced as a pluggable adapter.
* **Rollback:** Retain `app/orchestration/graph.py` with `@deprecated` banner.

---

## Decision D-02: API Route Prefix Strategy (v1 vs Root)
* **Date:** 2026-10-15 (Phase P0)
* **Context:** Frontend documentation mentioned `/api/v1/...` while actual frontend code calls `/api/...`.
* **Options Evaluated:**
  1. *Change frontend to `/api/v1`:* Touches frontend code which is currently frozen.
  2. *Mount routers under both `/api` and `/api/v1`:* Mounts existing routers under both prefixes in `app/main.py` without code duplication.
* **Choice:** Option 2.
* **Reason:** Satisfies both the real frontend implementation and any external documentation or clients expecting `/api/v1`. Zero frontend touch required.
* **Cost of being wrong:** Zero.
* **Rollback:** Remove prefix mount in `app/main.py`.

---

## Decision D-03: Task Queue Architecture for 1,000-Task Backlog
* **Date:** 2026-10-15 (Phase P0)
* **Context:** Need to process a single task on demand and a preloaded backlog of ~1,000 tasks durably, concurrently, resumably, and observably.
* **Options Evaluated:**
  1. *In-process asyncio.Queue:* Fast, but loses all state on process restart or kill. Fails chaos tests.
  2. *External Broker (Redis / Celery / RabbitMQ):* Requires running Redis daemon, adding new operational dependencies on Windows dev machine.
  3. *PostgreSQL-backed queue (`SELECT ... FOR UPDATE SKIP LOCKED`):* Uses existing PostgreSQL database, provides strict ACID transactions combining task state and audit logging, natural persistence across restarts, exactly-once lease semantics.
* **Choice:** Option 3 (PostgreSQL-backed queue using `SKIP LOCKED`).
* **Reason:** 1,000 tasks is a moderate volume easily handled by PostgreSQL; provides transactional coupling with audit events and zero external infrastructure burden.
* **Cost of being wrong:** Negligible for 1,000 tasks.
* **Rollback:** Abstract queue interface behind `TaskQueue` base class.

---

## Decision D-04: Knowledge Graph Storage & Query Strategy
* **Date:** 2026-10-15 (Phase P0)
* **Context:** Docker daemon is currently inactive on the developer machine. Knowledge graph must function reliably.
* **Options Evaluated:**
  1. *Force Neo4j / Docker requirement:* Halts local development if user cannot start Docker daemon immediately.
  2. *RelationalGraphEngine with dual-backend abstraction:* Serve graph queries, blast radius, and disruption impact via optimized PostgreSQL recursive queries / BFS, with idempotent sync to Neo4j if/when active (Gate G4).
* **Choice:** Option 2.
* **Reason:** Guarantees 100% operational functionality in development while honoring honesty rules (labelled as `relational_fallback` until Neo4j answers live Cypher query).
* **Cost of being wrong:** None; Neo4j sync code is preserved.
* **Rollback:** Flip `GRAPH_BACKEND=neo4j` when Docker is running.
