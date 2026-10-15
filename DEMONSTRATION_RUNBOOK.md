# ENTERPRISE AI SUPPLY CHAIN CONTROL ROOM — DEMONSTRATION RUNBOOK

**Target Repository:** `D:\MajorProject\EnterpriseAI`  
**Purpose:** Standard Operating Procedure for Live Evaluator Demonstrations  
**Audience:** Presenters, Evaluators, Engineering Leadership  

---

## 1. Prerequisites & Environment Configuration

### 1.1 Host Environment Prerequisites
- **Operating System:** Windows 10/11 or Linux / macOS
- **Python:** 3.11 or 3.12 (with active virtual environment or host Python)
- **Node.js:** v18+ (with `npm` v9+)
- **PostgreSQL Database:** Running locally or accessible over network (default: `localhost:5432`)
- **Web Browser:** Google Chrome, Microsoft Edge, or Mozilla Firefox

### 1.2 Required Environment Variables (Names Only)
The application expects configurations loaded from `backend/.env` or repository root `.env`. Never commit `.env` or display secret values.

| Variable Name | Classification | Expected Format / Purpose |
|---|---|---|
| `DATABASE_URL` | **Required** | PostgreSQL connection URI (`postgresql://...`) |
| `TEST_DATABASE_URL` | **Required for Tests** | Test database connection URI |
| `APP_ENVIRONMENT` | **Required** | `development` (for demo & tests) or `production` |
| `ADMIN_API_KEY` | **Required in Prod** | High-privilege administrative API key |
| `FINANCE_API_KEY` | **Required in Prod** | Financial approver API key |
| `SUPPLY_CHAIN_API_KEY` | **Required in Prod** | Supply chain & logistics approver API key |
| `OPERATOR_API_KEY` | **Required in Prod** | Operational execution API key |
| `VIEWER_API_KEY` | **Required in Prod** | Read-only viewing API key |
| `WEB3_PROVIDER_URI` | **Required for Blockchain** | EVM HTTPS RPC provider endpoint |
| `CONTRACT_ADDRESS` | **Required for Blockchain** | Deployed `EnterpriseAudit.sol` contract address (`0x...`) |
| `BLOCKCHAIN_PRIVATE_KEY` | **Required for Signer** | Signer private key (64-character hex) |
| `CHAIN_ID` | **Optional** | EVM Chain ID (`11155111` for Ethereum Sepolia) |
| `CHAIN_NAME` | **Optional** | Network name (`ethereum-sepolia`) |
| `EXPLORER_TX_URL_PREFIX` | **Optional** | Block explorer URL prefix |
| `VITE_API_BASE_URL` | **Frontend Config** | Backend API base URL (`http://localhost:8000`) |
| `NEO4J_URI` | **Optional** | Bolt URI (`bolt://localhost:7687`) — falls back cleanly to RelationalGraphEngine if offline |
| `LLM_PROVIDER_MODE` | **Optional** | `SIMULATION` (default deterministic engine) or `LIVE` |

---

## 2. Startup Instructions & URLs

### 2.1 Backend Startup
Open a terminal in `D:\MajorProject\EnterpriseAI\backend`:

```powershell
# Windows PowerShell
cd D:\MajorProject\EnterpriseAI\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Backend API Base URL:** `http://127.0.0.1:8000`
- **Swagger Interactive API Docs:** `http://127.0.0.1:8000/docs`
- **OpenAPI JSON Specification:** `http://127.0.0.1:8000/openapi.json`

### 2.2 Frontend Startup
Open a second terminal in `D:\MajorProject\EnterpriseAI\frontend`:

```powershell
# Windows PowerShell
cd D:\MajorProject\EnterpriseAI\frontend
npm run dev
```

- **Frontend Application URL:** `http://localhost:5173` (or port indicated by Vite)

---

## 3. Health Checks & Verification Commands

Before presenting to evaluators, execute these quick terminal checks:

### 3.1 Backend Health Check
```powershell
curl -s http://127.0.0.1:8000/api/health
```
*Expected response:* `{"status":"healthy","service":"Enterprise AI Mesh API"}`

### 3.2 Blockchain Subsystem Status Check
```powershell
curl -s -H "X-API-Key: dev-viewer-key" http://127.0.0.1:8000/api/audit/blockchain/status
```
*Expected response:*
```json
{
  "connected": true,
  "chain_id": 11155111,
  "chain_name": "ethereum-sepolia",
  "contract_address": "0xf7aE6E373be5ad0f9444D230f285e8E620b70b63",
  "bytecode_deployed": true
}
```

### 3.3 Knowledge Graph Status Check
```powershell
curl -s -H "X-API-Key: dev-viewer-key" http://127.0.0.1:8000/api/graph/status
```
*Expected response:*
```json
{
  "status": "HEALTHY",
  "engine": "RelationalGraphEngine",
  "connected": false,
  "node_count": 374,
  "relationship_count": 206
}
```

---

## 4. Authentication & Role-Based Access Control

In development mode (`APP_ENVIRONMENT=development`), the system provides verified pre-configured development keys:

| Role | Development Header | Permissions |
|---|---|---|
| **Viewer** | `X-API-Key: dev-viewer-key` | Read-only access to dashboard, orders, suppliers, graph, audit |
| **Operator** | `X-API-Key: dev-operator-key` | Can trigger scenario runs, simulate disruptions, propose actions |
| **Supply Chain Approver** | `X-API-Key: dev-supply-chain-key` | Can approve supplier rerouting and procurement decisions |
| **Finance Approver** | `X-API-Key: dev-finance-key` | Can approve financial commitments up to ₹60,000,000 |
| **Admin** | `X-API-Key: dev-admin-key` | Full operational, financial, and administrative authority |

---

## 5. Five-to-Ten-Minute Live Demonstration Sequence

Follow this scripted sequence during the presentation:

### Step 1: System Overview & Telemetry Dashboard (0:00 – 1:30)
1. Open browser to `http://localhost:5173`.
2. Highlight the real-time operational status indicators:
   - System Health: **HEALTHY**
   - Active Knowledge Graph: **RelationalGraphEngine**
   - Blockchain Network: **Ethereum Sepolia (Chain ID 11155111)**
3. Point out domain statistics: 200 orders, 8 active suppliers, 150 inventory lots across 5 warehouses.

### Step 2: Knowledge Graph & Multi-Hop Traversal (1:30 – 3:30)
1. Navigate to the **Knowledge Graph** tab (`/graph`).
2. Show the multi-tier canvas displaying Customers, Orders, Products, Warehouses, and Suppliers.
3. Use the **Entity Filter** to isolate `Supplier` and `Product` nodes.
4. **Honest Engine Disclosure:** Note to evaluators that graph exploration is powered by the high-performance relational graph engine (`RelationalGraphEngine`) querying PostgreSQL directly, providing seamless air-gapped resilience when the external Neo4j daemon is offline.

### Step 3: Interactive Disruption Simulation & Impact Analysis (3:30 – 5:30)
1. In the **Disruption Simulator** panel on the right of the Knowledge Graph page:
   - Select Origin Entity: **Supplier**
   - Select Target Entity: `SUP-001` (Bharat Mineral Logistics)
   - Select Severity: **HIGH**
   - Traversal Depth: **3 Hops**
2. Click **Run Disruption Simulation**.
3. Point out the immediate downstream impact metrics:
   - Affected Products (e.g., `MAT-IRON`)
   - Traversal path tracing the supply dependency
   - **Alternative Supplier Ranking:** Display the qualified alternatives automatically discovered by the graph (e.g., `SUP-005` IronBridge Metals Trading) with lead times, risk scores, and performance evidence.

### Step 4: Multi-Agent Synthesis & Governed Human-in-the-Loop Approval (5:30 – 7:30)
1. Navigate to **Workflows** (`/workflows`).
2. Demonstrate how the **Supervisor Agent** synthesizes specialist findings:
   - `InventoryAgent` checks on-hand stock and safety levels.
   - `ProcurementAgent` ranks qualified alternative suppliers.
   - `FinanceAgent` validates budget impact against policy thresholds.
   - `LogisticsAgent` verifies transit corridors and freight lead times.
3. Show the **Pending Approval** gating: When financial exposure or supplier rerouting requires authorized approval, the policy engine holds the action in `PENDING` state.
4. Switch to an authorized approver role (`dev-supply-chain-key` or `dev-admin-key`) and click **Approve Action**.
5. Observe the state transition to `APPROVED` / `EXECUTED` with zero UI latency.

### Step 5: Cryptographic Audit Trail & Sepolia On-Chain Verification (7:30 – 9:30)
1. Navigate to **Audit Trail** (`/audit`).
2. Show the append-only event log capturing every state change, actor ID, and RFC 8785 canonical hash.
3. Locate the verified Ethereum Sepolia anchor:
   - **Event ID:** `EVT-PHASE7-SEP-635CDB7E`
   - **Transaction Hash:** `0xb01e8f6cfc7f98098b8879e69b2d64b9ba055b7796d4be5926acd26965b75a3b`
   - **Mined Block:** `#11915814`
   - **Contract Address:** `0xf7aE6E373be5ad0f9444D230f285e8E620b70b63`
4. Demonstrate independent read-only verification:
   - Explain how `verifyAnchor` calls the deployed Solidity smart contract directly over Alchemy Sepolia RPC.
   - Confirm that the on-chain payload digest exactly matches the computed RFC 8785 SHA-256 hash (`0x1c6c5a5d8ad6bac09a5c85d06059d60b8e64f40a52c86c2206f78a07e03716bd`).
   - Click the Etherscan link to view the immutable transaction on Sepolia Etherscan in the browser.
5. Emphasize: **Zero test ETH spent during this demonstration — verification is strictly read-only.**

---

## 6. Distinction: Live vs Simulated vs Fallback Features

To ensure complete presentation honesty, present these architectural distinctions:

| Subsystem | Active Mode | Operational Reality |
|---|---|---|
| **Relational Database** | **LIVE** | Live PostgreSQL instance storing orders, inventory, suppliers, audit log |
| **Ethereum Blockchain** | **LIVE (Read-Only)** | Verified on-chain contract `0xf7aE...` on Sepolia block #11915814 via Alchemy RPC |
| **Knowledge Graph** | **FALLBACK (Active)** | RelationalGraphEngine querying PostgreSQL; live Neo4j daemon is blocked/offline |
| **Agent Reasoning** | **DETERMINISTIC SIMULATION** | Domain synthesis engine (`deterministic-simulation-v1`) grounded in DB data; no external LLM tokens |
| **Action Execution** | **SIMULATED ADAPTER** | Safe state transitions recorded in PostgreSQL without triggering physical trucks or orders |

---

## 7. Troubleshooting & FAQ

### Issue: Backend returns 503 "Database connection unavailable"
- **Cause:** PostgreSQL service is stopped or port 5432 is unreachable.
- **Fix:** Start PostgreSQL service via Windows Services (`services.msc`) or verify `DATABASE_URL` credentials in `backend/.env`.

### Issue: Blockchain status returns "Web3 provider unreachable"
- **Cause:** Internet connection down or Alchemy RPC rate limited.
- **Fix:** Verify internet access. The application will fall back to local database audit verification if external RPC is unreachable.

### Issue: Knowledge graph page says "RelationalGraphEngine" instead of "Neo4j"
- **Explanation:** This is expected when Docker Desktop is offline. The system was designed with resilient dual-engine architecture so demonstrations never crash even without Neo4j.

---

## 8. Graceful Shutdown Instructions

When the demonstration concludes:

1. In the backend terminal, press `Ctrl + C` to stop Uvicorn.
2. In the frontend terminal, press `Ctrl + C` to stop the Vite development server.
3. Close browser tabs.
4. No background processes or uncleaned state will remain.
