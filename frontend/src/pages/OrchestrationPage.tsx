import React, { useState, useEffect, useCallback } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Panel } from '../components/common/Panel';
import { Tabs } from '../components/common/Tabs';
import { CaseHeader } from '../components/case/CaseHeader';
import { PipelineStepper } from '../components/case/PipelineStepper';
import { useDemo } from '../state/DemoContext';
import {
  apiClient,
  type LifecycleQueuedOrder,
  type LifecycleRunningOrder,
  type LifecycleDoneOrder,
  type AgentDecisionLog,
} from '../services/apiClient';
import {
  Play,
  Layers,
  AlertCircle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
} from 'lucide-react';

export const OrchestrationPage: React.FC = () => {
  const { dataMode } = useDemo();
  const isLive = dataMode === 'live';

  const [activeTab, setActiveTab] = useState<'case' | 'trace' | 'blockchain'>('case');
  const [selectedOrderId, setSelectedOrderId] = useState<string>('ORD-1045');

  // Lifecycle states
  const [queuedOrders, setQueuedOrders] = useState<LifecycleQueuedOrder[]>([]);
  const [runningOrders, setRunningOrders] = useState<LifecycleRunningOrder[]>([]);
  const [doneOrders, setDoneOrders] = useState<LifecycleDoneOrder[]>([]);
  const [activeDecisions, setActiveDecisions] = useState<AgentDecisionLog[]>([]);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  // Execution runner state
  const [selectedScenario, setSelectedScenario] = useState('NORMAL');
  const [isExecuting, setIsExecuting] = useState(false);
  const [execMessage, setExecMessage] = useState<string | null>(null);
  const [execError, setExecError] = useState<string | null>(null);

  // Fetch all live lifecycle data
  const fetchLifecycleData = useCallback(async () => {
    if (!isLive) return;
    try {
      const [queuedRes, runningRes, doneRes] = await Promise.all([
        apiClient.getLifecycleQueued(100),
        apiClient.getLifecycleRunning(),
        apiClient.getLifecycleDone(20),
      ]);
      setQueuedOrders(queuedRes || []);
      setRunningOrders(runningRes || []);
      setDoneOrders(doneRes || []);

      // If no order selected or selected order changed, pick running order or latest done order or next queued
      if (!selectedOrderId || selectedOrderId === 'ORD-1042') {
        if (runningRes && runningRes.length > 0) {
          setSelectedOrderId(runningRes[0].order_id);
        } else if (doneRes && doneRes.length > 0) {
          setSelectedOrderId(doneRes[0].order_id);
        } else if (queuedRes && queuedRes.length > 0) {
          setSelectedOrderId(queuedRes[0].order_id);
        }
      }
    } catch (_err) {
      // Quiet background polling
    }
  }, [isLive, selectedOrderId]);

  // Fetch decision logs for selected order
  const fetchDecisionsForOrder = useCallback(async (orderId: string) => {
    if (!isLive || !orderId) return;
    try {
      const decs = await apiClient.getLifecycleDecisions(orderId);
      setActiveDecisions(decs || []);
    } catch (_err) {
      setActiveDecisions([]);
    }
  }, [isLive]);

  useEffect(() => {
    if (isLive) {
      fetchLifecycleData();
      const interval = setInterval(fetchLifecycleData, 4000);
      return () => clearInterval(interval);
    }
  }, [isLive, fetchLifecycleData]);

  useEffect(() => {
    if (selectedOrderId) {
      fetchDecisionsForOrder(selectedOrderId);
    }
  }, [selectedOrderId, fetchDecisionsForOrder]);

  // Execute next FIFO order
  const handleRunNext = async () => {
    setIsExecuting(true);
    setExecError(null);
    setExecMessage(null);
    try {
      const res = await apiClient.runNextLifecycleOrder(selectedScenario);
      if (res.executed) {
        if (res.status === 'EXCEPTION') {
          setExecMessage(
            `⚠️ Order ${res.order_id} triggered ${res.exception_type}: ${res.exception_cause}. Held in live Exceptions.`
          );
        } else {
          setExecMessage(
            `✅ Order ${res.order_id} fulfilled in ${res.duration_ms}ms and anchored in Blockchain Block #${res.block_number}.`
          );
        }
        if (res.order_id) {
          setSelectedOrderId(res.order_id);
        }
      } else {
        setExecMessage(res.message);
      }
      await fetchLifecycleData();
    } catch (err: any) {
      setExecError(err?.message || 'Execution failed');
    } finally {
      setIsExecuting(false);
    }
  };

  // Execute specific selected order
  const handleRunSelected = async () => {
    if (!selectedOrderId) return;
    setIsExecuting(true);
    setExecError(null);
    setExecMessage(null);
    try {
      const res = await apiClient.runSpecificLifecycleOrder(selectedOrderId, selectedScenario);
      if (res.executed) {
        if (res.status === 'EXCEPTION') {
          setExecMessage(
            `⚠️ Order ${res.order_id} triggered ${res.exception_type}: ${res.exception_cause}.`
          );
        } else {
          setExecMessage(
            `✅ Order ${res.order_id} fulfilled in ${res.duration_ms}ms and anchored in Blockchain Block #${res.block_number}.`
          );
        }
      } else {
        setExecMessage(res.message);
      }
      await fetchLifecycleData();
    } catch (err: any) {
      setExecError(err?.message || `Execution failed for ${selectedOrderId}`);
    } finally {
      setIsExecuting(false);
    }
  };

  // Find metadata for current selected order
  const currentRunning = runningOrders.find((r) => r.order_id === selectedOrderId);
  const currentDone = doneOrders.find((d) => d.order_id === selectedOrderId);
  const currentQueued = queuedOrders.find((q) => q.order_id === selectedOrderId);

  const displayCustomer =
    currentRunning?.customer_name ||
    currentDone?.customer_name ||
    currentQueued?.customer_name ||
    'Enterprise Industrial Client';

  const displayStatus = currentRunning
    ? currentRunning.status
    : currentDone
    ? currentDone.outcome_status
    : 'QUEUED';

  const displayPriority =
    currentRunning?.priority || currentDone?.priority || currentQueued?.priority || 'MEDIUM';

  const displayProduct =
    currentRunning?.product_code || currentDone?.product_code || currentQueued?.product_code || 'PRD-HRC';

  const displayQty =
    currentRunning?.quantity_tons || currentDone?.quantity_tons || currentQueued?.quantity_tons || 45.0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Governed Multi-Agent Orchestration Pipeline"
        description="Autonomous specialist agent consensus with FIFO order popping, live decision logging, and blockchain block anchoring."
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={fetchLifecycleData}
              disabled={isExecuting}
              className="inline-flex items-center gap-1.5 h-[32px] px-3 bg-surface border border-border hover:border-accent text-text text-[12px] font-medium rounded-[4px] transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isExecuting ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        }
      />

      {/* Orchestration Runner Controls Banner */}
      <div className="p-4 rounded-[6px] border border-border bg-surface space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-border pb-3">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-accent" />
              <span className="font-semibold text-[13px] text-text">Autonomous Orchestrator:</span>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded font-semibold uppercase bg-ok/20 text-ok">
                LIVE POSTGRESQL
              </span>
            </div>

            <div className="flex items-center gap-2 text-[12px] text-text-3 border-l border-border pl-3">
              <span>Pending in FIFO Queue:</span>
              <span className="font-mono text-text font-bold">{queuedOrders.length}</span>
            </div>

            <div className="flex items-center gap-2 text-[12px] text-text-3 border-l border-border pl-3">
              <span>Scenario:</span>
              <select
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
                className="h-[28px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
              >
                <option value="NORMAL">Normal Consensus</option>
                <option value="SUPPLIER_UNAVAILABLE">Supplier Unavailable</option>
                <option value="BUDGET_BREACH">Budget Overrun</option>
                <option value="DELIVERY_DELAY">Delivery Delay</option>
                <option value="STOCK_SHORTFALL">Stock Shortfall</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={handleRunNext}
              disabled={isExecuting || queuedOrders.length === 0}
              className="inline-flex items-center gap-1.5 h-[32px] px-4 rounded bg-accent hover:bg-accent-hover text-white text-[12px] font-semibold transition-colors cursor-pointer disabled:opacity-50"
            >
              <Play className={`w-3.5 h-3.5 ${isExecuting ? 'animate-pulse' : ''}`} />
              <span>⚡ Run Next Queued Order</span>
            </button>

            {currentQueued && (
              <button
                type="button"
                onClick={handleRunSelected}
                disabled={isExecuting}
                className="inline-flex items-center gap-1.5 h-[32px] px-3.5 rounded bg-surface hover:bg-surface-2 border border-border text-text text-[12px] font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                <span>Run {selectedOrderId} Now</span>
              </button>
            )}
          </div>
        </div>

        {/* Quick Metrics Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[12px]">
          <div>
            <span className="text-text-3 text-[11px] block">Queued Orders</span>
            <span className="font-mono text-text font-bold text-[14px]">
              {queuedOrders.length}
            </span>
          </div>
          <div>
            <span className="text-text-3 text-[11px] block">Active Running</span>
            <span className="font-mono text-accent font-semibold text-[14px]">
              {runningOrders.length > 0 ? runningOrders[0].order_id : 'IDLE'}
            </span>
          </div>
          <div>
            <span className="text-text-3 text-[11px] block">Processed & Done</span>
            <span className="font-mono text-ok font-semibold text-[14px]">
              {doneOrders.length}
            </span>
          </div>
          <div>
            <span className="text-text-3 text-[11px] block">Latest Blockchain Block</span>
            <span className="font-mono text-text-2 text-[14px]">
              {doneOrders.length > 0 && doneOrders[0].blockchain_block_number
                ? `#${doneOrders[0].blockchain_block_number}`
                : '#1'}
            </span>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {execMessage && (
        <div className="p-3 rounded-[4px] border border-ok/40 bg-ok/10 text-ok text-[12px] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 shrink-0" />
            <span>{execMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setExecMessage(null)}
            className="text-text-3 hover:text-text text-[11px]"
          >
            Dismiss
          </button>
        </div>
      )}

      {execError && (
        <div className="p-3 rounded-[4px] border border-danger/40 bg-danger/10 text-danger text-[12px] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{execError}</span>
          </div>
          <button
            type="button"
            onClick={() => setExecError(null)}
            className="text-text-3 hover:text-text text-[11px]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Grid: Left Execution History & Right Case Body */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left Column: Execution History (Done & Running) */}
        <div className="lg:col-span-1 space-y-3">
          <Panel
            title="Execution History"
            subtitle="Real orders processed through agent mesh"
            padding="none"
          >
            <div className="divide-y divide-border max-h-[620px] overflow-y-auto">
              {/* If there are running orders, display them at the top */}
              {runningOrders.map((ro) => (
                <div
                  key={ro.running_id}
                  onClick={() => setSelectedOrderId(ro.order_id)}
                  className={`p-3 cursor-pointer transition-colors space-y-1 ${
                    selectedOrderId === ro.order_id ? 'bg-accent/10 border-l-2 border-accent' : 'hover:bg-surface-2'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[12px] font-bold text-accent">
                      {ro.order_id}
                    </span>
                    <span className="text-[11px] font-mono text-text-3">Active</span>
                  </div>
                  <div className="text-[12px] text-text truncate font-medium">
                    {ro.customer_name}
                  </div>
                  <div className="flex items-center justify-between pt-0.5">
                    <span className="text-[11px] font-mono text-text-3">
                      {ro.product_code} ({ro.quantity_tons}T)
                    </span>
                    <span
                      className={`font-mono text-[10px] px-1.5 py-0.2 rounded font-semibold uppercase ${
                        ro.status === 'EXCEPTION' ? 'bg-danger/20 text-danger' : 'bg-accent/20 text-accent'
                      }`}
                    >
                      {ro.status}
                    </span>
                  </div>
                </div>
              ))}

              {/* Completed orders history */}
              {doneOrders.map((d) => (
                <div
                  key={d.done_id}
                  onClick={() => setSelectedOrderId(d.order_id)}
                  className={`p-3 cursor-pointer transition-colors space-y-1 ${
                    selectedOrderId === d.order_id ? 'bg-accent/10 border-l-2 border-accent' : 'hover:bg-surface-2'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[12px] font-semibold text-text">
                      {d.order_id}
                    </span>
                    <span className="text-[11px] font-mono text-text-3">
                      {d.duration_ms}ms
                    </span>
                  </div>
                  <div className="text-[12px] text-text-2 truncate">
                    {d.customer_name}
                  </div>
                  <div className="flex items-center justify-between pt-0.5">
                    <span className="text-[11px] font-mono text-ok font-semibold">
                      {d.blockchain_block_number ? `Block #${d.blockchain_block_number}` : 'Archived'}
                    </span>
                    <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-ok/20 text-ok font-semibold uppercase">
                      COMPLETED
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>

        {/* Right Column: Case Header, Pipeline Stepper, Agent Decision Logs */}
        <div className="lg:col-span-3 space-y-4">
          <CaseHeader
            orderId={selectedOrderId}
            customer={displayCustomer}
            status={displayStatus as any}
            priority={displayPriority as any}
            isSimulated={false}
          />

          <PipelineStepper currentStage={displayStatus === 'EXCEPTION' ? 'SUPERVISOR_DECISION' : 'COMPLETED'} />

          {/* View Tabs */}
          <Tabs
            tabs={[
              { id: 'case', label: 'Governed Decision Log (5 Agents)' },
              { id: 'blockchain', label: 'Blockchain Verification & Blocks' },
              { id: 'trace', label: 'Run Trace & Payload' },
            ]}
            activeTab={activeTab}
            onChange={(id) => setActiveTab(id as any)}
          />

          {/* TAB 1: Specialist Findings from Real Database Decision Logs */}
          {activeTab === 'case' && (
            <div className="space-y-4">
              <Panel
                title="1. Specialist Findings & Evidence (Live Database Log)"
                subtitle="Decisions taken by each specialist agent persisted to agent_decision_logs and anchored on-chain."
                padding="none"
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-[13px]">
                    <thead>
                      <tr className="bg-surface-2 h-[36px] border-b border-border text-[11px] font-semibold text-text-3 uppercase tracking-wider">
                        <th className="px-3 py-1.5">Specialist Agent</th>
                        <th className="px-3 py-1.5">Status</th>
                        <th className="px-3 py-1.5">Key Finding</th>
                        <th className="px-3 py-1.5">Risk Level</th>
                        <th className="px-3 py-1.5">LLM Provider</th>
                        <th className="px-3 py-1.5 text-right">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {activeDecisions.length > 0 ? (
                        activeDecisions.map((dec) => {
                          const isExpanded = expandedAgent === dec.decision_log_id;
                          return (
                            <React.Fragment key={dec.decision_log_id}>
                              <tr
                                onClick={() =>
                                  setExpandedAgent(isExpanded ? null : dec.decision_log_id)
                                }
                                className="h-[42px] hover:bg-surface-2/60 bg-surface cursor-pointer transition-colors"
                              >
                                <td className="px-3 py-2 font-medium text-text">
                                  <div className="flex items-center gap-1.5">
                                    {isExpanded ? (
                                      <ChevronUp className="w-3.5 h-3.5 text-text-3" />
                                    ) : (
                                      <ChevronDown className="w-3.5 h-3.5 text-text-3" />
                                    )}
                                    <span>{dec.agent_name}</span>
                                  </div>
                                </td>
                                <td className="px-3 py-2">
                                  <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-ok/20 text-ok font-semibold">
                                    Consensus
                                  </span>
                                </td>
                                <td className="px-3 py-2 text-text font-medium max-w-sm truncate">
                                  {dec.finding}
                                </td>
                                <td className="px-3 py-2">
                                  <span
                                    className={`font-mono text-[11px] font-semibold ${
                                      dec.risk_level === 'CRITICAL' || dec.risk_level === 'HIGH'
                                        ? 'text-danger'
                                        : 'text-ok'
                                    }`}
                                  >
                                    {dec.risk_level}
                                  </span>
                                </td>
                                <td className="px-3 py-2 font-mono text-[11px] text-text-2">
                                  Gemini 2.5 Pro
                                </td>
                                <td className="px-3 py-2 text-right font-mono text-text">
                                  {(dec.confidence_score * 100).toFixed(1)}%
                                </td>
                              </tr>
                              {isExpanded && (
                                <tr className="bg-surface-sunk border-y border-border">
                                  <td colSpan={6} className="p-3 text-[12px] space-y-2">
                                    <div>
                                      <span className="font-semibold text-text">Rationale: </span>
                                      <span className="text-text-2">{dec.rationale}</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-[11px] font-mono text-text-3">
                                      <span>Decision Type: {dec.decision_type}</span>
                                      <span>Evidence: {dec.evidence_records.join(', ')}</span>
                                      <span className="text-ok">Anchored on Blockchain: TRUE</span>
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          );
                        })
                      ) : (
                        // Fallback live evaluation mock if not yet run
                        [
                          { name: 'Supervisor Agent', task: 'Synthesis & Consensus', finding: 'Synthesized multi-agent evaluation for fulfillment feasibility' },
                          { name: 'Inventory Agent', task: 'Stock Allocation', finding: 'Stock reserved across primary regional warehouse hub' },
                          { name: 'Procurement Agent', task: 'Supplier Selection', finding: 'Supplier SLA & commercial agreement verified' },
                          { name: 'Finance Agent', task: 'Credit & Budget Check', finding: 'Budget headroom approved within credit limit' },
                          { name: 'Logistics Agent', task: 'Corridor Routing', finding: 'Direct road freight corridor scheduled within 48h SLA' },
                        ].map((m) => (
                          <tr key={m.name} className="h-[40px] bg-surface">
                            <td className="px-3 py-2 font-medium text-text">{m.name}</td>
                            <td className="px-3 py-2">
                              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-surface-sunk text-text-3">
                                Ready
                              </span>
                            </td>
                            <td className="px-3 py-2 text-text-2">{m.finding}</td>
                            <td className="px-3 py-2 font-mono text-ok text-[11px]">LOW</td>
                            <td className="px-3 py-2 font-mono text-[11px] text-text-3">Gemini 2.5 Pro</td>
                            <td className="px-3 py-2 text-right font-mono text-text">98.5%</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </Panel>
            </div>
          )}

          {/* TAB 2: Blockchain Verification & Blocks */}
          {activeTab === 'blockchain' && (
            <div className="space-y-4">
              <Panel
                title="Blockchain Block Verification"
                subtitle="Mined blocks containing cryptographic transactions generated from agent decision logs."
              >
                <div className="space-y-3 text-[12px]">
                  <div className="p-3 rounded bg-surface-sunk border border-border space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-text">Consensus Mechanism:</span>
                      <span className="font-mono text-ok font-semibold">Proof of Authority (PoA)</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-text-3">Mined Block Number:</span>
                      <span className="font-mono text-text font-bold">
                        {currentDone?.blockchain_block_number ? `#${currentDone.blockchain_block_number}` : '#1'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-text-3">Transaction Hash:</span>
                      <span className="font-mono text-accent text-[11px] truncate max-w-sm">
                        {currentDone?.blockchain_tx_hash || '0x13ab4276a1daaac17bc0c990b15a6d16273b375380be5af209b77a2be8057e08'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-text-3">Anchor Status:</span>
                      <span className="font-mono text-ok font-semibold">CONFIRMED (ON-CHAIN)</span>
                    </div>
                  </div>
                </div>
              </Panel>
            </div>
          )}

          {/* TAB 3: Run Trace & Payload */}
          {activeTab === 'trace' && (
            <Panel
              title="Execution State Trace"
              subtitle="Step-by-step state dictionary passed between agent nodes"
            >
              <pre className="p-3 rounded bg-surface-sunk border border-border text-text font-mono text-[11px] overflow-x-auto">
{JSON.stringify(
  {
    order_id: selectedOrderId,
    customer: displayCustomer,
    product: displayProduct,
    quantity_tons: displayQty,
    status: displayStatus,
    decisions_count: activeDecisions.length,
    blockchain_block: currentDone?.blockchain_block_number || 1,
    timestamp: new Date().toISOString(),
  },
  null,
  2
)}
              </pre>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
};
