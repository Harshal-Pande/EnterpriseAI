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
  (typeof window !== 'undefined' ? localStorage.getItem('ent_api_key') || 'dev-operator-key' : 'dev-operator-key');

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

export interface CreateOrderLineRequest {
  product_id: string;
  requested_qty: number;
  unit_price_inr?: number;
  uom?: string;
}

export interface CreateOrderRequest {
  order_id?: string;
  customer_ref: string;
  entity_id: string;
  priority?: string;
  required_delivery_at?: string;
  external_reference?: string;
  lines: CreateOrderLineRequest[];
}

export interface OrderCreateResponse {
  order_id: string;
  customer_ref: string;
  entity_id: string;
  status: string;
  priority: string;
  line_count: number;
  total_amount_inr: number;
  queue_position: number;
  message: string;
}

export interface BackendOrderQueueItem {
  queue_id: string;
  order_id: string;
  queue_position: number;
  status: string;
  enqueued_at: string;
  claimed_at?: string;
  completed_at?: string;
  attempt_count: number;
  last_error?: string;
  origin: string;
  customer_ref?: string;
  entity_id?: string;
  priority?: string;
  total_amount_inr?: number;
}

export interface BackendOrderQueueStatus {
  total_queued: number;
  total_processing: number;
  total_waiting_exception: number;
  total_completed: number;
  total_failed: number;
  auto_replenish: boolean;
  interval_seconds: number;
  runner_enabled: boolean;
  runner_status: string;
  next_eligible_run_time?: string;
  current_running_order_id?: string;
}

export interface BackendOperationalExceptionSummary {
  exception_id: string;
  order_id?: string;
  severity: string;
  exception_type: string;
  cause: string;
  owner_role: string;
  status: string;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  customer_ref?: string;
  entity_id?: string;
}

export interface BackendOperationalException {
  exception_id: string;
  order_id?: string;
  scenario_id?: string;
  workflow_run_id?: string;
  decision_id?: string;
  action_id?: string;
  approval_id?: string;
  severity: string;
  exception_type: string;
  cause: string;
  owner_role: string;
  status: string;
  ai_recommendation: Record<string, any>;
  proposed_action?: Record<string, any>;
  resolution_notes?: string;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  order_details?: Record<string, any>;
  action_details?: Record<string, any>;
  approval_details?: Record<string, any>;
}

export interface BackendExceptionActionProposeRequest {
  action_type: string;
  target_entity_id?: string;
  parameters: Record<string, any>;
  justification?: string;
  notes?: string;
}

export interface BackendExceptionResolutionResponse {
  exception_id: string;
  status: string;
  order_id?: string;
  order_status?: string;
  action_id?: string;
  action_status?: string;
  message: string;
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
  explorer_url?: string;
  explorerUrl?: string;
  confirmed_at?: string;
  confirmedAt?: string;
  receipt_status?: number;
}

export interface BackendBlockchainStatus {
  enabled?: boolean;
  mode: string;
  connected?: boolean;
  chain_name?: string;
  network_name?: string;
  chain_id: number | null;
  contract_address: string | null;
  contract_deployed?: boolean;
  signer_address?: string | null;
  rpc_configured: boolean;
  signer_configured: boolean;
  latest_block?: number | null;
  explorer_tx_url_prefix?: string | null;
  explorer_tx_url_template?: string | null;
  healthy?: boolean;
  details?: string;
  total_anchors?: number;
  total_anchors_tracked?: number;
  confirmed_anchors?: number;
  pending_anchors?: number;
}

export interface BackendAnchorRecord {
  anchor_id: string;
  event_id_or_batch_id: string;
  network_name: string;
  chain_id: number;
  contract_address: string;
  payload_hash: string;
  transaction_hash?: string | null;
  block_number?: number | null;
  confirmation_status: string;
  verification_status: string;
  gas_used?: number | null;
  receipt_status?: number | null;
  explorer_url?: string | null;
  submitted_at: string;
  confirmed_at?: string | null;
  error_details?: string | null;
  retry_count: number;
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
  on_chain_verified?: boolean;
  digest_verified?: boolean;
  contract_address?: string | null;
  explorer_url?: string | null;
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
  provider_name?: string;
  key_id?: string;
  fallback_occurred?: boolean;
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
  gemini_keys_configured?: number;
  openrouter_enabled?: boolean;
  openrouter_model?: string;
  description: string;
}

// ── API Services ───────────────────────────────────────────────────────────

export const apiClient = {
  // System Health
  checkHealth: () => apiFetch<{ status: string }>('/api/health'),
  checkLive: () => apiFetch<{ status: string }>('/api/live'),

  // Orders, Queue & Runner
  getOrders: (limit = 100, status?: string) =>
    apiFetch<BackendOrder[]>(
      `/api/orders/?limit=${limit}${status && status !== 'All' ? `&status=${status}` : ''}`
    ),
  getOrderSummary: () => apiFetch<BackendOrderSummary>('/api/orders/summary'),
  createOrder: (data: CreateOrderRequest) =>
    apiFetch<OrderCreateResponse>('/api/orders/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getOrderQueue: (limit = 100, offset = 0, status?: string) => {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    if (offset > 0) params.append('offset', offset.toString());
    if (status && status !== 'ALL') params.append('status', status);
    return apiFetch<BackendOrderQueueItem[]>(`/api/orders/queue?${params.toString()}`);
  },
  getOrderHistory: (limit = 100, offset = 0) =>
    apiFetch<BackendOrder[]>(`/api/orders/history?limit=${limit}&offset=${offset}`),
  getOrderQueueStatus: () =>
    apiFetch<BackendOrderQueueStatus>('/api/orders/queue/status'),
  getOrderQueueRunnerStatus: () =>
    apiFetch<any>('/api/orders/queue/runner/status'),
  startOrderQueueRunner: () =>
    apiFetch<{ status: string; message: string }>('/api/orders/queue/runner/start', {
      method: 'POST',
    }),
  pauseOrderQueueRunner: () =>
    apiFetch<{ status: string; message: string }>('/api/orders/queue/runner/pause', {
      method: 'POST',
    }),
  resumeOrderQueueRunner: () =>
    apiFetch<{ status: string; message: string }>('/api/orders/queue/runner/resume', {
      method: 'POST',
    }),
  stopOrderQueueRunner: () =>
    apiFetch<{ status: string; message: string }>('/api/orders/queue/runner/stop', {
      method: 'POST',
    }),
  processNextQueueOrder: () =>
    apiFetch<any>('/api/orders/queue/runner/process-next', {
      method: 'POST',
    }),

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

  // Operational Exceptions
  getExceptions: (status?: string, severity?: string, orderId?: string, limit = 50, offset = 0) => {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    if (offset > 0) params.append('offset', offset.toString());
    if (status && status !== 'ALL') params.append('status_filter', status);
    if (severity && severity !== 'ALL') params.append('severity', severity);
    if (orderId) params.append('order_id', orderId);
    return apiFetch<BackendOperationalExceptionSummary[]>(`/api/exceptions/?${params.toString()}`);
  },
  getExceptionDetail: (exceptionId: string) =>
    apiFetch<BackendOperationalException>(`/api/exceptions/${exceptionId}`),
  proposeExceptionAction: (exceptionId: string, data: BackendExceptionActionProposeRequest) =>
    apiFetch<any>(`/api/exceptions/${exceptionId}/propose-action`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  approveExceptionAction: (exceptionId: string, decision: 'APPROVED' | 'REJECTED', justification: string) =>
    apiFetch<any>(`/api/exceptions/${exceptionId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ decision, justification }),
    }),
  executeExceptionAction: (exceptionId: string) =>
    apiFetch<BackendExceptionResolutionResponse>(`/api/exceptions/${exceptionId}/execute`, {
      method: 'POST',
    }),
  resumeOrderFromException: (exceptionId: string, notes?: string) =>
    apiFetch<BackendExceptionResolutionResponse>(`/api/exceptions/${exceptionId}/resume`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    }),

  // Audit & Blockchain
  getAuditEvents: (limit = 50) =>
    apiFetch<BackendAuditEvent[]>(`/api/audit/events?limit=${limit}`),
  getBlockchainStatus: () =>
    apiFetch<BackendBlockchainStatus>('/api/audit/blockchain/status'),
  getBlockchainAnchors: (eventId?: string, confirmationStatus?: string, limit = 50, offset = 0) => {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    if (offset > 0) params.append('offset', offset.toString());
    if (eventId) params.append('event_id', eventId);
    if (confirmationStatus && confirmationStatus !== 'ALL') params.append('confirmation_status', confirmationStatus);
    return apiFetch<BackendAnchorRecord[]>(`/api/audit/anchors?${params.toString()}`);
  },
  anchorAuditEvent: (eventId: string, payload: Record<string, any> = {}, forceSimulation = false) =>
    apiFetch<BackendAnchorRecord>('/api/audit/anchor', {
      method: 'POST',
      body: JSON.stringify({
        event_id: eventId,
        payload,
        force_simulation: forceSimulation,
      }),
    }),
  verifyAuditEvent: (eventId: string, payload: Record<string, any> = {}) =>
    apiFetch<BackendAuditVerification>(`/api/audit/verify/${eventId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  verifyAnchorOnChain: (eventId: string) =>
    apiFetch<BackendAuditVerification>(`/api/audit/verify-on-chain/${eventId}`, {
      method: 'POST',
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

  // WebSocket Authentication Ticket (Phase 6 Hardened)
  getWsTicket: () =>
    apiFetch<{ ticket: string; expires_in: number; user_id: string; role: string }>('/api/ws/ticket', {
      method: 'POST',
    }),

  // Knowledge Graph (Phase 8)
  getKnowledgeGraph: (type?: string, q?: string, limit = 100) => {
    const params = new URLSearchParams();
    if (type) params.append('type', type);
    if (q) params.append('q', q);
    params.append('limit', String(limit));
    return apiFetch<BackendGraphResponse>(`/api/graph?${params.toString()}`);
  },
  getGraphStatus: () =>
    apiFetch<BackendGraphStatus>('/api/graph/status'),
  analyzeDisruptionImpact: (req: { entity_type: string; entity_id: string; severity?: string; max_depth?: number; simulate_alternatives?: boolean }) =>
    apiFetch<BackendDisruptionImpactResponse>('/api/graph/impact', {
      method: 'POST',
      body: JSON.stringify(req),
    }),
  syncKnowledgeGraph: () =>
    apiFetch<{ status: string; synced_nodes: number; synced_edges: number; duration_ms: number; message: string }>('/api/graph/sync', {
      method: 'POST',
    }),
  getEntityProvenance: (entityId: string, depth = 2) =>
    apiFetch<BackendGraphResponse>(`/api/graph/provenance/${encodeURIComponent(entityId)}?depth=${depth}`),
};

export interface BackendGraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
  status?: string;
  source_table?: string;
  source_id?: string;
}

export interface BackendGraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  label?: string;
  properties: Record<string, any>;
  directed: boolean;
}

export interface BackendGraphResponse {
  nodes: BackendGraphNode[];
  edges: BackendGraphEdge[];
  node_count: number;
  edge_count: number;
  query_time_ms: number;
  engine: string;
  timestamp: string;
}

export interface BackendGraphStatus {
  status: string;
  engine: string;
  connected: boolean;
  uri?: string;
  node_count: number;
  relationship_count: number;
  available_labels: string[];
  available_relationship_types: string[];
  last_synced_at?: string;
  error_message?: string;
}

export interface BackendDisruptionImpactResponse {
  disruption_origin: string;
  origin_type: string;
  severity: string;
  affected_order_ids: string[];
  affected_product_ids: string[];
  affected_warehouse_ids: string[];
  total_revenue_at_risk_inr: number;
  alternative_suppliers: any[];
  traversal_paths: any[][];
  mitigation_recommendation: string;
  graph_engine: string;
  analyzed_at: string;
}

