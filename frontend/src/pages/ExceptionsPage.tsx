import React, { useState } from 'react';
import { Play, Square, Zap, ShieldOff, TrendingUp, GitMerge, CheckCircle2, XCircle, RefreshCw, ShieldCheck, Clock, Cpu } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import type { DemoScenario } from '../types';

interface ScenarioConfig {
  id: DemoScenario;
  title: string;
  description: string;
  impact: string;
  mitigation: string;
  accentColor: string;
  icon: React.ReactNode;
  tag: string;
}

const SCENARIOS: ScenarioConfig[] = [
  {
    id: 'supplier_unavailable',
    title: 'Supplier Unavailable',
    description: 'Simulates total node failure for the primary Tier-1 material supplier. Procurement Agent detects the outage and automatically escalates to a backup supplier.',
    impact: '1 Node Outage',
    mitigation: 'Supplier B Fallback (Pune Hub)',
    accentColor: '#EF4444',
    icon: <ShieldOff className="w-4 h-4" />,
    tag: 'SUPPLIER',
  },
  {
    id: 'budget_breach',
    title: 'Budget Breach',
    description: 'Triggers a cost anomaly >15% over the approved procurement baseline. Finance Agent intercepts and forces a re-negotiation cycle with a cost-optimization strategy.',
    impact: '₹38,000 Quote Excess',
    mitigation: 'Finance Re-negotiation',
    accentColor: '#F59E0B',
    icon: <TrendingUp className="w-4 h-4" />,
    tag: 'FINANCE',
  },
  {
    id: 'delivery_delay',
    title: 'Delivery Delay +48h',
    description: 'Simulates severe road weather disruption on NH-53 Pune-Nagpur corridor. Logistics Agent autonomously reroutes to Express Rail Cargo.',
    impact: 'Highway NH-53 +48h',
    mitigation: 'Express Rail Reroute',
    accentColor: '#38BDF8',
    icon: <Zap className="w-4 h-4" />,
    tag: 'LOGISTICS',
  },
  {
    id: 'multi_exception',
    title: 'Multi-Exception Recovery',
    description: 'Injects simultaneous supplier outage AND highway delay to test full multi-agent autonomous resilience, coordinator re-planning, and cascaded recovery.',
    impact: 'Dual Cascade Failure',
    mitigation: 'Full Mesh Reroute',
    accentColor: '#8B5CF6',
    icon: <GitMerge className="w-4 h-4" />,
    tag: 'COMPOUND',
  },
];

export const ExceptionsPage: React.FC = () => {
  const {
    activeScenario,
    setActiveScenario,
    runDemoOrder,
    isSimulating,
    resetDemo,
    dataMode,
    liveApprovals,
    liveActions,
    liveSchedulerStatus,
    triggerScheduler,
    decideApproval,
    executeAction,
    refreshLiveData
  } = useDemo();

  const [isTriggeringScheduler, setIsTriggeringScheduler] = useState(false);
  const [decidingId, setDecidingId] = useState<string | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const handleTriggerScheduler = async () => {
    if (!window.confirm('Trigger background scenario scheduler cycle against PostgreSQL?')) return;
    setIsTriggeringScheduler(true);
    setActionFeedback(null);
    try {
      const res = await triggerScheduler();
      setActionFeedback(`Scheduler cycle executed: ${res?.leases_acquired ?? 0} lease(s) acquired, status: ${res?.status ?? 'success'}`);
    } catch (err: unknown) {
      setActionFeedback(`Scheduler error: ${err instanceof Error ? err.message : 'Execution failed'}`);
    } finally {
      setIsTriggeringScheduler(false);
    }
  };

  const handleDecideApproval = async (approvalId: string, decision: 'APPROVED' | 'REJECTED') => {
    const role = decision === 'APPROVED' ? 'FINANCE_APPROVER' : 'OPERATOR';
    if (!window.confirm(`${decision} pending approval ${approvalId} as role ${role}?`)) return;
    setDecidingId(approvalId);
    setActionFeedback(null);
    try {
      const ok = await decideApproval(approvalId, decision, `Decision confirmed by ${role} via Control Room UI`);
      if (ok) {
        setActionFeedback(`Approval ${approvalId} successfully recorded as ${decision}.`);
      } else {
        setActionFeedback(`Approval ${approvalId} decision failed.`);
      }
    } catch (err: unknown) {
      setActionFeedback(`Error deciding approval: ${err instanceof Error ? err.message : 'Request failed'}`);
    } finally {
      setDecidingId(null);
    }
  };

  const handleExecuteAction = async (actionId: string, actionType: string) => {
    const confirmMsg = `Execute simulated action ${actionId} (${actionType})?\n\nNOTE: This executes through the backend safe simulation adapter (sandbox). No real funds or purchase orders will be disbursed.`;
    if (!window.confirm(confirmMsg)) return;
    setExecutingId(actionId);
    setActionFeedback(null);
    try {
      const res = await executeAction(actionId);
      setActionFeedback(`Action ${actionId} executed via simulation adapter: status ${res?.status ?? 'COMPLETED'}`);
    } catch (err: unknown) {
      setActionFeedback(`Error executing action: ${err instanceof Error ? err.message : 'Execution failed'}`);
    } finally {
      setExecutingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Governance & Exception Control</h1>
            {dataMode === 'live' && (
              <span className="text-[10px] bg-blue-900/60 text-blue-300 border border-blue-500/30 px-2 py-0.5 rounded font-mono">
                LIVE POSTGRESQL GOVERNANCE
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Human-in-the-loop approvals, controlled simulation execution, and resilience scenario injection
          </p>
        </div>
        <div className="flex items-center gap-2">
          {dataMode === 'live' && (
            <button
              onClick={() => refreshLiveData()}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-mono font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </button>
          )}
          <button
            onClick={resetDemo}
            className="px-4 py-2 rounded-lg text-[12px] font-semibold transition shrink-0"
            style={{ background: '#111827', color: '#94A3B8', border: '1px solid #1E293B' }}
          >
            Reset Environment
          </button>
        </div>
      </div>

      {/* Action / Scheduler Feedback Banner */}
      {actionFeedback && (
        <div className="p-3.5 rounded-xl bg-sky-950/50 border border-sky-500/40 text-sky-200 text-xs font-mono flex items-center justify-between animate-fade-slide">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0" />
            <span>{actionFeedback}</span>
          </div>
          <button onClick={() => setActionFeedback(null)} className="text-slate-400 hover:text-white text-xs">
            ✕
          </button>
        </div>
      )}

      {/* ── LIVE GOVERNANCE PANELS (Rendered when in Live Mode) ──────────────── */}
      {dataMode === 'live' && (
        <div className="space-y-6">
          {/* 1. Scheduler Control */}
          <div className="rounded-xl p-5 bg-[#0F172A] border border-[#1E293B]">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
                  <Clock className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-white">Scenario Scheduler Status</h2>
                  <div className="text-xs text-slate-400 flex items-center gap-3 mt-0.5 font-mono">
                    <span>Status: <strong className="text-emerald-400">{liveSchedulerStatus?.is_running ? 'RUNNING' : 'STANDBY'}</strong></span>
                    <span>Interval: {liveSchedulerStatus?.interval_seconds ?? 60}s</span>
                    <span>Active Leases: {liveSchedulerStatus?.active_leases_count ?? 0}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={handleTriggerScheduler}
                disabled={isTriggeringScheduler}
                className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-mono font-bold flex items-center gap-2 transition disabled:opacity-50 shrink-0"
              >
                {isTriggeringScheduler ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                Trigger Scheduler Cycle
              </button>
            </div>
          </div>

          {/* 2. Pending Human Approvals Queue */}
          <div className="rounded-xl overflow-hidden bg-[#111827] border border-[#1E293B]">
            <div className="px-5 py-3.5 border-b border-[#1E293B] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-amber-400" />
                <h2 className="text-sm font-bold text-white">Pending Human Approvals Queue</h2>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                {liveApprovals.filter(a => a.status === 'PENDING').length} PENDING DECISIONS
              </span>
            </div>

            <div className="p-5">
              {liveApprovals.filter(a => a.status === 'PENDING').length === 0 ? (
                <div className="text-center py-6 text-slate-500 text-xs font-mono">
                  No pending approval requests in PostgreSQL database. Actions requiring human approval will appear here.
                </div>
              ) : (
                <div className="space-y-3">
                  {liveApprovals.filter(a => a.status === 'PENDING').map(appr => (
                    <div
                      key={appr.approval_id}
                      className="p-4 rounded-xl bg-[#080C14] border border-[#1E293B] flex flex-col md:flex-row md:items-center justify-between gap-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-white font-mono">
                            {appr.required_domain || appr.domain || 'FINANCE'} APPROVAL
                          </span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300">
                            Required Role: {appr.required_role || 'FINANCE_APPROVER'}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">ID: {appr.approval_id.slice(0, 8)}</span>
                        </div>
                        <div className="text-xs text-slate-300">{appr.reason || 'Pending human-in-the-loop governance sign-off.'}</div>
                        <div className="text-[11px] font-mono text-slate-500 flex items-center gap-3">
                          <span>Action: {appr.action_id ? appr.action_id.slice(0, 8) : 'N/A'}</span>
                          {appr.requested_amount && (
                            <span className="text-amber-400 font-bold">
                              Amount: ₹{appr.requested_amount.toLocaleString()} (Threshold: ₹{appr.threshold_amount?.toLocaleString()})
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => handleDecideApproval(appr.approval_id, 'APPROVED')}
                          disabled={decidingId === appr.approval_id}
                          className="px-3.5 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-300 border border-emerald-500/40 text-xs font-mono font-bold flex items-center gap-1.5 transition disabled:opacity-50"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" /> Approve
                        </button>
                        <button
                          onClick={() => handleDecideApproval(appr.approval_id, 'REJECTED')}
                          disabled={decidingId === appr.approval_id}
                          className="px-3.5 py-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 border border-rose-500/40 text-xs font-mono font-bold flex items-center gap-1.5 transition disabled:opacity-50"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Reject
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 3. Action Queue & Controlled Execution */}
          <div className="rounded-xl overflow-hidden bg-[#111827] border border-[#1E293B]">
            <div className="px-5 py-3.5 border-b border-[#1E293B] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                <h2 className="text-sm font-bold text-white">Controlled Action Queue & Simulation Execution</h2>
              </div>
              <span className="text-[10px] font-mono text-slate-400">
                {liveActions.length} recorded actions
              </span>
            </div>

            <div className="p-5">
              {liveActions.length === 0 ? (
                <div className="text-center py-6 text-slate-500 text-xs font-mono">
                  No actions in PostgreSQL queue. When specialist agents propose actions and pass policy gating, they appear here.
                </div>
              ) : (
                <div className="space-y-3">
                  {liveActions.slice(0, 10).map(act => {
                    const isExecutable = act.status === 'APPROVED';
                    const isExecuting = executingId === act.action_id;

                    return (
                      <div
                        key={act.action_id}
                        className="p-4 rounded-xl bg-[#080C14] border border-[#1E293B] flex flex-col md:flex-row md:items-center justify-between gap-4"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold font-mono text-white">{act.action_type}</span>
                            <span
                              className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                                ['COMPLETED', 'SUCCEEDED'].includes(act.status.toUpperCase())
                                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                                  : act.status.toUpperCase() === 'APPROVED'
                                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                                  : ['PENDING_APPROVAL', 'PROPOSED'].includes(act.status.toUpperCase())
                                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                                  : 'bg-slate-800 text-slate-400'
                              }`}
                            >
                              {act.status}
                            </span>
                            <span className="text-[10px] font-mono text-slate-600">ID: {act.action_id.slice(0, 8)}</span>
                          </div>
                          <div className="text-xs text-slate-400 font-mono truncate max-w-lg">
                            Payload: {JSON.stringify(act.payload)}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {isExecutable ? (
                            <button
                              onClick={() => handleExecuteAction(act.action_id, act.action_type)}
                              disabled={isExecuting}
                              className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-900 text-xs font-mono font-bold flex items-center gap-1.5 transition disabled:opacity-50"
                              title="Safe simulation execution: sandbox adapter only"
                            >
                              {isExecuting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                              Execute Simulation
                            </button>
                          ) : (
                            <span className="text-[11px] font-mono text-slate-600">
                              {['COMPLETED', 'SUCCEEDED'].includes(act.status.toUpperCase()) ? 'Executed via Simulation Adapter' : 'Requires Human Approval'}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── SCENARIOS SECTION HEADER ──────────────────────── */}
      <div className="pt-2">
        <h2 className="text-sm font-bold text-white mb-1">Resilience Failure Injection Scenarios</h2>
        <p className="text-xs text-slate-500">
          Inject real-time exception triggers to evaluate multi-agent reasoning and policy enforcement
        </p>
      </div>

      {/* Scenario Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SCENARIOS.map(scen => {
          const isSelected = activeScenario === scen.id;
          const isRunning  = isSimulating && isSelected;

          return (
            <div
              key={scen.id}
              className="rounded-xl overflow-hidden transition-all duration-200"
              style={{
                background: '#111827',
                border: `1px solid ${isSelected ? scen.accentColor + '40' : '#1E293B'}`,
                borderLeft: `4px solid ${scen.accentColor}`,
                boxShadow: isSelected ? `0 0 20px ${scen.accentColor}15` : 'none',
              }}
            >
              <div className="p-5 space-y-4">
                {/* Card Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                      style={{ background: scen.accentColor + '15', color: scen.accentColor }}
                    >
                      {scen.icon}
                    </div>
                    <div>
                      <div className="font-bold text-sm text-white">{scen.title}</div>
                      {isRunning && (
                        <span
                          className="text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded animate-pulse"
                          style={{ background: scen.accentColor + '20', color: scen.accentColor }}
                        >
                          SIMULATING
                        </span>
                      )}
                    </div>
                  </div>
                  <span
                    className="px-2 py-0.5 rounded text-[9px] font-mono font-bold shrink-0"
                    style={{ background: scen.accentColor + '15', color: scen.accentColor }}
                  >
                    {scen.tag}
                  </span>
                </div>

                {/* Description */}
                <p className="text-[12px] text-slate-400 leading-relaxed">{scen.description}</p>

                {/* Impact / Mitigation */}
                <div
                  className="grid grid-cols-2 gap-3 p-3 rounded-lg text-[11px] font-mono"
                  style={{ background: '#080C14', border: '1px solid #1E293B' }}
                >
                  <div>
                    <div className="text-[9px] text-slate-600 uppercase font-bold mb-0.5">Impact</div>
                    <div className="font-bold" style={{ color: scen.accentColor }}>{scen.impact}</div>
                  </div>
                  <div>
                    <div className="text-[9px] text-slate-600 uppercase font-bold mb-0.5">Mitigation</div>
                    <div className="font-bold text-emerald-400">{scen.mitigation}</div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-between gap-2 pt-1">
                  <button
                    onClick={() => setActiveScenario(scen.id)}
                    className="px-3 py-1.5 rounded-lg text-[11px] font-medium transition"
                    style={{
                      background: isSelected ? scen.accentColor + '12' : '#1E293B',
                      color: isSelected ? scen.accentColor : '#94A3B8',
                      border: `1px solid ${isSelected ? scen.accentColor + '30' : '#2D3748'}`,
                    }}
                  >
                    {isSelected ? '✓ Configured' : 'Select Scenario'}
                  </button>

                  {isRunning ? (
                    <button
                      onClick={resetDemo}
                      className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-bold font-mono transition"
                      style={{ background: 'rgba(239,68,68,0.1)', color: '#EF4444', border: '1px solid rgba(239,68,68,0.2)' }}
                    >
                      <Square className="w-3 h-3 fill-current" /> Halt
                    </button>
                  ) : (
                    <button
                      onClick={() => { setActiveScenario(scen.id); runDemoOrder(scen.id); }}
                      disabled={isSimulating}
                      className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-bold font-mono transition disabled:opacity-40"
                      style={{
                        background: scen.accentColor + '15',
                        color: scen.accentColor,
                        border: `1px solid ${scen.accentColor + '35'}`,
                      }}
                    >
                      <Play className="w-3 h-3 fill-current" /> Inject Failure
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
