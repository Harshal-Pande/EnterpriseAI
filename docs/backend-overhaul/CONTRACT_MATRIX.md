# Frontend-to-Backend Contract Matrix (Phase P1)

This matrix maps every API call made by the redesigned frontend (`frontend/src/services/apiClient.ts`, `state/DemoContext.tsx`, `types/index.ts`) against the FastAPI backend (`backend/app/main.py`, `backend/app/api/*.py`).

| Area | Frontend Method & Path | Expected Request / Query | Expected Response Fields | Backend Target Route | Match Status | Notes |
|---|---|---|---|---|---|---|
| **Health** | `GET /api/health` | None | `{status: string}` | `GET /api/health` | **MATCH** | 200 OK |
| **Health** | `GET /api/live` | None | `{status: string}` | `GET /api/live` | **MATCH** | Liveness probe called by `DemoContext.tsx` |
| **Health** | `GET /api/health/ready` | None | `{status: string, database: object}` | `GET /api/health/ready` | **SHAPE (Needs Subsystems)** | Need to enrich with per-subsystem objects |
| **Orders** | `GET /api/orders/?limit=100` | `limit`, `status` | `BackendOrder[]` | `GET /api/orders/` | **MATCH** | 200 items in DB |
| **Orders** | `GET /api/orders/summary` | None | `{total_orders, processing_count, completed_count, exception_count}` | `GET /api/orders/summary` | **MATCH** | Calculated via SQL filter counts |
| **Orders** | `GET /api/orders/{order_id}` | Path: `order_id` | `Order` with lines | `GET /api/orders/{order_id}` | **MATCH** | Single order with lines |
| **Inventory** | `GET /api/inventory/items?limit=100` | `limit` | `BackendInventoryItem[]` | `GET /api/inventory/items` | **MATCH** | Returns inventory rows |
| **Inventory** | `GET /api/inventory/summary` | None | `{total_skus, total_on_hand_mt, low_stock_alerts, total_valuation_inr}` | `GET /api/inventory/summary` | **MATCH** | Inventory aggregations |
| **Suppliers** | `GET /api/suppliers/?limit=100` | `limit` | `BackendSupplier[]` | `GET /api/suppliers/` | **MATCH** | Returns suppliers with reliability score |
| **Suppliers** | `GET /api/suppliers/{supplier_id}` | Path: `supplier_id` | `Supplier` detail with contracts/offers | `GET /api/suppliers/{supplier_id}` | **MATCH** | Detailed supplier profile |
| **Scheduler** | `GET /api/scheduler/status` | None | `BackendSchedulerStatus` | `GET /api/scheduler/status` | **MATCH** | Active status, lease, runs |
| **Scheduler** | `GET /api/scheduler/templates` | None | `BackendScenarioTemplate[]` | `GET /api/scheduler/templates` | **MATCH** | 15 scenario templates |
| **Scheduler** | `GET /api/scheduler/scenarios?limit=50` | `limit`, `status`, `offset` | `BackendScenarioInstance[]` | `GET /api/scheduler/scenarios` | **MATCH** | Scenario queue |
| **Scheduler** | `POST /api/scheduler/trigger` | `force`, `template_id`, `idempotency_key`, `seed` | `{executed, status, scenario_id}` | `POST /api/scheduler/trigger` | **MATCH** | Injects scenario instance |
| **Policies** | `GET /api/policies/rules` | None | `BackendPolicyRule[]` | `GET /api/policies/rules` | **MATCH** | 10 business rules |
| **Approvals** | `GET /api/approvals/?status=PENDING` | `status` | `BackendApprovalRequest[]` | `GET /api/approvals/` | **MATCH** | Returns approval requests |
| **Approvals** | `POST /api/approvals/{id}/decision` | Body: `{status, decided_by, reason}` | `BackendApprovalRequest` | `POST /api/approvals/{id}/decision` | **MATCH** | Decides approval |
| **Actions** | `GET /api/actions/?limit=50` | `limit`, `status` | `BackendActionRecord[]` | `GET /api/actions/` | **MATCH** | Governed action queue |
| **Actions** | `POST /api/actions/{id}/execute` | Path: `id` | `BackendActionRecord` | `POST /api/actions/{id}/execute` | **MATCH** | Executes governed action |
| **Audit** | `GET /api/audit/events?limit=50` | `limit` | `BackendAuditEvent[]` | `GET /api/audit/events` | **MATCH** | Returns event log |
| **Audit** | `GET /api/audit/blockchain/status` | None | `BackendBlockchainStatus` | `GET /api/audit/blockchain/status` | **MATCH** | Sepolia anchor status |
| **Audit** | `POST /api/audit/anchor` | Body: `{event_id, payload}` | `BackendAnchorRecord` | `POST /api/audit/anchor` | **MATCH** | Anchors event digest |
| **Audit** | `POST /api/audit/verify/{id}` | Path: `id`, Body: `payload` | `BackendAuditVerification` | `POST /api/audit/verify/{id}` | **MATCH** | Verifies canonical digest |
| **Orchestration** | `POST /api/orchestration/execute` | `order_id`, `template_id`, `severity` | `OrchestrationResult` | `POST /api/orchestration/execute` | **MATCH** | Executes GovernedOrchestrator pipeline |
| **Orchestration** | `GET /api/orchestration/providers` | None | `ProviderInfo` | `GET /api/orchestration/providers` | **MATCH** | Provider configuration info |
| **Orchestration** | `GET /api/orchestration/{id}` | Path: `id` | `{workflow_id, status, ...}` | `GET /api/orchestration/{workflow_id}` | **MATCH** | Workflow detail |
| **Orchestration** | `GET /api/orchestration/{id}/agents` | Path: `id` | `any[]` | `GET /api/orchestration/{id}/agents` | **MATCH** | Specialist agent runs |
| **Orchestration** | `GET /api/orchestration/{id}/governance`| Path: `id` | `any` | `GET /api/orchestration/{id}/governance`| **MATCH** | Governance policy checks |
| **Realtime** | `POST /api/ws/ticket` | None | `{ticket, expires_in, user_id, role}` | `POST /api/ws/ticket` | **MATCH** | Single-use WS auth ticket |
| **Graph** | `GET /api/graph` | `type`, `q`, `limit` | `BackendGraphResponse` | `GET /api/graph` | **MATCH** | RelationalGraphEngine nodes/edges |
| **Graph** | `GET /api/graph/status` | None | `BackendGraphStatus` | `GET /api/graph/status` | **MATCH** | Graph engine status |
| **Graph** | `POST /api/graph/impact` | Body: `DisruptionImpactRequest` | `DisruptionImpactResponse` | `POST /api/graph/impact` | **MATCH** | Downstream blast radius |
| **Graph** | `POST /api/graph/sync` | None | `{status, synced_nodes, ...}` | `POST /api/graph/sync` | **MATCH** | Idempotent sync |
| **Graph** | `GET /api/graph/provenance/{id}` | Path: `id`, `depth` | `BackendGraphResponse` | `GET /api/graph/provenance/{id}` | **MATCH** | Entity provenance subgraph |
| **Case File** | `/api/cases/{workflow_id}` | Path: `workflow_id` | Aggregated 7-step Case File | Missing | **MISSING (To add in P10)** | Dedicated aggregate endpoint |
| **Exceptions** | `/api/exceptions` | `status`, `severity`, `limit` | `ExceptionItem[]` | Missing | **MISSING (To add in P10)** | Dedicated queue endpoint |
| **Telemetry** | `/api/agents/telemetry` | None | Per-agent telemetry metrics | Missing | **MISSING (To add in P10)** | Agent mesh telemetry |
| **Benchmarks** | `/api/benchmarks/metrics` | None | System performance benchmarks | Missing | **MISSING (To add in P10)** | System benchmarks |
