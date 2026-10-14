import React from 'react';
import { Cpu, ShoppingBag, AlertTriangle, Activity, Play } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { LiveAgentMesh } from '../components/overview/LiveAgentMesh';
import { LiveOrderPanel } from '../components/overview/LiveOrderPanel';
import { AgentDecisionPanel } from '../components/overview/AgentDecisionPanel';
import { ActivityStream } from '../components/overview/ActivityStream';

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  accent?: 'normal' | 'warning' | 'active';
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, icon, accent = 'normal' }) => {
  const accentStyles = {
    normal:  { borderLeft: '3px solid #1E293B', borderColor: '#1E293B' },
    warning: { borderLeft: '3px solid #F59E0B' },
    active:  { borderLeft: '3px solid #38BDF8' },
  };
  const valueColor = {
    normal:  '#F8FAFC',
    warning: '#F59E0B',
    active:  '#38BDF8',
  }[accent];
  return (
    <div
      className="rounded-xl p-4 flex items-center gap-3.5"
      style={{
        background: '#111827',
        border: '1px solid #1E293B',
        ...accentStyles[accent]
      }}
    >
      <div
        className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
        style={{
          background: accent === 'warning' ? 'rgba(245,158,11,0.08)' : accent === 'active' ? 'rgba(56,189,248,0.08)' : '#162032',
          color: accent === 'warning' ? '#F59E0B' : accent === 'active' ? '#38BDF8' : '#475569'
        }}
      >
        {icon}
      </div>
      <div>
        <div className="text-[10px] font-mono font-bold uppercase tracking-widest" style={{ color: '#64748B' }}>
          {label}
        </div>
        <div className="text-2xl font-bold font-mono leading-none mt-0.5" style={{ color: valueColor }}>
          {value}
        </div>
      </div>
    </div>
  );
};

export const OverviewPage: React.FC = () => {
  const {
    orders,
    agents,
    activityLogs,
    runDemoOrder,
    isSimulating,
    dataMode,
    liveOrders,
    liveApprovals,
    liveAuditEvents,
    liveSchedulerStatus,
    wsConnectionState,
    isOrchestrating,
    executeLiveOrchestration,
    activeLiveOrderId,
  } = useDemo();

  const isLive = dataMode === 'live';

  const activeOrdersCount = isLive
    ? liveOrders.filter(o => ['PROCESSING', 'PENDING', 'OPEN', 'CONFIRMED'].includes((o.status || o.order_status || '').toUpperCase())).length || liveOrders.length
    : orders.filter(o => ['Processing', 'Approved', 'Awaiting Procurement', 'Finance Review'].includes(o.status)).length;

  const agentsOnlineCount = agents.filter(a => a.status === 'ONLINE' || a.status === 'BUSY').length;

  const exceptionsCount = isLive
    ? liveApprovals.filter(a => a.status === 'PENDING').length
    : orders.filter(o => o.status === 'Exception').length;

  const eventsTodayCount = isLive
    ? liveAuditEvents.length
    : activityLogs.length + 48;

  const getWsBadge = () => {
    switch (wsConnectionState) {
      case 'CONNECTED':
        return (
          <span className="inline-flex items-center gap-1.5 text-[10px] bg-emerald-950/70 text-emerald-300 border border-emerald-500/40 px-2.5 py-0.5 rounded-full font-mono font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            WS: CONNECTED
          </span>
        );
      case 'CONNECTING':
        return (
          <span className="inline-flex items-center gap-1.5 text-[10px] bg-blue-950/70 text-blue-300 border border-blue-500/40 px-2.5 py-0.5 rounded-full font-mono font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
            WS: CONNECTING
          </span>
        );
      case 'RECONNECTING':
        return (
          <span className="inline-flex items-center gap-1.5 text-[10px] bg-amber-950/70 text-amber-300 border border-amber-500/40 px-2.5 py-0.5 rounded-full font-mono font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            WS: RECONNECTING
          </span>
        );
      case 'UNAUTHORIZED':
        return (
          <span className="inline-flex items-center gap-1.5 text-[10px] bg-rose-950/70 text-rose-300 border border-rose-500/40 px-2.5 py-0.5 rounded-full font-mono font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
            WS: UNAUTHORIZED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 text-[10px] bg-slate-900 text-slate-400 border border-slate-700 px-2.5 py-0.5 rounded-full font-mono font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
            WS: OFFLINE
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-none">
      {/* ── Page Header ─────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-2xl font-extrabold text-white tracking-tight leading-none">
              Command Center Overview
            </h1>
            {isLive ? (
              <>
                <span className="text-[10px] bg-blue-900/60 text-blue-300 border border-blue-500/30 px-2 py-0.5 rounded font-mono font-semibold">
                  LIVE POSTGRESQL MESH
                </span>
                {getWsBadge()}
              </>
            ) : (
              <span className="text-[10px] bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded font-mono font-semibold">
                DEMO SIMULATION
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1.5">
            {isLive
              ? `Connected to PostgreSQL backend — Scheduler: ${liveSchedulerStatus?.status || (liveSchedulerStatus?.is_running ? 'Active' : 'Standby')} (${liveSchedulerStatus?.interval_seconds ?? liveSchedulerStatus?.configured_interval_seconds ?? 300}s, Queue: ${liveSchedulerStatus?.open_scenarios_count ?? 0}/${liveSchedulerStatus?.max_open_scenarios ?? 10}), Orders: ${liveOrders.length}, Audit Logs: ${liveAuditEvents.length}`
              : 'Autonomous Order Fulfilment & Decision Intelligence'}
          </p>
        </div>

        {isLive ? (
          <button
            id="overview-run-live"
            onClick={() => executeLiveOrchestration(activeLiveOrderId)}
            disabled={isOrchestrating}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-[13px] font-bold transition-all disabled:cursor-wait shrink-0"
            style={{
              background: isOrchestrating
                ? 'rgba(56,189,248,0.1)'
                : 'linear-gradient(135deg, #059669 0%, #0284C7 100%)',
              color: isOrchestrating ? '#38BDF8' : '#FFFFFF',
              border: `1px solid ${isOrchestrating ? 'rgba(56,189,248,0.3)' : 'transparent'}`,
              boxShadow: isOrchestrating ? 'none' : '0 4px 20px rgba(5,150,105,0.25)'
            }}
          >
            <Play className={`w-4 h-4 fill-current ${isOrchestrating ? 'animate-spin' : ''}`} />
            {isOrchestrating ? 'Orchestrating Pipeline…' : `Run Live Orchestration [${activeLiveOrderId}]`}
          </button>
        ) : (
          <button
            id="overview-run-demo"
            onClick={() => runDemoOrder()}
            disabled={isSimulating}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-[13px] font-bold transition-all disabled:cursor-wait shrink-0"
            style={{
              background: isSimulating
                ? 'rgba(56,189,248,0.1)'
                : 'linear-gradient(135deg, #38BDF8 0%, #2563EB 100%)',
              color: isSimulating ? '#38BDF8' : '#070F1A',
              border: `1px solid ${isSimulating ? 'rgba(56,189,248,0.3)' : 'transparent'}`,
              boxShadow: isSimulating ? 'none' : '0 4px 20px rgba(56,189,248,0.25)'
            }}
          >
            <Play className={`w-4 h-4 fill-current ${isSimulating ? 'animate-spin' : ''}`} />
            {isSimulating ? 'Simulation Running…' : 'Run Demo Order'}
          </button>
        )}
      </div>

      {/* ── Metric Cards ────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Agents Online"
          value={`${agentsOnlineCount}/5`}
          icon={<Cpu className="w-5 h-5" />}
          accent={agentsOnlineCount < 5 ? 'warning' : 'normal'}
        />
        <MetricCard
          label={isLive ? "Live Orders" : "Active Orders"}
          value={activeOrdersCount}
          icon={<ShoppingBag className="w-5 h-5" />}
          accent={isSimulating ? 'active' : 'normal'}
        />
        <MetricCard
          label={isLive ? "Pending Approvals" : "Attention"}
          value={exceptionsCount}
          icon={<AlertTriangle className="w-5 h-5" />}
          accent={exceptionsCount > 0 ? 'warning' : 'normal'}
        />
        <MetricCard
          label={isLive ? "Audit Log Events" : "Events (24h)"}
          value={eventsTodayCount}
          icon={<Activity className="w-5 h-5" />}
          accent={isSimulating ? 'active' : 'normal'}
        />
      </div>

      {/* ── Main Panel Row: Agent Mesh + Activity Stream ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <LiveAgentMesh />
        </div>
        <div>
          <ActivityStream />
        </div>
      </div>

      {/* ── Secondary Row: Order Runner + Decision Inspector ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <LiveOrderPanel />
        <AgentDecisionPanel />
      </div>
    </div>
  );
};
