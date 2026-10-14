# Enterprise AI Mesh

### A Hybrid Multi-Agent System for Order Fulfilment with Blockchain-Audited Coordination

**Enterprise AI Mesh** is a resilient supply chain control room demonstrating autonomous multi-agent coordination, decision intelligence, supply chain exception recovery, and blockchain audit logging.

---

## Monorepo Architecture Overview

```text
EnterpriseAI/
├── frontend/             # React 19 + TypeScript + Vite + Tailwind Control Room UI
├── backend/              # FastAPI Backend (PostgreSQL, APIs, Governance, Scheduler)
│   ├── app/              # Application source (API routers, DB connection, models, services)
│   ├── data/             # Operational seed dataset & validation scripts (1,327 source rows)
│   ├── db/               # PostgreSQL schema migrations (001_core, 002_runtime, 003_workflow)
│   └── tests/            # Automated Pytest test suite (unit & integration tests)
├── docker-compose.yml    # Containerized orchestration (PostgreSQL, FastAPI, React)
├── docs/                 # System Architecture, roadmaps, and audit reports
└── README.md
```

---

## Current Architecture & Implementation Status (Phases 0–4)

The repository reflects completed and verified implementations across Phases 0 through 4:

### 1. Implemented & Verified Capabilities
- **PostgreSQL Operational Foundation**: 1,327 validated operational seed rows spanning orders, inventory, products, warehouses, and suppliers.
- **REST APIs**: Full PostgreSQL-backed endpoints for Orders, Inventory, Suppliers, Workflows, Approvals, Policies, Actions, Scheduler, and Governed Orchestration.
- **Governed Multi-Agent Orchestration (Phase 4)**: Typed orchestration pipeline executing Supervisor, Inventory, Procurement, Finance, and Logistics specialists, validating outputs at each step, synthesizing evidence-backed recommendations, and identifying operational conflicts.
- **Dual-Mode LLM Provider Abstraction**: Local deterministic simulation mode and configured live LLM mode with bounded timeouts, retries, masked credential logs, and zero hallucinated successes on failure.
- **Persistent Five-Minute Scenario Engine**: Automated 300-second recurring scenario generation with distributed PostgreSQL lease locking, deterministic slot idempotency (`SCHED-<template>-SLOT-<ts>`), active queue capacity limits, operational data grounding, and watchdog orphan recovery.
- **Deterministic Policy & Approval Engine**: Server-side policy rule evaluation enforcing financial and operational thresholds (> 50M INR single-action approval threshold), human-in-the-loop approvals, and self-approval restrictions.
- **Cryptographic Audit Log**: Canonical SHA-256 payload hashing and tamper-evident event logging in `event_log`.
- **Role-Based Access Control (RBAC)**: Server-side API key authentication distinguishing `ADMIN`, `FINANCE_APPROVER`, `SUPPLY_CHAIN_APPROVER`, `OPERATOR`, and `VIEWER`.
- **Dual-Mode Frontend**: 12-screen React Operations Control Room with seamless switching between interactive Demo Simulation and Live PostgreSQL Backend modes, including dedicated Governed Orchestration view.

### 2. Simulation Boundaries & Design Targets
- **Action Execution**: Physical external action execution (ERP updates, payment dispatch, carrier booking) is executed through a safe simulation adapter unless an external enterprise adapter is explicitly configured.
- **Blockchain Anchoring**: Cryptographic SHA-256 digests and Merkle verification are computed locally. Network submission to public EVM chains (Polygon testnet) is simulated unless external Web3 RPC credentials and gas funds are configured.
- **Benchmarks**: Latency and MTTR metrics displayed in the UI represent illustrative architectural targets and model projections, not independently measured production load-test results.

---

## Running the Application Locally

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL 13+ (or Docker)

### 2. Quickstart via Docker Compose

```bash
# 1. Copy the environment configuration template
cp .env.example .env

# 2. Configure passwords and secure API keys in .env
# (Ensure POSTGRES_PASSWORD, ADMIN_API_KEY, etc. are set)

# 3. Start PostgreSQL, Backend, and Frontend containers
docker compose up --build
```

Access:
- Frontend UI: `http://localhost:5173`
- Backend API Docs: `http://localhost:8000/docs`
- Health Probe: `http://localhost:8000/api/health`

### 3. Local Development Setup

#### Backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure backend/.env with DATABASE_URL and TEST_DATABASE_URL
# Run migrations and load seed data:
python db/migrate.py
python data/load_seed_data.py

# Run FastAPI dev server:
uvicorn app.main:app --reload --port 8000
```

#### Frontend:
```bash
cd frontend
npm install
npm run dev
```

#### Automated Verification:
```bash
# Run backend test suite:
pytest -q

# Validate operational seed dataset (119 checks):
python backend/data/validate_seed_data.py --database-url-var TEST_DATABASE_URL

# Verify frontend build & linting:
cd frontend && npm run build && npm run lint
```