import React, { createContext, useContext, useState, useRef, useEffect } from 'react';
import type {
  Agent,
  AgentId,
  Order,
  Supplier,
  InventoryItem,
  AuditEvent,
  ActivityLog,
  WorkflowStage,
  DemoScenario,
  GraphNode,
  GraphEdge
} from '../types';
import {
  INITIAL_AGENTS,
  DEFAULT_ORDER,
  SAMPLE_ORDERS,
  INITIAL_SUPPLIERS,
  INITIAL_INVENTORY,
  INITIAL_AUDIT_EVENTS,
  INITIAL_ACTIVITY_LOGS,
  INITIAL_GRAPH_NODES,
  INITIAL_GRAPH_EDGES
} from '../data/initialDemoData';

interface DemoContextType {
  activeOrder: Order;
  orders: Order[];
  agents: Agent[];
  suppliers: Supplier[];
  inventory: InventoryItem[];
  auditEvents: AuditEvent[];
  activityLogs: ActivityLog[];
  workflowStage: WorkflowStage;
  activeScenario: DemoScenario;
  isSimulating: boolean;
  selectedAgentId: AgentId | null;
  selectedGraphNodeId: string | null;
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];
  runDemoOrder: (scenario?: DemoScenario) => void;
  resetDemo: () => void;
  setSelectedAgentId: (id: AgentId | null) => void;
  setSelectedGraphNodeId: (id: string | null) => void;
  setActiveScenario: (scenario: DemoScenario) => void;
  updateOrderStatus: (orderId: string, status: Order['status']) => void;
}

const DemoContext = createContext<DemoContextType | undefined>(undefined);

export const DemoProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeOrder, setActiveOrder] = useState<Order>(DEFAULT_ORDER);
  const [orders, setOrders] = useState<Order[]>(SAMPLE_ORDERS);
  const [agents, setAgents] = useState<Agent[]>(INITIAL_AGENTS);
  const [suppliers, setSuppliers] = useState<Supplier[]>(INITIAL_SUPPLIERS);
  const [inventory, setInventory] = useState<InventoryItem[]>(INITIAL_INVENTORY);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>(INITIAL_AUDIT_EVENTS);
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>(INITIAL_ACTIVITY_LOGS);
  const [workflowStage, setWorkflowStage] = useState<WorkflowStage>('IDLE');
  const [activeScenario, setActiveScenario] = useState<DemoScenario>('normal');
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [selectedAgentId, setSelectedAgentId] = useState<AgentId | null>('supervisor');
  const [selectedGraphNodeId, setSelectedGraphNodeId] = useState<string | null>('ord-1042');
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>(INITIAL_GRAPH_NODES);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>(INITIAL_GRAPH_EDGES);

  const simulationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const addActivityLog = (agent: ActivityLog['agent'], message: string, type: ActivityLog['type'] = 'info') => {
    const timeStr = new Date().toTimeString().split(' ')[0];
    setActivityLogs(prev => [
      {
        id: Math.random().toString(36).substring(2, 9),
        timestamp: timeStr,
        agent,
        message,
        type
      },
      ...prev
    ]);
  };

  const updateAgentState = (
    id: AgentId,
    active: boolean,
    status: Agent['status'],
    updates: Partial<Agent>
  ) => {
    setAgents(prev =>
      prev.map(a => {
        if (a.id === id) {
          return {
            ...a,
            active,
            status,
            ...updates
          };
        }
        return a.id === id ? a : { ...a, active: false };
      })
    );
  };

  const addAuditEvent = (
    type: string,
    actor: string,
    details: string
  ) => {
    const nextBlock = (auditEvents[0]?.blockNumber || 184729) + 1;
    const timeStr = new Date().toTimeString().split(' ')[0] + '.' + Math.floor(Math.random() * 900 + 100);
    const hash = '0x' + Array.from({ length: 16 }, () => Math.floor(Math.random() * 16).toString(16)).join('');

    const newEvent: AuditEvent = {
      blockNumber: nextBlock,
      eventId: `EVT-${Math.floor(Math.random() * 8000 + 1000)}`,
      type,
      actor,
      orderId: activeOrder.id,
      timestamp: timeStr,
      status: 'VERIFIED',
      txHash: hash,
      details
    };

    setAuditEvents(prev => [newEvent, ...prev]);
  };

  const resetDemo = () => {
    if (simulationTimerRef.current) clearTimeout(simulationTimerRef.current);
    setIsSimulating(false);
    setWorkflowStage('IDLE');
    setActiveOrder(DEFAULT_ORDER);
    setAgents(INITIAL_AGENTS);
    setSuppliers(INITIAL_SUPPLIERS);
    setInventory(INITIAL_INVENTORY);
    setAuditEvents(INITIAL_AUDIT_EVENTS);
    setActivityLogs(INITIAL_ACTIVITY_LOGS);
    setGraphNodes(INITIAL_GRAPH_NODES);
    setGraphEdges(INITIAL_GRAPH_EDGES);
  };

  const runDemoOrder = (scenarioParam?: DemoScenario) => {
    const scenario = scenarioParam || activeScenario;
    if (isSimulating) return;

    setIsSimulating(true);
    setWorkflowStage('RECEIVED');
    setActiveOrder(prev => ({ ...prev, status: 'Processing', currentAgent: 'supervisor' }));
    addActivityLog('supervisor', `Order ${activeOrder.id} received. Initiating Multi-Agent Workflow [Scenario: ${scenario.toUpperCase()}]`, 'info');

    // STEP 1: Supervisor Analysis (1.5s)
    simulationTimerRef.current = setTimeout(() => {
      setWorkflowStage('SUPERVISOR_ANALYSIS');
      updateAgentState('supervisor', true, 'BUSY', {
        currentTask: `Parsing order specification for ${activeOrder.product}`,
        inputReceived: `Order ${activeOrder.id}: Qty ${activeOrder.quantity}, Budget ₹${activeOrder.budget.toLocaleString()}`,
        currentAction: 'Searching Knowledge Graph & generating execution plan',
        lastDecision: 'Workplan generated. Sub-task dispatched to Inventory Agent.',
        rationale: 'Order syntax verified. Stock availability check required prior to procurement.',
        confidence: 99,
        nextAction: 'Invoke Inventory Agent'
      });
      addActivityLog('supervisor', 'Order specification parsed. Workplan dispatched to Inventory Agent', 'info');

      // STEP 2: Inventory Check (3.0s)
      simulationTimerRef.current = setTimeout(() => {
        setWorkflowStage('INVENTORY_CHECK');
        updateAgentState('inventory', true, 'BUSY', {
          currentTask: 'Warehouse stock check for WP-800 Pumps',
          inputReceived: 'Query: 120 units Industrial Water Pump',
          currentAction: 'Scanning Central Warehouse & Nagpur Regional Hub',
          lastDecision: 'Stock shortfall detected (78 units missing)',
          rationale: 'Available stock: 42 units. Required: 120 units. Reorder signal generated.',
          confidence: 98,
          nextAction: 'Send procurement trigger to Procurement Agent'
        });
        addActivityLog('inventory', 'Stock availability checked: 42 in stock, 78 unit shortfall detected', 'warning');
        addAuditEvent('INVENTORY_VERIFIED', 'Inventory Agent', 'Stock shortage of 78 units detected. Reorder signal generated.');

        // STEP 3: Procurement Negotiation (4.8s)
        simulationTimerRef.current = setTimeout(() => {
          setWorkflowStage('PROCUREMENT_NEGOTIATION');

          if (scenario === 'supplier_unavailable' || scenario === 'multi_exception') {
            // Scenario 1: Supplier A is unavailable
            setSuppliers([
              { id: 'SUP-A', name: 'Apex Industrial Dynamics', pricePerUnit: 6400, availability: 0, deliveryDays: 5, score: 30, status: 'UNAVAILABLE', notes: 'Supplier A offline / depleted' },
              { id: 'SUP-B', name: 'Bharat Heavy Engineering Solutions', pricePerUnit: 6600, availability: 150, deliveryDays: 2, score: 94, status: 'SELECTED', notes: 'Autonomous re-route: Supplier B selected' },
              { id: 'SUP-C', name: 'Crestline Global Logistics & Parts', pricePerUnit: 7400, availability: 200, deliveryDays: 1, score: 70, status: 'AVAILABLE', notes: 'Higher price alternative' }
            ]);

            updateAgentState('procurement', true, 'BUSY', {
              currentTask: 'Evaluating suppliers for 78 unit shortage',
              inputReceived: 'EXCEPTION TRIGGERED: Supplier A stock depleted (0 units)',
              currentAction: 'Autonomous Exception Recovery: Re-evaluating Supplier B & C',
              lastDecision: 'Supplier B selected as primary alternative (Score: 94%)',
              rationale: 'Supplier A failed availability check. Autonomous fallback to Supplier B satisfies SLA and budget.',
              confidence: 91,
              nextAction: 'Forward fallback quotation to Finance Agent'
            });
            addActivityLog('procurement', 'EXCEPTION: Primary Supplier A unavailable! Re-negotiating with Supplier B', 'warning');
            addActivityLog('procurement', 'Supplier B recommended: 150 units available @ ₹6,600/unit', 'success');
            addAuditEvent('SUPPLIER_RE_ROUTED', 'Procurement Agent', 'Supplier A unavailable. Re-routed to Supplier B.');

          } else if (scenario === 'budget_breach') {
            // Scenario 2: Budget Breach initially
            setSuppliers([
              { id: 'SUP-A', name: 'Apex Industrial Dynamics', pricePerUnit: 6400, availability: 0, deliveryDays: 5, score: 40, status: 'UNAVAILABLE', notes: 'Out of stock' },
              { id: 'SUP-B', name: 'Bharat Heavy Engineering Solutions', pricePerUnit: 6600, availability: 150, deliveryDays: 2, score: 85, status: 'AVAILABLE', notes: 'Secondary option' },
              { id: 'SUP-C', name: 'Crestline Global Logistics & Parts', pricePerUnit: 7400, availability: 200, deliveryDays: 1, score: 95, status: 'SELECTED', notes: 'High quote: ₹7,400/unit (Total ₹8,88,000)' }
            ]);

            updateAgentState('procurement', true, 'BUSY', {
              currentTask: 'Submitting premium vendor quotation to Finance',
              inputReceived: 'Supplier C express proposal: ₹7,400/unit',
              currentAction: 'Transmitting quotation (₹8,88,000 total)',
              lastDecision: 'Supplier C selected for 1-day express delivery',
              rationale: 'Prioritized speed over cost. Sent to Finance for authorization.',
              confidence: 88,
              nextAction: 'Await Finance sanction'
            });
            addActivityLog('procurement', 'Supplier C quote submitted: ₹8,88,000 (Express 1-day delivery)', 'info');

          } else {
            // Normal Scenario
            setSuppliers(INITIAL_SUPPLIERS);
            updateAgentState('procurement', true, 'BUSY', {
              currentTask: 'Multi-supplier evaluation matrix active',
              inputReceived: '3 qualified vendors evaluated for 78 unit shortage',
              currentAction: 'Ranking options by price, SLA, and reliability score',
              lastDecision: 'Supplier B selected (Price: ₹6,600/unit, Score: 94%)',
              rationale: 'Supplier B balances immediate availability with competitive cost.',
              confidence: 94,
              nextAction: 'Send cost estimate to Finance Agent'
            });
            addActivityLog('procurement', 'Evaluated 3 suppliers. Supplier B recommended (Score: 94%)', 'success');
            addAuditEvent('SUPPLIER_SELECTED', 'Procurement Agent', 'Supplier B chosen at ₹6,600/unit.');
          }

          // STEP 4: Finance Validation (6.8s)
          simulationTimerRef.current = setTimeout(() => {
            setWorkflowStage('FINANCE_VALIDATION');

            if (scenario === 'budget_breach' || scenario === 'multi_exception') {
              // Scenario 2 Exception: Budget breach handling
              updateAgentState('finance', true, 'BUSY', {
                currentTask: 'Evaluating Supplier C quote against cap',
                inputReceived: 'Quote: ₹8,88,000 vs Allocated Cap ₹8,50,000',
                currentAction: 'EXCEPTION DETECTED: Budget Breach of ₹38,000',
                lastDecision: 'REJECTED Initial Quote -> Requested Procurement Re-negotiation',
                rationale: 'Quote exceeds max threshold. Triggered sub-agent negotiation cycle.',
                confidence: 99,
                nextAction: 'Re-evaluate secondary proposal (Supplier B @ ₹7,92,000)'
              });
              addActivityLog('finance', 'EXCEEDS BUDGET: ₹8,88,000 quote rejected! Limit is ₹8,50,000', 'error');

              // Mini sub-step: Finance resolves breach with Procurement
              setTimeout(() => {
                setSuppliers([
                  { id: 'SUP-A', name: 'Apex Industrial Dynamics', pricePerUnit: 6400, availability: 0, deliveryDays: 5, score: 40, status: 'UNAVAILABLE', notes: 'Out of stock' },
                  { id: 'SUP-B', name: 'Bharat Heavy Engineering Solutions', pricePerUnit: 6600, availability: 150, deliveryDays: 2, score: 94, status: 'SELECTED', notes: 'Negotiated fallback accepted' },
                  { id: 'SUP-C', name: 'Crestline Global Logistics & Parts', pricePerUnit: 7400, availability: 200, deliveryDays: 1, score: 60, status: 'REJECTED_BUDGET', notes: 'Rejected by Finance' }
                ]);
                updateAgentState('finance', true, 'BUSY', {
                  currentTask: 'Validating revised Supplier B quote (₹7,92,000)',
                  inputReceived: 'Revised quote: ₹7,92,000',
                  currentAction: 'Verifying budget reserve headroom',
                  lastDecision: 'SANCTION APPROVED (₹58,000 headroom remaining)',
                  rationale: 'Revised quote of ₹7,92,000 complies with ₹8,50,000 budget cap.',
                  confidence: 97,
                  nextAction: 'Dispatch approval to Logistics Agent'
                });
                addActivityLog('finance', 'Budget breach resolved! Supplier B quote of ₹7,92,000 APPROVED', 'success');
                addAuditEvent('FINANCE_APPROVED_REVISED', 'Finance Agent', 'Revised budget of ₹7,92,000 approved after negotiation.');
              }, 1200);

            } else {
              // Normal Finance approval
              updateAgentState('finance', true, 'BUSY', {
                currentTask: 'Sanctioning order budget allocation',
                inputReceived: 'Procurement estimate: ₹7,92,000',
                currentAction: 'Checking corporate liquidity and account reserve',
                lastDecision: 'Budget check PASSED (₹58,000 reserve remaining)',
                rationale: 'Sanctioned ₹7,92,000 within max cap of ₹8,50,000.',
                confidence: 97,
                nextAction: 'Authorize logistics scheduling'
              });
              addActivityLog('finance', 'Budget approved: ₹7,92,000 sanctioned within cap', 'success');
              addAuditEvent('FINANCE_APPROVED', 'Finance Agent', 'Sanctioned budget of ₹7,92,000.');
            }

            // STEP 5: Logistics Feasibility (8.8s)
            simulationTimerRef.current = setTimeout(() => {
              setWorkflowStage('LOGISTICS_FEASIBILITY');

              if (scenario === 'delivery_delay' || scenario === 'multi_exception') {
                // Scenario 3: Delivery Delay
                updateAgentState('logistics', true, 'BUSY', {
                  currentTask: 'Transit route feasibility scan',
                  inputReceived: 'Road alert: Heavy rainfall on Pune-Nagpur Highway (NH-53)',
                  currentAction: 'EXCEPTION DETECTED: Standard road transit delayed by +48 hours',
                  lastDecision: 'Route Re-scheduled via Express Rail Freight',
                  rationale: 'Autonomous re-routing maintains 2-day delivery SLA despite highway disruption.',
                  confidence: 93,
                  nextAction: 'Return feasible transit token to Supervisor'
                });
                addActivityLog('logistics', 'EXCEPTION: Road delay detected on NH-53 (+48h)!', 'warning');
                addActivityLog('logistics', 'Re-routed to Express Rail Cargo: 2-day SLA guaranteed', 'success');
                addAuditEvent('LOGISTICS_RE_ROUTED', 'Logistics Agent', 'Re-routed from Road Freight to Express Rail Cargo.');

              } else {
                // Normal Logistics
                updateAgentState('logistics', true, 'BUSY', {
                  currentTask: 'Evaluating delivery corridor feasibility',
                  inputReceived: 'Origin: Supplier B (Pune), Dest: Nagpur DC',
                  currentAction: 'Scanning route weather, toll gates, and carrier SLA',
                  lastDecision: 'Route APPROVED via Express Freight (2 days)',
                  rationale: '480 km transit clear with 99.2% carrier reliability.',
                  confidence: 96,
                  nextAction: 'Transmit token to Supervisor Agent'
                });
                addActivityLog('logistics', 'Delivery feasibility confirmed: 2-day SLA via Pune-Nagpur corridor', 'info');
                addAuditEvent('LOGISTICS_CONFIRMED', 'Logistics Agent', 'Delivery feasibility verified.');
              }

              // STEP 6: Supervisor Final Decision (10.5s)
              simulationTimerRef.current = setTimeout(() => {
                setWorkflowStage('SUPERVISOR_DECISION');
                updateAgentState('supervisor', true, 'BUSY', {
                  currentTask: 'Evaluating sub-agent feasibility tokens & synthesizing decision',
                  inputReceived: 'Inventory: OK, Procurement: OK, Finance: APPROVED, Logistics: OK',
                  currentAction: 'Synthesizing final execution graph and immutable audit log',
                  lastDecision: 'ORDER APPROVED & EXECUTION AUTHORIZED',
                  rationale: 'All agent constraints satisfied. Supply chain risk score: Low (1.2%).',
                  confidence: 98,
                  nextAction: 'Commit state to Blockchain Audit Ledger'
                });
                addActivityLog('supervisor', 'All sub-agent tokens verified. Final Order Approval granted!', 'success');

                // STEP 7: Completed & Audit Trail (12.0s)
                simulationTimerRef.current = setTimeout(() => {
                  setWorkflowStage('COMPLETED');
                  setIsSimulating(false);

                  setActiveOrder(prev => ({
                    ...prev,
                    status: 'Approved',
                    currentAgent: 'supervisor'
                  }));

                  setOrders(prev =>
                    prev.map(o => (o.id === activeOrder.id ? { ...o, status: 'Approved' } : o))
                  );

                  // Update agent states to online/idle
                  setAgents(prev =>
                    prev.map(a => ({
                      ...a,
                      active: false,
                      status: 'ONLINE',
                      currentTask: 'Monitoring queue'
                    }))
                  );

                  addAuditEvent('PURCHASE_ORDER_RECORDED', 'Audit Engine', `Order ${activeOrder.id} fully verified and recorded on blockchain.`);
                  addActivityLog('AUDIT', `Immutable Audit block recorded for ${activeOrder.id}`, 'success');

                }, 1500);

              }, 1800);

            }, 2200);

          }, 2000);

        }, 1800);

      }, 1500);

    }, 1500);
  };

  const updateOrderStatus = (orderId: string, status: Order['status']) => {
    setOrders(prev => prev.map(o => (o.id === orderId ? { ...o, status } : o)));
    if (activeOrder.id === orderId) {
      setActiveOrder(prev => ({ ...prev, status }));
    }
  };

  useEffect(() => {
    return () => {
      if (simulationTimerRef.current) clearTimeout(simulationTimerRef.current);
    };
  }, []);

  return (
    <DemoContext.Provider
      value={{
        activeOrder,
        orders,
        agents,
        suppliers,
        inventory,
        auditEvents,
        activityLogs,
        workflowStage,
        activeScenario,
        isSimulating,
        selectedAgentId,
        selectedGraphNodeId,
        graphNodes,
        graphEdges,
        runDemoOrder,
        resetDemo,
        setSelectedAgentId,
        setSelectedGraphNodeId,
        setActiveScenario,
        updateOrderStatus
      }}
    >
      {children}
    </DemoContext.Provider>
  );
};

export const useDemo = () => {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error('useDemo must be used within a DemoProvider');
  }
  return context;
};
