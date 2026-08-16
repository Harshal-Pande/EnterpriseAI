# Enterprise AI Mesh — Handoff

## Current state

The frontend prototype is the project's strongest implemented subsystem. Backend and infrastructure pieces are intentionally starter-level.

## Before coding

Read, in order:
1. `memory.md`
2. `errors.md`
3. `progress.md`
4. `PROJECT_CONTEXT_EXTENDED.md`
5. `implementation_plan.md`

## First coding task

Build a real PostgreSQL-backed order path without changing the frontend visual components.

### Deliverable
`POST /api/v1/orders` → persist order → start workflow → `GET /api/v1/workflows/{workflow_id}` returns real state.

## Second coding task

Implement deterministic domain services for:
- inventory shortage
- supplier scoring
- budget validation
- logistics feasibility

## Third coding task

Replace `WorkflowGraph` simulation with real LangGraph execution.

## Fourth coding task

Connect frontend API services to FastAPI.

## Fifth coding task

Integrate Neo4j and pgvector.

## Sixth coding task

Deploy the audit contract and replace simulated transaction hashes.

## Seventh coding task

Add WebSockets/event streaming.

## Eighth coding task

Implement benchmark harness and compare against deterministic baseline.

## Final verification checklist

- [ ] No fake audit hashes presented as real.
- [ ] No fixed benchmark values presented as measured.
- [ ] No mock API responses remain in integrated mode.
- [ ] All five agents execute through a real workflow.
- [ ] Exceptions are testable.
- [ ] PostgreSQL is active.
- [ ] Neo4j is queried.
- [ ] RAG is functional.
- [ ] Blockchain transaction is verifiable.
- [ ] JWT/RBAC is enforced.
- [ ] WebSocket activity is real.
- [ ] Benchmark results are reproducible.
- [ ] Documentation matches the actual repository tree.
