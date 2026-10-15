# Enterprise AI Supply Chain Control Room

### A Hybrid Multi-Agent System for Order Fulfilment with Blockchain-Audited Coordination

**Enterprise AI Mesh** is a resilient supply chain control room demonstrating autonomous multi-agent coordination, decision intelligence, supply chain exception recovery, multi-key LLM failover with OpenRouter routing, and blockchain audit verification.

---

## 1. Project Overview & Objectives

The Enterprise AI Supply Chain Control Room automates exception handling in industrial order fulfillment while maintaining deterministic governance, safety constraints, human-in-the-loop approvals, and immutable auditability:

1. **Multi-Agent Coordination**: Specialist agents (Inventory, Procurement, Finance, Logistics, and Supervisor) collaborate to analyze supply chain disruptions and propose coordinated recovery actions.
2. **Deterministic Governance & Safety Gates**: LLMs propose recommendations, but application code enforces safety holds, quality constraints, and financial approval thresholds.
3. **Multi-Key LLM Fallback & OpenRouter Routing**: Up to seven Gemini API keys in deterministic agent-specific cyclic order, with automated failover on rate limits (429), timeouts, and transient errors, backed by OpenRouter as a secondary provider.
4. **Real-Time WebSocket Event Stream**: Secure, single-use ticket authenticated WebSocket client streaming orchestration steps and operational alerts.
5. **Knowledge Graph Intelligence**: Downstream multi-hop disruption impact analysis and alternative supplier ranking powered by a PostgreSQL-backed relational graph engine (`RelationalGraphEngine`) with dual-engine Neo4j support.
6. **Cryptographic & On-Chain Auditability**: Canonical RFC 8785 SHA-256 payload digests anchored to an immutable smart contract on Ethereum Sepolia.

---

## 2. Technology Stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2, Uvicorn, Psycopg2, HTTPX, Web3.py.
- **Frontend**: React 19, TypeScript, Vite, TailwindCSS, Lucide Icons, Canvas API.
- **Database**: PostgreSQL 13+ (Domain models, runtime instances, and audit logs).
- **Knowledge Graph**: Dual-Engine architecture — `RelationalGraphEngine` (active PostgreSQL domain graph) + `Neo4j` (optional Cypher graph).
- **Blockchain**: Ethereum Sepolia Testnet (EVM contract `EnterpriseAudit.sol`, Chain ID `11155111`).
- **AI Mesh Providers**: Google Gemini (`gemini-3.8-flash`) via OpenAI-compatible endpoint, OpenRouter (`google/gemini-3.8-flash` fallback), and deterministic offline `SimulationProvider`.

---

## 3. Monorepo Repository Structure & Entry Points

```text
EnterpriseAI/
├── frontend/                   # React 19 + TypeScript + Vite Control Room UI
│   ├── src/
│   │   ├── pages/              # 12 Operational pages (Overview, Orchestration, Graph, Audit, etc.)
│   │   ├── services/           # apiClient.ts, websocketClient.ts
│   │   ├── state/              # DemoContext.tsx (Live vs Simulation mode, state management)
│   │   └── components/         # Control room navigation, badges, modals
│   ├── package.json
│   └── vite.config.ts
├── backend/                    # FastAPI Backend Application
│   ├── app/
│   │   ├── api/                # REST endpoints (orders, inventory, orchestration, graph, audit, ws)
│   │   ├── core/               # llm_provider.py, security.py, events.py
│   │   ├── orchestration/      # governed.py (Multi-agent pipeline & policy gates)
│   │   ├── agents/             # inventory, procurement, finance, logistics, supervisor
│   │   ├── models/             # Pydantic domain, workflow, graph, and blockchain schemas
│   │   └── services/           # graph_service.py, blockchain_service.py, workflow_service.py
│   ├── data/                   # 1,327 validated operational seed rows from project dataset
│   ├── db/                     # PostgreSQL migrations (001_core through 005_blockchain)
│   ├── tests/                  # 300+ automated unit, regression, security, and provider tests
│   ├── requirements.txt
│   └── pytest.ini
├── DEMONSTRATION_RUNBOOK.md    # Evaluator presentation guide and step-by-step demo flow
└── README.md
```

---

## 4. Multi-Key Gemini Pool & OpenRouter Fallback Architecture

To prevent provider rate limits and free-tier quotas from halting operational workflows, the system implements a resilient multi-tier LLM routing pool:

### 4.1 Seven-Key Cyclic Priority Order

Each agent follows a deterministic cyclic sequence across the configured Gemini API keys:

| Agent | Position | Primary Key | Fallback Order |
|---|---|---|---|
| **InventoryAgent** | 1 | `key_1` | 1 → 2 → 3 → 4 → 5 → 6 → 7 |
| **ProcurementAgent** | 2 | `key_2` | 2 → 3 → 4 → 5 → 6 → 7 → 1 |
| **FinanceAgent** | 3 | `key_3` | 3 → 4 → 5 → 6 → 7 → 1 → 2 |
| **LogisticsAgent** | 4 | `key_4` | 4 → 5 → 6 → 7 → 1 → 2 → 3 |
| **SupervisorAgent** | 5 | `key_5` | 5 → 6 → 7 → 1 → 2 → 3 → 4 |
| **QualityAgent** | 6 | `key_6` | 6 → 7 → 1 → 2 → 3 → 4 → 5 |
| **ProductionAgent** | 7 | `key_7` | 7 → 1 → 2 → 3 → 4 → 5 → 6 |

- **Algorithm**: `offset = (agent_position - 1) % len(available_keys)`. Keys cycle deterministically regardless of how many keys are configured (1 to 7).
- **Deduplication**: Duplicate key values are automatically consolidated to a single active entry.
- **Thread Safety**: Request parameters are immutable per-attempt, preventing concurrent agent threads from mutating shared key state.

### 4.2 Intelligent Key Failover & OpenRouter Routing

```mermaid
flowchart TD
    A[Agent Step Triggered] --> B[Select Agent Preferred Gemini Key]
    B --> C[Execute Live Gemini Request]
    C -->|200 OK| D[Validate Structured JSON Contract]
    C -->|429 Rate Limit / 401 Auth / Timeout / 5xx| E{More Gemini Keys in Cycle?}
    E -->|Yes| F[Fail Over to Next Gemini Key]
    F --> C
    E -->|No| G{OpenRouter Enabled & Configured?}
    G -->|Yes| H[Invoke OpenRouter Fallback Endpoint]
    H -->|200 OK| D
    H -->|Fail / Timeout| I[Fail Closed: Halt Workflow & Record Audit]
    G -->|No| I
    D --> J[Policy Engine & Governance Gates]
```

- **OpenRouter Fallback**: Active when `OPENROUTER_ENABLED=true` and all Gemini keys fail or hit rate limits.
- **Fail-Closed Governance**: If all Gemini keys and OpenRouter fail, the orchestrator transitions the workflow to `FAILED` and blocks downstream execution. It **never** silently switches to simulation to fabricate success.

---

## 5. Subsystem Status & Operational Reality

| Subsystem | Active Mode | Reality & Verification Status |
|---|---|---|
| **Relational Database** | `LIVE` | 1,327 seed rows in PostgreSQL; full CRUD on domain entities and workflows. |
| **Multi-Agent Orchestration** | `LIVE` | Governed pipeline executing specialist agents with contract validation. |
| **Gemini LLM Provider** | `LIVE` | `gemini-3.8-flash` via OpenAI-compatible endpoint with multi-key pool. |
| **OpenRouter LLM Fallback** | `LIVE` | `google/gemini-3.8-flash` via OpenRouter endpoint (`sk-or-v1...`). |
| **Policy & Approval Engine** | `LIVE` | Hard limits (> ₹50M approval threshold, self-approval prevention). |
| **WebSocket Event Bus** | `LIVE` | Single-use ticket authentication (`/api/ws/ticket`), heartbeat, auto-reconnect. |
| **Blockchain Audit Anchor** | `LIVE (Read-Only)` | Verified Ethereum Sepolia contract `0xf7aE...` on block `#11915814`. |
| **Knowledge Graph** | `FALLBACK (Active)` | `RelationalGraphEngine` querying PostgreSQL; live Neo4j daemon is offline. |
| **Action Execution** | `SIMULATION` | Safe state transitions in DB; no external ERP or physical freight triggered. |

---

## 6. Environment Configuration

Copy `backend/.env.example` to `backend/.env`. Never commit secrets to version control.

```dotenv
# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/enterprise_ai_dev
TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/enterprise_ai_test

# Role-Based Server Authorization
APP_ENVIRONMENT=development
ADMIN_API_KEY=dev-admin-key
FINANCE_API_KEY=dev-finance-key
SUPPLY_CHAIN_API_KEY=dev-supply-chain-key
OPERATOR_API_KEY=dev-operator-key
VIEWER_API_KEY=dev-viewer-key

# Live LLM Provider (Google Gemini)
LLM_PROVIDER_MODE=LIVE
LLM_MODEL_NAME=gemini-3.8-flash
LLM_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_TIMEOUT_SECONDS=15.0
LLM_MAX_RETRIES=2
LLM_API_KEY=your_gemini_api_key

# 7-Key Gemini Pool (Optional additional keys)
GEMINI_API_KEY_1=your_gemini_key_1
GEMINI_API_KEY_2=your_gemini_key_2
GEMINI_API_KEY_3=your_gemini_key_3

# OpenRouter Fallback Provider
OPENROUTER_ENABLED=true
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_API_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=google/gemini-3.8-flash
OPENROUTER_MAX_TOKENS=1024

# Ethereum Sepolia Blockchain Verification (Read-Only)
SIMULATE_BLOCKCHAIN=true
WEB3_PROVIDER_URI=https://sepolia.infura.io/v3/YOUR_INFURA_KEY
CONTRACT_ADDRESS=0xf7aE6E373be5ad0f9444D230f285e8E620b70b63
CHAIN_ID=11155111
CHAIN_NAME=ethereum-sepolia
```

---

## 7. Exact PowerShell Commands to Run the Project

### Terminal 1: Backend API Server

```powershell
cd D:\MajorProject\EnterpriseAI\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **API Documentation**: `http://127.0.0.1:8000/docs`
- **Health Endpoint**: `http://127.0.0.1:8000/api/health`
- **Active Providers Info**: `http://127.0.0.1:8000/api/orchestration/providers`

### Terminal 2: Frontend Control Room UI

```powershell
cd D:\MajorProject\EnterpriseAI\frontend
npm run dev
```

- **Frontend URL**: `http://localhost:5173`

### Terminal 3: Port Connectivity & Health Verification

```powershell
# Port connectivity checks
Test-NetConnection 127.0.0.1 -Port 8000
Test-NetConnection 127.0.0.1 -Port 5173

# API Health check
curl -s http://127.0.0.1:8000/api/health
```

---

## 8. Automated Testing & Validation Commands

### Backend Regression Tests

```powershell
cd D:\MajorProject\EnterpriseAI\backend

# Run complete multi-key routing & OpenRouter test suite:
python -m pytest tests/test_multikey_routing.py -v

# Run governed orchestration test suite:
python -m pytest tests/test_orchestration.py -v

# Run full backend test suite:
python -m pytest -v
```

### Frontend Validation

```powershell
cd D:\MajorProject\EnterpriseAI\frontend

# Lint checks (oxlint):
npm run lint

# TypeScript verification & production bundle build:
npm run build
```

---

## 9. Troubleshooting & Known Limitations

1. **Google AI Studio Quota Limits**: Free-tier Gemini keys have a quota limit of 20 requests per day per project. If exhausted, the system automatically fails over to subsequent Gemini keys or OpenRouter.
2. **WebSocket Ticket Store**: Ticket exchange uses process-local memory. Multi-replica deployments behind a round-robin load balancer require a shared Redis cache or PostgreSQL ticket table with row-level locking.
3. **Knowledge Graph Engine**: When Docker Desktop or Neo4j is offline, graph features use `RelationalGraphEngine` over PostgreSQL. The UI displays `ENGINE: RELATIONALGRAPHENGINE` transparently.
4. **Seed Row Assertion Mismatch in Tests**: `test_isolation.py` and `test_seed_data.py` assert runtime tables have 0 rows. Real integration runs on `enterprise_ai_test` persist historical audit records and Sepolia anchors, which cause these 3 count checks to report mismatches. Domain seed tables (orders, products, inventory) retain 100% integrity.
5. **Academic/Demo Readiness**: The project is **complete for the defined academic/demo scope** with documented production gaps (shared Redis ticket store, multi-region load balancing, physical ERP connectors).