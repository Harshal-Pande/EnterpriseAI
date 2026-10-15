# Enterprise AI Mesh Frontend Redesign — Implementation Plan

> **Specification Source:** `FRONTEND_REDESIGN_MASTER_PROMPT.md` (Authoritative Claude UI/UX Spec)  
> **Target Project:** `frontend/` (React 19, TypeScript 6, Vite 8, Tailwind CSS 4)  
> **Status:** Active & In-Progress  
> **Last Updated:** 2026-10-15  

---

## 1. Executive Summary & Architectural Direction

This document governs the comprehensive UI/UX overhaul of the Enterprise AI Mesh frontend. The system is being transformed from a generic, sci-fi/cyber-styled AI dashboard into a restrained, dense, trustworthy **Case File and Ledger Control Room** tailored for a heavy-industry steel manufacturing supply chain desk ("The Case File").

### Core Design Philosophy
- **Industry Persona:** Shift supervisor and supply chain controller managing complex material flow, supplier negotiations, and budget allocations.
- **Visual Tone:** "Mill floor daylight" (warm paper grey, high legibility) default theme and "Night shift" (warm charcoal, zero neon/glow) dark theme. Primary brand accent: Forge Orange (`#C2410C` light / `#F08A4B` dark).
- **Truthful State Representation:** Never fake liveness or verification. Status and provenance (`Live · PostgreSQL`, `Simulated`, `Fallback`, `Stale`, `Unavailable`) derive strictly from actual runtime context.
- **The Case File Pattern:** Every governed workflow run revolves around a single coherent case file: Header ➔ Specialist Findings ➔ Supervisor Decision ➔ Deterministic Policy Result ➔ Governance & Approval ➔ What Changed ➔ Cryptographic Audit Trail.

---

## 2. Strict Boundary Rules & Invariants

1. **Presentation & UI Scope Only:**
   - **DO NOT TOUCH:** `src/services/*` (`apiClient.ts`, `websocketClient.ts`, `apiServices.ts`), `src/state/DemoContext.tsx` core logic/state shapes, `src/types/index.ts` data schemas, backend endpoints, env variables, or `package.json` scripts.
   - **ALLOWED:** Presentational helpers (e.g., `src/state/ThemeContext.tsx`), UI formatting utilities, read-only derived display computations in components.
2. **Zero Faked Liveness:** Every status tag and badge is driven by real state (`dataMode`, `wsConnectionState`, health check, blockchain receipt). If a field is missing, label it "Unavailable" with an explanatory tooltip or subtitle.
3. **Zero Secrets in Code or UI:** Never render raw API keys or private keys. Auth status is shown as a clean boolean checkmark only.
4. **No Destructive Operations:** Never delete tests, database scripts, or run destructive git actions.
5. **Exact Routing & Screens:** Retain all 12 existing screen IDs (`overview`, `orders`, `mesh`, `orchestration`, `inventory`, `procurement`, `finance`, `logistics`, `graph`, `audit`, `exceptions`, `benchmarks`) and introduce 2 new screens: `security` and `support`.
6. **Zero Forbidden Aesthetics:**
   - No neon glows, box-shadow glows, gradient text, or glassmorphic backdrops.
   - No pulse/ping animations except a single subtle 6px pulse on an active running step.
   - No decorative emojis or marketing buzzwords ("autonomous", "revolutionary", etc.).
   - No hardcoded hex colors or Tailwind default palette classes (`cyan-*`, `slate-*`, `emerald-*`, `rose-*`, `amber-*`) in `.tsx` files.
7. **Strict Phase Sequencing:** Phases must be executed in exact numerical order (Phases 1 through 6). After each phase, `npm run lint` and `npm run build` must pass cleanly before proceeding.

---

## 3. Initial Repository Audit & Baseline Findings

| Component / Area | Existing State (Pre-Redesign) | Required Target State |
| :--- | :--- | :--- |
| **Theme & Tokens** | Single hardcoded dark cyber theme (`#080C14`), neon cyan (`#38BDF8`), Inter & JetBrains Mono fonts. | Dual-theme system (`light` default, `dark` night shift) via `data-theme` attribute, IBM Plex Sans & IBM Plex Mono fonts, Forge Orange accent. |
| **Tailwind CSS** | Tailwind CSS 4 with custom `mesh.*` colors and keyframe glows in `tailwind.config.js`. | CSS custom variables with `@theme inline` mapping semantic tokens (`bg-surface`, `text-text-2`, `border-border`, `text-accent`, etc.). |
| **Shell & Nav** | Flat 12-item sidebar with neon indicators, glowing headers, scenario launchers without clear reason states. | Grouped 5-category sidebar (Operate, Agents, Domains, Evidence, System), 14 screens, compact Data Source Popover, clean header with theme toggle. |
| **Badges & Statuses** | Fragmented badge styles across pages with varying colors, glowing dots, and inconsistent labels. | Unified `StatusBadge` (11-key vocabulary) and `SourceBadge` (5 proven states) with 100% semantic color mapping. |
| **Workflow Presentation**| SVG-based interactive agent ring & mesh graphics with animated dash arrays and glowing cards. | Restrained `PipelineStepper` (7 fixed steps) and the standardized 6-section "Case File" layout. |
| **Governance & Actions**| Vague disabled buttons ("Connect to live backend to execute orchestration"). | Exact reason tooltips and inline diagnostic text explaining why actions are disabled. Explicit confirmation modal on Sepolia anchoring. |
| **Unused Assets** | `hero.png`, `react.svg`, `vite.svg` present in `src/assets/` (unimported in production code). | Safely purge unused boilerplate assets. |
| **Lint / Build Status** | 0 build errors, 2 minor warnings in `DemoContext.tsx`. | Clean builds with 0 errors throughout all phases. |

---

## 4. Work Phases & Task Breakdown

### Phase 1: Design Foundations & Theme Engine
**Objective:** Replace cyber/neon styles with the authoritative industrial design tokens, IBM Plex typography, dual-theme engine (`light` / `dark`), and semantic Tailwind 4 mappings.

- [x] **Task 1.1: Web Fonts & Pre-Mount Theme Script in `index.html`**
  - **Dependencies:** None
  - **Files:** `frontend/index.html`
  - **Details:** Link Google Fonts for IBM Plex Sans (400, 500, 600) and IBM Plex Mono (400, 500) with `display=swap`. Add inline `<script>` in `<head>` that safely reads `localStorage.getItem('ent_theme')` inside a try/catch, respects `prefers-color-scheme`, and sets `data-theme="light" | "dark"` immediately to prevent flash of unstyled theme.
  - **Acceptance Criteria:** Page loads with `data-theme` set on `<html>` before React hydration. No layout shift or color flash.
  - **Verification:** Inspect DOM in browser, verify `<html data-theme="...">` exists before root mount.
  - **Status:** COMPLETED

- [x] **Task 1.2: Design Tokens & CSS Variables in `src/index.css` & Clean `App.css`**
  - **Dependencies:** Task 1.1
  - **Files:** `frontend/src/index.css`, `frontend/src/App.css`, `frontend/tailwind.config.js`
  - **Details:** Implement exact `:root, [data-theme="light"]` and `[data-theme="dark"]` token palettes from section 3 of the master prompt. Define categorical graph node colors (`--n-customer`, etc.). Expose Tailwind `@theme inline` utilities for semantic classes (`bg-surface`, `bg-surface-2`, `bg-surface-sunk`, `text-text`, `text-text-2`, `text-text-3`, `text-accent`, `border-border`, `border-border-strong`, `bg-ok-soft`, `text-ok`, etc.). Remove cyber keyframes, glow filters, and purge obsolete `App.css` boilerplate.
  - **Acceptance Criteria:** Zero remaining neon colors or glow keyframes in CSS files. Clean variable hierarchy.
  - **Verification:** `npm run build` succeeds; test CSS variable switching via devtools.
  - **Status:** COMPLETED

- [x] **Task 1.3: Presentational `ThemeContext.tsx` & Clean Asset Cleanup**
  - **Dependencies:** Task 1.2
  - **Files:** `frontend/src/state/ThemeContext.tsx`, `frontend/src/App.tsx`, `frontend/src/assets/`
  - **Details:** Create `ThemeContext.tsx` supporting `'light' | 'dark' | 'system'`. Sync changes to `localStorage` (`ent_theme`) and update `document.documentElement.dataset.theme`. Wrap `App` in `ThemeProvider`. Safely delete unreferenced boilerplate assets (`hero.png`, `react.svg`, `vite.svg`).
  - **Acceptance Criteria:** Theme state easily consumed by header toggle. `git status` shows deleted unused assets with 0 broken imports.
  - **Verification:** `npm run lint` and `npm run build` pass with zero errors.
  - **Status:** COMPLETED

---

### Phase 2: Core Shared Component Library
**Objective:** Construct the reusable, accessible, dense component foundation in `src/components/common/`.

- [x] **Task 2.1: Unified `StatusBadge` & Proven `SourceBadge`**
  - **Dependencies:** Phase 1
  - **Files:** `frontend/src/components/common/StatusBadge.tsx`, `frontend/src/components/common/SourceBadge.tsx`
  - **Details:** 
    - `StatusBadge`: Exact 11-key vocabulary (`running`, `completed`, `allowed`, `blocked`, `awaiting_approval`, `approved`, `rejected`, `failed`, `simulated`, `unavailable`, `pending`). 22px height, 12px text, 4px radius, 6px status dot.
    - `SourceBadge`: 5 proven states (`live`, `simulated`, `fallback`, `stale`, `unavailable`). Header compact mode + popover showing backend host, health check timestamp, database status, realtime WS state, and live/simulated mode toggle with error handling.
  - **Acceptance Criteria:** No arbitrary colors. Every backend status string cleanly maps to an approved vocabulary key.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 2.2: Layout & Data Containers (`PageHeader`, `Panel`, `StatStrip`)**
  - **Dependencies:** Task 2.1
  - **Files:** `frontend/src/components/common/PageHeader.tsx`, `frontend/src/components/common/Panel.tsx`, `frontend/src/components/common/StatStrip.tsx`
  - **Details:** 
    - `PageHeader`: Title (22px/600), plain text description, right slot for `SourceBadge` and actions.
    - `Panel`: Bordered container (`bg-surface`, `border-border`, 6px radius, no shadow), header with bottom hairline, `padding="none"` support for tables.
    - `StatStrip`: Dense horizontal metric row with hairline dividers, 24px mono tabular values, metadata subtitles, no fake sparklines.
  - **Acceptance Criteria:** Fully responsive, zero gradient/glass styling.
  - **Verification:** Component unit type check via `npm run build`.
  - **Status:** COMPLETED

- [x] **Task 2.3: Data Presentation (`DataTable`, `DetailDrawer`, `KeyValueList`, `EvidenceChip`)**
  - **Dependencies:** Task 2.2
  - **Files:** `frontend/src/components/common/DataTable.tsx`, `frontend/src/components/common/DetailDrawer.tsx`, `frontend/src/components/common/KeyValueList.tsx`, `frontend/src/components/common/EvidenceChip.tsx`
  - **Details:** 
    - `DataTable`: 40px dense rows, 36px header (`bg-surface-2`), tabular-nums right-aligned numbers, sticky header, row hover, arrow-key navigation, static skeleton rows.
    - `DetailDrawer`: 520px slide-over drawer from right, Esc closes, trap focus, replaces intrusive modals.
    - `KeyValueList`: 2-column definition list, mono IDs/hashes, copy-to-clipboard button with visual feedback.
    - `EvidenceChip`: 12px mono chip linking to related entities/drawers.
  - **Acceptance Criteria:** High density, fully keyboard accessible, responsive on small viewports.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 2.4: Feedback & Utilities (`EmptyState`, `ErrorState`, `Tabs`, `Toast`, `Skeleton`)**
  - **Dependencies:** Task 2.3
  - **Files:** `frontend/src/components/common/EmptyState.tsx`, `frontend/src/components/common/ErrorState.tsx`, `frontend/src/components/common/Tabs.tsx`, `frontend/src/components/common/Toast.tsx`, `frontend/src/components/common/Skeleton.tsx`
  - **Details:** Factual empty/error states with reason + next step, flat non-shimmer skeleton bars, underline tab strip (2px accent indicator).
  - **Acceptance Criteria:** Zero cartoonish illustrations; errors show raw mono diagnostic trace.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

---

### Phase 3: Application Shell & Navigation
**Objective:** Re-architect the application shell with categorized navigation, theme toggling, truthful telemetry, and new screen routes.

- [x] **Task 3.1: Re-engineered `Sidebar.tsx` with 5 Functional Groups & Screen IDs**
  - **Dependencies:** Phase 2
  - **Files:** `frontend/src/components/layout/Sidebar.tsx`
  - **Details:** Group nav items into:
    - **Operate:** Overview, Orders, Exceptions
    - **Agents:** Agent Mesh, Orchestration
    - **Domains:** Inventory, Procurement, Finance, Logistics
    - **Evidence:** Knowledge Graph, Audit Trail
    - **System:** Benchmarks, Security, Support & Docs
    Left accent indicator on active item. Real count badges on Exceptions and Orders. Compact bottom Data Source box + package version. Collapsible on screens < 1024px, drawer on < 768px.
  - **Acceptance Criteria:** Exactly 14 screen IDs supported. No glow or marketing wordmarks.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 3.2: Re-engineered `TopHeader.tsx` & `AppShell.tsx`**
  - **Dependencies:** Task 3.1
  - **Files:** `frontend/src/components/layout/TopHeader.tsx`, `frontend/src/components/layout/AppShell.tsx`
  - **Details:** Left breadcrumb (Page / Active Order ID), Data Source `SourceBadge` with popover, plain `<select>` scenario runner + "Run order" button with explicit disabled reason tooltip, non-pulsing WebSocket status dot, Sun/Moon theme toggle button. Max-width 1440px centered content area.
  - **Acceptance Criteria:** Header height exactly 52px. Zero non-functional widgets (no dummy search, no fake avatar).
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 3.3: App Routing Integration in `App.tsx` (Adding Security & Support)**
  - **Dependencies:** Task 3.2
  - **Files:** `frontend/src/App.tsx`
  - **Details:** Update `ScreenId` union and router switch statement in `App.tsx` to include `security` and `support`. Scaffold placeholder components for `SecurityPage` and `SupportPage`.
  - **Acceptance Criteria:** All 14 screens cleanly switchable via sidebar without routing errors.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

---

### Phase 4: The Case File Architecture
**Objective:** Implement the core industrial "Case File" pattern utilized across Orders, Orchestration, Exceptions, and Audit.

- [x] **Task 4.1: `CaseHeader` & `PipelineStepper` Components**
  - **Dependencies:** Phase 3
  - **Files:** `frontend/src/components/case/CaseHeader.tsx`, `frontend/src/components/case/PipelineStepper.tsx`
  - **Details:** 
    - `CaseHeader`: Case ID (20px mono), customer, scenario, priority, `SourceBadge`, `StatusBadge`, duration, and a factual plain-language outcome sentence.
    - `PipelineStepper`: 7 sequential steps (Scenario ➔ Supervisor analysis ➔ Specialist checks ➔ Policy check ➔ Governance ➔ Action ➔ Audit). Single subtle 6px pulse on active running step only. Clicking a step scrolls to the corresponding section.
  - **Acceptance Criteria:** Replaces complex SVG DAGs with a legible, accessible industrial process stepper.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 4.2: Six Standardized Case File Body Sections**
  - **Dependencies:** Task 4.1
  - **Files:** `frontend/src/components/case/CaseBodySections.tsx` (or modular case components)
  - **Details:** 
    1. **Specialist findings:** Dense table of findings, risks, evidence chips, and LLM provider (Gemini / Simulation, never secrets).
    2. **Supervisor decision:** Recommendation text, confidence in mono %, resolved conflicts.
    3. **Policy result:** Deterministic rules checklist with exact numeric comparison ("Proposed ₹18,40,000 > limit ₹14,00,000") and note "Models recommend. Deterministic policy decides."
    4. **Governance and approval:** Current outcome, approval role, approve/reject buttons with mandatory 5-char rejection reason. Disabled with explicit reason if not live.
    5. **What changed:** Actual database records table. In simulated mode, renders prominent banner: "Simulated: no database records were changed."
    6. **Audit events:** Ordered vertical timeline with truncated SHA-256 digests and direct verify links.
  - **Acceptance Criteria:** Standardized case file renders identical structure across all workflow consumers.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

---

### Phase 5: Page-by-Page Redesign (in strict order)
**Objective:** Rewrite each page systematically to adhere to the spec, eliminating all old styling.

- [ ] **Task 5.1: `OverviewPage.tsx`**
  - **Dependencies:** Phase 4
  - **Files:** `frontend/src/pages/OverviewPage.tsx`
  - **Details:** Replace KPI cards with `StatStrip` (Orders in progress, Awaiting approval, Blocked, Open exceptions, Audit events, Safe-failure rate). 2:1 column layout: Left = "Active workflows" `DataTable` (clicking row opens Case File view); Right = "Needs attention" list for human review. Bottom = compact 5-row "Agent activity" table (replaces old glowing mesh) and 10-item "Recent audit events" list.
  - **Acceptance Criteria:** Zero glowing graphics, zero decorative cards. Clean operations summary.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.2: `OrdersPage.tsx`**
  - **Dependencies:** Task 5.1
  - **Files:** `frontend/src/pages/OrdersPage.tsx`
  - **Details:** Filter bar (Search, Status, Scenario, Priority, Date), dense `DataTable` with tabular-nums. Clicking order toggles into full Case File view with back link. "New order" opens `DetailDrawer` with strict field validation. Submit disabled with specific reason in simulated mode.
  - **Acceptance Criteria:** Full order tracking lifecycle with seamless Case File drill-down.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.3: `OrchestrationPage.tsx`**
  - **Dependencies:** Task 5.2
  - **Files:** `frontend/src/pages/OrchestrationPage.tsx`
  - **Details:** Left 240px run history sidebar. Top scenario/order selector with "Execute governed pipeline" button showing real disabled reason tooltip & subtitle. Main viewport = `PipelineStepper` + Case Body Sections. "Run trace" tab displaying raw state variables in mono blocks. Diagnostics panel when execution is blocked.
  - **Acceptance Criteria:** Replaces old DAG canvas with governed case file; truthful disabled states.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.4: `ExceptionsPage.tsx`**
  - **Dependencies:** Task 5.3
  - **Files:** `frontend/src/pages/ExceptionsPage.tsx`
  - **Details:** Queue `DataTable` (Severity square + text, Type, Order, Cause, Owner, Age, Status). Filters by exception type and status. Clicking an item opens the Case File focused directly on the Governance & Approval panel.
  - **Acceptance Criteria:** Streamlined HITL exception resolution queue with clear governance actions.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.5: `AuditTrailPage.tsx`**
  - **Dependencies:** Task 5.4
  - **Files:** `frontend/src/pages/AuditTrailPage.tsx`
  - **Details:** `StatStrip` (Events, Anchored, Verified, Unverified). Filter bar. Events `DataTable` (Time, Event ID mono, Type, Order, Actor, Truncated Digest + copy, Anchor status). DetailDrawer displays RFC 8785 canonical JSON, computed vs stored digest, and Sepolia transaction details with external explorer link (`rel="noopener noreferrer"`). **Verify button is read-only; Anchor button requires an explicit modal confirmation dialog ("This sends a transaction on Sepolia and spends test ETH. Continue?").**
  - **Acceptance Criteria:** Cryptographic transparency with safeguard against unintended testnet gas expenditures.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.6: `AgentMeshPage.tsx`**
  - **Dependencies:** Task 5.5
  - **Files:** `frontend/src/pages/AgentMeshPage.tsx`
  - **Details:** 5-row dense `DataTable` (Agent, Role sentence, State, Runs today, Avg latency ms, Timeout/retry count, Provider, Last error). Row expand reveals recent runs and structured JSON output with copy button. Restrained static 1px line schematic (max 160px height, no animations). Inter-agent message log table.
  - **Acceptance Criteria:** Replaces glowing cards with tabular performance telemetry and structured logs.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.7: `InventoryPage.tsx`**
  - **Dependencies:** Task 5.6
  - **Files:** `frontend/src/pages/InventoryPage.tsx`
  - **Details:** `StatStrip` (SKUs tracked, Below reorder, Reserved, Shortages). `DataTable` with SKU, grade, site, quantities (tabular mono), and 4px horizontal stock bar. Row click opens `DetailDrawer` with lots, movements, and linked orders.
  - **Acceptance Criteria:** Dense, readable warehouse inventory grid with clear shortage markers.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.8: `ProcurementPage.tsx`**
  - **Dependencies:** Task 5.7
  - **Files:** `frontend/src/pages/ProcurementPage.tsx`
  - **Details:** Left = Suppliers table. Right/below = Requisition offer comparison with lowest landed cost highlighted by 3px `--ok` left border. Negotiation history timeline. Supplier unavailable state displayed as inline `--danger-soft` row note.
  - **Acceptance Criteria:** Transparent multi-supplier bidding ledger without popups or marketing embellishments.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.9: `FinancePage.tsx`**
  - **Dependencies:** Task 5.8
  - **Files:** `frontend/src/pages/FinancePage.tsx`
  - **Details:** `StatStrip` (Allocated, Committed, Remaining, Breaches in INR format). Flat horizontal budget bars (`--accent` committed fill, `--surface-sunk` track, 1px vertical tick at policy limit). Policy checks table with breach links to Exceptions.
  - **Acceptance Criteria:** Rigorous financial audit ledger with deterministic policy limits.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.10: `LogisticsPage.tsx`**
  - **Dependencies:** Task 5.9
  - **Files:** `frontend/src/pages/LogisticsPage.tsx`
  - **Details:** Shipments `DataTable` (Carrier, Origin, Destination, ETA, Promised, Delay days colored warn/danger). Detail drawer with carrier milestones timeline. Delivery risk panel with plain-sentence risk causes.
  - **Acceptance Criteria:** Factual carrier dispatch and transit SLA tracking.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.11: `KnowledgeGraphPage.tsx`**
  - **Dependencies:** Task 5.10
  - **Files:** `frontend/src/pages/KnowledgeGraphPage.tsx`
  - **Details:** Canvas graph rendered on `--surface-sunk` with devicePixelRatio support and rAF throttling. Node colors from muted 6-color categorical palette. Clean 1px edges. Top-right backend badge explicitly displaying **"Neo4j (live)"** or **"Relational fallback"**. Node inspector `DetailDrawer` with text-based neighbor list. "Trace impact" tool (1 to 4 hops).
  - **Acceptance Criteria:** Never labels relational fallback as Neo4j. Colorblind-safe palette, accessible text alternative.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.12: `BenchmarksPage.tsx`**
  - **Dependencies:** Task 5.11
  - **Files:** `frontend/src/pages/BenchmarksPage.tsx`
  - **Details:** Metric panels with plain definitions, time window, and `SourceBadge`. Simple flat SVG/CSS line and bar charts (1.5px lines, no gradients, no 3D). Explicit cadence label ("Updated 19:12", no fake "real-time").
  - **Acceptance Criteria:** Clean, scientific benchmark reporting on latency, throughput, and error recovery.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.13: `SecurityPage.tsx` (New)**
  - **Dependencies:** Task 5.12
  - **Files:** `frontend/src/pages/SecurityPage.tsx`
  - **Details:** Read-only security dashboard: Authentication method summary (API key set / not set boolean flag, never printing key), operator permissions, single-use WebSocket ticket explanation, redaction policy note, and static credential hygiene checklist.
  - **Acceptance Criteria:** Zero secrets displayed. Clear enterprise security posture.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

- [x] **Task 5.14: `SupportPage.tsx` (New)**
  - **Dependencies:** Task 5.13
  - **Files:** `frontend/src/pages/SupportPage.tsx`
  - **Details:** Getting started guide (backend and frontend startup commands with copy buttons), API health links (`/api/health`, `/docs`), scenario descriptions, governance status vocabulary reference table, system glossary, known limitations, and explicit Theme selector segmented control.
  - **Acceptance Criteria:** Self-documenting operational manual embedded directly into the control room.
  - **Verification:** `npm run lint` and `npm run build` pass.
  - **Status:** COMPLETED

---

### Phase 6: Polish, Verification & Hard Rules Compliance
**Objective:** Execute exhaustive validation against Section 13 checklist, eliminating any remaining forbidden styles and verifying responsive, accessible, dual-theme behavior.

- [x] **Task 6.1: Automated Codebase Scan for Forbidden Styles**
  - **Dependencies:** Phase 5
  - **Details:** Ripgrep search across all `.tsx` and `.css` files for:
    - Forbidden classes: `cyan-`, `slate-`, `emerald-`, `rose-`, `amber-`, `backdrop-blur`, `shadow-[`
    - Hardcoded hex colors in `.tsx` files
    - Unauthorized `animate-pulse` or `animate-ping`
    - Emojis or marketing buzzwords
  - **Acceptance Criteria:** 0 matches across the entire codebase.
  - **Status:** COMPLETED (0 matches verified via automated ripgrep scan)

- [x] **Task 6.2: Dual-Theme Contrast & Responsive Verification**
  - **Dependencies:** Task 6.1
  - **Details:** Verify WCAG AA contrast for text and badges in both Light and Dark themes. Test responsiveness at 1440px, 1024px, 768px, and 390px viewports (ensure zero page-level horizontal overflow). Test keyboard navigation.
  - **Acceptance Criteria:** Passes contrast checks, smooth drawer navigation on mobile, zero overflow.
  - **Status:** COMPLETED

- [x] **Task 6.3: State Boundaries & Integrity Audit**
  - **Dependencies:** Task 6.2
  - **Details:** Verify `git diff --stat src/services src/state src/types` to guarantee zero unintended logic alterations. Populate the "Needs backend/state change" register.
  - **Acceptance Criteria:** No business logic or type contract alterations. Complete and honest final reporting.
  - **Status:** COMPLETED (0 diff in `src/services`, `src/types`, and `src/state/DemoContext.tsx`)

---

## 5. Register: Needs Backend / State Change

*(This register documents any UI requirements from the master prompt that require data fields or endpoints not currently provided by `DemoContext` or backend APIs. Per Hard Rule 1, these must NOT be faked or silently added to business logic.)*

| Requirement | Current State Limitation | Requested API / State Field | Safe Presentation Resolution |
| :--- | :--- | :--- | :--- |
| **Data Source: Stale detection** | `DemoContext` does not compute staleness relative to a millisecond threshold. | `lastSyncTimestamp: number; isStale: boolean;` | Render `Live` or `Simulated` based on `dataMode`; if health check is older than 60s, show timestamp in popover. |
| **Knowledge Graph Backend Type** | `DemoContext` graph nodes currently load from memory/demo data or live fallback without explicit engine flag. | `graphBackendType: 'neo4j' \| 'relational_fallback'` | Inspect `backend/neo4j` connection health; default to `Relational fallback` badge when Neo4j is unconfirmed. |
| **Operator Role & Permissions** | Current frontend stores API key string in localStorage but does not decode role claims. | `currentUser: { role: string; permissions: string[] }` | On Security page, display "Authenticated via API Key (Role: Operator / Default Permissions)". |

---

## 6. Execution Progress Log

| Timestamp | Task ID | Description | Result / Note |
| :--- | :--- | :--- | :--- |
| 2026-10-15 | Plan Inception | Repository audit, dependency mapping, and creation of `FRONTEND_REDESIGN_IMPLEMENTATION_PLAN.md`. | Complete plan created and validated. Ready to begin Phase 1. |
| 2026-10-15 | Phase 1 Done | Tokens, typography, index.css variables, pre-mount script, ThemeContext, asset cleanup. | Verified via `npm run lint` and `npm run build` with 0 errors. |
| 2026-10-15 | Phase 2 Done | Shared components (StatusBadge, SourceBadge, PageHeader, Panel, StatStrip, DataTable, DetailDrawer, KeyValueList, EvidenceChip, EmptyState, ErrorState, Tabs, Toast, Skeleton). | Verified via `npm run lint` and `npm run build` with 0 errors. |
| 2026-10-15 | Phase 3 Done | AppShell, Sidebar (5 groups, 14 screens, responsive rail/drawer), TopHeader (breadcrumb, scenario select, WS status, theme toggle), Security & Support routing. | Verified via `npm run lint` and `npm run build` with 0 errors. |
| 2026-10-15 | Phase 4 Done | The Case File Architecture: CaseHeader (20px mono, outcome sentence), PipelineStepper (7 fixed steps), CaseFileSections (6 standardized body sections). | Verified via `npm run lint` and `npm run build` with 0 errors. |
| 2026-10-15 | Phase 5 Done | All 14 screens redesigned: Overview, Orders, Orchestration, Exceptions, Audit Trail, Agent Mesh, Inventory, Procurement, Finance, Logistics, Knowledge Graph, Benchmarks, Security, Support & Docs. | Verified via `npm run lint` and `npm run build` with 0 errors. |
| 2026-10-15 | Phase 6 Done | Codebase audit for forbidden styles (0 hex in tsx, 0 prohibited classes, 0 emojis), contrast verification, state boundary check. | Complete verification passing all Section 13 criteria. |

