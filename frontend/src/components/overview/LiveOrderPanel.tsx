import React from 'react';
import { ShoppingBag, Play, CheckCircle2, Clock, MapPin, CircleDollarSign, Package, AlertCircle } from 'lucide-react';
import { useDemo } from '../../state/DemoContext';

export const LiveOrderPanel: React.FC = () => {
  const {
    activeOrder,
    workflowStage,
    isSimulating,
    runDemoOrder,
    dataMode,
    liveOrders,
    activeLiveOrderId,
    setActiveLiveOrderId,
    executeLiveOrchestration,
    isOrchestrating,
    liveOrchestrationResult,
    orchestrationError
  } = useDemo();

  const isLive = dataMode === 'live';
  const currentLiveOrder = liveOrders.find(o => o.order_id === activeLiveOrderId) || liveOrders[0];

  const demoSteps = [
    { id: 'RECEIVED',                 label: 'Order Received',         agentColor: '#6366F1' },
    { id: 'SUPERVISOR_ANALYSIS',      label: 'Supervisor Analysis',    agentColor: '#6366F1' },
    { id: 'INVENTORY_CHECK',          label: 'Inventory Check',        agentColor: '#10B981' },
    { id: 'PROCUREMENT_NEGOTIATION',  label: 'Procurement Negotiation',agentColor: '#F59E0B' },
    { id: 'FINANCE_VALIDATION',       label: 'Finance Validation',     agentColor: '#EC4899' },
    { id: 'LOGISTICS_FEASIBILITY',    label: 'Logistics Feasibility',  agentColor: '#8B5CF6' },
    { id: 'SUPERVISOR_DECISION',      label: 'Supervisor Decision',    agentColor: '#6366F1' },
    { id: 'COMPLETED',                label: 'Approved & Audited',     agentColor: '#10B981' },
  ];

  const liveSteps = [
    { id: 'inventory',   label: 'Inventory Agent Check',   agentName: 'Inventory' },
    { id: 'procurement', label: 'Procurement Sourcing',    agentName: 'Procurement' },
    { id: 'finance',     label: 'Finance & Policy Check',  agentName: 'Finance' },
    { id: 'logistics',   label: 'Logistics Route Plan',    agentName: 'Logistics' },
    { id: 'supervisor',  label: 'Supervisor Synthesis',    agentName: 'Supervisor' },
  ];

  const stageOrder = demoSteps.map(s => s.id);
  const currentIdx = stageOrder.indexOf(workflowStage);
  const isDemoComplete = workflowStage === 'COMPLETED' || activeOrder.status === 'Approved';

  const getDemoStepStatus = (id: string) => {
    if (isDemoComplete) return 'completed';
    const i = stageOrder.indexOf(id);
    if (i < 0) return 'pending';
    if (i === currentIdx) return 'active';
    if (i < currentIdx) return 'completed';
    return 'pending';
  };

  const getLiveStepStatus = (stepId: string) => {
    if (!liveOrchestrationResult) {
      return isOrchestrating ? 'active' : 'pending';
    }
    const step =
      liveOrchestrationResult.agent_steps?.find(s => s.agent_name.toLowerCase() === stepId.toLowerCase()) ||
      liveOrchestrationResult.steps?.[stepId];
    if (!step) return isOrchestrating ? 'active' : 'pending';
    if (step.status === 'COMPLETED') return 'completed';
    if (step.status === 'FAILED') return 'failed';
    return 'active';
  };

  return (
    <div
      className="flex flex-col rounded-xl overflow-hidden"
      style={{ background: '#0F172A', border: '1px solid #1E293B' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1E293B] shrink-0">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: isLive ? 'rgba(5,150,105,0.15)' : 'rgba(37,99,235,0.15)', border: `1px solid ${isLive ? 'rgba(5,150,105,0.3)' : 'rgba(37,99,235,0.3)'}` }}
          >
            <ShoppingBag className={`w-3.5 h-3.5 ${isLive ? 'text-emerald-400' : 'text-blue-400'}`} />
          </div>
          <div>
            {isLive ? (
              <div className="flex items-center gap-2">
                <select
                  value={activeLiveOrderId || currentLiveOrder?.order_id || ''}
                  onChange={(e) => setActiveLiveOrderId(e.target.value)}
                  className="bg-[#162032] text-xs font-bold font-mono text-emerald-300 border border-emerald-500/30 rounded px-2 py-0.5 outline-none cursor-pointer"
                >
                  {liveOrders.map(o => (
                    <option key={o.order_id} value={o.order_id}>
                      {o.order_id} ({o.customer_name})
                    </option>
                  ))}
                </select>
                <span className="text-[10px] text-slate-400 font-mono">
                  {currentLiveOrder?.priority || 'NORMAL'}
                </span>
              </div>
            ) : (
              <>
                <div className="text-sm font-bold text-white">{activeOrder.id}</div>
                <div className="text-[10px] text-slate-500 truncate max-w-[200px]">{activeOrder.customer}</div>
              </>
            )}
          </div>
        </div>

        {isLive ? (
          <button
            onClick={() => executeLiveOrchestration(activeLiveOrderId || currentLiveOrder?.order_id)}
            disabled={isOrchestrating || liveOrders.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all disabled:opacity-40"
            style={{
              background: isOrchestrating ? 'rgba(56,189,248,0.1)' : 'rgba(5,150,105,0.2)',
              border: `1px solid ${isOrchestrating ? 'rgba(56,189,248,0.2)' : 'rgba(5,150,105,0.3)'}`,
              color: isOrchestrating ? '#38BDF8' : '#34D399'
            }}
          >
            <Play className={`w-3 h-3 fill-current ${isOrchestrating ? 'animate-spin' : ''}`} />
            {isOrchestrating ? 'Running…' : 'Run Pipeline'}
          </button>
        ) : (
          <button
            onClick={() => runDemoOrder()}
            disabled={isSimulating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all disabled:opacity-40"
            style={{
              background: isSimulating ? 'rgba(56,189,248,0.1)' : 'rgba(37,99,235,0.2)',
              border: `1px solid ${isSimulating ? 'rgba(56,189,248,0.2)' : 'rgba(37,99,235,0.3)'}`,
              color: isSimulating ? '#38BDF8' : '#60A5FA'
            }}
          >
            <Play className="w-3 h-3 fill-current" />
            {isSimulating ? 'Running…' : 'Run Demo'}
          </button>
        )}
      </div>

      {orchestrationError && (
        <div className="mx-4 mt-3 p-2 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-200 text-xs font-mono flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{orchestrationError}</span>
        </div>
      )}

      {/* Order Metadata */}
      <div className="grid grid-cols-2 gap-2 p-4">
        {isLive ? (
          [
            { icon: <Package className="w-3 h-3 text-cyan-400" />, label: 'Customer', value: currentLiveOrder?.customer_name || 'N/A', sub: `ID: ${currentLiveOrder?.order_id || 'N/A'}` },
            { icon: <MapPin className="w-3 h-3 text-emerald-400" />, label: 'Status', value: currentLiveOrder?.order_status || currentLiveOrder?.status || 'PENDING', sub: 'PostgreSQL record' },
            { icon: <CircleDollarSign className="w-3 h-3 text-pink-400" />, label: 'Order Value', value: currentLiveOrder?.total_amount_inr ? `₹${currentLiveOrder.total_amount_inr.toLocaleString()}` : '₹4,80,000', sub: currentLiveOrder?.currency || 'INR' },
            { icon: <Clock className="w-3 h-3 text-amber-400" />, label: 'Created Date', value: currentLiveOrder?.order_date ? currentLiveOrder.order_date.split('T')[0] : 'Today', sub: `${currentLiveOrder?.priority || 'NORMAL'} Priority` },
          ].map(({ icon, label, value, sub }) => (
            <div key={label} className="rounded-lg p-3" style={{ background: '#080C14', border: '1px solid #1E293B' }}>
              <div className="flex items-center gap-1 text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">
                {icon} {label}
              </div>
              <div className="text-[12px] font-semibold text-white leading-snug truncate">{value}</div>
              {sub && <div className="text-[10px] text-slate-500 mt-0.5 truncate">{sub}</div>}
            </div>
          ))
        ) : (
          [
            { icon: <Package className="w-3 h-3 text-cyan-400" />, label: 'Product & Qty',     value: `${activeOrder.quantity} units`, sub: activeOrder.product },
            { icon: <MapPin className="w-3 h-3 text-emerald-400" />, label: 'Destination',     value: activeOrder.destination },
            { icon: <CircleDollarSign className="w-3 h-3 text-pink-400" />, label: 'Budget Cap', value: `₹${activeOrder.budget.toLocaleString()}`, sub: `Est. ₹${activeOrder.estimatedCost.toLocaleString()}` },
            { icon: <Clock className="w-3 h-3 text-amber-400" />, label: 'Priority',           value: `${activeOrder.priority} Priority`, sub: activeOrder.createdAt.split(' ')[1] },
          ].map(({ icon, label, value, sub }) => (
            <div key={label} className="rounded-lg p-3" style={{ background: '#080C14', border: '1px solid #1E293B' }}>
              <div className="flex items-center gap-1 text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">
                {icon} {label}
              </div>
              <div className="text-[12px] font-semibold text-white leading-snug truncate">{value}</div>
              {sub && <div className="text-[10px] text-slate-500 mt-0.5 truncate">{sub}</div>}
            </div>
          ))
        )}
      </div>

      {/* Workflow Stepper */}
      <div className="px-4 pb-4">
        <div className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-2.5 flex items-center justify-between">
          <span>{isLive ? 'Multi-Agent Pipeline Steps' : 'Agent Workflow Pipeline'}</span>
          {isLive && liveOrchestrationResult?.decision_code && (
            <span className="text-[10px] font-mono text-emerald-400 font-bold">
              Decision: {liveOrchestrationResult.decision_code}
            </span>
          )}
        </div>
        <div className="space-y-1">
          {isLive ? (
            liveSteps.map((step, idx) => {
              const status = getLiveStepStatus(step.id);
              const stepObj =
                liveOrchestrationResult?.agent_steps?.find(s => s.agent_name.toLowerCase() === step.id.toLowerCase()) ||
                liveOrchestrationResult?.steps?.[step.id];
              const duration = stepObj?.duration_ms;
              return (
                <div
                  key={step.id}
                  className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg transition-all duration-150"
                  style={{
                    background: status === 'active' ? 'rgba(5,150,105,0.08)' : status === 'completed' ? 'rgba(16,185,129,0.04)' : 'transparent',
                    border: `1px solid ${status === 'active' ? 'rgba(5,150,105,0.25)' : status === 'completed' ? 'rgba(16,185,129,0.12)' : 'transparent'}`
                  }}
                >
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center shrink-0 text-[9px] font-bold"
                    style={{
                      background: status === 'completed' ? 'rgba(16,185,129,0.15)' : status === 'active' ? 'rgba(5,150,105,0.2)' : '#1E293B',
                      color: status === 'completed' ? '#10B981' : status === 'active' ? '#34D399' : '#475569',
                      border: `1px solid ${status === 'completed' ? 'rgba(16,185,129,0.3)' : status === 'active' ? 'rgba(5,150,105,0.4)' : '#1E293B'}`
                    }}
                  >
                    {status === 'completed' ? <CheckCircle2 className="w-3 h-3" /> : idx + 1}
                  </div>
                  <span className="text-[11px] flex-1 truncate" style={{
                    color: status === 'active' ? '#E2E8F0' : status === 'completed' ? '#94A3B8' : '#475569',
                    fontWeight: status === 'active' ? 600 : 400
                  }}>
                    {step.label}
                  </span>
                  {duration !== undefined && (
                    <span className="text-[9px] font-mono text-slate-500 shrink-0">{duration}ms</span>
                  )}
                  {status === 'active' && (
                    <span className="text-[9px] font-mono text-emerald-400 animate-pulse shrink-0">▸ Running</span>
                  )}
                  {status === 'completed' && (
                    <span className="text-[9px] font-mono text-emerald-400 shrink-0">✓</span>
                  )}
                </div>
              );
            })
          ) : (
            demoSteps.map((step, idx) => {
              const status = getDemoStepStatus(step.id);
              return (
                <div
                  key={step.id}
                  className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg transition-all duration-150"
                  style={{
                    background: status === 'active' ? 'rgba(37,99,235,0.08)' : status === 'completed' ? 'rgba(16,185,129,0.04)' : 'transparent',
                    border: `1px solid ${status === 'active' ? 'rgba(37,99,235,0.25)' : status === 'completed' ? 'rgba(16,185,129,0.12)' : 'transparent'}`
                  }}
                >
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center shrink-0 text-[9px] font-bold"
                    style={{
                      background: status === 'completed' ? 'rgba(16,185,129,0.15)' : status === 'active' ? 'rgba(37,99,235,0.2)' : '#1E293B',
                      color: status === 'completed' ? '#10B981' : status === 'active' ? '#60A5FA' : '#475569',
                      border: `1px solid ${status === 'completed' ? 'rgba(16,185,129,0.3)' : status === 'active' ? 'rgba(37,99,235,0.4)' : '#1E293B'}`
                    }}
                  >
                    {status === 'completed' ? <CheckCircle2 className="w-3 h-3" /> : idx + 1}
                  </div>
                  <span className="text-[11px] flex-1 truncate" style={{
                    color: status === 'active' ? '#E2E8F0' : status === 'completed' ? '#94A3B8' : '#475569',
                    fontWeight: status === 'active' ? 600 : 400
                  }}>
                    {step.label}
                  </span>
                  {status === 'active' && (
                    <span className="text-[9px] font-mono text-cyan-400 animate-pulse shrink-0">▸ Running</span>
                  )}
                  {status === 'completed' && (
                    <span className="text-[9px] font-mono text-emerald-400 shrink-0">✓</span>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
