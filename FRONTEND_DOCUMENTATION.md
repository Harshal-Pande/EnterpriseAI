# Enterprise AI Control Room — Frontend Technical Architecture & Reference

> **System Component:** Enterprise AI Mesh Frontend  
> **Repository Path:** `frontend/`  
> **Role:** Real-Time Autonomous Multi-Agent Supply Chain Mission Control Room  
> **Tech Stack:** React 19 · TypeScript 6 · Vite 8 · Tailwind CSS 4 · Lucide React · WebSockets  
> **Operating Modes:** Dual-Mode (Live Backend Integration / Offline Autonomous Simulation)

---

## 1. Executive Summary & Context

The **Enterprise AI Control Room** is the mission-critical human-machine interface (HMI) and operational cockpit for the Enterprise AI Mesh platform. It gives operators, supply chain directors, and compliance officers continuous visibility and deterministic control over an autonomous mesh of 5 specialized AI agents orchestrating end-to-end supply chain order fulfillment:

1. **Supervisor Agent:** Root orchestrator, policy dispatcher, and overall consensus evaluator.
2. **Inventory Agent:** Real-time multi-warehouse stock level tracking, reservation management, and shortage alerts.
3. **Procurement Agent:** Automated supplier discovery, quotation evaluation, dynamic price negotiations, and purchase order drafting.
4. **Finance Agent:** Automated budget validation, margin compliance verification, and transaction disbursement gates.
5. **Logistics Agent:** Multi-carrier shipping feasibility, fleet dispatch, route optimization, and SLA/ETA tracking.

```
                     ┌───────────────────────────────────────────────┐
                     │     Enterprise AI Control Room (React 19)     │
                     └──────┬──────────────────┬─────────────────┬───┘
                            │ REST (FastAPI)   │ WebSockets      │ Neo4j Graph API
                            ▼                  ▼                 ▼
                     ┌───────────────┐  ┌───────────────┐  ┌────────────────┐
                     │ Backend APIs  │  │ Real-time WS  │  │ Knowledge Graph│
                     │ (Port 8000)   │  │ Channel Hub   │  │ (Port 7474)    │
                     └──────┬────────┘  └──────┬────────┘  └────────────────┘
                            │                  │
               ┌────────────┴──────────────────┴─────────────┐
               ▼                                             ▼
     ┌──────────────────┐                          ┌──────────────────┐
     │ PostgreSQL (DB)  │                          │ Blockchain Node  │
     │ State & Orders   │                          │ Sepolia / Audit  │
     └──────────────────┘                          └──────────────────┘
```

### Key Capabilities
- **Dual-Mode Execution Architecture:** 
  - **Live Mode:** Connects over REST and WebSockets to the FastAPI backend, streaming live agent runs, triggering LangGraph state machines, managing Human-in-the-Loop (HITL) approval gates, and executing blockchain audit trail verifications.
  - **Demo / Simulation Mode:** Completely self-contained client-side simulation engine enabling presentations, offline testing, and interactive walkthroughs of realistic edge scenarios (`supplier_unavailable`, `budget_breach`, `delivery_delay`, `multi_exception`).
- **Explainable Autonomous Decisions (XAI):** Full transparency into agent reasoning, input parameters, policy evaluations, confidence scores, and action proposals.
- **Human-in-the-Loop (HITL) Exception Management:** Deterministic intervention approval gates requiring human authorization for budget overruns or supplier substitutions.
- **Cryptographic Audit Trail:** Visual verification of SHA-256 state hashes anchored into Sepolia testnet or local blockchain ledgers.
- **Interactive Enterprise Knowledge Graph:** Canvas-rendered entity relationship exploration across Customers, Orders, Products, Warehouses, Suppliers, and Shipments.

---

## 2. Frontend Execution Scripts & Commands

All frontend commands should be executed from within the `frontend/` directory:

```bash
cd frontend
```

### 2.1 NPM Scripts (defined in `package.json`)

| Script | Command | Purpose & Description |
| :--- | :--- | :--- |
| **`npm run dev`** | `vite` | Starts the Vite local development server with Hot Module Replacement (HMR). Default port: `http://localhost:5173`. |
| **`npm run build`** | `tsc -b && vite build` | Performs strict incremental TypeScript type checking (`tsc -b`) followed by optimized production tree-shaking and bundling via Vite into `dist/`. |
| **`npm run lint`** | `oxlint` | Executes ultra-fast code linting across all `.ts` and `.tsx` source files using the Rust-based Oxlint engine. |
| **`npm run preview`** | `vite preview` | Boots a local static HTTP server to preview the production build artifacts generated in `dist/`. |

### 2.2 Docker & Containerization

The frontend is containerized using a two-stage build defined in `frontend/Dockerfile`:
- **Stage 1 (Build):** `node:20-alpine` installs dependencies via `npm ci` and compiles the static bundle using `npm run build`.
- **Stage 2 (Runtime):** `nginx:alpine` serves the production distribution via high-performance Nginx on port 80.

#### Build and run standalone container:
```bash
# Build image
docker build -t enterpriseai-frontend:latest ./frontend

# Run container mapped to port 5173
docker run -d -p 5173:80 --name enterpriseai-frontend enterpriseai-frontend:latest
```

#### Run via Root Docker Compose:
The frontend is pre-configured as service `frontend` in `docker-compose.yml`:
```bash
# From repository root
docker compose up -d --build frontend
```
*Note: In Docker Compose, the container port `80` is mapped to host port `5173`.*

---

## 3. Configuration & Environment Variables

Frontend configuration is handled through Vite environment variables defined in `.env` or `.env.example`:

| Variable | Default Value | Purpose |
| :--- | :--- | :--- |
| **`VITE_API_BASE_URL`** | `http://localhost:8000` | Target URL for the FastAPI backend service providing REST endpoints and WebSocket handshakes (`/api/ws`). |
| **`VITE_API_KEY`** | `""` (Fallback: `dev-operator-key`) | Optional build-time API key. For security, runtime credentials can also be set directly in browser `localStorage` under `ent_api_key`. |

> [!NOTE]
> All `VITE_*` environment variables are baked into the compiled JavaScript bundle at build time. Never place production private keys, administrator secrets, or database credentials in these variables.

---

## 4. Complete File Inventory

Below is the directory structure and file catalog of everything present in `frontend/`:

```
frontend/
├── .env                              # Local environment variable configuration
├── .env.example                      # Template for environment variables with security guidelines
├── .gitignore                        # Git exclusion rules for node_modules and build artifacts
├── Dockerfile                        # Multi-stage production Docker build (Node.js + Nginx)
├── index.html                        # Single-page HTML entry point and font/metadata declarations
├── old_mesh.txt                      # Deprecated legacy mesh scratch file
├── package.json                      # Project dependencies, metadata, and scripts
├── package-lock.json                 # Pinned dependency lockfile
├── postcss.config.js                 # PostCSS configuration for Tailwind CSS 4 integration
├── tailwind.config.js                # Tailwind theme extensions, color tokens, and font families
├── tsconfig.json                     # Root TypeScript project reference configuration
├── tsconfig.app.json                 # Client TypeScript compiler options (DOM, JSX, Strict)
├── tsconfig.node.json                # Node/Vite tooling TypeScript configuration
├── vite.config.ts                    # Vite build configuration with React plugin
├── public/
│   ├── favicon.svg                   # Application favicon
│   └── icons.svg                     # Vector asset icons
└── src/
    ├── App.css                       # Root component CSS styling and utility overrides
    ├── App.tsx                       # Main application shell and 12-page screen routing logic
    ├── index.css                     # Global design tokens, neon cyber-industrial variables & scrollbars
    ├── main.tsx                      # React 19 application bootstrapping and DOM root mount
    ├── assets/
    │   ├── hero.png                  # System promotional visual asset
    │   ├── react.svg                 # React brand asset
    │   └── vite.svg                  # Vite brand asset
    ├── types/
    │   └── index.ts                  # Shared TypeScript interfaces (Agents, Orders, Workflows, Audit)
    ├── services/
    │   ├── apiClient.ts              # Strongly typed REST client for FastAPI backend endpoints
    │   ├── apiServices.ts             # Domain-specific backend API abstraction services
    │   └── websocketClient.ts        # Resilient WebSocket client with auto-reconnect & deduplication
    ├── state/
    │   └── DemoContext.tsx           # Global React Context provider managing Live vs. Demo state
    ├── data/
    │   └── initialDemoData.ts        # Comprehensive offline simulation datasets and topologies
    ├── components/
    │   ├── common/
    │   │   └── StatusBadge.tsx       # Standardized status badge for agents, orders, and states
    │   ├── layout/
    │   │   ├── AppShell.tsx          # Master viewport layout frame (Sidebar + Header + Content)
    │   │   ├── Sidebar.tsx           # 12-screen navigation menu with live status badges
    │   │   └── TopHeader.tsx         # Cockpit telemetry bar, mode switch, WS status, & controls
    │   └── overview/
    │       ├── ActivityStream.tsx    # Chronological audit and event activity stream
    │       ├── AgentDecisionPanel.tsx # Explainable AI (XAI) rationale and policy inspector
    │       ├── LiveAgentMesh.tsx     # Visual agent network topology with workload rings
    │       └── LiveOrderPanel.tsx    # Interactive order feed with search and status filters
    └── pages/
        ├── OverviewPage.tsx          # Executive dashboard & mission control center
        ├── OrdersPage.tsx            # Order management, status pipeline, and batch creator
        ├── AgentMeshPage.tsx         # In-depth agent telemetry, workload, and inter-agent comms
        ├── OrchestrationPage.tsx     # Multi-agent LangGraph workflow DAG & step execution
        ├── InventoryPage.tsx         # Multi-warehouse stock tracking, reservations, and shortages
        ├── ProcurementPage.tsx       # Supplier quotation evaluation, scoring, and auto-negotiation
        ├── FinancePage.tsx           # Budget allocations, margin checks, and disbursement policies
        ├── LogisticsPage.tsx         # Carrier feasibility, delivery routing, and ETA tracking
        ├── KnowledgeGraphPage.tsx    # Interactive Neo4j knowledge graph visualizer (canvas)
        ├── AuditTrailPage.tsx        # Cryptographic ledger, SHA-256 verification, & blockchain anchoring
        ├── ExceptionsPage.tsx        # Human-in-the-Loop (HITL) approval gate and exception resolution
        └── BenchmarksPage.tsx        # Mesh latency, throughput, token cost, and accuracy telemetry
```

---

## 5. Architectural Deep-Dive

### 5.1 Universal State Management: `DemoContext.tsx`
Located in `src/state/DemoContext.tsx`, this central provider unifies two distinct operating modalities:

1. **Live Backend Mode:**
   - Periodically queries FastAPI REST endpoints for real orders, inventory items, suppliers, active approvals, controlled actions, and scheduler cycles.
   - Subscribes to the WebSocket client (`websocketClient.ts`) on channels `workflows`, `approvals`, `actions`, `scheduler`, and `orchestration`.
   - Incoming WebSocket events dynamically trigger state updates without requiring page refreshes.
   - Exposes functions to trigger live LangGraph agent orchestrations (`executeLiveOrchestration`), approve/reject HITL exceptions (`decideApproval`), and submit state hashes to the blockchain (`anchorAuditEvent`).
2. **Interactive Simulation Mode:**
   - Driven by `data/initialDemoData.ts`.
   - Simulates realistic multi-agent execution step-by-step through a state machine timer (`runDemoOrder`).
   - Cycles through stages: `SUPERVISOR_ANALYSIS` ➔ `INVENTORY_CHECK` ➔ `PROCUREMENT_NEGOTIATION` ➔ `FINANCE_VALIDATION` ➔ `LOGISTICS_FEASIBILITY` ➔ `SUPERVISOR_DECISION` ➔ `ORDER_FULFILLED`.
   - Simulates edge-case failure modes including supplier stockouts, pricing budget breaches, and carrier transit delays.

### 5.2 Real-Time WebSocket Client: `websocketClient.ts`
Located in `src/services/websocketClient.ts`, providing enterprise-grade streaming communications:
- **Resilient Reconnection:** Bounded exponential backoff with random jitter to prevent server thundering herds.
- **Heartbeat Keepalive:** Automatic ping/pong exchange to detect half-open TCP connections.
- **Channel Subscriptions:** Targeted message dispatching (`workflows`, `approvals`, `actions`, `scheduler`).
- **Deduplication Cache:** Bounded LRU-style cache tracking recent event IDs to eliminate duplicate renders.
- **Replay Catch-Up:** Automatically requests missed event replays upon reconnection.

### 5.3 Typed Backend API Client: `apiClient.ts`
Located in `src/services/apiClient.ts`, providing type-safe abstractions over all FastAPI endpoints:
- Orders, inventory, and supplier querying.
- Workflow run dispatching (`POST /api/v1/orchestration/run`).
- Autonomous scheduler cycle triggers (`POST /api/v1/scheduler/run-cycle`).
- Human-in-the-Loop approval decision gates (`POST /api/v1/approvals/{id}/decide`).
- Controlled action execution (`POST /api/v1/actions/{id}/execute`).
- SHA-256 cryptographic state verification (`GET /api/v1/audit/verify/{event_id}`).
- Blockchain transaction anchoring (`POST /api/v1/audit/anchor/{event_id}`).

---

## 6. The 12 Mission Control Pages

The application provides 12 specialized operations screens, selectable via the `Sidebar.tsx`:

| Screen ID | Page Component | Functional Scope & Capabilities |
| :--- | :--- | :--- |
| **`overview`** | `OverviewPage.tsx` | **Executive Mission Control.** System KPIs (Active Agents, Orders Processing, Exceptions, Audit Events), Live Agent Mesh visualizer, active order pipeline, real-time XAI decision panel, and recent activity stream. |
| **`orders`** | `OrdersPage.tsx` | **Order Operations.** Full searchable and filterable table of customer orders, stage tracker, priority categorization, order creation modal, and instant workflow dispatch. |
| **`mesh`** | `AgentMeshPage.tsx` | **Agent Mesh Diagnostics.** Individual telemetry cards for all 5 agents showing CPU/memory workload, completed task counts, average response latency, and inter-agent communication logs. |
| **`orchestration`** | `OrchestrationPage.tsx` | **Workflow DAG Execution.** Visual representation of the LangGraph multi-agent execution pipeline with step transitions, state variables, agent outputs, and step-by-step trace inspection. |
| **`inventory`** | `InventoryPage.tsx` | **Warehouse & Stock Management.** Real-time SKU stock levels, reserved quantities, reorder thresholds, warehouse location assignments, and shortage alerts. |
| **`procurement`** | `ProcurementPage.tsx` | **Supplier Discovery & Bidding.** Dynamic price quotes, supplier scorecards (reliability, cost, speed), automated RFQ generation, and counter-offer negotiation telemetry. |
| **`finance`** | `FinancePage.tsx` | **Financial Governance.** Order profitability analysis, budget threshold checks, transaction cost breakdown, margin policy validation, and automated payment release triggers. |
| **`logistics`** | `LogisticsPage.tsx` | **Fleet & Transit Logistics.** Carrier selection, transit route feasibility scoring, SLA adherence tracking, delivery ETA projections, and transport delay handling. |
| **`graph`** | `KnowledgeGraphPage.tsx` | **Enterprise Knowledge Graph.** Interactive canvas-based network graph displaying Neo4j entity relationships across Customers, Orders, Products, Warehouses, Suppliers, and Shipments with node inspectors. |
| **`audit`** | `AuditTrailPage.tsx` | **Cryptographic Blockchain Audit.** Immutable event ledger recording all agent decisions, SHA-256 state hashes, Merkle root verification, and live Sepolia testnet transaction explorer links. |
| **`exceptions`** | `ExceptionsPage.tsx` | **HITL Exception Center.** Human-in-the-Loop decision queue presenting flagged anomalies, budget deviations, and policy violations for manual operator approval or rejection. |
| **`benchmarks`** | `BenchmarksPage.tsx` | **Mesh Performance Telemetry.** Quantitative benchmarking graphs displaying agent decision latency, workflow throughput, LLM token utilization, and recovery rates from simulated failures. |

---

## 7. Design System & User Experience

- **Aesthetic:** High-density, cyber-industrial dark mode (`#080C14` canvas background) built for mission control environments.
- **Color Semantics:**
  - **Cyan (`#38BDF8`):** Active agents, primary actions, running workflows.
  - **Emerald (`#10B981`):** Verified states, approved orders, optimal inventory.
  - **Amber (`#F59E0B`):** Warnings, pending approvals, low stock thresholds.
  - **Rose (`#EF4444`):** Exceptions, budget breaches, agent errors.
  - **Slate (`#64748B` / `#1E293B`):** Structural borders, secondary text, muted metadata.
- **Typography:** Modern clean sans-serif paired with monospaced accents (`font-mono`) for numerical figures, SHA-256 hashes, timestamps, and order identifiers.

---

## 8. Development & Troubleshooting FAQ

### Q: Why does the UI show "SIMULATED / DEMO MODE" instead of live data?
**A:** By default or if the FastAPI backend is unreachable on `http://localhost:8000`, the application runs in Demo Mode. To connect to the live backend:
1. Ensure the backend is running (`uvicorn app.main:app --host 0.0.0.0 --port 8000`).
2. Click the **"SWITCH TO LIVE"** button located in the `TopHeader` bar.
3. If using Docker, ensure `VITE_API_BASE_URL` is set to your reachable host/container endpoint.

### Q: How do I change the API Key used for backend requests?
**A:** Open browser Developer Tools (`F12`), switch to the Console, and run:
```javascript
localStorage.setItem('ent_api_key', 'your-operator-or-admin-api-key');
location.reload();
```

### Q: How do I trigger an end-to-end agent scenario demonstration?
**A:** In the `TopHeader` or `OverviewPage`, select any scenario from the dropdown:
- `Normal Fulfillment`: Standard happy path order fulfillment.
- `Supplier Unavailable`: Triggers dynamic supplier discovery and re-negotiation.
- `Budget Breach`: Triggers a Finance Agent policy violation and sends an alert to the Exceptions HITL page.
- `Delivery Delay`: Simulates carrier logistic bottleneck and route recalculation.
Then click the **"Run Scenario"** button.
