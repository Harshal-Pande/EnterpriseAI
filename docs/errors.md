# Enterprise AI Mesh — Errors, Gaps, and Technical Debt

This file records issues found by comparing the current repository with the project synopsis and intended architecture.

## Critical gaps

### E001 — Frontend is not connected to the backend
**Severity:** High

`frontend/src/services/apiServices.ts` returns local constants from `initialDemoData.ts`. The UI therefore does not depend on FastAPI for orders, agents, suppliers, inventory, audit, graph, or benchmark data.

**Impact:** The system currently demonstrates the final UX but not a real full-stack execution path.

**Fix:** Introduce an HTTP client layer with environment-configured API base URL, typed DTOs, error handling, loading states, and fallback/demo mode only when explicitly enabled.

---

### E002 — LangGraph is not actually running
**Severity:** Critical

The backend requirements comment out LangGraph, and `WorkflowGraph.run_workflow()` explicitly simulates execution. It calls Supervisor and Inventory but does not execute a compiled `StateGraph` or the full five-agent workflow.

**Impact:** The central multi-agent claim is currently a prototype simulation.

**Fix:** Define a typed shared state, create nodes for all five agents, add conditional routing, compile the graph, and persist execution events.

---

### E003 — Database is not active
**Severity:** Critical

PostgreSQL/pgvector dependencies are commented in `requirements.txt`. The schema exists only as notes.

**Impact:** Business state is not durable and RAG cannot be backed by live operational data.

**Fix:** Add SQLAlchemy/asyncpg or another deliberate persistence layer, migrations, connection lifecycle, repositories, and integration tests.

---

### E004 — Blockchain audit is simulated in the frontend
**Severity:** Critical

The frontend creates synthetic block numbers and random-looking transaction hashes. The Solidity contract is not deployed.

**Impact:** Audit UI can be mistaken for real blockchain evidence.

**Fix:** Label demo hashes as simulated until deployment. After deployment, have the backend submit signed transactions and persist the real transaction hash, block number, contract address, and network.

---

### E005 — Security requirements are not integrated
**Severity:** High

The synopsis specifies JWT authentication and RBAC. The inspected starter backend does not show integrated authentication/authorization middleware.

**Fix:** Define roles, scopes, service identity, JWT verification, protected routes, and audit rules before exposing real business actions.

## Architecture inconsistencies

### E006 — Root directory structure differs from architecture documents
The README and architecture documentation describe root-level `agents/`, `services/`, `database/`, `infra/`, and `contracts/`, while the current repository instead has `backend/`, `blockchain/`, `frontend/`, `knowledge-graph/`, and `docs/`.

**Fix:** Either update documentation to match the actual tree or intentionally create the missing directories as integration work begins.

### E007 — React version documentation mismatch
`docs/architecture.md` says React 18, while `frontend/package.json` currently declares React 19.

**Fix:** Treat `package.json` as the implementation source of truth and update architecture docs.

### E008 — Polygon network naming needs normalization
The roadmap references Polygon Mumbai/Testnet while the synopsis says Polygon testnet. The final documentation should name the exact network selected for deployment and record its chain ID.

### E009 — MCP is a stated technology but no MCP implementation is visible
The synopsis names Anthropic MCP for tool/data access, but the inspected repository does not show an MCP server/tool implementation.

**Fix:** Define MCP only after the tool boundary is clear. Do not add MCP merely as a label.

## Functional issues

### E010 — Starter agent outputs are placeholders
The starter agents return hardcoded results such as `SUPP-001`, `estimated_cost: 5000`, or a fixed route ID.

**Fix:** Replace each with deterministic domain logic first; add LLM reasoning only where reasoning is actually useful.

### E011 — Workflow state is too small for a production-quality execution
The current state contains workflow/order IDs, current agent, status, inventory status, supplier, cost, finance status, route ID, and audit trail.

**Fix:** Add structured order details, exception state, decisions, evidence references, tool calls, timestamps, confidence, approval status, retry metadata, and correlation IDs.

### E012 — No durable event bus
The synopsis proposes Kafka or NATS and Node.js consumers, but no active event bus integration is visible.

**Fix:** First establish a direct synchronous end-to-end path. Add an event bus after the state contract and event schema are stable.

## Demo-data quality issues

### E013 — Benchmark values are demo values
The benchmark service returns fixed values. They must not be cited as experimentally measured results until a benchmark harness produces them.

### E014 — Audit values are demo values
The frontend initial audit records contain hashes and block numbers that look realistic. They are demo data.

### E015 — Knowledge graph sample data is incomplete relative to the final five-agent model
The sample Cypher creates Supervisor, Inventory, and Procurement agents, while the final system also requires Finance and Logistics.

**Fix:** Extend seed data to represent all five agents and their relevant decision relationships.

### E016 — Sample identifiers are inconsistent
The graph sample uses `WP-800` as an order ID in one sample record, while the frontend treats WP-800 as the product model and `ORD-1042` as the order ID.

**Fix:** Normalize entity identifiers before database integration.

## UI debt already acknowledged by the repository

- Activity stream should have contained internal scrolling.
- Benchmark page needs layout/orientation redesign.
- Knowledge graph visualization needs major improvement.

## Error-handling policy

Every integration should return:
- correlation/workflow ID
- machine-readable error code
- human-readable message
- retryability
- source component
- timestamp
- relevant entity ID

Do not silently convert integration failures into successful demo values.
