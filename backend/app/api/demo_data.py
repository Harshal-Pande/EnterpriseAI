from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter()

INITIAL_AGENTS = [
  {
    "id": "supervisor",
    "name": "Supervisor Agent",
    "role": "Workflow Coordinator & Decision Arbiter",
    "status": "ONLINE",
    "workload": 45,
    "tasksCompleted": 1240,
    "avgResponseMs": 180,
    "currentTask": "Awaiting incoming order request",
    "inputReceived": "Order stream listener active",
    "currentAction": "Monitoring mesh inter-agent communications",
    "lastDecision": "System initialized and synchronized",
    "rationale": "All node heartbeat responses normal. RAG context index primed.",
    "confidence": 99,
    "nextAction": "Delegate order verification to Inventory Agent upon arrival",
    "active": False
  },
  {
    "id": "inventory",
    "name": "Inventory Agent",
    "role": "Stock Level & Shortage Monitoring",
    "status": "ONLINE",
    "workload": 32,
    "tasksCompleted": 980,
    "avgResponseMs": 110,
    "currentTask": "Monitoring warehouse stock thresholds",
    "inputReceived": "Stock query for Industrial Water Pump",
    "currentAction": "Evaluating local warehouse levels vs demand",
    "lastDecision": "Stock shortfall detected (78 units required)",
    "rationale": "Current available stock is 42 units; required quantity is 120 units.",
    "confidence": 98,
    "nextAction": "Trigger reorder signal to Procurement Agent",
    "active": False
  },
  {
    "id": "procurement",
    "name": "Procurement Agent",
    "role": "Supplier Selection & Negotiation Engine",
    "status": "ONLINE",
    "workload": 68,
    "tasksCompleted": 750,
    "avgResponseMs": 340,
    "currentTask": "Supplier evaluation & negotiation matrix active",
    "inputReceived": "Reorder signal: 78 units Industrial Water Pump",
    "currentAction": "Ranking 3 qualified suppliers by price, availability, and SLA",
    "lastDecision": "Supplier B selected (Score: 92/100)",
    "rationale": "Supplier B offers immediate stock availability at ₹6,600/unit with 2-day delivery.",
    "confidence": 94,
    "nextAction": "Transmit cost estimation to Finance Agent",
    "active": False
  },
  {
    "id": "finance",
    "name": "Finance Agent",
    "role": "Budget Validation & Risk Assessment",
    "status": "ONLINE",
    "workload": 25,
    "tasksCompleted": 1120,
    "avgResponseMs": 210,
    "currentTask": "Budget reserve validation",
    "inputReceived": "Procurement invoice proposal: ₹7,92,000",
    "currentAction": "Cross-checking order value against allocated cap (₹8,50,000)",
    "lastDecision": "Budget check PASSED (₹58,000 headroom remaining)",
    "rationale": "Requested ₹7,92,000 is within max budget limit of ₹8,50,000 with 6.8% safety reserve.",
    "confidence": 97,
    "nextAction": "Authorize purchase allocation and signal Logistics Agent",
    "active": False
  },
  {
    "id": "logistics",
    "name": "Logistics Agent",
    "role": "Route Feasibility & Fulfillment Scheduling",
    "status": "ONLINE",
    "workload": 40,
    "tasksCompleted": 890,
    "avgResponseMs": 290,
    "currentTask": "Transit route feasibility assessment",
    "inputReceived": "Shipment request: Pune Hub -> Nagpur DC",
    "currentAction": "Simulating weather, transit lanes, and carrier availability",
    "lastDecision": "Route approved via Express Air Freight (2-day SLA)",
    "rationale": "480 km route clear; express carrier available with 99.2% on-time historical SLA.",
    "confidence": 96,
    "nextAction": "Return final execution feasibility token to Supervisor",
    "active": False
  }
]

INITIAL_SUPPLIERS = [
  {
    "id": "SUP-A",
    "name": "Apex Industrial Dynamics",
    "pricePerUnit": 6400,
    "availability": 0,
    "deliveryDays": 5,
    "score": 54,
    "status": "UNAVAILABLE",
    "notes": "Stock deplete until end of month"
  },
  {
    "id": "SUP-B",
    "name": "Bharat Heavy Engineering Solutions",
    "pricePerUnit": 6600,
    "availability": 150,
    "deliveryDays": 2,
    "score": 94,
    "status": "SELECTED",
    "notes": "Optimal trade-off: Immediate availability with 2-day delivery"
  },
  {
    "id": "SUP-C",
    "name": "Crestline Global Logistics & Parts",
    "pricePerUnit": 7400,
    "availability": 200,
    "deliveryDays": 1,
    "score": 72,
    "status": "AVAILABLE",
    "notes": "Fast delivery but 12% premium above target price"
  }
]

INITIAL_INVENTORY = [
  {
    "id": "INV-101",
    "productName": "Industrial Water Pump (Model WP-800)",
    "currentStock": 42,
    "reorderThreshold": 100,
    "required": 120,
    "shortage": 78,
    "status": "REORDER_REQUIRED"
  },
  {
    "id": "INV-102",
    "productName": "Hydraulic Actuator Valves",
    "currentStock": 18,
    "reorderThreshold": 25,
    "required": 50,
    "shortage": 32,
    "status": "REORDER_REQUIRED"
  },
  {
    "id": "INV-103",
    "productName": "High-Pressure Armored Hoses",
    "currentStock": 410,
    "reorderThreshold": 200,
    "required": 300,
    "shortage": 0,
    "status": "OK"
  },
  {
    "id": "INV-104",
    "productName": "Heavy-Duty Conveyor Motors",
    "currentStock": 35,
    "reorderThreshold": 20,
    "required": 15,
    "shortage": 0,
    "status": "OK"
  },
  {
    "id": "INV-105",
    "productName": "Turbine Control Units",
    "currentStock": 6,
    "reorderThreshold": 10,
    "required": 8,
    "shortage": 2,
    "status": "LOW_STOCK"
  }
]

INITIAL_AUDIT_EVENTS = [
  {
    "blockNumber": 184725,
    "eventId": "EVT-9001",
    "type": "ORDER_CREATED",
    "actor": "Customer Portal",
    "orderId": "ORD-1042",
    "timestamp": "16:42:08.102",
    "status": "VERIFIED",
    "txHash": "0x7f83a91c2049e88b1",
    "details": "Order ORD-1042 initialized for 120 units WP-800"
  },
  {
    "blockNumber": 184726,
    "eventId": "EVT-9002",
    "type": "SUPERVISOR_ASSIGNED",
    "actor": "Supervisor Agent",
    "orderId": "ORD-1042",
    "timestamp": "16:42:09.410",
    "status": "VERIFIED",
    "txHash": "0x3a88f71e9902d1442",
    "details": "Workflow graph initialized. Assigned to sub-agents."
  }
]

INITIAL_GRAPH_NODES = [
  { "id": "cust-1", "label": "Tata Steels Ltd", "type": "Customer", "details": { "Code": "CUST-881", "Sector": "Heavy Metals", "Tier": "Platinum" }, "x": 100, "y": 150 },
  { "id": "ord-1042", "label": "ORD-1042", "type": "Order", "status": "Processing", "details": { "Value": "₹8,50,000", "Priority": "High", "Qty": 120 }, "x": 300, "y": 150 },
  { "id": "prod-800", "label": "WP-800 Pump", "type": "Product", "details": { "Category": "Industrial Pumps", "SKU": "SKU-WP-800", "Criticality": "High" }, "x": 500, "y": 100 },
  { "id": "sup-b", "label": "Supplier B (Bharat Heavy)", "type": "Supplier", "status": "Selected", "details": { "Rating": "4.8/5.0", "Location": "Pune Hub", "SLA": "99.2%" }, "x": 700, "y": 100 },
  { "id": "wh-nagpur", "label": "Nagpur DC Hub", "type": "Warehouse", "details": { "Capacity": "85% full", "Manager": "K. Verma", "Region": "Central IN" }, "x": 500, "y": 250 }
]

INITIAL_GRAPH_EDGES = [
  { "id": "e1", "source": "cust-1", "target": "ord-1042", "label": "placed" },
  { "id": "e2", "source": "ord-1042", "target": "prod-800", "label": "contains" },
  { "id": "e3", "source": "prod-800", "target": "sup-b", "label": "supplied by" },
  { "id": "e4", "source": "ord-1042", "target": "wh-nagpur", "label": "fulfilled from" }
]

@router.get("/agents")
def get_agents():
    return INITIAL_AGENTS

@router.get("/agents/{agent_id}")
def get_agent_by_id(agent_id: str):
    for agent in INITIAL_AGENTS:
        if agent["id"] == agent_id:
            return agent
    return None

@router.get("/suppliers")
def get_suppliers():
    return INITIAL_SUPPLIERS

@router.get("/inventory")
def get_inventory():
    return INITIAL_INVENTORY

@router.get("/audit")
def get_audit_events():
    return INITIAL_AUDIT_EVENTS

@router.get("/knowledge-graph")
def get_knowledge_graph():
    return {"nodes": INITIAL_GRAPH_NODES, "edges": INITIAL_GRAPH_EDGES}

@router.get("/benchmarks")
def get_benchmarks():
    return {
      "latencyMs": { "traditional": 4800, "agentMesh": 1520 },
      "processingCostRs": { "traditional": 1450, "agentMesh": 840 },
      "exceptionHandlingRate": { "traditional": 18.5, "agentMesh": 98.4 },
      "explainabilityScore": { "traditional": 12.0, "agentMesh": 94.5 },
      "recoveryTimeSec": { "traditional": 14400, "agentMesh": 8.5 }
    }
