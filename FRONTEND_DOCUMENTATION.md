# Enterprise AI Control Room — Frontend Technical Architecture & Reference

> **System Component:** Enterprise AI Mesh Frontend  
> **Repository Path:** `frontend/`  
> **Role:** Heavy-Industry Supply Chain Case File & Ledger Control Room  
> **Tech Stack:** React 19 · TypeScript 6 · Vite 8 · Tailwind CSS 4 · Lucide React · WebSockets · HTML5 Canvas  
> **Design Philosophy:** "The Case File" — Dense, legible, trustworthy operations log for Eastern Alloy & Steel (EAS)  
> **Theme System:** Dual-Theme ("Mill floor daylight" Light default / "Night shift" Dark mode) via `data-theme`  
> **Active Port:** `http://localhost:5173/` (Vite Dev Server)

---

## 1. Executive Summary & Design System

The **Enterprise AI Control Room** is the human-machine interface (HMI) for operators, dispatchers, and compliance controllers managing autonomous multi-agent steel supply chain operations. 

Departing completely from flashy, dark-neon "sci-fi AI cockpits", this interface is designed around the metaphor of **"The Case File"** — a calm, high-density, paper-inspired operations desk crossed with an immutable industrial shift ledger.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        TOP HEADER (52px, --surface, bottom border)                     │
│  [Breadcrumb: Orders / ORD-1042]       [SourceBadge]  [Scenario Select] [Run] [Theme]  │
├───────────────────┬────────────────────────────────────────────────────────────────────┤
│   FIXED SIDEBAR   │                   SCROLLABLE CONTENT VIEWPORT                      │
│     (232px)       │                     (Max 1440px Centered)                          │
│                   │                                                                    │
│  OPERATE          │  ┌──────────────────────────────────────────────────────────────┐  │
│  - Overview       │  │ PAGE HEADER: Title (22px/600), Description, Actions          │  │
│  - Orders         │  └──────────────────────────────────────────────────────────────┘  │
│  - Exceptions     │                                                                    │
│                   │  ┌──────────────────────────────────────────────────────────────┐  │
│  AGENTS           │  │ STATSTRIP: Tabular-nums KPI Cells separated by hairlines     │  │
│  - Agent Mesh     │  └──────────────────────────────────────────────────────────────┘  │
│  - Orchestration  │                                                                    │
│                   │  ┌──────────────────────────────────────────────────────────────┐  │
│  DOMAINS          │  │ THE CASE FILE / MAIN PANELS                                  │  │
│  - Inventory      │  │  - CaseHeader (20px mono ID, badges, plain outcome sentence) │  │
│  - Procurement    │  │  - PipelineStepper (7 fixed steps, single running pulse)     │  │
│  - Finance        │  │  - Stacked Panels: Findings, Supervisor, Policy, Approval,   │  │
│  - Logistics      │  │    What Changed (Simulated Banner), Audit Timeline           │  │
│                   │  └──────────────────────────────────────────────────────────────┘  │
│  EVIDENCE         │                                                                    │
│  - Knowledge Graph│  ┌──────────────────────────────────────────────────────────────┐  │
│  - Audit Trail    │  │ DENSE DATATABLES / CANVASES (40px rows, sticky headers)      │  │
│                   │  └──────────────────────────────────────────────────────────────┘  │
│  SYSTEM           │                                                                    │
│  - Benchmarks     │  ┌──────────────────────────────────────────────────────────────┐  │
│  - Security       │  │ ACCESSIBLE DETAIL DRAWERS (520px slide-over, Esc to close)   │  │
│  - Support & Docs │  └──────────────────────────────────────────────────────────────┘  │
└───────────────────┴────────────────────────────────────────────────────────────────────┘
```

### 1.1 Strict Design Tokens & Palette

The styling engine uses Tailwind CSS 4 with CSS custom properties declared in `src/index.css` under `:root, [data-theme="light"]` and `[data-theme="dark"]`, mapped via `@theme inline`:

| Token | Light Theme ("Mill floor daylight", Default) | Dark Theme ("Night shift", Charcoal) | Semantic Purpose |
| :--- | :--- | :--- | :--- |
| **`--bg`** | `#F4F2EE` (Warm paper grey) | `#17181A` (Deep warm charcoal) | Page canvas background |
| **`--surface`** | `#FFFFFF` (Pure white) | `#1F2124` (Elevated panel surface) | Primary panels, cards, headers |
| **`--surface-2`** | `#EEEBE5` (Subtle stone fill) | `#272A2E` (Subtle hover fill) | Table headers, row hover, inactive fills |
| **`--surface-sunk`**| `#E7E3DB` (Recessed canvas) | `#141517` (Deep recessed surface)| Inputs, code blocks, graph canvas |
| **`--border`** | `#D9D4CA` (Hairline divider) | `#33373C` (Subtle divider border) | 1px panel boundaries & dividers |
| **`--border-strong`**| `#B9B2A5` | `#4A4F56` | Emphasized borders, active tabs |
| **`--text`** | `#1C1F23` (Near-black) | `#ECE9E3` (Warm off-white) | High-contrast body typography |
| **`--text-2`** | `#4A5058` (Cool charcoal) | `#B4B0A8` (Muted silver) | Secondary descriptions, subheadings |
| **`--text-3`** | `#7A8088` (Muted slate) | `#868279` (Deep metadata text) | Tertiary metadata, timestamps, units |
| **`--accent`** | `#C2410C` (Forge Orange) | `#F08A4B` (Forge Orange Glow) | **The single primary brand accent** |
| **`--accent-soft`**| `#FBE9DD` | `#3A2417` | Accent tint background |
| **`--ok` / `-soft`**| `#2F6B3F` / `#E3EFE5` | `#6FBF84` / `#1E2F24` | Approved, completed, healthy |
| **`--warn` / `-soft`**| `#8A5A00` / `#F7EBCF` | `#E0B04A` / `#33290F` | Awaiting approval, low stock, delay |
| **`--danger` / `-soft`**| `#A32626` / `#F6DEDC` | `#E8776F` / `#38201E` | Blocked, failed, rejected, breach |
| **`--info` / `-soft`**| `#2C5A7A` / `#DCE8F0` | `#7FB0D3` / `#1B2B38` | Running steps, in-transit shipments |
| **`--sim` / `-soft`**| `#5B4B8A` / `#E8E3F2` | `#B3A3E0` / `#2A2540` | **Simulated data exclusively** |

### 1.2 Truthful State & Vocabulary Governance
1. **Zero Faked Liveness:** Every status label derives strictly from real context state (`Live · PostgreSQL`, `Simulated`, `Fallback`, `Stale`, `Unavailable`).
2. **Standardized Status Vocabulary (`StatusBadge.tsx`):** Exactly 11 deterministic keys: `running`, `completed`, `allowed`, `blocked`, `awaiting_approval`, `approved`, `rejected`, `failed`, `simulated`, `unavailable`, `pending`.
3. **Typography Standards:**
   - **Sans:** IBM Plex Sans (400, 500, 600) for all headings, labels, and copy.
   - **Mono:** IBM Plex Mono (400, 500) strictly for Order IDs, SKUs, SHA-256 hashes, timestamps, and numeric table columns with `font-variant-numeric: tabular-nums`.

---

## 2. Execution Scripts & Commands

All frontend commands should be executed from within the `frontend/` directory:

```bash
cd frontend
```

### 2.1 NPM Scripts (`package.json`)

| Script | Command | Purpose & Description |
| :--- | :--- | :--- |
| **`npm run dev`** | `vite` | Starts the local Vite development server with Hot Module Replacement (HMR) at `http://localhost:5173/`. |
| **`npm run build`** | `tsc -b && vite build` | Runs strict TypeScript type-checking (`tsc -b`) and compiles production bundle to `dist/`. |
| **`npm run lint`** | `oxlint` | High-speed static analysis with zero errors across all `.ts` and `.tsx` source files. |
| **`npm run preview`** | `vite preview` | Boots a local static server to preview the compiled `dist/` production assets. |

### 2.2 Docker & Containerization

The frontend is containerized using a multi-stage Dockerfile:
- **Build Stage:** `node:20-alpine` builds the app with `npm ci` and `npm run build`.
- **Production Stage:** `nginx:alpine` serves static files on port 80.

```bash
# Build standalone Docker image
docker build -t enterpriseai-frontend:latest ./frontend

# Run container mapped to port 5173
docker run -d -p 5173:80 --name enterpriseai-frontend enterpriseai-frontend:latest
```

---

## 3. Configuration & Environment Variables

| Variable | Default Value | Purpose |
| :--- | :--- | :--- |
| **`VITE_API_BASE_URL`** | `http://localhost:8000` | Backend API base URL for REST calls and WebSocket handshakes (`/api/ws`). |
| **`VITE_API_KEY`** | `""` (Fallback: `dev-operator-key`) | Build-time API key. Runtime credentials can also be set in browser `localStorage.getItem('ent_api_key')`. |

---

## 4. Complete File Inventory

```
frontend/
├── Dockerfile                        # Multi-stage production container definition (Node 20 -> Nginx)
├── index.html                        # HTML entry point: IBM Plex fonts & pre-mount theme script
├── package.json                      # Dependencies: React 19, Vite 8, Tailwind CSS 4, Lucide React
├── package-lock.json                 # Pinned dependencies
├── postcss.config.js                 # PostCSS setup
├── tailwind.config.js                # Tailwind 4 configuration with selector dark mode
├── tsconfig.json                     # Root TypeScript project references
├── tsconfig.app.json                 # Client TS configuration (Strict, React 19 JSX)
├── tsconfig.node.json                # Vite tooling TS configuration
├── vite.config.ts                    # Vite bundler configuration
├── public/
│   ├── favicon.svg                   # Application favicon
│   └── icons.svg                     # Vector assets
└── src/
    ├── App.css                       # Boilerplate reset
    ├── App.tsx                       # App component, ThemeProvider wrapping, and 14 screen routes
    ├── index.css                     # Design tokens (:root, [data-theme="dark"]), @theme inline utilities
    ├── main.tsx                      # Application mounting onto #root
    ├── types/
    │   └── index.ts                  # Shared data schemas (Order, Agent, Supplier, Inventory, Audit)
    ├── services/
    │   ├── apiClient.ts              # Strongly typed REST client for all 14 FastAPI backend routers
    │   ├── apiServices.ts             # Domain service helper abstractions
    │   └── websocketClient.ts        # Resilient WebSocket client with auto-reconnect & ticket handshake
    ├── state/
    │   ├── DemoContext.tsx           # Universal State Engine (Live Backend Integration vs. Offline Demo)
    │   └── ThemeContext.tsx          # Dual-theme manager ('light' | 'dark' | 'system') with persistence
    ├── data/
    │   └── initialDemoData.ts        # Baseline industrial data (EAS steel mill entities, orders, inventory)
    ├── components/
    │   ├── case/                     # The Case File Architecture Components
    │   │   ├── CaseFileSections.tsx  # 6 stacked panels: Findings, Supervisor, Policy, Approval, What Changed, Audit
    │   │   ├── CaseHeader.tsx        # Case title, 20px mono ID, badges, and plain outcome sentence
    │   │   └── PipelineStepper.tsx   # 7 fixed sequential steps with single running pulse
    │   ├── common/                   # Core Shared UI Component Library
    │   │   ├── DataTable.tsx         # Dense 40px table, sticky headers, keyboard navigation, sorting
    │   │   ├── DetailDrawer.tsx      # Accessible 520px slide-over inspector drawer with Esc capture
    │   │   ├── EmptyState.tsx        # Text-based empty state with cause and next action
    │   │   ├── ErrorState.tsx        # Mono error block with reload action
    │   │   ├── EvidenceChip.tsx      # Compact entity link chip (e.g. inventory_lot:LOT-2291)
    │   │   ├── KeyValueList.tsx      # 2-column definition list with copy-to-clipboard action
    │   │   ├── PageHeader.tsx        # 22px page title, subtitle, SourceBadge, and action buttons
    │   │   ├── Panel.tsx             # 6px radius, hairline header, padding variants
    │   │   ├── Skeleton.tsx          # Flat surface-2 skeleton bars (zero shimmer)
    │   │   ├── SourceBadge.tsx       # 5 proven states with diagnostic popover & mode switch
    │   │   ├── StatStrip.tsx         # Tabular-nums KPI strip replacing large tiles
    │   │   ├── StatusBadge.tsx       # Unified 11-key status vocabulary with 100% semantic colors
    │   │   ├── Tabs.tsx              # Underline tab switcher
    │   │   └── Toast.tsx             # Bottom-left toast notification with colored accent bar
    │   └── layout/                   # Application Shell & Navigation
    │       ├── AppShell.tsx          # 1440px max-width shell with skip-to-content accessibility link
    │       ├── Sidebar.tsx           # 5 grouped categories, 14 screens, active bar, count badges
    │       └── TopHeader.tsx         # Breadcrumb, SourceBadge, scenario select, run button, theme toggle
    └── pages/                        # The 14 Mission Control Screens
        ├── OverviewPage.tsx          # Operations overview: StatStrip, Active Workflows, Needs Attention
        ├── OrdersPage.tsx            # Orders ledger, filter bar, drill-down Case File, New Order drawer
        ├── OrchestrationPage.tsx     # Governed execution: PipelineStepper, Case body, Run trace tab
        ├── ExceptionsPage.tsx        # Queue table: Severity square, cause, Governance Case File inspection
        ├── AuditTrailPage.tsx        # RFC 8785 canonical JSON drawer, Verify action, Sepolia anchor dialog
        ├── AgentMeshPage.tsx         # 5-row telemetry table, JSON output inspector, static schematic
        ├── InventoryPage.tsx         # Stock table with 4px stock bar, warehouse lots DetailDrawer
        ├── ProcurementPage.tsx       # Qualified suppliers, lowest landed cost offer comparison, timeline
        ├── FinancePage.tsx           # INR StatStrip, flat horizontal budget bars with limit tick, policy checks
        ├── LogisticsPage.tsx         # Shipments table with delay text, carrier events drawer, delivery risk
        ├── KnowledgeGraphPage.tsx    # Canvas graph on surface-sunk, 6 muted colors, Neo4j vs Fallback badge
        ├── BenchmarksPage.tsx        # Flat SVG charts (1.5px lines), metric panels with definitions & refresh
        ├── SecurityPage.tsx          # Read-only auth summary, boolean API key presence, hygiene checklist
        └── SupportPage.tsx           # Startup copy commands, API health links, vocabulary table, glossary
```

---

## 5. The Case File Architecture (`src/components/case/`)

The center of the application is **"The Case File"**, which structures every workflow run top-to-bottom like an auditable industrial operations dossier:

### 5.1 CaseHeader (`CaseHeader.tsx`)
- Order ID in 20px mono typography.
- Customer name, scenario type, priority tag.
- `SourceBadge` and overall governance `StatusBadge`.
- Started timestamp and duration.
- **One-line Outcome Sentence:** Composed from state in plain words without hype (e.g. *"Blocked: purchase would exceed Q4 raw-material budget by ₹4.2L. Awaiting approval from Finance Head."*).

### 5.2 PipelineStepper (`PipelineStepper.tsx`)
Seven fixed sequential stages:
```
Scenario ──▶ Supervisor ──▶ Specialists ──▶ Policy ──▶ Governance ──▶ Action ──▶ Audit
```
- Numbered 24px circles: `--surface-2` (pending), `--info` with a single subtle pulse (running), `--ok` with checkmark (done), `--danger` with cross (blocked/failed), `--warn` with clock (awaiting approval).
- Clicking a step smoothly scrolls to its corresponding panel below.

### 5.3 Case Body Sections (`CaseFileSections.tsx`)
Stacked panels in rigid order:
1. **Specialist Findings:** Table showing Agent, Status, Finding summary, Risk level, Evidence chips, Provider (`Gemini`, `OpenRouter`, or `Simulation`), and Latency.
2. **Supervisor Decision:** Synthesized recommendation, confidence percentage in mono, resolved conflicts, and proposed actions list.
3. **Deterministic Policy Result:** Checklist of evaluated business rules with inputs, thresholds, and PASS/FAIL badges. Includes fixed disclaimer: *"Models recommend. Deterministic policy decides."*
4. **Governance & Approval:** Current outcome badge, required role, and Approve/Reject buttons. Rejection enforces a mandatory reason input (minimum 5 characters).
5. **What Changed:** Table of persisted database mutations (Table, Record, Before ➔ After). In simulated mode, renders a prominent banner in `--sim-soft`: *"Simulated: no database records were changed."*
6. **Audit Events:** Vertical left-rail timeline of state transitions with truncated SHA-256 hashes (`0x1c6c…16bd`) and copy actions.

---

## 6. The 14 Mission Control Screens

The navigation is divided into 5 clear operational groups:

### Group 1: Operate
- **Overview (`OverviewPage.tsx`):** StatStrip (Orders in progress, Awaiting approval, Blocked, Open exceptions, Audit events today, Safe-failure rate). 2:1 column layout: Left = Active workflows `DataTable`; Right = Needs attention queue. Below: 5-row compact Agent activity table and Recent audit events.
- **Orders (`OrdersPage.tsx`):** Filter bar (Search, Status, Scenario, Priority, Date). Dense `DataTable`. Clicking an order switches to the full-width Case File view with a back link. "New order" button opens an accessible `DetailDrawer` with field validation.
- **Exceptions (`ExceptionsPage.tsx`):** Queue `DataTable` showing Severity square + label (Critical = danger, High = warn, Medium = info, Low = neutral), Type, Order, Cause, Owner, Age, and Status. Row click opens the Case File focused on the Governance & Approval panel.

### Group 2: Agents
- **Agent Mesh (`AgentMeshPage.tsx`):** 5-row dense telemetry table (Supervisor, Inventory, Procurement, Finance, Logistics) with Role sentence, State, Runs today, Avg latency, Timeout/retries, Provider, and Last error. Row expand reveals recent runs and structured JSON output with copy action. Includes a restrained 160px static schematic.
- **Orchestration (`OrchestrationPage.tsx`):** Top order/scenario controls with "Execute governed pipeline" button showing exact disabled reason tooltips. Main view displays the `PipelineStepper` and Case body sections. Left 240px run history sidebar. "Run trace" tab for raw state variable inspection. Diagnostics panel when execution is blocked.

### Group 3: Domains
- **Inventory (`InventoryPage.tsx`):** StatStrip (SKUs tracked, Below reorder level, Reserved, Shortages). `DataTable` with SKU, Grade, Site, On-hand, Reserved, Available, Reorder point, and Status. Available cell includes a thin 4px horizontal stock bar. Row click opens lot inspection `DetailDrawer`.
- **Procurement (`ProcurementPage.tsx`):** Qualified suppliers table with inline unavailable note. 40 MT slab requisition offer comparison with lowest landed cost highlighted by a 3px `--ok` left border. Negotiation history timeline.
- **Finance (`FinancePage.tsx`):** StatStrip in INR format. Flat horizontal budget bars (`--accent` committed fill, `--surface-sunk` track, 1px vertical tick at policy limit). Deterministic policy checks table linking breaches to Exceptions.
- **Logistics (`LogisticsPage.tsx`):** Shipments `DataTable` (Shipment, Order, Carrier, Origin, Destination, ETA, Promised, Delay days, Status). Delay column colored warn (>0d) or danger (over SLA). Carrier events timeline drawer. "Delivery risk" panel listing orders at risk with plain-sentence causes.

### Group 4: Evidence
- **Knowledge Graph (`KnowledgeGraphPage.tsx`):** Interactive HTML5 Canvas graph on `--surface-sunk` with rAF rendering and devicePixelRatio support. 6-color muted categorical palette (`--n-customer`, `--n-order`, `--n-product`, `--n-warehouse`, `--n-supplier`, `--n-shipment`). Clean 1px edges. Labels shown only on hover/selection and for immediate neighbors. Zoom/pan, "Fit", and "Reset" actions. Top-right backend badge: **"Neo4j (live)"** or **"Relational fallback"**. "Trace impact" tool with 1 to 4 hop selector. Accessible text list alternative.
- **Audit Trail (`AuditTrailPage.tsx`):** StatStrip (Events, Anchored, Verified, Unverified). Events `DataTable`. Row click opens `DetailDrawer` displaying RFC 8785 canonical JSON, computed vs stored SHA-256 digest, and Sepolia transaction details with explorer link (`rel="noopener noreferrer"`). **Verify button is read-only; Anchor button requires an explicit confirmation modal dialog ("This sends a transaction on Sepolia and spends test ETH. Continue?").**

### Group 5: System
- **Benchmarks (`BenchmarksPage.tsx`):** Metric panels with plain definitions, time windows, data source, refresh cadence, and `SourceBadge`. Simple flat SVG line and bar charts (1.5px lines, single series `--accent`, multi-series `--info`, `--ok`, `--warn`, axis labels in `text-3`). Explicit refresh timestamps ("Updated 19:15").
- **Security (`SecurityPage.tsx`, New):** Read-only authentication summary (API key set / not set boolean flag, never printing key), operator permissions, single-use WebSocket ticket explanation, redaction policy note, and static credential hygiene checklist.
- **Support & Docs (`SupportPage.tsx`, New):** Startup commands with copy buttons (backend and frontend), API health links (`/api/health`, `/docs`), scenario descriptions, governance status vocabulary reference table, system glossary, known limitations, and explicit Theme segmented control.

---

## 7. State Management & Real-Time Communications

### 7.1 Universal State Engine (`DemoContext.tsx`)
- **Live Mode Integration:** Automatically fetches orders, inventory, suppliers, approvals, actions, and audit logs from FastAPI REST endpoints. Connects to WebSockets for live streaming.
- **Simulated Mode Execution:** Provides a client-side execution engine running realistic edge-case scenarios (`normal`, `supplier_unavailable`, `budget_breach`, `delivery_delay`, `multi_exception`).
- **Data Boundary:** Strictly isolates presentation components from modifying services or API contracts.

### 7.2 WebSocket Streaming (`websocketClient.ts`)
- Full-duplex connection to `ws://localhost:8000/api/ws`.
- Authenticated via single-use ticket generated via `POST /api/ws/ticket`.
- Bounded exponential backoff with jitter and LRU message deduplication.
- Dynamic subscription to channels: `workflows`, `approvals`, `actions`, `scheduler`, `orchestration`.

---

## 8. Accessibility & Responsive Verification

- **Breakpoints:**
  - `1280px+`: Full desktop layout with 232px sidebar and 1440px centered content.
  - `1024px`: Sidebar collapses smoothly to a 56px icon rail.
  - `768px`: Sidebar transforms into an accessible slide-over drawer toggled from a menu button. Panels collapse to a single column.
  - `390px`: Mobile layout with zero page-level horizontal overflow; tables scroll horizontally within their panels.
- **Keyboard Navigation:** Every button and interactive element has a visible 2px outline in `var(--focus)` offset by 2px. Arrow Up/Down navigates `DataTable` rows; Enter opens detail; Esc closes slide-over drawers.
- **WCAG AA Compliance:** Body text and badge combinations maintain at least 4.5:1 contrast against surfaces in both Light and Dark modes.
