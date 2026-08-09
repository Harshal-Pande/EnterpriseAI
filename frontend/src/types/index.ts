export type AgentId = 'supervisor' | 'inventory' | 'procurement' | 'finance' | 'logistics';

export type AgentStatus = 'ONLINE' | 'BUSY' | 'WAITING' | 'ERROR';

export type WorkflowStage =
  | 'IDLE'
  | 'RECEIVED'
  | 'SUPERVISOR_ANALYSIS'
  | 'INVENTORY_CHECK'
  | 'PROCUREMENT_NEGOTIATION'
  | 'FINANCE_VALIDATION'
  | 'LOGISTICS_FEASIBILITY'
  | 'SUPERVISOR_DECISION'
  | 'ORDER_FULFILLED'
  | 'COMPLETED'
  | 'EXCEPTION';

export type DemoScenario =
  | 'normal'
  | 'supplier_unavailable'
  | 'budget_breach'
  | 'delivery_delay'
  | 'multi_exception';

export interface Agent {
  id: AgentId;
  name: string;
  role: string;
  status: AgentStatus;
  workload: number;
  tasksCompleted: number;
  avgResponseMs: number;
  currentTask: string;
  inputReceived: string;
  currentAction: string;
  lastDecision: string;
  rationale: string;
  confidence: number;
  nextAction: string;
  active: boolean;
}

export type OrderStatus =
  | 'Processing'
  | 'Approved'
  | 'Awaiting Procurement'
  | 'Finance Review'
  | 'Delayed'
  | 'Exception'
  | 'Completed';

export interface Order {
  id: string;
  customer: string;
  product: string;
  quantity: number;
  destination: string;
  budget: number;
  estimatedCost: number;
  status: OrderStatus;
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
  currentAgent: AgentId;
  createdAt: string;
  auditHash?: string;
  notes?: string;
}

export interface Supplier {
  id: string;
  name: string;
  pricePerUnit: number;
  availability: number;
  deliveryDays: number;
  score: number;
  status: 'SELECTED' | 'AVAILABLE' | 'UNAVAILABLE' | 'REJECTED_BUDGET';
  notes: string;
}

export interface InventoryItem {
  id: string;
  productName: string;
  currentStock: number;
  reorderThreshold: number;
  required: number;
  shortage: number;
  status: 'OK' | 'LOW_STOCK' | 'REORDER_REQUIRED';
}

export interface AuditEvent {
  blockNumber: number;
  eventId: string;
  type: string;
  actor: string;
  orderId: string;
  timestamp: string;
  status: 'VERIFIED' | 'PENDING';
  txHash: string;
  details: string;
}

export interface ActivityLog {
  id: string;
  timestamp: string;
  agent: AgentId | 'AUDIT' | 'SYSTEM';
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'Customer' | 'Order' | 'Product' | 'Supplier' | 'Warehouse';
  status?: string;
  details: Record<string, string | number>;
  x: number;
  y: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}
