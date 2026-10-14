# Enterprise AI Mesh

### A Hybrid Multi-Agent System for Order Fulfilment with Blockchain-Audited Coordination

**Enterprise AI Mesh** is a major academic project demonstrating autonomous multi-agent coordination, decision intelligence, supply chain exception recovery, and blockchain audit logging.

---

## Monorepo Architecture Overview

```text
EnterpriseAI/
├── frontend/             # React + TypeScript + Tailwind Command Center UI
├── backend/              # FastAPI REST & WebSocket APIs (Phase 2)
├── agents/               # LangGraph Multi-Agent Orchestration (Phase 3)
├── services/             # Background & Event Services (NATS/Kafka) (Phase 4)
├── contracts/            # Solidity Smart Contracts (Polygon Testnet) (Phase 5)
├── database/             # PostgreSQL / pgvector / Neo4j Schemas & Migrations (Phase 6)
├── infra/                # Docker Compose & K8s Configuration
├── docs/                 # System Architecture & Documentation
└── README.md
```

---

## Current status (honest)

- **Frontend**: interactive command-center prototype with **simulated** data. It does not call the backend.
- **Backend API**: FastAPI starter; endpoints return **hardcoded** JSON.
- **Phase 1 (data/schema)**: workbook validation, PostgreSQL migrations, and seed scripts live under `backend/data` and `backend/db`. See `PHASE_1_DATA_AUDIT.md` and `backend/README.md`.
- Blockchain, Neo4j, LangGraph, and the 300-second scheduler are **not** implemented.

## Frontend prototype (simulated command center)

The frontend prototype is fully operational and structured as an **Enterprise AI Operations Command Center**.

### Key Features Implemented:
1. **Interactive Live Agent Mesh**: Visual node topology connecting Supervisor, Inventory, Procurement, Finance, and Logistics Agents with real-time status pulses and animated communication channels.
2. **Deterministic Simulation Engine**: Step-by-step order fulfillment runner for Order **ORD-1042** (Industrial Water Pump WP-800).
3. **11 Major Command Screens**:
   - **Overview**: System metrics, live mesh, active order runner, concise agent decision rationale, and live activity stream.
   - **Orders**: Full order registry & detail inspection drawer.
   - **Agent Mesh**: Agent health, workload %, latency monitoring.
   - **Inventory**: Warehouse stock tracking & shortage reorder signal alerts.
   - **Procurement**: Live supplier comparison matrix (3 suppliers) & multi-agent negotiation timeline.
   - **Finance**: Budget reserve validation & expenditure sanctioning.
   - **Logistics**: Corridor feasibility, distance & carrier SLA selection.
   - **Knowledge Graph**: Interactive entity node explorer prepared for Neo4j Cypher queries.
   - **Audit Trail**: Immutable block ledger with transaction hashes (`0x7f83...a91c`).
   - **Exceptions**: Resilience scenario runner supporting 4 exception scenarios (*Supplier Unavailable*, *Budget Breach*, *Delivery Delay*, *Multi-Exception*).
   - **Benchmarks**: Performance metrics comparing Traditional Pipeline vs Enterprise AI Mesh.

---

## How to Run the Frontend Locally

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (if not already installed)
npm install

# Start Vite Development Server
npm run dev

# Build production bundle
npm run build
```

---

## Future API Integration Boundary

Frontend components consume state via typed API services in `frontend/src/services/apiServices.ts` and `frontend/src/state/DemoContext.tsx`. These services can be connected directly to the FastAPI backend endpoints in Phase 2 without modifying frontend visual components.