import type { Agent, Order, Supplier, InventoryItem, AuditEvent, ActivityLog, GraphNode, GraphEdge } from '../types';

export const INITIAL_AGENTS: Agent[] = [
  {
    id: 'supervisor',
    name: 'Supervisor Agent',
    role: 'Workflow Coordinator & Decision Arbiter',
    status: 'ONLINE',
    workload: 45,
    tasksCompleted: 1240,
    avgResponseMs: 180,
    currentTask: 'Awaiting incoming order request',
    inputReceived: 'Order stream listener active',
    currentAction: 'Monitoring mesh inter-agent communications',
    lastDecision: 'System initialized and synchronized',
    rationale: 'All node heartbeat responses normal. RAG context index primed.',
    confidence: 99,
    nextAction: 'Delegate order verification to Inventory Agent upon arrival',
    active: false
  },
  {
    id: 'inventory',
    name: 'Inventory Agent',
    role: 'Stock Level & Shortage Monitoring',
    status: 'ONLINE',
    workload: 32,
    tasksCompleted: 980,
    avgResponseMs: 110,
    currentTask: 'Monitoring warehouse stock thresholds',
    inputReceived: 'Stock query for Industrial Water Pump',
    currentAction: 'Evaluating local warehouse levels vs demand',
    lastDecision: 'Stock shortfall detected (78 units required)',
    rationale: 'Current available stock is 42 units; required quantity is 120 units.',
    confidence: 98,
    nextAction: 'Trigger reorder signal to Procurement Agent',
    active: false
  },
  {
    id: 'procurement',
    name: 'Procurement Agent',
    role: 'Supplier Selection & Negotiation Engine',
    status: 'ONLINE',
    workload: 68,
    tasksCompleted: 750,
    avgResponseMs: 340,
    currentTask: 'Supplier evaluation & negotiation matrix active',
    inputReceived: 'Reorder signal: 78 units Industrial Water Pump',
    currentAction: 'Ranking 3 qualified suppliers by price, availability, and SLA',
    lastDecision: 'Supplier B selected (Score: 92/100)',
    rationale: 'Supplier B offers immediate stock availability at ₹6,600/unit with 2-day delivery.',
    confidence: 94,
    nextAction: 'Transmit cost estimation to Finance Agent',
    active: false
  },
  {
    id: 'finance',
    name: 'Finance Agent',
    role: 'Budget Validation & Risk Assessment',
    status: 'ONLINE',
    workload: 25,
    tasksCompleted: 1120,
    avgResponseMs: 210,
    currentTask: 'Budget reserve validation',
    inputReceived: 'Procurement invoice proposal: ₹7,92,000',
    currentAction: 'Cross-checking order value against allocated cap (₹8,50,000)',
    lastDecision: 'Budget check PASSED (₹58,000 headroom remaining)',
    rationale: 'Requested ₹7,92,000 is within max budget limit of ₹8,50,000 with 6.8% safety reserve.',
    confidence: 97,
    nextAction: 'Authorize purchase allocation and signal Logistics Agent',
    active: false
  },
  {
    id: 'logistics',
    name: 'Logistics Agent',
    role: 'Route Feasibility & Fulfillment Scheduling',
    status: 'ONLINE',
    workload: 40,
    tasksCompleted: 890,
    avgResponseMs: 290,
    currentTask: 'Transit route feasibility assessment',
    inputReceived: 'Shipment request: Pune Hub -> Nagpur DC',
    currentAction: 'Simulating weather, transit lanes, and carrier availability',
    lastDecision: 'Route approved via Express Air Freight (2-day SLA)',
    rationale: '480 km route clear; express carrier available with 99.2% on-time historical SLA.',
    confidence: 96,
    nextAction: 'Return final execution feasibility token to Supervisor',
    active: false
  }
];

export const DEFAULT_ORDER: Order = {
  id: 'ORD-1042',
  customer: 'Tata Steels Ltd - Nagpur Division',
  product: 'Industrial Water Pump (Model WP-800)',
  quantity: 120,
  destination: 'Nagpur Distribution Center',
  budget: 850000,
  estimatedCost: 792000,
  status: 'Processing',
  priority: 'High',
  currentAgent: 'supervisor',
  createdAt: '2026-08-09 16:42:00',
  auditHash: '0x7f83a91c2049e88b'
};

export const SAMPLE_ORDERS: Order[] = [
  DEFAULT_ORDER,
  {
    id: 'ORD-1043',
    customer: 'Reliance Logistics Hub',
    product: 'Hydraulic Actuator Valves',
    quantity: 50,
    destination: 'Bhiwandi Fulfillment Hub',
    budget: 420000,
    estimatedCost: 395000,
    status: 'Approved',
    priority: 'Critical',
    currentAgent: 'logistics',
    createdAt: '2026-08-09 15:30:12',
    auditHash: '0x9b41c88d1033f2a1'
  },
  {
    id: 'ORD-1044',
    customer: 'Mahindra Defense Systems',
    product: 'High-Pressure Armored Hoses',
    quantity: 300,
    destination: 'Nashik Manufacturing Plant',
    budget: 1200000,
    estimatedCost: 1180000,
    status: 'Finance Review',
    priority: 'Medium',
    currentAgent: 'finance',
    createdAt: '2026-08-09 14:15:00',
    auditHash: '0x3a88f71e9902d144'
  },
  {
    id: 'ORD-1045',
    customer: 'Adani Ports & Special Logistics',
    product: 'Heavy-Duty Conveyor Motors',
    quantity: 15,
    destination: 'Mundra Port Terminal',
    budget: 650000,
    estimatedCost: 610000,
    status: 'Awaiting Procurement',
    priority: 'High',
    currentAgent: 'procurement',
    createdAt: '2026-08-09 13:05:40',
    auditHash: '0x1c55d00a4421b987'
  },
  {
    id: 'ORD-1046',
    customer: 'L&T Heavy Engineering',
    product: 'Turbine Control Units',
    quantity: 8,
    destination: 'Hazira Works Complex',
    budget: 1800000,
    estimatedCost: 1750000,
    status: 'Completed',
    priority: 'Low',
    currentAgent: 'supervisor',
    createdAt: '2026-08-09 11:20:10',
    auditHash: '0x8e22c99b1190a331'
  },
  {
    id: 'ORD-1047',
    customer: 'JSW Steel Energy',
    product: 'Cooling Tower Fan Modules',
    quantity: 45,
    destination: 'Bellary Integrated Plant',
    budget: 950000,
    estimatedCost: 995000,
    status: 'Exception',
    priority: 'Critical',
    currentAgent: 'finance',
    createdAt: '2026-08-09 10:00:00',
    auditHash: '0x4f11a88b7762c554',
    notes: 'Budget breach: Quote exceeded limit by ₹45,000'
  }
];

export const INITIAL_SUPPLIERS: Supplier[] = [
  {
    id: 'SUP-A',
    name: 'Apex Industrial Dynamics',
    pricePerUnit: 6400,
    availability: 0,
    deliveryDays: 5,
    score: 54,
    status: 'UNAVAILABLE',
    notes: 'Stock deplete until end of month'
  },
  {
    id: 'SUP-B',
    name: 'Bharat Heavy Engineering Solutions',
    pricePerUnit: 6600,
    availability: 150,
    deliveryDays: 2,
    score: 94,
    status: 'SELECTED',
    notes: 'Optimal trade-off: Immediate availability with 2-day delivery'
  },
  {
    id: 'SUP-C',
    name: 'Crestline Global Logistics & Parts',
    pricePerUnit: 7400,
    availability: 200,
    deliveryDays: 1,
    score: 72,
    status: 'AVAILABLE',
    notes: 'Fast delivery but 12% premium above target price'
  }
];

export const INITIAL_INVENTORY: InventoryItem[] = [
  {
    id: 'INV-101',
    productName: 'Industrial Water Pump (Model WP-800)',
    currentStock: 42,
    reorderThreshold: 100,
    required: 120,
    shortage: 78,
    status: 'REORDER_REQUIRED'
  },
  {
    id: 'INV-102',
    productName: 'Hydraulic Actuator Valves',
    currentStock: 18,
    reorderThreshold: 25,
    required: 50,
    shortage: 32,
    status: 'REORDER_REQUIRED'
  },
  {
    id: 'INV-103',
    productName: 'High-Pressure Armored Hoses',
    currentStock: 410,
    reorderThreshold: 200,
    required: 300,
    shortage: 0,
    status: 'OK'
  },
  {
    id: 'INV-104',
    productName: 'Heavy-Duty Conveyor Motors',
    currentStock: 35,
    reorderThreshold: 20,
    required: 15,
    shortage: 0,
    status: 'OK'
  },
  {
    id: 'INV-105',
    productName: 'Turbine Control Units',
    currentStock: 6,
    reorderThreshold: 10,
    required: 8,
    shortage: 2,
    status: 'LOW_STOCK'
  }
];

export const INITIAL_AUDIT_EVENTS: AuditEvent[] = [
  {
    blockNumber: 184725,
    eventId: 'EVT-9001',
    type: 'ORDER_CREATED',
    actor: 'Customer Portal',
    orderId: 'ORD-1042',
    timestamp: '16:42:08.102',
    status: 'VERIFIED',
    txHash: '0x7f83a91c2049e88b1',
    details: 'Order ORD-1042 initialized for 120 units WP-800'
  },
  {
    blockNumber: 184726,
    eventId: 'EVT-9002',
    type: 'SUPERVISOR_ASSIGNED',
    actor: 'Supervisor Agent',
    orderId: 'ORD-1042',
    timestamp: '16:42:09.410',
    status: 'VERIFIED',
    txHash: '0x3a88f71e9902d1442',
    details: 'Workflow graph initialized. Assigned to sub-agents.'
  },
  {
    blockNumber: 184727,
    eventId: 'EVT-9003',
    type: 'INVENTORY_VERIFIED',
    actor: 'Inventory Agent',
    orderId: 'ORD-1042',
    timestamp: '16:42:10.825',
    status: 'VERIFIED',
    txHash: '0x9b41c88d1033f2a13',
    details: 'Warehouse check complete: Stock shortfall 78 units.'
  },
  {
    blockNumber: 184728,
    eventId: 'EVT-9004',
    type: 'SUPPLIER_SELECTED',
    actor: 'Procurement Agent',
    orderId: 'ORD-1042',
    timestamp: '16:42:16.090',
    status: 'VERIFIED',
    txHash: '0x1c55d00a4421b9874',
    details: 'Supplier B selected (Quote: ₹6,600/unit, 2-day delivery)'
  },
  {
    blockNumber: 184729,
    eventId: 'EVT-9005',
    type: 'FINANCE_APPROVED',
    actor: 'Finance Agent',
    orderId: 'ORD-1042',
    timestamp: '16:42:18.512',
    status: 'VERIFIED',
    txHash: '0x8e22c99b1190a3315',
    details: 'Budget reserve approved: ₹7,92,000 sanctioned.'
  }
];

export const INITIAL_ACTIVITY_LOGS: ActivityLog[] = [
  { id: '1', timestamp: '16:42:08', agent: 'supervisor', message: 'Order ORD-1042 received from Tata Steels Ltd', type: 'info' },
  { id: '2', timestamp: '16:42:10', agent: 'inventory', message: 'Warehouse stock checked: 42 available, 78 units shortfall', type: 'warning' },
  { id: '3', timestamp: '16:42:13', agent: 'procurement', message: 'Evaluated 3 suppliers (Supplier A, B, C)', type: 'info' },
  { id: '4', timestamp: '16:42:16', agent: 'procurement', message: 'Supplier B recommended (Confidence: 94%)', type: 'success' },
  { id: '5', timestamp: '16:42:18', agent: 'finance', message: 'Budget approved: ₹7,92,000 sanctioned within cap', type: 'success' },
  { id: '6', timestamp: '16:42:21', agent: 'logistics', message: 'Delivery feasibility confirmed via Pune-Nagpur corridor', type: 'info' },
  { id: '7', timestamp: '16:42:23', agent: 'supervisor', message: 'Order approved and final execution graph generated', type: 'success' },
  { id: '8', timestamp: '16:42:24', agent: 'AUDIT', message: 'Purchase order event recorded on audit ledger (#184729)', type: 'info' }
];

export const INITIAL_GRAPH_NODES: GraphNode[] = [
  { id: 'cust-1', label: 'Tata Steels Ltd', type: 'Customer', details: { Code: 'CUST-881', Sector: 'Heavy Metals', Tier: 'Platinum' }, x: 100, y: 150 },
  { id: 'ord-1042', label: 'ORD-1042', type: 'Order', status: 'Processing', details: { Value: '₹8,50,000', Priority: 'High', Qty: 120 }, x: 300, y: 150 },
  { id: 'prod-800', label: 'WP-800 Pump', type: 'Product', details: { Category: 'Industrial Pumps', SKU: 'SKU-WP-800', Criticality: 'High' }, x: 500, y: 100 },
  { id: 'sup-b', label: 'Supplier B (Bharat Heavy)', type: 'Supplier', status: 'Selected', details: { Rating: '4.8/5.0', Location: 'Pune Hub', SLA: '99.2%' }, x: 700, y: 100 },
  { id: 'wh-nagpur', label: 'Nagpur DC Hub', type: 'Warehouse', details: { Capacity: '85% full', Manager: 'K. Verma', Region: 'Central IN' }, x: 500, y: 250 }
];

export const INITIAL_GRAPH_EDGES: GraphEdge[] = [
  { id: 'e1', source: 'cust-1', target: 'ord-1042', label: 'placed' },
  { id: 'e2', source: 'ord-1042', target: 'prod-800', label: 'contains' },
  { id: 'e3', source: 'prod-800', target: 'sup-b', label: 'supplied by' },
  { id: 'e4', source: 'ord-1042', target: 'wh-nagpur', label: 'fulfilled from' }
];
