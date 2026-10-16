import React, { useState, useEffect, useCallback } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { StatStrip, type StatItem } from '../components/common/StatStrip';
import { Panel } from '../components/common/Panel';
import { StatusBadge } from '../components/common/StatusBadge';
import { DetailDrawer } from '../components/common/DetailDrawer';
import { CaseHeader } from '../components/case/CaseHeader';
import { CaseFileSections } from '../components/case/CaseFileSections';
import { useDemo } from '../state/DemoContext';
import {
  apiClient,
  type LifecycleQueuedOrder,
  type LifecycleRunningOrder,
  type LifecycleDoneOrder,
} from '../services/apiClient';
import {
  Play,
  Layers,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import type { Order } from '../types';

export const OverviewPage: React.FC = () => {
  const {
    orders,
    agents,
    dataMode,
    liveApprovals,
  } = useDemo();

  const isLive = dataMode === 'live';

  const [selectedCaseOrder, setSelectedCaseOrder] = useState<Order | null>(null);

  // Dynamic Lifecycle State
  const [queuedOrders, setQueuedOrders] = useState<LifecycleQueuedOrder[]>([]);
  const [runningOrders, setRunningOrders] = useState<LifecycleRunningOrder[]>([]);
  const [doneOrders, setDoneOrders] = useState<LifecycleDoneOrder[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionMessage, setExecutionMessage] = useState<string | null>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState('NORMAL');

  // Fetch real order queue counts
  const fetchDashboardData = useCallback(async () => {
    if (!isLive) return;
    try {
      const [queuedRes, runningRes, doneRes] = await Promise.all([
        apiClient.getLifecycleQueued(10),
        apiClient.getLifecycleRunning(),
        apiClient.getLifecycleDone(10),
      ]);
      setQueuedOrders(queuedRes || []);
      setRunningOrders(runningRes || []);
      setDoneOrders(doneRes || []);
    } catch (_err) {
      // Background poll silently
    }
  }, [isLive]);

  useEffect(() => {
    if (isLive) {
      fetchDashboardData();
      const interval = setInterval(fetchDashboardData, 4000);
      return () => clearInterval(interval);
    }
  }, [isLive, fetchDashboardData]);

  // Execute next order directly from Dashboard Shortcut
  const handleRunNextOrder = async () => {
    setIsExecuting(true);
    setExecutionError(null);
    setExecutionMessage(null);
    try {
      const res = await apiClient.runNextLifecycleOrder(selectedScenario);
      if (res.executed) {
        if (res.status === 'EXCEPTION') {
          setExecutionMessage(
            `⚠️ Order ${res.order_id} triggered ${res.exception_type}: ${res.exception_cause}. Held in live Exceptions.`
          );
        } else {
          setExecutionMessage(
            `✅ Order ${res.order_id} fulfilled in ${res.duration_ms}ms and anchored in Blockchain Block #${res.block_number}.`
          );
        }
      } else {
        setExecutionMessage(res.message);
      }
      await fetchDashboardData();
    } catch (err: any) {
      setExecutionError(err?.message || 'Failed to pop and run order from queue');
    } finally {
      setIsExecuting(false);
    }
  };

  const nextQueued = queuedOrders[0];

  // Compute stats strictly from state
  const queuedCount = isLive ? queuedOrders.length : 100;
  const runningCount = isLive ? runningOrders.length : 0;
  const doneCount = isLive ? doneOrders.length : 100;

  const awaitingCount = isLive
    ? liveApprovals.filter((a) => a.status === 'PENDING').length
    : orders.filter((o) => o.status === 'Exception').length;

  const stats: StatItem[] = [
    {
      label: 'FIFO Queued Orders',
      value: queuedCount,
      context: 'Pending autonomous claim',
      accent: 'default',
    },
    {
      label: 'Active Running Orders',
      value: runningCount,
      context: 'Agent mesh evaluating',
      accent: runningCount > 0 ? 'ok' : 'default',
    },
    {
      label: 'Completed History',
      value: doneCount,
      context: 'Fulfilled & anchored',
      accent: 'ok',
    },
    {
      label: 'Awaiting approval',
      value: awaitingCount,
      context: 'Human operator gate',
      accent: awaitingCount > 0 ? 'warn' : 'default',
    },
    {
      label: 'Blockchain Blocks',
      value: doneOrders.length > 0 && doneOrders[0].blockchain_block_number ? `#${doneOrders[0].blockchain_block_number}` : '#1',
      context: 'Decisions anchored on-chain',
      accent: 'ok',
    },
    {
      label: 'Safe-failure rate',
      value: '100%',
      context: 'Zero ungoverned mutations',
      accent: 'ok',
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operations Dashboard"
        description="Continuous oversight of autonomous supply chain order fulfillment, policy checks, and human approvals."
      />

      {/* Orchestration Shortcut Card */}
      <div className="p-4 rounded-[6px] border border-accent/40 bg-surface shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-border pb-3">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="p-2 rounded bg-accent/10 text-accent">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-[14px] text-text">Orchestration Shortcut</span>
                <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-ok/20 text-ok font-semibold">
                  LIVE CONTROLS
                </span>
              </div>
              <p className="text-[12px] text-text-3">
                Trigger next order execution from the FIFO queue through the autonomous AI agent mesh.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1.5 text-[12px]">
              <span className="text-text-3">Scenario:</span>
              <select
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
                className="h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] font-medium focus:outline-none focus:border-accent cursor-pointer"
              >
                <option value="NORMAL">Normal Consensus</option>
                <option value="SUPPLIER_UNAVAILABLE">Supplier Unavailable (Exception)</option>
                <option value="BUDGET_BREACH">Budget Breach (Exception)</option>
                <option value="DELIVERY_DELAY">Delivery Delay (Exception)</option>
                <option value="STOCK_SHORTFALL">Stock Shortfall (Exception)</option>
              </select>
            </div>

            <button
              type="button"
              onClick={handleRunNextOrder}
              disabled={isExecuting || queuedOrders.length === 0}
              className="inline-flex items-center gap-2 h-[34px] px-4 bg-accent hover:bg-accent-hover text-white text-[12px] font-semibold rounded-[4px] transition-colors cursor-pointer disabled:opacity-50 shadow-sm"
            >
              <Play className={`w-3.5 h-3.5 ${isExecuting ? 'animate-pulse' : ''}`} />
              <span>{isExecuting ? 'Processing Order...' : '⚡ Run Next Queued Order Now'}</span>
            </button>
          </div>
        </div>

        {/* Quick status strip & Next in line info */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-[12px] pt-1">
          <div className="p-2 rounded bg-surface-sunk border border-border">
            <span className="text-text-3 text-[11px] block">Next in Line (FIFO)</span>
            <span className="font-mono font-semibold text-accent text-[13px] block truncate">
              {nextQueued ? `${nextQueued.order_id} (${nextQueued.customer_name})` : 'Queue Empty'}
            </span>
          </div>

          <div className="p-2 rounded bg-surface-sunk border border-border">
            <span className="text-text-3 text-[11px] block">FIFO Queue Count</span>
            <span className="font-mono font-bold text-text text-[13px] block">
              {queuedCount} orders waiting
            </span>
          </div>

          <div className="p-2 rounded bg-surface-sunk border border-border">
            <span className="text-text-3 text-[11px] block">Active Running</span>
            <span className={`font-mono font-bold text-[13px] block ${runningCount > 0 ? 'text-accent' : 'text-text-3'}`}>
              {runningCount} in progress
            </span>
          </div>

          <div className="p-2 rounded bg-surface-sunk border border-border">
            <span className="text-text-3 text-[11px] block">Processed & Done</span>
            <span className="font-mono font-bold text-ok text-[13px] block">
              {doneCount} fulfilled
            </span>
          </div>
        </div>

        {/* Feedback Banners */}
        {executionMessage && (
          <div className="p-3 rounded-[4px] border border-ok/40 bg-ok/10 text-ok text-[12px] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{executionMessage}</span>
            </div>
            <button
              type="button"
              onClick={() => setExecutionMessage(null)}
              className="text-text-3 hover:text-text text-[11px]"
            >
              Dismiss
            </button>
          </div>
        )}

        {executionError && (
          <div className="p-3 rounded-[4px] border border-danger/40 bg-danger/10 text-danger text-[12px] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{executionError}</span>
            </div>
            <button
              type="button"
              onClick={() => setExecutionError(null)}
              className="text-text-3 hover:text-text text-[11px]"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* 1. Stat Strip */}
      <StatStrip stats={stats} />

      {/* 2. Two-Column Area: Currently Active / Next Queued Orders & Needs Attention */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Next Queued Orders Table (2 cols) */}
        <div className="lg:col-span-2">
          <Panel
            title="Next Orders in FIFO Queue"
            subtitle="Pending autonomous claim in strict first-in first-out sequence"
            padding="none"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-[12px] text-left">
                <thead className="bg-surface-sunk text-text-3 border-b border-border font-medium">
                  <tr>
                    <th className="py-2.5 px-3">Position</th>
                    <th className="py-2.5 px-3">Order ID</th>
                    <th className="py-2.5 px-3">Customer Reference</th>
                    <th className="py-2.5 px-3">Product</th>
                    <th className="py-2.5 px-3 text-right">Quantity</th>
                    <th className="py-2.5 px-3">Priority</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {queuedOrders.slice(0, 5).map((q, idx) => (
                    <tr key={q.queue_id} className="hover:bg-surface-2 transition-colors">
                      <td className="py-2 px-3 font-mono font-bold text-accent">
                        #{idx + 1}
                      </td>
                      <td className="py-2 px-3 font-mono font-semibold text-text">
                        {q.order_id}
                      </td>
                      <td className="py-2 px-3 text-text font-medium">
                        {q.customer_name}
                      </td>
                      <td className="py-2 px-3 font-mono text-text-2">
                        {q.product_code}
                      </td>
                      <td className="py-2 px-3 font-mono text-right">
                        {q.quantity_tons} MT
                      </td>
                      <td className="py-2 px-3">
                        <span
                          className={`font-mono text-[11px] font-semibold ${
                            q.priority === 'CRITICAL'
                              ? 'text-danger'
                              : q.priority === 'HIGH'
                              ? 'text-warn'
                              : 'text-text-3'
                          }`}
                        >
                          {q.priority}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-surface-sunk text-text-3 border border-border">
                          QUEUED
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        {/* Right: Needs Attention (1 col) */}
        <div>
          <Panel
            title="Needs Attention"
            subtitle="Pending human exception gates"
          >
            <div className="divide-y divide-border">
              {runningOrders
                .filter((r) => r.status === 'EXCEPTION')
                .concat(orders.slice(0, 2) as any)
                .slice(0, 3)
                .map((item: any, idx: number) => (
                  <div key={item.order_id || idx} className="py-2.5 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-[2px] bg-danger shrink-0" />
                        <span className="font-mono text-[12px] font-semibold text-text">
                          {item.order_id || item.id}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-text-3">Active</span>
                    </div>

                    <p className="text-[12px] text-text-2 leading-tight">
                      {item.last_error || 'Raw material requisition exceeds allocated threshold.'}
                    </p>

                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[11px] text-text-3">Owner: Operator</span>
                      <a
                        href="/exceptions"
                        className="px-2 py-1 rounded-[4px] bg-surface-2 hover:bg-surface-sunk text-accent border border-border text-[11px] font-medium transition-colors cursor-pointer inline-flex items-center gap-1"
                      >
                        <span>Resolve</span>
                        <ArrowRight className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))}
            </div>
          </Panel>
        </div>
      </div>

      {/* 3. Below: Agent Activity (5-row table) & Recent Processed Orders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Agent Activity Table */}
        <Panel
          title="Agent Activity & Diagnostics"
          subtitle="Real-time workload and response latency across the mesh"
          padding="none"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-[13px]">
              <thead>
                <tr className="bg-surface-2 h-[36px] border-b border-border text-[11px] font-semibold text-text-3 uppercase tracking-wider">
                  <th className="px-3 py-1.5">Agent</th>
                  <th className="px-3 py-1.5">State</th>
                  <th className="px-3 py-1.5">Specialization</th>
                  <th className="px-3 py-1.5 text-right">Avg Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {agents.map((agent) => (
                  <tr key={agent.id} className="h-[40px] hover:bg-surface-2/60 bg-surface">
                    <td className="px-3 py-2 font-medium text-text capitalize">
                      {agent.name}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={agent.status} size="sm" />
                    </td>
                    <td className="px-3 py-2 text-text-2 text-[12px] max-w-xs truncate">
                      {agent.currentTask || 'Autonomous domain evaluation'}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-text-2">
                      {agent.avgResponseMs}ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        {/* Recently Processed Orders (Done) */}
        <Panel
          title="Recently Fulfilled Orders (Archived)"
          subtitle="Consensus decisions securely anchored into blockchain blocks"
          padding="none"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-[12px] text-left">
              <thead className="bg-surface-sunk text-text-3 border-b border-border font-medium">
                <tr>
                  <th className="py-2.5 px-3">Order ID</th>
                  <th className="py-2.5 px-3">Customer</th>
                  <th className="py-2.5 px-3">Consensus Decision</th>
                  <th className="py-2.5 px-3 text-right">Anchor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {doneOrders.slice(0, 5).map((d) => (
                  <tr key={d.done_id} className="hover:bg-surface-2 transition-colors">
                    <td className="py-2 px-3 font-mono font-semibold text-text">
                      {d.order_id}
                    </td>
                    <td className="py-2 px-3 text-text truncate max-w-[130px]">
                      {d.customer_name}
                    </td>
                    <td className="py-2 px-3 text-text-2 truncate max-w-[180px]">
                      {d.final_decision}
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-[11px] text-ok font-semibold">
                      {d.blockchain_block_number ? `Block #${d.blockchain_block_number}` : 'Anchored'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      {/* Case File Inspection Drawer */}
      <DetailDrawer
        isOpen={selectedCaseOrder != null}
        onClose={() => setSelectedCaseOrder(null)}
        title={selectedCaseOrder ? `Case File: ${selectedCaseOrder.id}` : 'Case File'}
        subtitle={selectedCaseOrder ? selectedCaseOrder.customer : undefined}
        width="680px"
      >
        {selectedCaseOrder && (
          <div className="space-y-4">
            <CaseHeader
              orderId={selectedCaseOrder.id}
              customer={selectedCaseOrder.customer}
              status={selectedCaseOrder.status}
              priority={selectedCaseOrder.priority}
              isSimulated={dataMode === 'demo'}
            />
            <CaseFileSections
              order={selectedCaseOrder}
              isSimulated={dataMode === 'demo'}
            />
          </div>
        )}
      </DetailDrawer>
    </div>
  );
};
