# Enterprise AI Mesh — Extended Project Context

## 1. Project identity

**Title:** Enterprise AI Mesh — A Hybrid Multi-Agent System for Order Fulfilment with Blockchain-Audited Coordination.

The supplied synopsis identifies this as a 2025–26 Semester VI project, Group 14, under the Department of Computer Science & Engineering at Shri Ramdeobaba College of Engineering & Management.

The synopsis names four student contributors: Harshal Pande, Harshvardhan Singh, OmSingh Bais, and Riddhi Chaturvedi.

## 2. Problem

The project targets enterprise workflows that are normally implemented as deterministic sequences such as Inventory → Finance → Warehouse → Logistics. The synopsis argues that hardcoded workflows become brittle when exceptions cross departmental boundaries, for example supplier unavailability, budget breach, or delivery delay.

The intended solution is a self-hostable multi-agent order-fulfilment system where specialist agents collaborate under a Supervisor and key business decisions are anchored to an immutable audit layer.

## 3. Intended agents

1. Supervisor Agent — orchestration and task routing.
2. Inventory Agent — stock and reorder analysis.
3. Procurement Agent — supplier comparison/negotiation.
4. Finance Agent — budget validation and approval.
5. Logistics Agent — shipment feasibility and scheduling.

## 4. Current repository reality

The GitHub repository currently contains:

- `frontend/` — React/TypeScript/Vite command-center prototype.
- `backend/` — FastAPI starter backend.
- `blockchain/` — Solidity starter contract.
- `knowledge-graph/` — Neo4j schema/sample data.
- `docs/` — architecture documentation.
- Root `PROJECT_CONTEXT.md` and `PROJECT_ROADMAP.md`.

The root README describes additional future-oriented directories such as `agents/`, `services/`, `database/`, and `infra/`, but these are not present as root directories in the currently inspected repository tree.

## 5. Frontend status

The frontend is the most developed part.

It contains pages for:
- Overview
- Orders
- Agent Mesh
- Inventory
- Procurement
- Finance
- Logistics
- Knowledge Graph
- Audit Trail
- Exceptions
- Benchmarks

The frontend has a typed demo context and initial demo dataset. `apiServices.ts` currently resolves local constants rather than making HTTP requests.

## 6. Backend status

FastAPI exposes starter routes for:
- health
- orders
- workflow
- agents
- audit

The backend has agent classes and a workflow-state type, but the LangGraph dependency is commented out and the orchestration graph explicitly describes itself as a simulation.

## 7. Data status

PostgreSQL/pgvector is planned. The backend schema notes describe intended tables for orders, inventory, suppliers, and audit events. No active database connection is established.

Neo4j has constraints and sample Cypher data, but active application-level connection/querying is not established.

## 8. Blockchain status

`EnterpriseAudit.sol` exists and can store audit events by order ID. The contract comments explicitly state it is a starter implementation and has not been deployed to Polygon.

The frontend audit trail is currently simulated. It generates block numbers and hashes in client-side state; these values must not be represented as real on-chain transaction hashes.

## 9. Security status

The synopsis calls for JWT authentication, RBAC, and audit logging. These are not demonstrated as active integrated controls in the inspected backend.

## 10. Benchmark status

The frontend contains benchmark values for latency, processing cost, exception handling, explainability, and recovery time. Because the values are returned by a local demo service, they should be treated as **illustrative/demo metrics**, not measured experimental results.

## 11. Source-of-truth policy

For implementation status, prefer the actual repository code over roadmap language.

For academic scope and final objectives, use the supplied synopsis.

When these disagree, document the disagreement rather than silently choosing one.
