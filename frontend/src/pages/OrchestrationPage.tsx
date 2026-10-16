import React, { useState, useEffect, useCallback, useRef } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Panel } from '../components/common/Panel';
import { StatusBadge } from '../components/common/StatusBadge';
import { Tabs } from '../components/common/Tabs';
import { CaseHeader } from '../components/case/CaseHeader';
import { PipelineStepper } from '../components/case/PipelineStepper';
import { CaseFileSections } from '../components/case/CaseFileSections';
import { useDemo } from '../state/DemoContext';
import {
  apiClient,
  type BackendOrderQueueStatus,
  type BackendScenarioInstance,
} from '../services/apiClient';
import {
  Play,
  Pause,
  Square,
  FastForward,
  Clock,
  Layers,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import type { DemoScenario } from '../types';

export const OrchestrationPage: React.FC = () => {
  const {
    dataMode,
    isLiveConnected,
    activeScenario,
    setActiveScenario,
    workflowStage,
    orders,
  } = useDemo();

  const isLive = dataMode === 'live';
  const isExecutionAllowed = isLive && isLiveConnected;

  const [activeTab, setActiveTab] = useState<'case' | 'trace'>('case');
  const [selectedOrderId, setSelectedOrderId] = useState('ORD-1042');
  const [isExecutingSingle, setIsExecutingSingle] = useState(false);
  const [execMessage, setExecMessage] = useState<string | null>(null);
  const [execError, setExecError] = useState<string | null>(null);

  // Sequential Queue Runner State
  const [runnerStatus, setRunnerStatus] = useState<BackendOrderQueueStatus | null>(null);
  const [runnerActionLoading, setRunnerActionLoading] = useState(false);
  const [countdownSeconds, setCountdownSeconds] = useState<number | null>(null);
  const [liveRuns, setLiveRuns] = useState<BackendScenarioInstance[]>([]);

  const countdownIntervalRef = useRef<any>(null);

  // Fetch queue runner status and live runs
  const fetchRunnerAndRuns = useCallback(async () => {
    if (!isLive) return;
    try {
      const [statusRes, runsRes] = await Promise.all([
        apiClient.getOrderQueueStatus(),
        apiClient.getSchedulerScenarios(10),
      ]);
      setRunnerStatus(statusRes);
      setLiveRuns(runsRes || []);

      // Calculate countdown to next_eligible_run_time
      if (statusRes.next_eligible_run_time) {
        const nextTime = new Date(statusRes.next_eligible_run_time).getTime();
        const now = Date.now();
        const diffSec = Math.max(0, Math.floor((nextTime - now) / 1000));
        setCountdownSeconds(diffSec);
      } else {
        setCountdownSeconds(null);
      }
    } catch (_err: any) {
      // Quiet background polling error
    }
  }, [isLive]);

  // Periodic polling for queue runner & run history
  useEffect(() => {
    if (!isLive) return;
    fetchRunnerAndRuns();
    const interval = setInterval(fetchRunnerAndRuns, 5000);
    return () => clearInterval(interval);
  }, [isLive, fetchRunnerAndRuns]);

  // Local second-by-second countdown decrementer
  useEffect(() => {
    if (countdownSeconds !== null && countdownSeconds > 0) {
      countdownIntervalRef.current = setInterval(() => {
        setCountdownSeconds((prev) => (prev && prev > 0 ? prev - 1 : 0));
      }, 1000);
    }
    return () => {
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    };
  }, [countdownSeconds]);

  // Runner controls
  const handleStartRunner = async () => {
    setRunnerActionLoading(true);
    setExecError(null);
    try {
      const res = await apiClient.startOrderQueueRunner();
      setExecMessage(res.message);
      await fetchRunnerAndRuns();
    } catch (err: any) {
      setExecError(err.message || 'Failed to start sequential runner');
    } finally {
      setRunnerActionLoading(false);
    }
  };

  const handlePauseRunner = async () => {
    setRunnerActionLoading(true);
    setExecError(null);
    try {
      const res = await apiClient.pauseOrderQueueRunner();
      setExecMessage(res.message);
      await fetchRunnerAndRuns();
    } catch (err: any) {
      setExecError(err.message || 'Failed to pause sequential runner');
    } finally {
      setRunnerActionLoading(false);
    }
  };

  const handleResumeRunner = async () => {
    setRunnerActionLoading(true);
    setExecError(null);
    try {
      const res = await apiClient.resumeOrderQueueRunner();
      setExecMessage(res.message);
      await fetchRunnerAndRuns();
    } catch (err: any) {
      setExecError(err.message || 'Failed to resume sequential runner');
    } finally {
      setRunnerActionLoading(false);
    }
  };

  const handleStopRunner = async () => {
    setRunnerActionLoading(true);
    setExecError(null);
    try {
      const res = await apiClient.stopOrderQueueRunner();
      setExecMessage(res.message);
      await fetchRunnerAndRuns();
    } catch (err: any) {
      setExecError(err.message || 'Failed to stop sequential runner');
    } finally {
      setRunnerActionLoading(false);
    }
  };

  const handleProcessNextNow = async () => {
    setRunnerActionLoading(true);
    setExecError(null);
    try {
      const res = await apiClient.processNextQueueOrder();
      setExecMessage(
        res.processed
          ? `Processed order ${res.order_id} in ${res.duration_ms}ms (Status: ${res.orchestration_status})`
          : res.message
      );
      if (res.order_id) setSelectedOrderId(res.order_id);
      await fetchRunnerAndRuns();
    } catch (err: any) {
      setExecError(err.message || 'Failed to execute immediate order claim');
    } finally {
      setRunnerActionLoading(false);
    }
  };

  // Single order execution
  const handleExecuteSingle = async () => {
    if (!isExecutionAllowed) return;
    setIsExecutingSingle(true);
    setExecError(null);
    setExecMessage(null);
    try {
      const res = await apiClient.executeOrchestration(selectedOrderId);
      setExecMessage(
        `Governed orchestration completed for ${selectedOrderId} in ${res.total_duration_ms || 0}ms.`
      );
      await fetchRunnerAndRuns();
    } catch (err: any) {
      setExecError(err?.message || 'Orchestration execution failed');
    } finally {
      setIsExecutingSingle(false);
    }
  };

  const activeOrder = orders.find((o) => o.id === selectedOrderId) || orders[0];

  // Fallback demo past runs if in demo mode
  const fallbackDemoRuns = [
    { id: 'RUN-2026-904', orderId: 'ORD-1042', status: 'approved', time: '19:15', scenario: 'Budget overrun' },
    { id: 'RUN-2026-903', orderId: 'ORD-1039', status: 'completed', time: '18:42', scenario: 'Normal flow' },
    { id: 'RUN-2026-902', orderId: 'ORD-1035', status: 'awaiting_approval', time: '17:30', scenario: 'Supplier stockout' },
    { id: 'RUN-2026-901', orderId: 'ORD-1031', status: 'blocked', time: '16:04', scenario: 'Margin breach' },
  ];

  const formatCountdown = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Governed Orchestration Pipeline"
        description="Sequential 1-by-1 order queue runner with 5-minute backend intervals, atomic claim, and live agent mesh execution."
      />

      {/* Sequential Queue Runner Control Banner */}
      <div className="p-4 rounded-[6px] border border-border bg-surface space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-border pb-3">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-accent" />
              <span className="font-semibold text-[13px] text-text">Sequential Queue Runner:</span>
              <span
                className={`font-mono text-[11px] px-2 py-0.5 rounded font-semibold uppercase ${
                  runnerStatus?.runner_status === 'RUNNING'
                    ? 'bg-ok/20 text-ok'
                    : runnerStatus?.runner_status === 'PAUSED'
                    ? 'bg-warn/20 text-warn'
                    : 'bg-surface-sunk text-text-3'
                }`}
              >
                {runnerStatus ? runnerStatus.runner_status : isLive ? 'INITIALIZING' : 'SIMULATED'}
              </span>
            </div>

            <div className="flex items-center gap-2 text-[12px] text-text-3 border-l border-border pl-3">
              <span>Pending in Queue:</span>
              <span className="font-mono text-text font-bold">
                {runnerStatus ? runnerStatus.total_queued : 100}
              </span>
            </div>

            <div className="flex items-center gap-2 text-[12px] text-text-3 border-l border-border pl-3">
              <span>Auto-Replenish:</span>
              <span className="font-mono text-ok font-semibold">
                {runnerStatus?.auto_replenish !== false ? 'ENABLED (100 Cap)' : 'DISABLED'}
              </span>
            </div>

            {countdownSeconds !== null && countdownSeconds > 0 && runnerStatus?.runner_status === 'RUNNING' && (
              <div className="flex items-center gap-1.5 text-[12px] text-accent font-mono bg-accent/10 px-2 py-0.5 rounded border border-accent/20">
                <Clock className="w-3.5 h-3.5" />
                <span>Next claim in: {formatCountdown(countdownSeconds)}</span>
              </div>
            )}
          </div>

          {/* Runner Action Buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            {runnerStatus?.runner_status === 'RUNNING' ? (
              <button
                type="button"
                onClick={handlePauseRunner}
                disabled={runnerActionLoading || !isLive}
                className="inline-flex items-center gap-1.5 h-[30px] px-3 rounded bg-surface hover:bg-surface-2 border border-border text-warn text-[12px] font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                <Pause className="w-3.5 h-3.5" />
                <span>Pause</span>
              </button>
            ) : runnerStatus?.runner_status === 'PAUSED' ? (
              <button
                type="button"
                onClick={handleResumeRunner}
                disabled={runnerActionLoading || !isLive}
                className="inline-flex items-center gap-1.5 h-[30px] px-3 rounded bg-ok hover:bg-ok/90 text-white text-[12px] font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Resume</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleStartRunner}
                disabled={runnerActionLoading || !isLive}
                className="inline-flex items-center gap-1.5 h-[30px] px-3 rounded bg-ok hover:bg-ok/90 text-white text-[12px] font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Start Queue</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleStopRunner}
              disabled={runnerActionLoading || !isLive || runnerStatus?.runner_status === 'STOPPED'}
              className="inline-flex items-center gap-1.5 h-[30px] px-3 rounded bg-surface hover:bg-surface-2 border border-border text-text-3 text-[12px] font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              <Square className="w-3.5 h-3.5" />
              <span>Stop</span>
            </button>

            <button
              type="button"
              onClick={handleProcessNextNow}
              disabled={runnerActionLoading || !isLive}
              className="inline-flex items-center gap-1.5 h-[30px] px-3 rounded bg-accent hover:bg-accent-hover text-white text-[12px] font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              <FastForward className="w-3.5 h-3.5" />
              <span>Process Next Now</span>
            </button>
          </div>
        </div>

        {/* Queue Metrics Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-[12px]">
          <div>
            <span className="text-text-3 text-[11px] block">Queued Orders</span>
            <span className="font-mono text-text font-bold text-[14px]">
              {runnerStatus ? runnerStatus.total_queued : 100}
            </span>
          </div>
          <div>
            <span className="text-text-3 text-[11px] block">Active Claim</span>
            <span className="font-mono text-accent font-semibold text-[14px]">
              {runnerStatus?.current_running_order_id || 'IDLE'}
            </span>
          </div>
          <div>
            <span className="text-text-3 text-[11px] block">Waiting Exceptions</span>
            <span
              className={`font-mono font-semibold text-[14px] ${
                (runnerStatus?.total_waiting_exception || 0) > 0 ? 'text-warn' : 'text-text-3'
              }`}
            >
              {runnerStatus ? runnerStatus.total_waiting_exception : 0}
            </span>
          </div>
          <div>
            <span className="text-text-3 text-[11px] block">Completed Orders</span>
            <span className="font-mono text-ok font-semibold text-[14px]">
              {runnerStatus ? runnerStatus.total_completed : 100}
            </span>
          </div>
          <div>
            <span className="text-text-3 text-[11px] block">Backend Interval</span>
            <span className="font-mono text-text-2 text-[14px]">
              {runnerStatus ? `${runnerStatus.interval_seconds}s (5 min)` : '300s (5 min)'}
            </span>
          </div>
        </div>
      </div>

      {/* Manual One-Off Order Execution Bar */}
      <div className="p-3.5 rounded-[6px] border border-border bg-surface flex flex-col md:flex-row md:items-center justify-between gap-4 text-[13px]">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="text-text-3 text-[12px]">One-Off Target Order:</span>
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

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleExecuteSingle}
            disabled={!isExecutionAllowed || isExecutingSingle}
            className="h-[32px] px-4 bg-accent hover:bg-accent-hover text-white text-[12px] font-medium rounded-[4px] transition-colors cursor-pointer disabled:bg-surface-2 disabled:text-text-3 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {isExecutingSingle ? 'Executing...' : 'Run Single Order Now'}
          </button>
        </div>
      </div>

      {/* Success / Info Notification */}
      {execMessage && (
        <div className="p-3 rounded-[4px] border border-ok/40 bg-ok/10 text-ok text-[12px] flex items-center gap-2">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{execMessage}</span>
        </div>
      )}

      {/* Error Message */}
      {execError && (
        <div className="p-3 rounded-[4px] border border-danger/40 bg-danger/10 text-danger text-[12px] font-mono flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{execError}</span>
        </div>
      )}

      {/* Main Layout: Left Run History (Col 1) & Right Case Body (Col 2-4) */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left Column: Live Run History */}
        <div className="lg:col-span-1">
          <Panel
            title="Run History"
            subtitle={isLive ? 'Real backend execution history' : 'Simulated evaluations'}
            padding="none"
          >
            <div className="divide-y divide-border max-h-[600px] overflow-y-auto">
              {isLive && liveRuns.length > 0
                ? liveRuns.map((run) => (
                    <div
                      key={run.scenario_id}
                      onClick={() => run.linked_order_id && setSelectedOrderId(run.linked_order_id)}
                      className="p-3 hover:bg-surface-2 cursor-pointer transition-colors space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[12px] font-semibold text-text truncate max-w-[130px]">
                          {run.scenario_id.slice(0, 8)}...
                        </span>
                        <span className="text-[11px] font-mono text-text-3">
                          {run.scheduled_at ? run.scheduled_at.split('T')[1]?.slice(0, 5) : 'Now'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[12px] text-text-2">
                          {run.linked_order_id || 'RUN'}
                        </span>
                        <StatusBadge status={run.status} size="sm" />
                      </div>
                      <div className="text-[11px] text-text-3 truncate">
                        {run.scenario_template_id} — {run.severity}
                      </div>
                    </div>
                  ))
                : fallbackDemoRuns.map((run) => (
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
    inventory: { finding: 'Inventory allocated at EAS-EAST', score: 0.95 },
    procurement: { finding: 'Supplier SUP-001 active offer valid', score: 0.98 },
    logistics: { finding: 'Direct road corridor SLA 48h met', score: 0.91 },
    finance: { finding: 'Spend within delegated ₹50 Cr budget limit', score: 0.99 },
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
