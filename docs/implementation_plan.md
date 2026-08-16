# Enterprise AI Mesh — Implementation Plan

## Milestone 1 — Make the backend real

### Tasks
- Add database configuration.
- Add PostgreSQL connection.
- Add migrations.
- Implement order/inventory/supplier repositories.
- Replace mock API responses with repository reads.
- Add integration tests.

### Exit criteria
Creating an order through the API changes persistent state and the frontend can retrieve it after restart.

## Milestone 2 — Canonical workflow state

Create a versioned `WorkflowState` with:
- workflow ID
- order details
- inventory result
- procurement candidates
- procurement decision
- finance decision
- logistics plan
- exception list
- evidence
- audit references
- timestamps

### Exit criteria
A serialized state can survive a workflow step and be replayed.

## Milestone 3 — Deterministic domain services

Implement:
- stock shortage calculation
- supplier scoring
- budget validation
- route/SLA feasibility
- exception classification

### Exit criteria
Unit tests cover normal flow and all three required exception types.

## Milestone 4 — LangGraph

Implement:
- StateGraph
- Supervisor node
- Inventory node
- Procurement node
- Finance node
- Logistics node
- conditional transitions
- retries/timeouts
- terminal states

### Exit criteria
A real graph executes all necessary nodes without calling frontend simulation logic.

## Milestone 5 — Agent intelligence

Add an LLM only where it adds value:
- supplier negotiation rationale
- ambiguous exception interpretation
- evidence summarization
- decision explanation

All LLM decisions must call deterministic tools for facts.

## Milestone 6 — RAG and graph

### pgvector
Index:
- policies
- supplier terms
- product documents
- historical negotiations
- logistics SLAs

### Neo4j
Connect:
Customer → Order → Product → Supplier → Warehouse

And:
Agent → Decision → Approval → AuditEvent

## Milestone 7 — Blockchain

- Compile/deploy contract.
- Record contract address and chain ID.
- Add backend signing configuration.
- Submit only key audit checkpoints.
- Store transaction receipts.
- Verify transaction hashes.

## Milestone 8 — Frontend integration

Replace local `apiServices` with HTTP services.

Keep the current UI components intact as much as possible.

Add:
- loading states
- error states
- reconnect logic
- real activity stream
- API-driven audit trail

## Milestone 9 — Event streaming

Choose one broker: Kafka or NATS.

Do not implement both initially.

Publish workflow events and consume them for real-time UI updates.

## Milestone 10 — Security

Implement:
- JWT authentication
- RBAC
- service-to-service identity
- least privilege
- audit access controls
- secret management

## Milestone 11 — Benchmarking

Run repeated trials with identical synthetic orders.

Measure:
- end-to-end latency
- cost
- exception recovery rate
- recovery time
- explainability score
- failure rate
- tool/LLM call count

## Milestone 12 — Academic hardening

Produce:
- architecture diagram
- methodology
- baseline definition
- experiment protocol
- results
- limitations
- reproducibility instructions
