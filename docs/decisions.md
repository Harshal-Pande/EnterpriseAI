# Enterprise AI Mesh — Architecture Decisions

## ADR-001 — Supervisor-based orchestration

**Decision:** Use a Supervisor with specialist agents.

**Reason:** Matches the project synopsis and provides a clear coordination boundary.

## ADR-002 — Hybrid deterministic + agentic architecture

**Decision:** Use deterministic tools for factual business calculations and agents for coordination/reasoning.

**Reason:** Improves reproducibility, safety, explainability, and benchmarking.

## ADR-003 — PostgreSQL as transactional source of truth

**Decision:** Business records belong in PostgreSQL.

**Reason:** Orders, inventory, approvals, and workflow state require durable transactional semantics.

## ADR-004 — Neo4j for relationships

**Decision:** Use Neo4j for product/supplier/customer/warehouse relationships.

**Reason:** The project specifically requires a knowledge graph and dependency analysis.

## ADR-005 — pgvector for RAG

**Decision:** Use pgvector for semantic retrieval over business knowledge.

**Reason:** It keeps retrieval close to transactional infrastructure while supporting the stated RAG requirement.

## ADR-006 — Blockchain as audit checkpoint

**Decision:** Store audit anchors/checkpoints on-chain rather than all application data.

**Reason:** The repository's existing context explicitly adopts this design and it avoids turning blockchain into the primary database.

## ADR-007 — Frontend-first prototype

**Decision:** Preserve the current frontend while integrating the backend.

**Reason:** The existing command center demonstrates the intended UX and is the strongest completed subsystem.

## ADR-008 — One event broker initially

**Decision:** Choose Kafka or NATS, not both, for the first implementation.

**Reason:** The synopsis allows either and running both adds unnecessary integration complexity.

## ADR-009 — Real benchmark harness required

**Decision:** Fixed demo metrics are not research results.

**Reason:** Academic claims need repeatable measured experiments.

## ADR-010 — Explicit simulation labeling

**Decision:** Any synthetic audit hash, simulated workflow, or fixed benchmark must be labeled as simulation/demo data.

**Reason:** Prevents accidental misrepresentation in project presentations.
