# Enterprise AI Mesh — Architectural Specifications

## Architectural Principles & Layered Responsibilities

### 1. Frontend Layer (`/frontend`)
- **Technology**: React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite.
- **Responsibilities**: Command Center UI, interactive SVG Agent Mesh, Knowledge Graph inspection, live activity feed, order registry, exception simulation runner, audit block explorer, benchmarking views.
- **Contract Boundary**: Consumes data via `frontend/src/services/apiServices.ts` and `frontend/src/state/DemoContext.tsx`.

### 2. Backend API Layer (`/backend`) — Phase 2
- **Technology**: Python 3.11+, FastAPI, Pydantic v2, WebSockets.
- **Responsibilities**: REST API endpoints (`/api/v1/orders`, `/api/v1/agents`, `/api/v1/audit`), authentication, RBAC authorization, WebSocket live event dispatcher.

### 3. Agent Orchestration Layer (`/agents`) — Phase 3
- **Technology**: LangGraph, LangChain, OpenAI / Anthropic / Llama-3 LLM adapters.
- **Agents**:
  - `Supervisor Agent`: Workflow planner & sub-agent token arbiter.
  - `Inventory Agent`: PostgreSQL / pgvector stock & reorder signal generator.
  - `Procurement Agent`: Multi-supplier negotiation scoring matrix.
  - `Finance Agent`: Budget reserve validation & risk governance.
  - `Logistics Agent`: Freight route corridor feasibility & SLA verifier.

### 4. Data Layer (`/database`) — Phase 4
- **PostgreSQL**: Transactional business records & order state tables.
- **pgvector**: Semantic vector index for RAG retrieval.
- **Neo4j**: Graph database for Customer -> Order -> Product -> Supplier -> Warehouse entity relationships.

### 5. Audit & Smart Contract Layer (`/contracts`) — Phase 5
- **Solidity**: Immutable audit logging smart contract (`AuditLedger.sol`).
- **Polygon Network**: Polygon Mumbai / Amoy testnet deployment.
