import type { Agent, Order, Supplier, InventoryItem, AuditEvent, GraphNode, GraphEdge } from '../types';
import {
  INITIAL_AGENTS,
  DEFAULT_ORDER,
  SAMPLE_ORDERS,
  INITIAL_SUPPLIERS,
  INITIAL_INVENTORY,
  INITIAL_AUDIT_EVENTS,
  INITIAL_GRAPH_NODES,
  INITIAL_GRAPH_EDGES
} from '../data/initialDemoData';

export const agentService = {
  getAgents: async (): Promise<Agent[]> => {
    return Promise.resolve(INITIAL_AGENTS);
  },
  getAgentById: async (id: string): Promise<Agent | undefined> => {
    return Promise.resolve(INITIAL_AGENTS.find(a => a.id === id));
  }
};

export const orderService = {
  getOrders: async (): Promise<Order[]> => {
    return Promise.resolve(SAMPLE_ORDERS);
  },
  getPrimaryOrder: async (): Promise<Order> => {
    return Promise.resolve(DEFAULT_ORDER);
  }
};

export const supplierService = {
  getSuppliers: async (): Promise<Supplier[]> => {
    return Promise.resolve(INITIAL_SUPPLIERS);
  }
};

export const inventoryService = {
  getInventory: async (): Promise<InventoryItem[]> => {
    return Promise.resolve(INITIAL_INVENTORY);
  }
};

export const auditService = {
  getAuditEvents: async (): Promise<AuditEvent[]> => {
    return Promise.resolve(INITIAL_AUDIT_EVENTS);
  }
};

export const graphService = {
  getKnowledgeGraph: async (): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> => {
    return Promise.resolve({ nodes: INITIAL_GRAPH_NODES, edges: INITIAL_GRAPH_EDGES });
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
    return Promise.resolve({
      latencyMs: { traditional: 4800, agentMesh: 1520 },
      processingCostRs: { traditional: 1450, agentMesh: 840 },
      exceptionHandlingRate: { traditional: 18.5, agentMesh: 98.4 },
      explainabilityScore: { traditional: 12.0, agentMesh: 94.5 },
      recoveryTimeSec: { traditional: 14400, agentMesh: 8.5 }
    });
  }
};
