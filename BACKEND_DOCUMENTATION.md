# Enterprise AI Mesh — Backend Technical Architecture & Reference

> **System Component:** Enterprise AI Mesh Backend  
> **Repository Path:** `backend/`  
> **Role:** Governed Autonomous Multi-Agent Supply Chain Orchestration Engine & API Gateway  
> **Tech Stack:** Python 3.12 · FastAPI 0.110+ · Pydantic v2 · psycopg2-binary · WebSockets · Web3.py · Neo4j Bolt · RFC 8785 Canonical JSON  
> **Architectural Paradigm:** "Agents PROPOSE, Orchestrator GOVERNS, PostgreSQL PERSISTS"  
> **Execution Status:** Production-Ready & Actively Running on `http://127.0.0.1:8000`

---

## 1. Executive Summary & Architectural Context

The **Enterprise AI Mesh Backend** is a high-assurance, enterprise-governed backend designed to operate the digital supply chain control room for a heavy-industry steel manufacturer (**Eastern Alloy & Steel — EAS**). 

Unlike conventional "black-box" generative AI systems that execute actions autonomously without verifiable controls, the Enterprise AI Mesh enforces **strict operational governance**, **deterministic policy validation**, and **immutable cryptographic proof** over every multi-agent interaction.

```
                                  ┌──────────────────────────────────────────────┐
                                  │      Control Room Frontend (React 19)        │
                                  └───────────────┬──────────────────┬───────────┘
                                                  │ REST (Port 8000) │ WS (/api/ws)
                                                  ▼                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       FASTAPI APPLICATION LAYER                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ API Routers: Health · Orders · Inventory · Suppliers · Workflow · Agents · Audit · Graph ·      │  │
│  │              Scheduler · Policies · Approvals · Actions · Governed Orchestration · WebSockets    │  │
│  └───────────────────────────────────┬──────────────────────────────────────────┬───────────────────┘  │
│                                      │                                          │                      │
│                                      ▼                                          ▼                      │
│  ┌──────────────────────────────────────────────────────┐     ┌─────────────────────────────────────┐  │
│  │             GOVERNED ORCHESTRATION ENGINE            │     │       AUTONOMOUS SCHEDULER          │  │
│  │  - Correlation ID Threading & Context Grounding     │     │  - Distributed Lease Lock Engine    │  │
│  │  - Pydantic Output Contracts & Safety Guardrails     │     │  - Anomaly & Disruption Injection   │  │
│  │  - Supervisor Consensus & Evidence Verification     │     │  - Continuous Simulation Runner     │  │
│  └──────────┬───────────────────────────────────────────┘     └──────────────────┬──────────────────┘  │
│             │                                                                    │                     │
│             ▼                                                                    │                     │
│  ┌────────────────────────────────────────────────────────────────────────┐      │                     │
│  │                   SPECIALIST AGENT REASONING MESH                      │      │                     │
│  │   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │      │                     │
│  │   │  Inventory   │ │ Procurement  │ │   Finance    │ │  Logistics   │  │      │                     │
│  │   │  Specialist  │ │  Specialist  │ │  Specialist  │ │  Specialist  │  │      │                     │
│  │   └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘  │      │                     │
│  │          └────────────────┼────────────────┼────────────────┘          │      │                     │
│  │                           ▼                ▼                           │      │                     │
│  │             ┌──────────────────────────────────────────┐               │      │                     │
│  │             │   Supervisor Orchestrator & Synthesizer  │               │      │                     │
│  │             └─────────────────────┬────────────────────┘               │      │                     │
│  └───────────────────────────────────┼────────────────────────────────────┘      │                     │
│                                      │                                           │                     │
│                                      ▼                                           │                     │
│  ┌────────────────────────────────────────────────────────────────────────┐      │                     │
│  │            DETERMINISTIC GOVERNANCE & ACTION LIFECYCLE                 │      │                     │
│  │  - Deterministic Policy Engine (Python Expressions / Budgets / Limits) │      │                     │
│  │  - Human-in-the-Loop (HITL) Gate (Pending/Approved/Rejected Lifecycle) │      │                     │
│  │  - SafeSimulationAdapter & Controlled Action Queue Execution           │      │                     │
│  └───────────────────────────────────┬────────────────────────────────────┘      │                     │
│                                      │                                           │                     │
│                                      ▼                                           │                     │
│  ┌────────────────────────────────────────────────────────────────────────┐      │                     │
│  │                 CRYPTOGRAPHIC PROOF & LEDGER LOGGING                   │      │                     │
│  │  - RFC 8785 Canonical JSON Serialization                               │      │                     │
│  │  - SHA-256 Digest Hashing                                              │      │                     │
│  │  - Ethereum Sepolia Smart Contract Anchoring (Web3.py)                 │      │                     │
│  └───────────────────────────────────┬────────────────────────────────────┘      │                     │
└──────────────────────────────────────┼───────────────────────────────────────────┼─────────────────────┘
                                       │                                           │
                                       ▼                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         PERSISTENCE LAYER                                              │
│  ┌─────────────────────────────────────────────────────┐  ┌─────────────────────────────────────────┐  │
│  │         PostgreSQL Database (Engine & Ledger)       │  │       Neo4j Graph Database (Topology)   │  │
│  │  - 33 Relational & Runtime Tables (001-005 Schemas) │  │  - Multi-Tier Supply Provenance Graph   │  │
│  │  - ACID Transactions & Audit Hash Storage           │  │  - Disruption Blast-Radius Traversal    │  │
│  └─────────────────────────────────────────────────────┘  └─────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure & File Inventory

The backend is strictly modularized across `app/`, `db/`, and `data/` directories:

```
backend/
├── app/
│   ├── agents/                     # Specialist and supervisor reasoning implementations
│   │   ├── __init__.py
│   │   ├── finance.py              # Budget validation, cost analysis, margin checks
│   │   ├── inventory.py            # Warehouse stock checks, reservation logic, shortages
│   │   ├── logistics.py            # Route feasibility, carrier selection, transit delays
│   │   ├── procurement.py          # Supplier discovery, price negotiation, lead-time scores
│   │   └── supervisor.py           # Multi-agent coordination, synthesis, conflict resolution
│   ├── api/                        # FastAPI route handlers (REST & WebSockets)
│   │   ├── __init__.py
│   │   ├── actions.py              # Controlled action proposals & execution engine
│   │   ├── agents.py               # Direct specialist invocation & telemetry queries
│   │   ├── approvals.py            # Human-in-the-loop decision endpoints (approve/reject)
│   │   ├── audit.py                # Audit log queries, SHA-256 verification, Sepolia anchoring
│   │   ├── graph.py                # Knowledge graph querying, topology, and impact simulation
│   │   ├── health.py               # Liveness, readiness, and subsystem connectivity status
│   │   ├── inventory.py            # Stock balances, reorder thresholds, warehouse summaries
│   │   ├── orchestration.py        # Governed pipeline runs, step execution, and diagnostics
│   │   ├── orders.py               # Order ingestion, tracking, status transitions, metrics
│   │   ├── policies.py             # Deterministic business rule inspection & evaluation
│   │   ├── scheduler.py            # Background scenario scheduler inspection & cycle triggers
│   │   ├── suppliers.py            # Supplier performance, contracts, active quotations
│   │   ├── workflow.py             # Workflow state machines and transitions
│   │   └── ws.py                   # Real-time WebSocket event broadcaster & auth tickets
│   ├── contracts/                  # Smart contract ABIs and interface artifacts
│   │   └── enterprise_audit_abi.json # Ethereum Sepolia EnterpriseAudit ABI
│   ├── core/                       # Core engine services, security, LLMs, and events
│   │   ├── __init__.py
│   │   ├── events.py               # Asynchronous in-memory event bus and channel broker
│   │   ├── llm_provider.py         # SimulationProvider & LiveProvider (Gemini/OpenRouter)
│   │   ├── sanitizer.py            # Input sanitization, log scrubbing, credential redaction
│   │   └── security.py             # Role-based access control (RBAC), API key auth, tickets
│   ├── db/                         # Application-level database connection pool
│   │   ├── __init__.py
│   │   └── database.py             # ThreadedConnectionPool management, lifespan hooks
│   ├── models/                     # Strongly-typed Pydantic schemas and contracts
│   │   ├── __init__.py
│   │   ├── action.py               # Action proposal and execution records
│   │   ├── agent_contracts.py      # Structured JSON schema contracts for agent outputs
│   │   ├── agent_run.py            # Agent run tracking, duration, token usage models
│   │   ├── audit.py                # Cryptographic audit record and anchor models
│   │   ├── audit_event.py          # Legacy audit event mappings
│   │   ├── blockchain.py           # Sepolia status, gas usage, transaction receipts
│   │   ├── graph.py                # Graph nodes, edges, and blast-radius responses
│   │   ├── inventory.py            # Inventory balance and lot schemas
│   │   ├── order.py                # Order and order line representations
│   │   ├── policy.py               # Policy evaluation requests and outputs
│   │   ├── supplier.py             # Supplier profile, offer, and risk band schemas
│   │   └── workflow.py             # Workflow state machines and transition payloads
│   ├── orchestration/              # Workflow governance and orchestration engines
│   │   ├── __init__.py
│   │   ├── governed.py             # 10-phase governed multi-agent execution pipeline
│   │   ├── graph.py                # LangGraph state machine workflow definitions
│   │   └── state.py                # State machine typed dictionary interfaces
│   ├── services/                   # Business logic and domain service engines
│   │   ├── __init__.py
│   │   ├── action_service.py       # Controlled action queue management & SafeSimulationAdapter
│   │   ├── agent_run_service.py    # Agent telemetry, latency metrics, output persistence
│   │   ├── approval_service.py     # Approval gate state machine and audit creation
│   │   ├── audit_service.py        # Legacy audit log adapter
│   │   ├── blockchain_service.py   # Web3 Sepolia integration, RFC 8785, digest hashing
│   │   ├── graph_service.py        # Neo4j Cypher executor & RelationalGraphEngine fallback
│   │   ├── policy_service.py       # Deterministic Python expression policy evaluation
│   │   ├── scheduler_service.py    # Background autonomous scheduler & distributed lease locks
│   │   └── workflow_service.py     # Order workflow state transitions and validations
│   └── main.py                     # FastAPI application entrypoint, lifespan, CORS, router mounting
├── data/                           # Data loading, mapping, and validation infrastructure
│   ├── __init__.py
│   ├── column_mappings.py          # 49KB authoritative workbook-to-PostgreSQL mapping specs
│   ├── inspect_workbook.py         # Structural analysis utility for industrial Excel dataset
│   ├── load_seed_data.py           # Idempotent bulk data loader (INSERT ... ON CONFLICT DO NOTHING)
│   ├── run_validation.py           # Zero-database standalone dataset integrity validator
│   ├── validate_seed_data.py       # Database-backed dataset reconciliation script
│   ├── validation_report.json      # Post-load validation results (119 checks, 100% pass)
│   ├── validators.py               # Standalone business rule and constraint validator library
│   ├── workbook_inspection.json    # Complete schema inspection of the 40-sheet dataset
│   └── workbook_validation_report.json # Standalone inspection report
├── db/                             # Migration engine and versioned SQL scripts
│   ├── __init__.py
│   ├── connection.py               # Database URL resolution and psycopg2 connector
│   ├── migrate.py                  # Versioned, checksummed SQL migration runner
│   ├── apply_migrations.py         # Programmatic helper to run migrations
│   └── migrations/                 # Sequential SQL migration files
│       ├── 001_operational_schema.sql         # Core domain master data (22 tables)
│       ├── 002_runtime_schema.sql             # Orchestration & runtime tables (11 tables)
│       ├── 003_workflow_agent_schema.sql      # Agent run performance indexing
│       ├── 004_scheduler_lifecycle_schema.sql # Distributed scheduler lease lock columns
│       └── 005_blockchain_anchoring_schema.sql# Sepolia confirmation & gas metrics
├── tests/                          # Automated pytest test suite
├── Dockerfile                      # Production container image definition
├── pytest.ini                      # Pytest discovery and logging configuration
├── requirements.txt                # Pinned production and test dependencies
├── .env.example                    # Sample environment template (secrets omitted)
└── README.md                       # Backend overview and developer quickstart
```

---

## 3. Execution Scripts & Developer Commands

All backend commands must be run from within the `backend/` directory or repository root:

### 3.1 Running the Backend API Server
```powershell
# From D:\MajorProject\EnterpriseAI\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **API Base:** `http://127.0.0.1:8000`
- **Swagger Documentation:** `http://127.0.0.1:8000/docs`
- **OpenAPI Schema:** `http://127.0.0.1:8000/openapi.json`
- **Health Check:** `http://127.0.0.1:8000/api/health`

### 3.2 Database Migration Engine
The migration runner in `backend/db/migrate.py` is idempotent and maintains a tracking table `_schema_migrations` storing SHA-256 checksums:
```powershell
# Dry run: view pending migrations without applying
python backend/db/migrate.py --dry-run

# Apply all migrations to default DATABASE_URL
python backend/db/migrate.py

# Apply migrations to test database
python backend/db/migrate.py --database-url-var TEST_DATABASE_URL
```

### 3.3 Dataset Validation & Seed Loading
```powershell
# 1. Standalone workbook validation (requires no database, runs 119 rule checks)
python backend/data/run_validation.py

# 2. Inspect Excel workbook structure and generate JSON dump
python backend/data/inspect_workbook.py

# 3. Dry-run seed data loading (verifies conversions without writing to DB)
python backend/data/load_seed_data.py --dry-run

# 4. Perform idempotent seed data load into PostgreSQL
python backend/data/load_seed_data.py

# 5. Reconcile database contents against original workbook rows
python backend/data/validate_seed_data.py
```

### 3.4 Automated Testing
```powershell
# Run the complete backend test suite
pytest backend/tests/ -v

# Run with coverage report
pytest backend/tests/ --cov=app --cov-report=term-missing
```

### 3.5 Docker Deployment
```powershell
# Build backend image
docker build -t enterpriseai-backend:latest ./backend

# Run standalone container with environment variables
docker run -d -p 8000:8000 --env-file backend/.env --name enterpriseai-backend enterpriseai-backend:latest
```

---

## 4. Configuration & Environment Variables

Configurations are loaded by `backend/db/connection.py` from `backend/.env` or root `.env`.

| Environment Variable | Required | Default Value | Purpose |
| :--- | :--- | :--- | :--- |
| **`DATABASE_URL`** | **Yes** | `postgresql://enterprise_ai:enterprise_dev_pass@localhost:5432/enterprise_ai` | Primary PostgreSQL database connection string. |
| **`TEST_DATABASE_URL`** | Optional | `postgresql://enterprise_ai:enterprise_dev_pass@localhost:5432/enterprise_ai_test` | Dedicated connection string for automated test suites. |
| **`APP_ENVIRONMENT`** | No | `development` | Environment mode (`development`, `staging`, `production`). |
| **`ADMIN_API_KEY`** | **Yes (Prod)** | `dev-admin-key` | Master administrative API key for high-privilege operations. |
| **`FINANCE_API_KEY`** | **Yes (Prod)** | `dev-finance-key` | Financial role key for approving budget allocations. |
| **`SUPPLY_CHAIN_API_KEY`**| **Yes (Prod)**| `dev-supply-key` | Operational key for supplier and inventory management. |
| **`OPERATOR_API_KEY`** | **Yes (Prod)** | `dev-operator-key` | Operator key for executing workflows and triggering runs. |
| **`VIEWER_API_KEY`** | No | `dev-viewer-key` | Read-only key allowing telemetry and dashboard inspection. |
| **`CORS_ALLOWED_ORIGINS`**| No | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of allowed frontend web origins. |
| **`SCHEDULER_ENABLED`**| No | `true` | Enables background autonomous scenario injection runner. |
| **`SCHEDULER_INTERVAL_SECONDS`**| No | `300` | Frequency of background scheduler evaluation cycles. |
| **`NEO4J_URI`** | No | `bolt://localhost:7687` | Neo4j Bolt endpoint. Falls back cleanly to relational SQL graph if offline. |
| **`NEO4J_USER`** | No | `neo4j` | Neo4j database user credentials. |
| **`NEO4J_PASSWORD`** | No | `enterprise_dev_pass` | Neo4j database password credentials. |
| **`LLM_PROVIDER_MODE`** | No | `SIMULATION` | `SIMULATION` (deterministic engine) or `LIVE` (multi-key external LLM). |
| **`LLM_MODEL_NAME`** | No | `gemini-2.0-flash` | Target model for live inference calls. |
| **`GEMINI_API_KEY_1..7`**| Conditional | *None* | Multi-key pool supporting up to 7 distinct API keys for agent load balancing. |
| **`OPENROUTER_ENABLED`**| No | `false` | Enables OpenRouter as a multi-model fallback provider. |
| **`OPENROUTER_API_KEY`**| Conditional | *None* | OpenRouter authentication token. |
| **`WEB3_PROVIDER_URI`** | No | `https://rpc.sepolia.org` | Ethereum Sepolia JSON-RPC HTTPS endpoint. |
| **`CONTRACT_ADDRESS`** | No | `0x1c55d00a4421b98744b76a08479e0a29367816bd` | Address of deployed `EnterpriseAudit.sol` on Sepolia. |
| **`BLOCKCHAIN_PRIVATE_KEY`**| Conditional| *None* | 64-character hex private key for transaction signing. |
| **`SIMULATE_BLOCKCHAIN`**| No | `true` | When true, simulates on-chain anchoring without consuming testnet ETH. |

---

## 5. API Router Catalogue

The backend mounts 14 dedicated routers under the `/api` prefix in `app/main.py`:

### 5.1 Health & Subsystem Readiness (`/api/health`)
- **`GET /api/health`**: Returns system liveness, active service name, and version (`200 OK`).
- **`GET /api/health/ready`**: Verifies connectivity across PostgreSQL connection pool, Neo4j graph engine, and blockchain provider.

### 5.2 Orders Engine (`/api/orders`)
- **`GET /api/orders/`**: Paginated list of customer orders with status, priority, and date filtering.
- **`POST /api/orders/`**: Ingest new customer order with line items and validation against `products`.
- **`GET /api/orders/{order_id}`**: Detailed order record including line items, promised dates, and customer details.
- **`GET /api/orders/summary`**: Aggregated count of open, in-progress, completed, and exception orders.
- **`PATCH /api/orders/{order_id}/status`**: Transition order status (`OPEN`, `IN_PROGRESS`, `AT_RISK`, `COMPLETED`, `CANCELLED`).

### 5.3 Inventory Management (`/api/inventory`)
- **`GET /api/inventory/items`**: List multi-warehouse inventory balances, available stock, safety points, and signals.
- **`GET /api/inventory/summary`**: High-level inventory KPI strip (total SKUs, below-reorder count, shortages).
- **`GET /api/inventory/reorder-policies`**: Configured minimum/maximum stock thresholds by SKU and warehouse site.
- **`POST /api/inventory/reserve`**: Create temporary stock reservation for an in-flight order.

### 5.4 Suppliers & Bidding (`/api/suppliers`)
- **`GET /api/suppliers/`**: List qualified suppliers, historical reliability scores, lead times, and risk bands.
- **`GET /api/suppliers/{supplier_id}`**: Individual supplier profile and active contracts.
- **`GET /api/suppliers/offers`**: Real-time quotations for steel slabs, billets, coils, and industrial spares.

### 5.5 Governed Orchestration (`/api/orchestration`)
- **`POST /api/orchestration/execute`**: Executes the 10-phase governed multi-agent pipeline for an order and scenario template.
- **`GET /api/orchestration/{workflow_id}`**: Retrieves complete case file data, execution state, and correlation trace.
- **`GET /api/orchestration/{workflow_id}/agents`**: Step-by-step specialist telemetry, latencies, and evidence links.
- **`GET /api/orchestration/{workflow_id}/governance`**: Deterministic policy decisions and approval gate requirements.
- **`POST /api/orchestration/{workflow_id}/retry`**: Resumes or retries a failed workflow from its last valid checkpoint.
- **`GET /api/orchestration/providers`**: Current provider mode (`SIMULATION` vs `LIVE`) and model operational metadata.

### 5.6 Human-in-the-Loop Approvals (`/api/approvals`)
- **`GET /api/approvals/`**: List active approval requests filtered by status (`PENDING`, `APPROVED`, `REJECTED`).
- **`POST /api/approvals/{approval_id}/decision`**: Human authorization endpoint. Requires role authorization, decision enum, and minimum 5-character reason string.

### 5.7 Controlled Actions (`/api/actions`)
- **`GET /api/actions/`**: Action queue inspection (proposed, approved, executing, succeeded, failed).
- **`POST /api/actions/{action_id}/execute`**: Executes an approved action through `SafeSimulationAdapter`.

### 5.8 Cryptographic Audit & Blockchain (`/api/audit`)
- **`GET /api/audit/events`**: Chronological event ledger records with actor, order, timestamp, and payload hash.
- **`GET /api/audit/blockchain/status`**: On-chain connection status, contract address, chain ID, and network name.
- **`POST /api/audit/anchor`**: Computes RFC 8785 canonical JSON hash and submits anchoring transaction to Sepolia.
- **`POST /api/audit/verify/{event_id}`**: Read-only verification comparing stored digest against recomputed canonical hash.

### 5.9 Knowledge Graph Engine (`/api/graph`)
- **`GET /api/graph`**: Retrieves topological subgraphs (nodes & relationships) filtered by entity type or query string.
- **`GET /api/graph/status`**: Engine backend type (`Neo4j (live)` vs `Relational fallback`), node counts, relationship counts.
- **`POST /api/graph/impact`**: Simulates disruption blast radius and identifies impacted orders up to N hops.
- **`POST /api/graph/sync`**: Synchronizes PostgreSQL master data into Neo4j graph nodes.

### 5.10 Autonomous Scheduler (`/api/scheduler`)
- **`GET /api/scheduler/status`**: Current scheduler lifecycle, lease expiration, run counts, and lock holder.
- **`GET /api/scheduler/templates`**: List of 15 predefined disruption templates (Supplier Unavailable, Budget Breach, etc.).
- **`GET /api/scheduler/scenarios`**: History of injected scenario instances and their resolution statuses.
- **`POST /api/scheduler/trigger`**: Forces immediate evaluation of a scheduled disruption scenario.

### 5.11 Business Policies (`/api/policies`)
- **`GET /api/policies/rules`**: Inspects active deterministic business rules, condition expressions, and failure actions.
- **`POST /api/policies/evaluate`**: Tests an input payload against business rules and returns structured PASS/FAIL verdicts.

### 5.12 Real-Time WebSockets (`/api/ws`)
- **`POST /api/ws/ticket`**: Generates a cryptographically random, single-use, 60-second authentication ticket.
- **`WebSocket /api/ws`**: Secure full-duplex connection. Requires valid ticket handshake. Broadcasts real-time events (`WORKFLOW_TRANSITION`, `AGENT_RUN_COMPLETE`, `POLICY_EVALUATION`, `APPROVAL_REQUESTED`, `ACTION_EXECUTED`).

---

## 6. Core Subsystem Architecture

### 6.1 Multi-Agent Specialist Reasoning Mesh
Specialist agents live in `app/agents/` and inherit from standard reasoning contracts:
- **Supervisor Agent (`supervisor.py`):** Acts as root coordinator. Evaluates initial scenario, assigns tasks to specialists, resolves inter-agent conflicts, and formulates final synthesized recommendations.
- **Inventory Agent (`inventory.py`):** Queries stock balances across warehouses (e.g. Pune Hub, Nagpur DC). Calculates net available stock, identifies shortages, and determines whether procurement is needed.
- **Procurement Agent (`procurement.py`):** Identifies qualified suppliers from `suppliers` and `supplier_offers`. Evaluates quotes based on unit price, reliability rating, and lead-time. Formulates purchase order proposals.
- **Finance Agent (`finance.py`):** Checks proposed costs against departmental budgets (`budgets`). Flags threshold breaches when single actions exceed statutory caps (e.g. ₹10,00,000 threshold).
- **Logistics Agent (`logistics.py`):** Evaluates freight transit corridors (e.g. Pune-Nagpur NH-53). Detects weather delays, assesses carrier SLAs, and proposes rerouting (e.g. switching road hauler to Concor Rail Freight).

### 6.2 Governed Orchestration Engine (`governed.py`)
Every workflow run proceeds through 10 deterministic lifecycle phases:
1. **Correlation Tracking:** Generates a persistent UUID `correlation_id` carried across all downstream database logs.
2. **Operational Grounding:** Queries PostgreSQL to verify baseline order and inventory evidence exists.
3. **Selective Dispatch:** Invokes only relevant specialists (e.g., skips procurement if stock is on hand).
4. **Contract Validation:** Enforces strict Pydantic parsing (`SupervisorOutput`, `InventoryOutput`, etc.). If an LLM returns malformed JSON, execution fails closed.
5. **Supervisor Synthesis:** Formulates unified recommendations and resolves conflicting constraints.
6. **Deterministic Policy Gating:** Evaluates recommended actions against deterministic Python rules in `business_rules`.
7. **Approval Lifecycle:** If an action requires human sign-off, halts execution and creates an `approval_requests` record.
8. **Controlled Action Execution:** Passes approved actions to `SafeSimulationAdapter` to apply changes safely.
9. **Durable Persistence:** Writes all runs, decisions, evaluations, and state changes to PostgreSQL.
10. **Cryptographic Proof:** Emits audit event records hashed via RFC 8785.

### 6.3 LLM Provider Layer (`llm_provider.py`)
Provides transparent execution across two distinct operating modes:
- **SimulationProvider (Default):** Completely deterministic, offline engine that uses rule-based heuristics and template logic to formulate agent responses. Fully functional with zero external API dependencies.
- **LiveProvider:** Pluggable connector supporting Google Gemini (with an automatic multi-key rotating pool across `GEMINI_API_KEY_1..7`) and OpenRouter as an automatic fallback. Adheres to strict timeout boundaries (default: 30s) and redacts sensitive credentials.

### 6.4 Autonomous Scheduler & Distributed Lease Engine (`scheduler_service.py`)
The scheduler runs background cycles evaluating scenario templates:
- **Distributed Leader Lease:** Uses PostgreSQL `scheduler_state` with `lease_expires_at` and `locked_by` to prevent race conditions in multi-worker deployments.
- **Scenario Injection:** Injects synthetic disruption scenarios (`supplier_unavailable`, `budget_breach`, `delivery_delay`, `multi_exception`) to exercise the governed multi-agent mesh.

### 6.5 Cryptographic Ledger & Sepolia Anchoring (`blockchain_service.py`)
Provides mathematical proof of event integrity:
1. **Canonical Serialization:** Standardizes payload formatting via RFC 8785 (Deterministic JSON Canonicalization).
2. **SHA-256 Digesting:** Generates immutable state digests (`0x...`).
3. **Sepolia Smart Contract Anchoring:** The `anchorAuditEvent` function interfaces with `EnterpriseAudit.sol` on Ethereum Sepolia via Web3.py:
   ```solidity
   function recordEvent(string calldata eventId, bytes32 payloadHash) external;
   ```
4. **Tamper Detection:** The read-only `/api/audit/verify/{event_id}` endpoint recalculates the digest from raw database rows and verifies on-chain receipts, flagging any internal database tampering.
