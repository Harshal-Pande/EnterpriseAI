import React from 'react';
import { TrendingDown, Download, Zap, Clock, Activity, BarChart3, Play, Square } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import type { DemoScenario } from '../types';

/* ─────────────────────────────────────────────────
   Bar Group — one metric pair (Legacy vs AI Mesh)
───────────────────────────────────────────────── */
interface BarGroupProps {
  label: string;
  legacyMs: number;
  meshMs: number;
  maxMs: number;
}

const BarGroup: React.FC<BarGroupProps> = ({ label, legacyMs, meshMs, maxMs }) => {
  const maxBarHeight = 160;
  const legacyH     = Math.round((legacyMs / maxMs) * maxBarHeight);
  const meshH       = Math.round((meshMs  / maxMs) * maxBarHeight);
  const improvement = Math.round(((legacyMs - meshMs) / legacyMs) * 100);

  return (
    <div className="flex flex-col items-center gap-2 flex-1 min-w-0">
      {/* Bars */}
      <div className="w-full flex items-end justify-center gap-2" style={{ height: `${maxBarHeight}px` }}>
        <div className="flex flex-col items-center gap-0.5 shrink-0">
          <span className="text-[9px] font-mono text-slate-600">{legacyMs}ms</span>
          <div
            className="w-10 rounded-t-sm"
            style={{ height: `${legacyH}px`, background: '#1E293B' }}
            title={`Legacy: ${legacyMs}ms`}
          />
        </div>
        <div className="flex flex-col items-center gap-0.5 shrink-0">
          <span className="text-[9px] font-mono text-cyan-500">{meshMs}ms</span>
          <div
            className="w-10 rounded-t-sm"
            style={{
              height: `${meshH}px`,
              background: 'linear-gradient(to top, #38BDF8, #6366F1)'
            }}
            title={`AI Mesh: ${meshMs}ms`}
          />
        </div>
      </div>
      {/* Label */}
      <div className="text-center px-1">
        <div className="text-[11px] text-slate-300 font-medium leading-snug truncate max-w-[90px]">{label}</div>
        <div className="text-[10px] font-mono text-emerald-400 font-bold mt-0.5">-{improvement}%</div>
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────
   Exception Scenario Card
───────────────────────────────────────────────── */
interface ScenarioCardProps {
  id: DemoScenario;
  title: string;
  description: string;
  impact: string;
  mitigation: string;
  accentColor: string;
  tag: string;
  icon: React.ReactNode;
  isSelected: boolean;
  isRunning: boolean;
  isSimulating: boolean;
  onSelect: () => void;
  onInject: () => void;
  onHalt: () => void;
}

const ScenarioCard: React.FC<ScenarioCardProps> = ({
  title, description, impact, mitigation, accentColor, tag, icon,
  isSelected, isRunning, isSimulating, onSelect, onInject, onHalt
}) => (
  <div
    className="rounded-xl overflow-hidden flex flex-col transition-all duration-200"
    style={{
      background: '#111827',
      border: `1px solid ${isSelected ? accentColor + '40' : '#1E293B'}`,
      borderLeft: `4px solid ${accentColor}`,
      boxShadow: isSelected ? `0 0 18px ${accentColor}12` : 'none',
    }}
  >
    <div className="p-5 flex flex-col gap-4 flex-1">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: accentColor + '15', color: accentColor }}
          >
            {icon}
          </div>
          <div className="min-w-0">
            <div className="font-bold text-sm text-white leading-tight">{title}</div>
            {isRunning && (
              <span
                className="inline-block text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded animate-pulse mt-0.5"
                style={{ background: accentColor + '20', color: accentColor }}
              >
                Simulating
              </span>
            )}
          </div>
        </div>
        <span
          className="shrink-0 px-2 py-0.5 rounded text-[9px] font-mono font-bold"
          style={{ background: accentColor + '15', color: accentColor }}
        >
          {tag}
        </span>
      </div>

      {/* Description */}
      <p className="text-[12px] text-slate-400 leading-relaxed flex-1">{description}</p>

      {/* Impact / Mitigation */}
      <div
        className="grid grid-cols-2 gap-3 p-3 rounded-lg text-[11px] font-mono"
        style={{ background: '#080C14', border: '1px solid #1E293B' }}
      >
        <div>
          <div className="text-[9px] text-slate-600 uppercase font-bold mb-0.5">Impact</div>
          <div className="font-bold" style={{ color: accentColor }}>{impact}</div>
        </div>
        <div>
          <div className="text-[9px] text-slate-600 uppercase font-bold mb-0.5">Mitigation</div>
          <div className="font-bold text-emerald-400">{mitigation}</div>
        </div>
      </div>

      {/* Buttons */}
      <div className="flex items-center justify-between gap-2">
        <button
          onClick={onSelect}
          className="px-3 py-1.5 rounded-lg text-[11px] font-medium transition"
          style={{
            background:  isSelected ? accentColor + '12' : '#1E293B',
            color:       isSelected ? accentColor : '#94A3B8',
            border:      `1px solid ${isSelected ? accentColor + '30' : '#2D3748'}`,
          }}
        >
          {isSelected ? '✓ Configured' : 'Select Scenario'}
        </button>

        {isRunning ? (
          <button
            onClick={onHalt}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-bold font-mono transition"
            style={{ background: 'rgba(239,68,68,0.1)', color: '#EF4444', border: '1px solid rgba(239,68,68,0.2)' }}
          >
            <Square className="w-3 h-3 fill-current" /> Halt
          </button>
        ) : (
          <button
            onClick={onInject}
            disabled={isSimulating}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-bold font-mono transition disabled:opacity-40"
            style={{
              background: accentColor + '15',
              color:      accentColor,
              border:     `1px solid ${accentColor + '35'}`,
            }}
          >
            <Play className="w-3 h-3 fill-current" /> Inject Failure
          </button>
        )}
      </div>
    </div>
  </div>
);

/* ─────────────────────────────────────────────────
   BenchmarksPage — main component
───────────────────────────────────────────────── */

const SCENARIO_CONFIGS: {
  id: DemoScenario;
  title: string;
  description: string;
  impact: string;
  mitigation: string;
  accentColor: string;
  tag: string;
  icon: React.ReactNode;
}[] = [
  {
    id:          'supplier_unavailable',
    title:       'Supplier Unavailable',
    description: 'Simulates total node failure for the primary Tier-1 material supplier. Procurement Agent detects the outage and automatically escalates to a backup supplier.',
    impact:      '1 Node Outage',
    mitigation:  'Supplier B Fallback',
    accentColor: '#EF4444',
    tag:         'SUPPLIER',
    icon:        <Zap className="w-4 h-4" />,
  },
  {
    id:          'budget_breach',
    title:       'Budget Breach',
    description: 'Triggers a cost anomaly >15% over the approved procurement baseline. Finance Agent intercepts and forces a re-negotiation cycle with a cost-optimization strategy.',
    impact:      '₹38,000 Quote Excess',
    mitigation:  'Finance Re-negotiation',
    accentColor: '#F59E0B',
    tag:         'FINANCE',
    icon:        <Activity className="w-4 h-4" />,
  },
  {
    id:          'delivery_delay',
    title:       'Delivery Delay +48h',
    description: 'Simulates severe road weather disruption on NH-53 Pune-Nagpur corridor. Logistics Agent autonomously reroutes to Express Rail Cargo to meet SLA.',
    impact:      'Highway NH-53 +48h',
    mitigation:  'Express Rail Reroute',
    accentColor: '#38BDF8',
    tag:         'LOGISTICS',
    icon:        <Clock className="w-4 h-4" />,
  },
  {
    id:          'multi_exception',
    title:       'Multi-Exception Recovery',
    description: 'Injects simultaneous supplier outage AND highway delay to test full multi-agent autonomous resilience, coordinator re-planning, and cascaded recovery.',
    impact:      'Dual Cascade Failure',
    mitigation:  'Full Mesh Reroute',
    accentColor: '#8B5CF6',
    tag:         'COMPOUND',
    icon:        <BarChart3 className="w-4 h-4" />,
  },
];

const BENCHMARK_DATA = [
  { label: 'Query Resolution',  legacyMs: 750,  meshMs: 220 },
  { label: 'Data Aggregation',  legacyMs: 950,  meshMs: 380 },
  { label: 'Decision Engine',   legacyMs: 600,  meshMs: 140 },
  { label: 'Exception Recovery',legacyMs: 1200, meshMs: 310 },
  { label: 'Audit Commit',      legacyMs: 480,  meshMs: 88  },
];

export const BenchmarksPage: React.FC = () => {
  const { agents, activeScenario, setActiveScenario, isSimulating, runDemoOrder, resetDemo } = useDemo();

  const maxMs      = Math.max(...BENCHMARK_DATA.map(b => b.legacyMs));
  const avgLatency = Math.round(agents.reduce((s, a) => s + a.avgResponseMs, 0) / agents.length);

  const kpiCards = [
    {
      label: 'MTTR',
      value: '1.2s',
      sub:   '↓ 95% vs Legacy 24.5s',
      icon:  <Zap className="w-4 h-4" />,
      color: '#10B981'
    },
    {
      label: 'Avg Agent Latency',
      value: `${avgLatency}ms`,
      sub:   `↓ 62% vs Legacy 620ms`,
      icon:  <Clock className="w-4 h-4" />,
      color: '#38BDF8'
    },
    {
      label: 'Compute Overhead',
      value: '-42%',
      sub:   'vs Deterministic Pipeline',
      icon:  <Activity className="w-4 h-4" />,
      color: '#F59E0B'
    },
    {
      label: 'SLA Compliance',
      value: '99.4%',
      sub:   '+0.12% ↑ across all agents',
      icon:  <BarChart3 className="w-4 h-4" />,
      color: '#8B5CF6'
    },
    {
      label: 'Auto-Resolved Exceptions',
      value: '96.1%',
      sub:   'Human override: 3.9%',
      icon:  <TrendingDown className="w-4 h-4" />,
      color: '#EC4899'
    },
  ];

  return (
    <div className="space-y-8">

      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Benchmarks & Performance</h1>
          <p className="text-sm text-slate-500 mt-1">
            Comparative analysis vs. legacy pipeline · Real-time stress testing simulator
          </p>
        </div>
        <button
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-semibold transition shrink-0"
          style={{ background: '#111827', color: '#94A3B8', border: '1px solid #1E293B' }}
        >
          <Download className="w-3.5 h-3.5" /> Export Report
        </button>
      </div>

      {/* ══════════════════════════════════════════
          SECTION 1 — PERFORMANCE COMPARISON
      ══════════════════════════════════════════ */}
      <div className="space-y-5">
        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-[#1E293B]" />
          <span className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest shrink-0">
            Performance Comparison
          </span>
          <div className="h-px flex-1 bg-[#1E293B]" />
        </div>

        {/* ── Full-width Latency Chart ── */}
        <div
          className="rounded-xl overflow-hidden w-full"
          style={{ background: '#111827', border: '1px solid #1E293B' }}
        >
          <div className="px-6 py-4 border-b border-[#1E293B] flex items-center justify-between">
            <h2 className="text-sm font-bold text-white">Latency vs. Throughput — AI Mesh vs. Legacy Pipeline</h2>
            <div className="flex items-center gap-5 text-[11px] font-mono shrink-0">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#1E293B] inline-block" />
                <span className="text-slate-500">Deterministic Pipeline</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span
                  className="w-3 h-3 rounded-sm inline-block"
                  style={{ background: 'linear-gradient(135deg, #38BDF8, #6366F1)' }}
                />
                <span className="text-slate-300">Enterprise AI Mesh</span>
              </div>
            </div>
          </div>

          <div className="p-6">
            <div className="flex gap-3 items-end">
              {/* Y-axis */}
              <div
                className="flex flex-col justify-between text-right shrink-0 pb-8"
                style={{ width: '48px', height: '200px' }}
              >
                {[1200, 900, 600, 300, 0].map(v => (
                  <span key={v} className="text-[9px] font-mono text-slate-600 leading-none">{v}ms</span>
                ))}
              </div>

              {/* Chart area */}
              <div className="flex-1 min-w-0 relative">
                {/* Gridlines */}
                <div
                  className="absolute inset-x-0 top-0 pointer-events-none flex flex-col justify-between"
                  style={{ height: '160px' }}
                >
                  {[0, 1, 2, 3, 4].map(i => (
                    <div key={i} className="w-full border-t border-[#1E293B]" />
                  ))}
                </div>

                {/* Bar groups */}
                <div className="flex items-end gap-4 lg:gap-6 pb-0" style={{ height: '200px' }}>
                  {BENCHMARK_DATA.map(b => (
                    <BarGroup key={b.label} {...b} maxMs={maxMs} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── KPI Cards Row — full width, 3+ cols ── */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {kpiCards.map(({ label, value, sub, icon, color }) => (
            <div key={label} className="rounded-xl p-4" style={{ background: '#111827', border: '1px solid #1E293B' }}>
              <div className="flex items-center gap-2 mb-2.5">
                <div
                  className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: color + '15', color }}
                >
                  {icon}
                </div>
                <span className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-wider leading-tight">
                  {label}
                </span>
              </div>
              <div className="text-xl font-bold font-mono" style={{ color }}>{value}</div>
              <div className="flex items-center gap-1 mt-1">
                <TrendingDown className="w-3 h-3 text-emerald-400 shrink-0" />
                <span className="text-[10px] font-mono text-emerald-400">{sub}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ══════════════════════════════════════════
          SECTION 2 — EXCEPTION SIMULATORS
      ══════════════════════════════════════════ */}
      <div className="space-y-5">
        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-[#1E293B]" />
          <span className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest shrink-0">
            Exception Simulators &amp; Stress Testing
          </span>
          <div className="h-px flex-1 bg-[#1E293B]" />
        </div>

        <p className="text-[12px] text-slate-500">
          Inject controlled failures to test Mesh routing and recovery. Select a scenario then click{' '}
          <strong className="text-slate-400">Inject Failure</strong> to run the demo.
        </p>

        {/* ── 2 × 2 Scenario Grid — full content width ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {SCENARIO_CONFIGS.map(scen => {
            const isSelected = activeScenario === scen.id;
            const isRunning  = isSimulating && isSelected;
            return (
              <ScenarioCard
                key={scen.id}
                {...scen}
                isSelected={isSelected}
                isRunning={isRunning}
                isSimulating={isSimulating}
                onSelect={() => setActiveScenario(scen.id)}
                onInject={() => { setActiveScenario(scen.id); runDemoOrder(scen.id); }}
                onHalt={resetDemo}
              />
            );
          })}
        </div>
      </div>

    </div>
  );
};
