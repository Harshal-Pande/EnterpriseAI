import React from 'react';
import { Play, Square, Zap, ShieldOff, TrendingUp, GitMerge } from 'lucide-react';
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
  const { activeScenario, setActiveScenario, runDemoOrder, isSimulating, resetDemo } = useDemo();

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Exception Simulator</h1>
          <p className="text-sm text-slate-500 mt-1">
            Inject controlled failures to test autonomous mesh resilience and recovery
          </p>
        </div>
        <button
          onClick={resetDemo}
          className="px-4 py-2 rounded-lg text-[12px] font-semibold transition shrink-0"
          style={{ background: '#111827', color: '#94A3B8', border: '1px solid #1E293B' }}
        >
          Reset Environment
        </button>
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
