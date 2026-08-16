# Enterprise AI Mesh — Persistent Engineering Memory

This file is intended to be read before making substantial changes.

## Project invariants

1. Do not break the existing frontend while backend integration is added.
2. Never present simulated data as real integration.
3. Keep business validation deterministic where possible.
4. Use LLMs for reasoning, negotiation, summarization, and ambiguous exception handling—not arithmetic that can be implemented as deterministic rules.
5. Every workflow should have a correlation/workflow ID.
6. Every material business decision should be explainable through structured evidence.
7. Blockchain is an audit checkpoint layer, not the primary business database.
8. PostgreSQL is the transactional source of truth.
9. Neo4j is for entity relationships/dependency analysis.
10. pgvector/RAG is for retrieval of relevant business knowledge.
11. The deterministic baseline must implement the same business task as the agent system.
12. Benchmark results must come from repeatable measured runs.

## Canonical business flow

`Order Received → Supervisor → Inventory → Procurement → Finance → Logistics → Completion`

Exceptions can route backward or sideways:

- Supplier unavailable → Procurement selects alternative supplier.
- Budget breach → Procurement revises option or Finance rejects/escalates.
- Delivery delay → Logistics proposes alternate corridor/carrier; Supervisor re-evaluates.
- Multi-exception → Supervisor coordinates multiple agents.

## Canonical demo order

`ORD-1042`

Product:
`Industrial Water Pump (Model WP-800)`

Quantity:
`120`

Budget:
`₹850,000`

Frontend demo data says:
- current stock: 42
- shortage: 78
- Supplier B: ₹6,600/unit, 2-day delivery
- estimated cost: ₹792,000
- Finance headroom: ₹58,000

These are synthetic demonstration values.

## State design memory

The shared state should be append/update safe and serializable. Prefer structured fields over free-form strings.

Recommended top-level state:
- workflow metadata
- order
- inventory result
- procurement candidates
- procurement decision
- finance decision
- logistics plan
- exceptions
- evidence references
- audit events
- agent execution metadata

## Audit memory

Never generate a fake transaction hash after blockchain integration.

The audit record should include:
- event ID
- workflow ID
- order ID
- event type
- actor/agent
- payload hash
- transaction hash
- block number
- contract address
- network/chain ID
- timestamp

## AI memory / RAG memory

Use memory for:
- supplier contracts
- historical negotiations
- procurement policies
- finance approval rules
- logistics SLAs
- product specifications
- prior exception resolutions

Do not store sensitive secrets or arbitrary prompts as long-term memory.

## Development sequence

Database → state contract → deterministic domain services → agent tools → LangGraph → frontend API integration → Neo4j/RAG → blockchain → WebSockets → benchmark harness → security hardening.
