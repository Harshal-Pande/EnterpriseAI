import type { Agent, Order, Supplier, InventoryItem, AuditEvent, GraphNode, GraphEdge } from '../types';
import { DEFAULT_ORDER } from '../data/initialDemoData';

const API_BASE = 'http://127.0.0.1:8000/api';

export const agentService = {
  getAgents: async (): Promise<Agent[]> => {
    const res = await fetch(`${API_BASE}/agents`);
    return res.json();
  },
  getAgentById: async (id: string): Promise<Agent | undefined> => {
    const res = await fetch(`${API_BASE}/agents/${id}`);
    return res.json();
  }
};

export const orderService = {
  getOrders: async (): Promise<Order[]> => {
    const res = await fetch(`${API_BASE}/orders`);
    return res.json();
  },
  getPrimaryOrder: async (): Promise<Order> => {
    try {
        const res = await fetch(`${API_BASE}/orders`);
        const orders = await res.json();
        if (orders.length > 0) return orders[0];
    } catch (e) {
        console.error(e);
    }
    return DEFAULT_ORDER;
  }
};

export const supplierService = {
  getSuppliers: async (): Promise<Supplier[]> => {
    const res = await fetch(`${API_BASE}/suppliers`);
    return res.json();
  }
};

export const inventoryService = {
  getInventory: async (): Promise<InventoryItem[]> => {
    const res = await fetch(`${API_BASE}/inventory`);
    return res.json();
  }
};

export const auditService = {
  getAuditEvents: async (): Promise<AuditEvent[]> => {
    const res = await fetch(`${API_BASE}/audit`);
    return res.json();
  }
};

export const graphService = {
  getKnowledgeGraph: async (): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> => {
    const res = await fetch(`${API_BASE}/knowledge-graph`);
    return res.json();
  }
};

export interface BenchmarkData {
  latencyMs: { traditional: number; agentMesh: number };
  processingCostRs: { traditional: number; agentMesh: number };
  exceptionHandlingRate: { traditional: number; agentMesh: number };
  explainabilityScore: { traditional: number; agentMesh: number };
  recoveryTimeSec: { traditional: number; agentMesh: number };
}

export const benchmarkService = {
  getBenchmarkMetrics: async (): Promise<BenchmarkData> => {
    const res = await fetch(`${API_BASE}/benchmarks`);
    return res.json();
  }
};
