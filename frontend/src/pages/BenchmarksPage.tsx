import React from 'react';
import { BarChart3, TrendingDown, Download, Zap, Clock, Activity } from 'lucide-react';
import { useDemo } from '../state/DemoContext';

interface BarGroupProps {
  label: string;
  legacyMs: number;
  meshMs: number;
  maxMs: number;
}

const BarGroup: React.FC<BarGroupProps> = ({ label, legacyMs, meshMs, maxMs }) => {
  const legacyH = Math.round((legacyMs / maxMs) * 160);
  const meshH   = Math.round((meshMs  / maxMs) * 160);
  const improvement = Math.round(((legacyMs - meshMs) / legacyMs) * 100);

  return (
    <div className="flex flex-col items-center gap-2 flex-1">
      <div className="w-full flex items-end justify-center gap-2 h-40">
        <div className="flex flex-col items-center gap-0.5">
          <span className="text-[9px] font-mono text-slate-600">{legacyMs}ms</span>
          <div
            className="w-10 rounded-t-md"
            style={{ height: `${legacyH}px`, background: '#1E293B' }}
          />
        </div>
        <div className="flex flex-col items-center gap-0.5">
          <span className="text-[9px] font-mono text-cyan-400">{meshMs}ms</span>
          <div
            className="w-10 rounded-t-md"
            style={{
              height: `${meshH}px`,
              background: 'linear-gradient(to top, #38BDF8, #6366F1)'
            }}
          />
        </div>
      </div>
      <div className="text-center">
        <div className="text-[11px] text-slate-300 font-medium">{label}</div>
        <div className="text-[10px] font-mono text-emerald-400 font-bold">-{improvement}%</div>
      </div>
    </div>
  );
};

export const BenchmarksPage: React.FC = () => {
  const { agents } = useDemo();
  const avgLatency = Math.round(agents.reduce((sum, a) => sum + a.avgResponseMs, 0) / agents.length);

  const benchmarkData = [
    { label: 'Query Resolution', legacyMs: 750, meshMs: 220 },
    { label: 'Data Aggregation', legacyMs: 950, meshMs: 380 },
    { label: 'Decision Engine',  legacyMs: 600, meshMs: 140 },
    { label: 'Exception Recovery', legacyMs: 1200, meshMs: 310 },
    { label: 'Audit Commit',    legacyMs: 480,  meshMs: 88  },
  ];
  const maxMs = Math.max(...benchmarkData.map(b => b.legacyMs));

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Performance Benchmarks</h1>
          <p className="text-sm text-slate-500 mt-1">
            Latency comparison vs. legacy pipeline · AI Mesh operational efficiency metrics
          </p>
        </div>
        <button
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-semibold transition shrink-0"
          style={{ background: '#111827', color: '#94A3B8', border: '1px solid #1E293B' }}
        >
          <Download className="w-3.5 h-3.5" /> Export Report
        </button>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'MTTR (Recovery Time)', value: '1.2s',    base: '24.5s',  pct: '95%', icon: <Zap className="w-4 h-4" />, color: '#10B981' },
          { label: 'Avg Agent Latency',    value: `${avgLatency}ms`, base: '620ms', pct: '62%', icon: <Clock className="w-4 h-4" />, color: '#38BDF8' },
          { label: 'Compute Efficiency',   value: '42%',     base: 'Legacy 100%', pct: '↓58%', icon: <Activity className="w-4 h-4" />, color: '#F59E0B' },
          { label: 'SLA Compliance Rate',  value: '99.4%',   base: 'All Agents', pct: '+0.12%', icon: <BarChart3 className="w-4 h-4" />, color: '#8B5CF6' },
        ].map(({ label, value, base, pct, icon, color }) => (
          <div key={label} className="rounded-xl p-4" style={{ background: '#111827', border: '1px solid #1E293B' }}>
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: color + '15', color }}>
                {icon}
              </div>
              <span className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-wider">{label}</span>
            </div>
            <div className="text-2xl font-bold font-mono" style={{ color }}>{value}</div>
            <div className="flex items-center gap-1.5 mt-1">
              <TrendingDown className="w-3 h-3 text-emerald-400 shrink-0" />
              <span className="text-[10px] font-mono text-emerald-400">{pct} vs {base}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Latency Chart — 2 cols */}
        <div className="lg:col-span-2 rounded-xl overflow-hidden" style={{ background: '#111827', border: '1px solid #1E293B' }}>
          <div className="px-5 py-4 border-b border-[#1E293B] flex items-center justify-between">
            <h2 className="text-sm font-bold text-white">Latency Comparison: AI Mesh vs Legacy Pipeline</h2>
            <div className="flex items-center gap-4 text-[11px] font-mono shrink-0">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#1E293B]" />
                <span className="text-slate-500">Legacy</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm" style={{ background: '#38BDF8' }} />
                <span className="text-slate-300">AI Mesh</span>
              </div>
            </div>
          </div>

          <div className="p-6 pb-4">
            {/* Y-axis labels + chart */}
            <div className="flex gap-2">
              {/* Y axis */}
              <div className="flex flex-col justify-between text-[10px] font-mono text-slate-600 h-40 py-1 shrink-0 w-12 text-right pr-2">
                {[1200, 900, 600, 300, 0].map(v => (
                  <span key={v}>{v}ms</span>
                ))}
              </div>
              {/* Bars + X axis */}
              <div className="flex-1 relative">
                {/* Horizontal gridlines */}
                <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
                  {[0, 1, 2, 3, 4].map(i => (
                    <div key={i} className="border-t border-[#1E293B] w-full" />
                  ))}
                </div>
                <div className="relative flex items-end gap-4 h-40">
                  {benchmarkData.map(b => (
                    <BarGroup key={b.label} {...b} maxMs={maxMs} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Agent Efficiency Panel — 1 col */}
        <div className="rounded-xl overflow-hidden" style={{ background: '#0F172A', border: '1px solid #1E293B' }}>
          <div className="px-5 py-4 border-b border-[#1E293B]">
            <h2 className="text-sm font-bold text-white">Agent Efficiency</h2>
          </div>
          <div className="p-5 space-y-3">
            {agents.map(agent => {
              const efficiency = Math.max(0, Math.round(100 - (agent.workload * 0.5)));
              return (
                <div key={agent.id} className="space-y-1.5">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-medium text-slate-300 capitalize">{agent.name.replace(' Agent', '')}</span>
                    <span className="font-mono text-slate-500">{agent.avgResponseMs}ms</span>
                  </div>
                  <div className="h-1.5 rounded-full overflow-hidden" style={{ background: '#1E293B' }}>
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${efficiency}%`,
                        background: efficiency > 70
                          ? 'linear-gradient(90deg, #38BDF8, #6366F1)'
                          : 'linear-gradient(90deg, #F59E0B, #EF4444)'
                      }}
                    />
                  </div>
                  <div className="text-[9px] font-mono text-slate-600 text-right">{efficiency}% efficient</div>
                </div>
              );
            })}
          </div>

          {/* Efficiency Metrics */}
          <div className="px-5 pb-5 space-y-3">
            <div className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest pt-3 border-t border-[#1E293B]">
              System Metrics
            </div>
            {[
              { label: 'Autonomous Decisions',  value: '98.7%', color: '#10B981' },
              { label: 'Human Override Rate',   value: '1.3%',  color: '#F59E0B' },
              { label: 'Exception Auto-Resolve', value: '96.1%', color: '#38BDF8' },
              { label: 'Audit Block Success',   value: '100%',  color: '#8B5CF6' },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex items-center justify-between text-[11px] py-1 border-b border-[#1E293B] last:border-0">
                <span className="text-slate-400">{label}</span>
                <span className="font-mono font-bold" style={{ color }}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
