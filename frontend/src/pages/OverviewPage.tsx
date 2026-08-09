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
  const { orders, agents, activityLogs, runDemoOrder, isSimulating } = useDemo();

  const activeOrdersCount  = orders.filter(o => ['Processing', 'Approved', 'Awaiting Procurement', 'Finance Review'].includes(o.status)).length;
  const agentsOnlineCount  = agents.filter(a => a.status === 'ONLINE' || a.status === 'BUSY').length;
  const exceptionsCount    = orders.filter(o => o.status === 'Exception').length;
  const eventsTodayCount   = activityLogs.length + 48;

  return (
    <div className="space-y-6 max-w-none">
      {/* ── Page Header ─────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight leading-none">
            Command Center Overview
          </h1>
          <p className="text-sm text-slate-500 mt-1.5">
            Autonomous Order Fulfilment & Decision Intelligence
          </p>
        </div>

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
          label="Active Orders"
          value={activeOrdersCount}
          icon={<ShoppingBag className="w-5 h-5" />}
          accent={isSimulating ? 'active' : 'normal'}
        />
        <MetricCard
          label="Attention"
          value={exceptionsCount || 2}
          icon={<AlertTriangle className="w-5 h-5" />}
          accent="warning"
        />
        <MetricCard
          label="Events (24h)"
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
