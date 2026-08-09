import React, { useState } from 'react';
import {
  Play, RotateCcw, Cpu, Search, Bell, Settings, HelpCircle,
  ChevronDown, X
} from 'lucide-react';
import { useDemo } from '../../state/DemoContext';
import type { DemoScenario } from '../../types';

const SCENARIOS: { id: DemoScenario; label: string; tag: string }[] = [
  { id: 'normal',              label: 'Normal Order Flow',          tag: 'Standard' },
  { id: 'supplier_unavailable',label: 'Supplier Unavailable',       tag: 'Exception' },
  { id: 'budget_breach',       label: 'Budget Breach',              tag: 'Exception' },
  { id: 'delivery_delay',      label: 'Delivery Delay (+48h)',       tag: 'Exception' },
  { id: 'multi_exception',     label: 'Multi-Exception Recovery',   tag: 'Stress' },
];

export const TopHeader: React.FC = () => {
  const {
    isSimulating,
    workflowStage,
    activeScenario,
    setActiveScenario,
    runDemoOrder,
    resetDemo
  } = useDemo();

  const [showScenarioPicker, setShowScenarioPicker] = useState(false);
  const [showNotifPanel, setShowNotifPanel] = useState(false);

  const activeScenarioMeta = SCENARIOS.find(s => s.id === activeScenario) ?? SCENARIOS[0];

  const stageLabel: Record<string, string> = {
    IDLE:                    'Idle',
    RECEIVED:                'Order Received',
    SUPERVISOR_ANALYSIS:     'Supervisor Analysing',
    INVENTORY_CHECK:         'Inventory Check',
    PROCUREMENT_NEGOTIATION: 'Procurement Negotiating',
    FINANCE_VALIDATION:      'Finance Validating',
    LOGISTICS_FEASIBILITY:   'Logistics Routing',
    SUPERVISOR_DECISION:     'Final Decision',
    COMPLETED:               'Order Completed',
  };

  return (
    <header
      className="h-12 shrink-0 flex items-center justify-between px-5 gap-4 sticky top-0 z-20"
      style={{
        background: '#07090F',
        borderBottom: '1px solid #1A2438'
      }}
    >
      {/* Left: Title + Search */}
      <div className="flex items-center gap-5 min-w-0">
        <div className="shrink-0">
          <span className="text-[13px] font-bold text-white tracking-tight">
            Enterprise AI Mesh
          </span>
        </div>

        {/* Global Search */}
        <div className="relative w-56 hidden lg:block">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search orders, agents, IDs…"
            id="global-search"
            className="w-full h-8 pl-9 pr-3 text-[12px] text-slate-200 placeholder-slate-600 rounded-lg focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition"
            style={{ background: '#0F172A', border: '1px solid #1E293B' }}
          />
        </div>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-2 shrink-0">

        {/* System Status Badge */}
        <div
          className="hidden md:flex items-center gap-2 px-3 h-7 rounded-md text-[11px] font-medium"
          style={{
            background: isSimulating ? 'rgba(56,189,248,0.08)' : 'rgba(16,185,129,0.08)',
            border: `1px solid ${isSimulating ? 'rgba(56,189,248,0.2)' : 'rgba(16,185,129,0.2)'}`,
            color: isSimulating ? '#38BDF8' : '#10B981'
          }}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${isSimulating ? 'bg-cyan-400 animate-ping' : 'bg-emerald-400'}`}
          />
          <span className="font-mono text-[10px]">
            {isSimulating ? (stageLabel[workflowStage] ?? workflowStage) : 'System Status: Optimal'}
          </span>
        </div>

        {/* Icon Group */}
        <div className="flex items-center gap-0.5" style={{ borderRight: '1px solid #1E293B', paddingRight: '8px', marginRight: '4px' }}>
          {/* Notifications */}
          <div className="relative">
            <button
              id="btn-notifications"
              onClick={() => setShowNotifPanel(v => !v)}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] transition"
            >
              <Bell className="w-4 h-4" />
            </button>
            {showNotifPanel && (
              <div
                className="absolute right-0 top-10 w-72 rounded-xl shadow-2xl z-50 animate-fade-slide text-xs"
                style={{ background: '#0F172A', border: '1px solid #24334D' }}
              >
                <div className="flex items-center justify-between px-4 py-3 border-b border-[#1E293B]">
                  <span className="font-bold text-white text-sm">Notifications</span>
                  <button onClick={() => setShowNotifPanel(false)} className="text-slate-500 hover:text-white"><X className="w-3.5 h-3.5" /></button>
                </div>
                <div className="p-3 space-y-2">
                  {[
                    { color: 'amber', text: 'Inventory shortfall detected: 78 units WP-800' },
                    { color: 'rose',  text: 'Exception order ORD-1047: Budget breach alert' },
                    { color: 'cyan',  text: 'Audit block #184729 committed to Polygon layer' },
                  ].map(({ color, text }) => (
                    <div key={text} className="p-2.5 rounded-lg flex gap-2.5 items-start" style={{ background: '#080C14', border: '1px solid #1E293B' }}>
                      <span className={`w-1.5 h-1.5 rounded-full mt-1 shrink-0 ${color === 'amber' ? 'bg-amber-400' : color === 'rose' ? 'bg-rose-400' : 'bg-cyan-400'}`} />
                      <span className="text-slate-300 text-[11px] leading-relaxed">{text}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <button
            id="btn-settings"
            className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] transition"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>

          <button
            id="btn-help"
            className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] transition"
            title="Help"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        </div>

        {/* Scenario Picker */}
        <div className="relative">
          <button
            id="scenario-picker"
            onClick={() => !isSimulating && setShowScenarioPicker(v => !v)}
            disabled={isSimulating}
            className="flex items-center gap-2 h-8 px-3 rounded-lg text-[11px] font-medium text-slate-300 hover:text-white transition disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: '#111827', border: '1px solid #1E293B' }}
          >
            <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
              activeScenario === 'normal'
                ? 'bg-emerald-500/15 text-emerald-300'
                : 'bg-amber-500/15 text-amber-300'
            }`}>
              {activeScenarioMeta.tag}
            </span>
            <span className="hidden sm:inline max-w-[120px] truncate">{activeScenarioMeta.label}</span>
            <ChevronDown className="w-3 h-3 text-slate-500 shrink-0" />
          </button>

          {showScenarioPicker && (
            <div
              className="absolute right-0 top-10 w-64 rounded-xl shadow-2xl z-50 text-xs animate-fade-slide"
              style={{ background: '#0F172A', border: '1px solid #24334D' }}
            >
              <div className="px-3 py-2 border-b border-[#1E293B]">
                <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider">Demo Scenarios</span>
              </div>
              {SCENARIOS.map(s => (
                <button
                  key={s.id}
                  onClick={() => { setActiveScenario(s.id); setShowScenarioPicker(false); }}
                  className={`w-full flex items-center justify-between px-3 py-2.5 text-left transition hover:bg-white/[0.05] ${
                    s.id === activeScenario ? 'text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span>{s.label}</span>
                  <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold ${
                    s.tag === 'Standard'  ? 'bg-emerald-500/15 text-emerald-300' :
                    s.tag === 'Stress'    ? 'bg-purple-500/15 text-purple-300'   :
                                            'bg-amber-500/15  text-amber-300'
                  }`}>{s.tag}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Reset */}
        <button
          id="btn-reset"
          onClick={resetDemo}
          disabled={isSimulating}
          title="Reset Simulation"
          className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] transition disabled:opacity-40"
          style={{ border: '1px solid #1E293B' }}
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        {/* Run Demo Order - Primary CTA */}
        <button
          id="btn-run-demo"
          onClick={() => runDemoOrder()}
          disabled={isSimulating}
          className="flex items-center gap-2 px-4 h-8 rounded-lg text-[12px] font-bold transition-all disabled:cursor-wait shrink-0"
          style={isSimulating ? {
            background: 'rgba(56,189,248,0.12)',
            border: '1px solid rgba(56,189,248,0.3)',
            color: '#38BDF8'
          } : {
            background: 'linear-gradient(135deg, #38BDF8 0%, #2563EB 100%)',
            color: '#07090F',
            boxShadow: '0 2px 12px rgba(56,189,248,0.25)'
          }}
        >
          {isSimulating ? (
            <>
              <Cpu className="w-3.5 h-3.5 animate-spin" />
              <span className="hidden sm:inline font-mono text-[10px]">{stageLabel[workflowStage] ?? 'Running…'}</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Run Demo Order</span>
            </>
          )}
        </button>

        {/* User Avatar */}
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 cursor-pointer"
          style={{
            background: 'linear-gradient(135deg, #312E81 0%, #1E1B4B 100%)',
            border: '1px solid rgba(99,102,241,0.3)',
            color: '#A5B4FC'
          }}
          title="Admin"
        >
          AS
        </div>
      </div>
    </header>
  );
};
