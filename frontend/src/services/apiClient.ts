/**
 * Centralized Typed API Client for Enterprise AI Mesh Backend.
 *
 * Connects React frontend directly to FastAPI + PostgreSQL endpoints:
 * - Orders, Inventory, Suppliers
 * - Workflows and Agent Runs
 * - Scheduler Status & Cycle Triggers
 * - Deterministic Policy Evaluations & Approvals
 * - Controlled Action Queue Proposals & Executions
 * - Audit Event Log & Blockchain Integrity Verification
 */

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000';

const API_KEY =
  (import.meta.env.VITE_API_KEY as string) ||
  (typeof window !== 'undefined' ? localStorage.getItem('ent_api_key') || '' : '');

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
    ...(options.headers as Record<string, string>),
  };

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errorData: any = {};
      try {
        errorData = await res.json();
      } catch {
        errorData = { message: res.statusText };
      }
      throw new ApiError(
        errorData.detail || errorData.message || `HTTP ${res.status}`,
        res.status,
        errorData
      );
    }

    return await res.json();
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(err.message || 'Network error connecting to backend', 0);
  }
}

// ── Models ─────────────────────────────────────────────────────────────────

export interface BackendOrder {
  order_id: string;
  customer_name: string;
  order_status: string;
  status?: string;
  order_date: string;
  priority: string;
  total_amount_inr?: number;
  currency?: string;
}

export interface BackendOrderSummary {
  total_orders: number;
  processing_count: number;
  completed_count: number;
  exception_count: number;
}

export interface BackendInventoryItem {
  inventory_id: string;
  item_id: string;
  item_name: string;
  warehouse_id: string;
  on_hand_qty: number;
  reserved_qty: number;
  available_qty: number;
  safety_stock_qty: number;
  reorder_point_qty: number;
  stock_status: 'OK' | 'LOW_STOCK' | 'REORDER_REQUIRED';
}

export interface BackendInventorySummary {
  total_skus: number;
  total_on_hand: number;
  total_available: number;
  reorder_required_count: number;
  low_stock_count: number;
}

export interface BackendSupplier {
  id?: string;
  supplier_id: string;
  name?: string;
  supplier_name: string;
  supplier_category?: string;
  category?: string;
  status: string;
  risk_band?: string;
  historical_on_time_rate?: number;
  reliability_score?: number;
  score?: number;
  default_lead_time_hours?: number;
  delivery_days?: number;
  deliveryDays?: number;
  price_per_unit?: number;
  pricePerUnit?: number;
  availability?: number;
  notes?: string;
  contracts_count?: number;
  offers_count?: number;
  is_active?: boolean;
  lead_time_days?: number;
  rating?: number;
  contact_email?: string;
}

export interface BackendSchedulerStatus {
  scheduler_name: string;
  configured_interval_seconds: number;
  interval_seconds?: number;
  status?: string;
  is_locked: boolean;
  is_running?: boolean;
  locked_by: string | null;
  lock_acquired_at?: string | null;
  lease_expires_at: string | null;
  last_run_at?: string | null;
  last_scheduled_at?: string | null;
  last_status: string | null;
  last_skip_reason?: string | null;
  open_scenarios_count?: number;
  max_open_scenarios?: number;
  total_runs: number;
  consecutive_failures: number;
  active_leases_count?: number;
}

export interface BackendScenarioTemplate {
  template_id: string;
  scenario_template_id: string;
  scenario_type: string;
  domain: string;
  severity: string;
  description: string;
  injection_method: string;
  agents_involved: string;
  expected_response: string;
  guardrail: string;
}

export interface BackendScenarioInstance {
  scenario_id: string;
  template_id: string;
  scenario_template_id: string;
  scheduled_at: string | null;
  created_at: string | null;
  status: string;
  severity: string;
  linked_order_id: string | null;
  linked_batch_id: string | null;
  input_overlay: Record<string, any>;
  idempotency_key: string;
  updated_at: string | null;
}

export interface BackendApprovalRequest {
  approval_id: string;
  action_id?: string;
  decision_id?: string;
  scenario_id?: string;
  requested_at: string;
  required_domain?: string;
  domain?: string;
  required_role?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | string;
  decided_by?: string;
  decided_at?: string;
  reason?: string;
  requested_amount?: number;
  threshold_amount?: number;
}

export interface BackendActionRecord {
  action_id: string;
  scenario_id: string;
  decision_id?: string;
  action_type: string;
  target_entity_id?: string;
  payload: Record<string, any>;
  status: 'PROPOSED' | 'APPROVED' | 'REJECTED' | 'EXECUTING' | 'SUCCEEDED' | 'FAILED' | 'COMPLETED' | string;
  requires_approval: boolean;
  approved_by?: string;
  created_at: string;
  executed_at?: string;
  result?: any;
  idempotency_key: string;
}

export interface BackendAuditEvent {
  event_id: string;
  eventId?: string;
  event_type: string;
  event?: string;
  type?: string;
  timestamp?: string;
  event_timestamp?: string;
  entity_type?: string;
  entity_id?: string;
  order_id?: string;
  orderId?: string;
  actor_type?: string;
  actor_id?: string;
  actor?: string;
  status: string;
  blockchain_status?: string;
  block_number?: number;
  blockNumber?: number;
  tx_hash?: string;
  txHash?: string;
  details?: string;
  note?: string;
  reason_code?: string;
  payload_hash?: string;
  created_at?: string;
  event_digest?: string;
}

export interface BackendAuditVerification {
  event_id: string;
  matched: boolean;
  verified?: boolean;
  computed_hash: string;
  computed_digest?: string;
  anchored_hash?: string;
  verification_status: string;
  confirmation_status?: string;
  block_number?: number;
  transaction_hash?: string;
  details: string;
}

export interface BackendPolicyRule {
  rule_id: string;
  domain: string;
  rule_name: string;
  condition_expression: string;
  failure_action: string;
  enabled: boolean;
}

export interface OrchestrationAgentStep {
  agent_name: string;
  phase: string;
  status: string;
  deterministic_output: Record<string, any>;
  llm_recommendation?: Record<string, any>;
  llm_reasoning?: string;
  llm_confidence?: number;
  is_simulation: boolean;
  agent_run_id?: string;
  duration_ms?: number;
  evidence_refs: Record<string, any>[];
  error?: string;
  error_code?: string;
}

export interface OrchestrationResult {
  correlation_id: string;
  workflow_id: string;
  scenario_id?: string;
  order_id: string;
  status: string;
  provider_mode: string;
  phases_completed: string[];
  agent_steps: OrchestrationAgentStep[];
  steps?: Record<string, any>;
  governance: Record<string, any>;
  decision_summary?: string;
  decision_code?: string;
  human_approval_required: boolean;
  recommended_action?: Record<string, any>;
  action_result?: Record<string, any>;
  conflicts?: string[];
  missing_evidence?: string[];
  proposed_next_step?: string;
  can_retry?: boolean;
  total_duration_ms?: number;
  started_at: string;
  completed_at?: string;
  error?: string;
  error_code?: string;
}

export interface ProviderInfo {
  mode: string;
  model_name: string;
  is_simulation: boolean;
  description: string;
}

// ── API Services ───────────────────────────────────────────────────────────

export const apiClient = {
  // System Health
  checkHealth: () => apiFetch<{ status: string }>('/api/health'),
  checkLive: () => apiFetch<{ status: string }>('/api/live'),

  // Orders
  getOrders: (limit = 100, status?: string) =>
    apiFetch<BackendOrder[]>(
      `/api/orders/?limit=${limit}${status && status !== 'All' ? `&status=${status}` : ''}`
    ),
  getOrderSummary: () => apiFetch<BackendOrderSummary>('/api/orders/summary'),

  // Inventory
  getInventoryItems: (limit = 100) =>
    apiFetch<BackendInventoryItem[]>(`/api/inventory/items?limit=${limit}`),
  getInventorySummary: () =>
    apiFetch<BackendInventorySummary>('/api/inventory/summary'),

  // Suppliers
  getSuppliers: (limit = 100) =>
    apiFetch<BackendSupplier[]>(`/api/suppliers/?limit=${limit}`),

  // Scheduler & Scenarios
  getSchedulerStatus: () =>
    apiFetch<BackendSchedulerStatus>('/api/scheduler/status'),
  getSchedulerTemplates: () =>
    apiFetch<BackendScenarioTemplate[]>('/api/scheduler/templates'),
  getSchedulerScenarios: (limit = 50, status?: string, offset = 0) => {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    if (offset > 0) params.append('offset', offset.toString());
    if (status && status !== 'ALL') params.append('status', status);
    return apiFetch<BackendScenarioInstance[]>(
      `/api/scheduler/scenarios?${params.toString()}`
    );
  },
  triggerScheduler: (force = false, templateId?: string, idempotencyKey?: string, seed?: number) => {
    const params = new URLSearchParams();
    if (force) params.append('force', 'true');
    if (templateId) params.append('template_id', templateId);
    if (idempotencyKey) params.append('idempotency_key', idempotencyKey);
    if (seed !== undefined) params.append('seed', seed.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    return apiFetch<{ executed: boolean; status: string; scenario_id?: string; reason?: string; last_skip_reason?: string; leases_acquired?: number }>(
      `/api/scheduler/trigger${query}`,
      { method: 'POST' }
    );
  },

  // Policies & Approvals
  getPolicyRules: () => apiFetch<BackendPolicyRule[]>('/api/policies/rules'),
  getApprovals: (status = 'PENDING') =>
    apiFetch<BackendApprovalRequest[]>(`/api/approvals/?status=${status}`),
  decideApproval: (
    approvalId: string,
    decision: 'APPROVED' | 'REJECTED',
    decidedBy = 'control_room_operator',
    reason = 'Approved from Control Room Console'
  ) =>
    apiFetch<BackendApprovalRequest>(`/api/approvals/${approvalId}/decision`, {
      method: 'POST',
      body: JSON.stringify({
        status: decision,
        decided_by: decidedBy,
        reason,
      }),
    }),

  // Actions
  getActions: (limit = 50, status?: string) =>
    apiFetch<BackendActionRecord[]>(
      `/api/actions/?limit=${limit}${status ? `&status=${status}` : ''}`
    ),
  executeAction: (actionId: string) =>
    apiFetch<BackendActionRecord>(`/api/actions/${actionId}/execute`, {
      method: 'POST',
    }),

  // Audit & Blockchain
  getAuditEvents: (limit = 50) =>
    apiFetch<BackendAuditEvent[]>(`/api/audit/events?limit=${limit}`),
  verifyAuditEvent: (eventId: string, payload: Record<string, any> = {}) =>
    apiFetch<BackendAuditVerification>(`/api/audit/verify/${eventId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Governed Orchestration (Phase 4)
  executeOrchestration: (orderId = 'ORD-1042', templateId = 'TPL-010', severity = 'MEDIUM', idempotencyKey?: string) => {
    const params = new URLSearchParams({
      order_id: orderId,
      template_id: templateId,
      severity,
    });
    if (idempotencyKey) params.append('idempotency_key', idempotencyKey);
    return apiFetch<OrchestrationResult>(`/api/orchestration/execute?${params.toString()}`, {
      method: 'POST',
    });
  },
  runOrchestrationForWorkflow: (workflowId: string) =>
    apiFetch<OrchestrationResult>(`/api/orchestration/${workflowId}/run`, {
      method: 'POST',
    }),
  retryOrchestration: (workflowId: string) =>
    apiFetch<OrchestrationResult>(`/api/orchestration/${workflowId}/retry`, {
      method: 'POST',
    }),
  getOrchestration: (workflowId: string) =>
    apiFetch<any>(`/api/orchestration/${workflowId}`),
  getWorkflowAgents: (workflowId: string) =>
    apiFetch<any[]>(`/api/orchestration/${workflowId}/agents`),
  getWorkflowGovernance: (workflowId: string) =>
    apiFetch<any>(`/api/orchestration/${workflowId}/governance`),
  getProviderInfo: () =>
    apiFetch<ProviderInfo>('/api/orchestration/providers'),
};
