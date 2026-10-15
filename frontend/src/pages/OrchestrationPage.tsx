import React, { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Panel } from '../components/common/Panel';
import { StatusBadge } from '../components/common/StatusBadge';
import { Tabs } from '../components/common/Tabs';
import { CaseHeader } from '../components/case/CaseHeader';
import { PipelineStepper } from '../components/case/PipelineStepper';
import { CaseFileSections } from '../components/case/CaseFileSections';
import { useDemo } from '../state/DemoContext';
import { apiClient } from '../services/apiClient';
import type { DemoScenario } from '../types';

export const OrchestrationPage: React.FC = () => {
  const {
    dataMode,
    isLiveConnected,
    activeScenario,
    setActiveScenario,
    workflowStage,
    orders,
    wsConnectionState,
  } = useDemo();

  const isLive = dataMode === 'live';
  const isExecutionAllowed = isLive && isLiveConnected;

  const [activeTab, setActiveTab] = useState<'case' | 'trace'>('case');
  const [selectedOrderId, setSelectedOrderId] = useState('ORD-1042');
  const [isExecuting, setIsExecuting] = useState(false);
  const [execError, setExecError] = useState<string | null>(null);

  const handleExecute = async () => {
    if (!isExecutionAllowed) return;
    setIsExecuting(true);
    setExecError(null);
    try {
      await apiClient.executeOrchestration(selectedOrderId);
    } catch (err: any) {
      setExecError(err?.message || 'Orchestration execution failed');
    } finally {
      setIsExecuting(false);
    }
  };

  const disabledReason = !isLive
    ? 'Mode is Simulated. Switch to live mode to execute governed LangGraph orchestration.'
    : !isLiveConnected
    ? 'Backend health check failed. Ensure FastAPI service is running on port 8000.'
    : isExecuting
    ? 'Execution in progress.'
    : '';

  const activeOrder = orders.find((o) => o.id === selectedOrderId) || orders[0];

  const pastRuns = [
    { id: 'RUN-2026-904', orderId: 'ORD-1042', status: 'approved', time: '19:15', scenario: 'Budget overrun' },
    { id: 'RUN-2026-903', orderId: 'ORD-1039', status: 'completed', time: '18:42', scenario: 'Normal flow' },
    { id: 'RUN-2026-902', orderId: 'ORD-1035', status: 'awaiting_approval', time: '17:30', scenario: 'Supplier stockout' },
    { id: 'RUN-2026-901', orderId: 'ORD-1031', status: 'blocked', time: '16:04', scenario: 'Margin breach' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Governed Orchestration Pipeline"
        description="Deterministic LangGraph agent mesh execution, state transition tracking, and policy enforcement."
      />

      {/* Top Controls Bar */}
      <div className="p-3.5 rounded-[6px] border border-border bg-surface flex flex-col md:flex-row md:items-center justify-between gap-4 text-[13px]">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="text-text-3 text-[12px]">Order / Requisition:</span>
            <select
              value={selectedOrderId}
              onChange={(e) => setSelectedOrderId(e.target.value)}
              className="h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] font-mono focus:outline-none focus:border-accent cursor-pointer"
            >
              {orders.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.id} ({o.customer})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-text-3 text-[12px]">Scenario:</span>
            <select
              value={activeScenario}
              onChange={(e) => setActiveScenario(e.target.value as DemoScenario)}
              className="h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
            >
              <option value="normal">Normal fulfilment</option>
              <option value="supplier_unavailable">Supplier unavailable</option>
              <option value="budget_breach">Budget overrun</option>
              <option value="delivery_delay">Delivery delay</option>
              <option value="multi_exception">Combined failure</option>
            </select>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center gap-2">
          {disabledReason && (
            <span className="text-[11px] text-text-3 max-w-xs text-right">
              {disabledReason}
            </span>
          )}
          <button
            type="button"
            onClick={handleExecute}
            disabled={!isExecutionAllowed || isExecuting}
            title={disabledReason || 'Execute governed orchestration pipeline'}
            className="h-[32px] px-4 bg-accent hover:bg-accent-hover text-white text-[12px] font-medium rounded-[4px] transition-colors cursor-pointer disabled:bg-surface-2 disabled:text-text-3 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {isExecuting ? 'Executing pipeline...' : 'Execute governed pipeline'}
          </button>
        </div>
      </div>

      {/* Execution error message if any */}
      {execError && (
        <div className="p-3 rounded-[4px] border border-danger/40 bg-surface text-danger text-[12px] font-mono">
          {execError}
        </div>
      )}

      {/* Diagnostics panel when execution is blocked */}
      {!isExecutionAllowed && (
        <div className="p-4 rounded-[6px] border border-border bg-surface-2/40 text-[12px] space-y-2">
          <div className="font-semibold text-text text-[13px]">
            Why live execution is unavailable:
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-text-2">
            <div>
              <span className="text-text-3 block text-[11px]">Operating Mode:</span>
              <span className="font-mono text-text capitalize">{dataMode}</span>
            </div>
            <div>
              <span className="text-text-3 block text-[11px]">Backend Host:</span>
              <span className="font-mono text-text">localhost:8000</span>
            </div>
            <div>
              <span className="text-text-3 block text-[11px]">Health Check:</span>
              <span className={`font-mono ${isLiveConnected ? 'text-ok' : 'text-danger'}`}>
                {isLiveConnected ? 'Reachable' : 'Unreachable'}
              </span>
            </div>
            <div>
              <span className="text-text-3 block text-[11px]">Database:</span>
              <span className="font-mono text-text">{isLiveConnected ? 'Connected' : 'Disconnected'}</span>
            </div>
            <div>
              <span className="text-text-3 block text-[11px]">Realtime WS:</span>
              <span className="font-mono text-text">{wsConnectionState}</span>
            </div>
          </div>
        </div>
      )}

      {/* Main Layout: Left Run History (240px) & Right Case / Stepper */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left Column: Run History */}
        <div className="lg:col-span-1">
          <Panel
            title="Run History"
            subtitle="Recent pipeline evaluations"
            padding="none"
          >
            <div className="divide-y divide-border">
              {pastRuns.map((run) => (
                <div
                  key={run.id}
                  className="p-3 hover:bg-surface-2 cursor-pointer transition-colors space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[12px] font-semibold text-text">
                      {run.id}
                    </span>
                    <span className="text-[11px] font-mono text-text-3">
                      {run.time}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[12px] text-text-2">{run.orderId}</span>
                    <StatusBadge status={run.status} size="sm" />
                  </div>
                  <div className="text-[11px] text-text-3 truncate">
                    {run.scenario}
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>

        {/* Right Column: Active Stepper + Case Body Sections / Trace */}
        <div className="lg:col-span-3 space-y-4">
          <CaseHeader
            orderId={activeOrder.id}
            customer={activeOrder.customer}
            status={activeOrder.status}
            priority={activeOrder.priority}
            isSimulated={dataMode === 'demo'}
          />

          <PipelineStepper currentStage={workflowStage} />

          {/* View Tabs */}
          <Tabs
            tabs={[
              { id: 'case', label: 'Governed Case File' },
              { id: 'trace', label: 'Run Trace & State Variables' },
            ]}
            activeTab={activeTab}
            onChange={(id) => setActiveTab(id as any)}
          />

          {activeTab === 'case' ? (
            <CaseFileSections
              order={activeOrder}
              isSimulated={dataMode === 'demo'}
            />
          ) : (
            <Panel
              title="Execution State Trace (Raw State Variables)"
              subtitle="Step-by-step state dictionary passed between LangGraph agent nodes"
            >
              <div className="space-y-4 text-[12px]">
                <div>
                  <div className="font-semibold text-text mb-1">State: supervisor_input</div>
                  <pre className="p-3 rounded-[4px] bg-surface-sunk border border-border text-text font-mono text-[11px] overflow-x-auto">
{JSON.stringify(
  {
    order_id: activeOrder.id,
    customer: activeOrder.customer,
    product: activeOrder.product,
    quantity_tons: activeOrder.quantity,
    budget_limit_inr: activeOrder.budget,
    required_delivery_date: '2026-10-18T00:00:00Z',
    status: activeOrder.status,
  },
  null,
  2
)}
                  </pre>
                </div>

                <div>
                  <div className="font-semibold text-text mb-1">State: specialist_consensus</div>
                  <pre className="p-3 rounded-[4px] bg-surface-sunk border border-border text-text font-mono text-[11px] overflow-x-auto">
{JSON.stringify(
  {
    inventory_available: false,
    shortage_tons: 15,
    procurement_recommendation: {
      supplier: 'JSW Steel Limited',
      quote_per_ton: 41500,
      total_inr: 1660000,
      lead_time_days: 2,
    },
    finance_policy: {
      budget_allowed: false,
      overrun_inr: 240000,
      requires_override: true,
    },
    logistics_routing: {
      carrier: 'Concor Rail Freight',
      corridor: 'East Corridor 04',
      transit_hours: 38,
      on_time_confidence: 0.94,
    },
  },
  null,
  2
)}
                  </pre>
                </div>
              </div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
};
