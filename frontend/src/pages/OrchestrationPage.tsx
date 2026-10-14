import React, { useState, useCallback } from 'react';
import {
  Play,
  Cpu,
  CheckCircle2,
  XCircle,
  Clock,
  Shield,
  Zap,
  AlertTriangle,
  Brain,
  ChevronDown,
  ChevronRight,
  GitBranch,
  Loader2,
  Server,
  RotateCcw,
  AlertOctagon,
  FileQuestion,
  ArrowRight,
} from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { apiClient, type OrchestrationResult, type OrchestrationAgentStep, type ProviderInfo } from '../services/apiClient';

const PHASE_COLORS: Record<string, string> = {
  INVENTORY_ANALYSIS: '#10B981',
  PROCUREMENT_EVALUATION: '#F59E0B',
  FINANCE_REVIEW: '#EC4899',
  LOGISTICS_PLANNING: '#8B5CF6',
  SUPERVISOR_SYNTHESIS: '#6366F1',
  POLICY_EVALUATION: '#06B6D4',
  APPROVAL_GATE: '#F97316',
  ACTION_PROPOSAL: '#3B82F6',
  ACTION_EXECUTION: '#14B8A6',
  COMPLETED: '#22C55E',
  FAILED: '#EF4444',
  BLOCKED: '#F43F5E',
  INITIALIZED: '#64748B',
};

const STATUS_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  COMPLETED: { bg: 'rgba(34,197,94,0.1)', text: '#22C55E', border: 'rgba(34,197,94,0.3)' },
  FAILED: { bg: 'rgba(239,68,68,0.1)', text: '#EF4444', border: 'rgba(239,68,68,0.3)' },
  BLOCKED: { bg: 'rgba(244,63,94,0.1)', text: '#F43F5E', border: 'rgba(244,63,94,0.3)' },
  AWAITING_APPROVAL: { bg: 'rgba(249,115,22,0.1)', text: '#F97316', border: 'rgba(249,115,22,0.3)' },
  RUNNING: { bg: 'rgba(56,189,248,0.1)', text: '#38BDF8', border: 'rgba(56,189,248,0.3)' },
};

export const OrchestrationPage: React.FC = () => {
  const { dataMode, isLiveConnected } = useDemo();
  const isLive = dataMode === 'live' && isLiveConnected;

  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<OrchestrationResult | null>(null);
  const [providerInfo, setProviderInfo] = useState<ProviderInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedStep, setExpandedStep] = useState<string | null>(null);
  const [orderId, setOrderId] = useState('ORD-1001');

  const fetchProviderInfo = useCallback(async () => {
    try {
      const info = await apiClient.getProviderInfo();
      setProviderInfo(info);
    } catch {
      // Non-critical — provider info panel will show unavailable
    }
  }, []);

  React.useEffect(() => {
    if (isLive) {
      fetchProviderInfo();
    }
  }, [isLive, fetchProviderInfo]);

  const handleExecute = async () => {
    setIsExecuting(true);
    setError(null);
    setResult(null);
    setExpandedStep(null);

    try {
      const res = await apiClient.executeOrchestration(orderId);
      setResult(res);
    } catch (err: any) {
      setError(err?.message || 'Orchestration execution failed');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleRetry = async () => {
    if (!result?.workflow_id) return;
    setIsExecuting(true);
    setError(null);

    try {
      const res = await apiClient.retryOrchestration(result.workflow_id);
      setResult(res);
    } catch (err: any) {
      setError(err?.message || 'Retry or resume failed');
    } finally {
      setIsExecuting(false);
    }
  };

  const statusStyle = result
    ? STATUS_STYLES[result.status] || STATUS_STYLES.RUNNING
    : null;

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="pb-5 border-b border-[#1E293B]">
        <h1 className="text-2xl font-extrabold text-white tracking-tight">
          Governed Orchestration
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Multi-agent decision pipeline with LLM recommendations, policy evaluation, and approval gating
        </p>
      </div>

      {/* Control Bar */}
      <div
        className="rounded-xl p-4 flex flex-wrap items-center gap-4"
        style={{ background: '#0F172A', border: '1px solid #1E293B' }}
      >
        {/* Order ID Input */}
        <div className="flex items-center gap-2">
          <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
            Order ID
          </label>
          <input
            id="orchestration-order-id"
            type="text"
            value={orderId}
            onChange={e => setOrderId(e.target.value)}
            className="bg-[#080C14] border border-[#1E293B] rounded-lg px-3 py-2 text-xs font-mono text-cyan-400 focus:outline-none focus:border-cyan-500/50 w-32"
          />
        </div>

        {/* Execute Button */}
        <button
          id="orchestration-execute-btn"
          onClick={handleExecute}
          disabled={isExecuting || !isLive}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-bold transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: isExecuting
              ? 'rgba(56,189,248,0.1)'
              : 'linear-gradient(135deg, #0E7490 0%, #0891B2 100%)',
            border: '1px solid rgba(56,189,248,0.3)',
            color: '#E2F8FF',
          }}
        >
          {isExecuting ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Executing Pipeline…
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5" />
              Execute Governed Pipeline
            </>
          )}
        </button>

        {/* Retry / Resume Button (when permitted) */}
        {result?.can_retry && (
          <button
            id="orchestration-retry-btn"
            onClick={handleRetry}
            disabled={isExecuting || !isLive}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold transition-all duration-200 disabled:opacity-40"
            style={{
              background: 'rgba(245,158,11,0.15)',
              border: '1px solid rgba(245,158,11,0.35)',
              color: '#FBBF24',
            }}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            {result.status === 'AWAITING_APPROVAL' ? 'Resume After Approval' : 'Retry Workflow'}
          </button>
        )}

        {/* Provider Badge */}
        {providerInfo && (
          <div
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-[10px] font-mono"
            style={{
              background: providerInfo.is_simulation
                ? 'rgba(139,92,246,0.1)'
                : 'rgba(16,185,129,0.1)',
              border: `1px solid ${providerInfo.is_simulation ? 'rgba(139,92,246,0.3)' : 'rgba(16,185,129,0.3)'}`,
              color: providerInfo.is_simulation ? '#A78BFA' : '#34D399',
            }}
          >
            <Brain className="w-3 h-3" />
            {providerInfo.mode} — {providerInfo.model_name}
          </div>
        )}

        {!isLive && (
          <div className="flex items-center gap-2 text-[10px] font-mono text-amber-400/70">
            <AlertTriangle className="w-3 h-3" />
            Connect to live backend to execute orchestration
          </div>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div
          className="rounded-xl px-5 py-4 flex items-center gap-3"
          style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)' }}
        >
          <XCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span className="text-xs text-red-300">{error}</span>
        </div>
      )}

      {/* Result Panel */}
      {result && (
        <div className="space-y-4">
          {/* Result Header */}
          <div
            className="rounded-xl overflow-hidden"
            style={{ background: '#0F172A', border: `1px solid ${statusStyle?.border || '#1E293B'}` }}
          >
            <div
              className="px-5 py-4 flex flex-wrap items-center justify-between gap-3"
              style={{ background: statusStyle?.bg || 'transparent' }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ background: 'rgba(0,0,0,0.3)', border: `1px solid ${statusStyle?.border}` }}
                >
                  {result.status === 'COMPLETED' ? (
                    <CheckCircle2 className="w-5 h-5" style={{ color: statusStyle?.text }} />
                  ) : result.status === 'FAILED' || result.status === 'BLOCKED' ? (
                    <XCircle className="w-5 h-5" style={{ color: statusStyle?.text }} />
                  ) : (
                    <Clock className="w-5 h-5" style={{ color: statusStyle?.text }} />
                  )}
                </div>
                <div>
                  <div className="text-sm font-bold text-white flex items-center gap-2">
                    <span>Orchestration {result.status}</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/40 text-slate-400 border border-slate-700">
                      wf: {result.workflow_id.slice(0, 8)}…
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-slate-500">
                    Correlation: {result.correlation_id.slice(0, 16)}…
                  </div>
                </div>
              </div>

              {/* Quick stats */}
              <div className="flex items-center gap-4">
                {[
                  { label: 'Agents', value: result.agent_steps.length, color: '#38BDF8' },
                  { label: 'Phases', value: result.phases_completed.length, color: '#A78BFA' },
                  {
                    label: 'Duration',
                    value: result.total_duration_ms
                      ? `${Math.round(result.total_duration_ms)}ms`
                      : '—',
                    color: '#F59E0B',
                  },
                ].map(s => (
                  <div key={s.label} className="text-center">
                    <div className="text-lg font-bold font-mono" style={{ color: s.color }}>
                      {s.value}
                    </div>
                    <div className="text-[9px] font-mono text-slate-600 uppercase">{s.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Decision Summary */}
            {result.decision_summary && (
              <div className="px-5 py-4 border-t" style={{ borderColor: statusStyle?.border || '#1E293B' }}>
                <div className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-1.5">
                  Decision Summary
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">{result.decision_summary}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span
                    className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono font-bold"
                    style={{
                      background: result.human_approval_required
                        ? 'rgba(249,115,22,0.1)'
                        : 'rgba(34,197,94,0.1)',
                      border: `1px solid ${result.human_approval_required ? 'rgba(249,115,22,0.3)' : 'rgba(34,197,94,0.3)'}`,
                      color: result.human_approval_required ? '#F97316' : '#22C55E',
                    }}
                  >
                    <Shield className="w-3 h-3" />
                    {result.decision_code}
                  </span>
                  <span
                    className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono"
                    style={{
                      background: 'rgba(139,92,246,0.1)',
                      border: '1px solid rgba(139,92,246,0.3)',
                      color: '#A78BFA',
                    }}
                  >
                    <Server className="w-3 h-3" />
                    {result.provider_mode}
                  </span>
                  {result.proposed_next_step && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono text-cyan-300 bg-cyan-900/30 border border-cyan-700/40">
                      <ArrowRight className="w-3 h-3" />
                      Next: {result.proposed_next_step}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Supervisor Conflicts / Missing Evidence Alerts */}
          {((result.conflicts && result.conflicts.length > 0) || (result.missing_evidence && result.missing_evidence.length > 0)) && (
            <div className="space-y-2">
              {result.conflicts && result.conflicts.map((conflict, idx) => (
                <div
                  key={`conflict-${idx}`}
                  className="rounded-xl px-4 py-3 flex items-start gap-3"
                  style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.3)' }}
                >
                  <AlertOctagon className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-[10px] font-mono font-bold text-amber-400 uppercase tracking-wider">
                      Supervisor Conflict Detected
                    </div>
                    <div className="text-xs text-amber-200 mt-0.5">{conflict}</div>
                  </div>
                </div>
              ))}
              {result.missing_evidence && result.missing_evidence.map((me, idx) => (
                <div
                  key={`missing-${idx}`}
                  className="rounded-xl px-4 py-3 flex items-start gap-3"
                  style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.3)' }}
                >
                  <FileQuestion className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-[10px] font-mono font-bold text-rose-400 uppercase tracking-wider">
                      Missing Grounded Evidence
                    </div>
                    <div className="text-xs text-rose-200 mt-0.5">{me}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pipeline Phase Timeline */}
          <div
            className="rounded-xl p-5"
            style={{ background: '#0F172A', border: '1px solid #1E293B' }}
          >
            <div className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-4">
              Pipeline Phases
            </div>
            <div className="flex flex-wrap gap-2">
              {result.phases_completed.map((phase, i) => (
                <div
                  key={`${phase}-${i}`}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-mono font-bold"
                  style={{
                    background: `${PHASE_COLORS[phase] || '#64748B'}15`,
                    border: `1px solid ${PHASE_COLORS[phase] || '#64748B'}40`,
                    color: PHASE_COLORS[phase] || '#64748B',
                  }}
                >
                  <CheckCircle2 className="w-3 h-3" />
                  {phase.replace(/_/g, ' ')}
                </div>
              ))}
            </div>
          </div>

          {/* Agent Steps */}
          <div
            className="rounded-xl overflow-hidden"
            style={{ background: '#0F172A', border: '1px solid #1E293B' }}
          >
            <div className="px-5 py-4 border-b border-[#1E293B]">
              <div className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest">
                Agent Execution Steps
              </div>
            </div>

            <div className="divide-y divide-[#1E293B]">
              {result.agent_steps.map((step: OrchestrationAgentStep) => {
                const isExpanded = expandedStep === step.agent_name;
                const phaseColor = PHASE_COLORS[step.phase] || '#64748B';
                const isFailed = step.status === 'FAILED';
                const isSkipped = step.status === 'SKIPPED';

                return (
                  <div key={step.agent_name}>
                    {/* Step Header */}
                    <button
                      onClick={() => setExpandedStep(isExpanded ? null : step.agent_name)}
                      className="w-full px-5 py-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center"
                          style={{
                            background: `${phaseColor}15`,
                            border: `1px solid ${phaseColor}40`,
                          }}
                        >
                          <Cpu className="w-4 h-4" style={{ color: phaseColor }} />
                        </div>
                        <div className="text-left">
                          <div className="text-xs font-bold text-white">{step.agent_name}</div>
                          <div className="text-[10px] font-mono text-slate-500">
                            {step.phase.replace(/_/g, ' ')}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        {step.duration_ms !== undefined && step.duration_ms !== null && (
                          <span className="text-[10px] font-mono text-slate-500">
                            {Math.round(step.duration_ms)}ms
                          </span>
                        )}
                        <span
                          className="px-2 py-0.5 rounded text-[9px] font-mono font-bold"
                          style={{
                            background: isFailed
                              ? 'rgba(239,68,68,0.1)'
                              : isSkipped
                              ? 'rgba(100,116,139,0.1)'
                              : 'rgba(34,197,94,0.1)',
                            border: `1px solid ${isFailed ? 'rgba(239,68,68,0.3)' : isSkipped ? 'rgba(100,116,139,0.3)' : 'rgba(34,197,94,0.3)'}`,
                            color: isFailed ? '#EF4444' : isSkipped ? '#94A3B8' : '#22C55E',
                          }}
                        >
                          {step.status}
                        </span>
                        {step.is_simulation && (
                          <span className="px-1.5 py-0.5 rounded text-[8px] font-mono text-violet-400 bg-violet-500/10 border border-violet-500/20">
                            SIM
                          </span>
                        )}
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                        )}
                      </div>
                    </button>

                    {/* Expanded Detail */}
                    {isExpanded && (
                      <div className="px-5 pb-4 space-y-3">
                        {/* LLM Recommendation */}
                        {step.llm_reasoning && (
                          <div
                            className="rounded-lg px-4 py-3"
                            style={{
                              background: 'rgba(139,92,246,0.05)',
                              border: '1px solid rgba(139,92,246,0.2)',
                            }}
                          >
                            <div className="flex items-center gap-1.5 text-[9px] font-mono font-bold text-violet-400 uppercase tracking-widest mb-1.5">
                              <Brain className="w-3 h-3" />
                              LLM Recommendation
                              {step.llm_confidence !== undefined && step.llm_confidence !== null && (
                                <span className="ml-2 text-violet-300">
                                  ({(step.llm_confidence * 100).toFixed(0)}% confidence)
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-slate-300 leading-relaxed">
                              {step.llm_reasoning}
                            </p>
                            {step.llm_recommendation && (
                              <pre className="mt-2 text-[10px] font-mono text-slate-400 bg-[#080C14] rounded p-2 overflow-x-auto">
                                {JSON.stringify(step.llm_recommendation, null, 2)}
                              </pre>
                            )}
                          </div>
                        )}

                        {/* Deterministic Output */}
                        <div
                          className="rounded-lg px-4 py-3"
                          style={{ background: '#080C14', border: '1px solid #1E293B' }}
                        >
                          <div className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-1.5">
                            Deterministic Output
                          </div>
                          <pre className="text-[10px] font-mono text-slate-400 overflow-x-auto max-h-48 overflow-y-auto">
                            {JSON.stringify(step.deterministic_output, null, 2)}
                          </pre>
                        </div>

                        {/* Evidence Refs */}
                        {step.evidence_refs.length > 0 && (
                          <div
                            className="rounded-lg px-4 py-3"
                            style={{ background: '#080C14', border: '1px solid #1E293B' }}
                          >
                            <div className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-1.5">
                              Evidence References
                            </div>
                            <div className="space-y-1">
                              {step.evidence_refs.map((ref, idx) => (
                                <div key={idx} className="text-[10px] font-mono text-cyan-400/70">
                                  {JSON.stringify(ref)}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Error */}
                        {step.error && (
                          <div
                            className="rounded-lg px-4 py-3"
                            style={{
                              background: 'rgba(239,68,68,0.05)',
                              border: '1px solid rgba(239,68,68,0.2)',
                            }}
                          >
                            <div className="text-[9px] font-mono font-bold text-red-400 uppercase tracking-widest mb-1">
                              Error
                            </div>
                            <p className="text-[11px] text-red-300">{step.error}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Governance Summary */}
          {result.governance && Object.keys(result.governance).length > 0 && (
            <div
              className="rounded-xl p-5"
              style={{ background: '#0F172A', border: '1px solid #1E293B' }}
            >
              <div className="flex items-center gap-1.5 text-[9px] font-mono font-bold text-cyan-500 uppercase tracking-widest mb-3">
                <Shield className="w-3 h-3" />
                Governance Summary
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(result.governance).map(([key, value]) => (
                  <div key={key} className="rounded-lg p-3" style={{ background: '#080C14', border: '1px solid #1E293B' }}>
                    <div className="text-[9px] font-mono text-slate-600 uppercase mb-1">
                      {key.replace(/_/g, ' ')}
                    </div>
                    <div className="text-xs font-mono text-white truncate">
                      {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Action */}
          {result.recommended_action && Object.keys(result.recommended_action).length > 0 && (
            <div
              className="rounded-xl p-5"
              style={{ background: '#0F172A', border: '1px solid #1E293B' }}
            >
              <div className="flex items-center gap-1.5 text-[9px] font-mono font-bold text-amber-500 uppercase tracking-widest mb-3">
                <Zap className="w-3 h-3" />
                Recommended Action
              </div>
              <pre className="text-[11px] font-mono text-slate-300 bg-[#080C14] rounded-lg p-4 border border-[#1E293B] overflow-x-auto">
                {JSON.stringify(result.recommended_action, null, 2)}
              </pre>
            </div>
          )}

          {/* Simulated Action Execution Outcome */}
          {result.action_result && Object.keys(result.action_result).length > 0 && (
            <div
              className="rounded-xl p-5"
              style={{ background: '#0F172A', border: '1px solid rgba(20,184,166,0.3)' }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-1.5 text-[9px] font-mono font-bold text-teal-400 uppercase tracking-widest">
                  <CheckCircle2 className="w-3 h-3" />
                  Simulated Action Execution Outcome
                </div>
                <span className="px-2 py-0.5 rounded text-[8px] font-mono text-teal-300 bg-teal-500/15 border border-teal-500/30">
                  SAFE_SIMULATION
                </span>
              </div>
              <pre className="text-[11px] font-mono text-teal-200 bg-[#080C14] rounded-lg p-4 border border-[#1E293B] overflow-x-auto">
                {JSON.stringify(result.action_result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!result && !isExecuting && !error && (
        <div className="flex flex-col items-center justify-center py-20">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
            style={{
              background: 'linear-gradient(135deg, rgba(56,189,248,0.1) 0%, rgba(139,92,246,0.1) 100%)',
              border: '1px solid rgba(56,189,248,0.2)',
            }}
          >
            <GitBranch className="w-7 h-7 text-cyan-400" />
          </div>
          <h2 className="text-lg font-bold text-white mb-2">Multi-Agent Orchestration</h2>
          <p className="text-xs text-slate-500 max-w-md text-center leading-relaxed">
            Execute the governed multi-agent pipeline to analyze an order through
            Inventory → Procurement → Finance → Logistics → Supervisor stages,
            with LLM recommendations, policy evaluation, and approval gating.
          </p>
          <p className="text-[10px] text-slate-600 mt-3 font-mono">
            {isLive
              ? 'Click "Execute Governed Pipeline" to begin'
              : 'Switch to Live PostgreSQL mode to execute orchestration'}
          </p>
        </div>
      )}
    </div>
  );
};
