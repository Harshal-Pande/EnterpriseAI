import React from 'react';
import { AlertTriangle, Play, Square } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import type { DemoScenario } from '../types';

export const ExceptionsPage: React.FC = () => {
  const { activeScenario, setActiveScenario, runDemoOrder, isSimulating, resetDemo } = useDemo();

  const scenarios: {
    id: DemoScenario;
    title: string;
    description: string;
    borderClass: string;
    impact: string;
    mitigation: string;
  }[] = [
    {
      id: 'supplier_unavailable',
      title: 'Supplier Unavailable',
      description: 'Simulates total node failure for primary raw material supplier (Tier 1). Procurement Agent detects outage and re-routes.',
      borderClass: 'border-l-4 border-l-rose-500',
      impact: '1 Shortage',
      mitigation: 'Supplier B (Pune)'
    },
    {
      id: 'budget_breach',
      title: 'Budget Breach',
      description: 'Triggers cost anomaly >15% over projected baseline in procurement phase. Finance Agent forces negotiation cycle.',
      borderClass: 'border-l-4 border-l-amber-500',
      impact: '+₹38,000 Quote',
      mitigation: 'Finance Re-negotiation'
    },
    {
      id: 'delivery_delay',
      title: 'Delivery Delay',
      description: 'Simulates +48h road weather delay on primary transit route. Logistics Agent automatically reroutes to rail cargo.',
      borderClass: 'border-l-4 border-l-cyan-500',
      impact: '+48h NH-53 Delay',
      mitigation: 'Express Rail Freight'
    },
    {
      id: 'multi_exception',
      title: 'Compound Multi-Exception',
      description: 'Triggers simultaneous supplier outage AND highway delay to test total multi-agent autonomous resilience and recovery.',
      borderClass: 'border-l-4 border-l-purple-500',
      impact: 'Dual Node Outage',
      mitigation: 'Full Agent Mesh Reroute'
    }
  ];

  return (
    <div className="space-y-6 font-sans">
      {/* Header matching Screenshot 1 */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1B2638] pb-5">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Exception Simulators & Stress Testing
          </h1>
          <p className="text-sm text-slate-400 font-medium mt-1">
            Inject controlled failures to test Mesh routing and recovery.
          </p>
        </div>

        <button
          onClick={resetDemo}
          className="px-4 py-2 bg-[#162035] hover:bg-[#1E2C4A] text-slate-200 font-semibold rounded-lg text-xs border border-[#233148] shadow transition shrink-0 self-start md:self-auto"
        >
          Reset Environment State
        </button>
      </div>

      {/* Exception Simulator Cards matching Screenshot 1 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {scenarios.map((scen) => {
          const isSelected = activeScenario === scen.id;
          const isActiveSimulating = isSimulating && isSelected;

          return (
            <div
              key={scen.id}
              className={`bg-[#111827] border border-[#1E293B] ${scen.borderClass} rounded-xl p-5 shadow-xl transition-all space-y-4 ${
                isSelected ? 'ring-2 ring-cyan-500/30' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-base text-white">{scen.title}</h3>
                  {isActiveSimulating && (
                    <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-300 text-[10px] font-mono rounded font-bold uppercase animate-pulse">
                      ACTIVE
                    </span>
                  )}
                </div>
                <AlertTriangle className="w-4 h-4 text-slate-400" />
              </div>

              <p className="text-xs text-slate-400 leading-relaxed font-sans">
                {scen.description}
              </p>

              {/* Impact & Mitigation Stats matching Screenshot 1 */}
              <div className="p-3 bg-[#090D16] rounded-lg border border-[#1E293B] grid grid-cols-2 gap-2 text-xs font-mono">
                <div>
                  <div className="text-[10px] text-slate-500 uppercase font-bold">IMPACTED</div>
                  <div className="text-white font-bold">{scen.impact}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase font-bold">MITIGATION</div>
                  <div className="text-emerald-400 font-bold">{scen.mitigation}</div>
                </div>
              </div>

              {/* Action Buttons matching Screenshot 1 */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => setActiveScenario(scen.id)}
                  className="px-3.5 py-1.5 bg-[#162035] hover:bg-[#1E2C4A] text-slate-300 rounded-lg text-xs font-medium border border-[#233148] transition"
                >
                  Configure
                </button>

                {isActiveSimulating ? (
                  <button
                    onClick={resetDemo}
                    className="px-4 py-1.5 bg-[#E0F8FF] text-slate-900 font-bold rounded-lg text-xs font-mono shadow flex items-center gap-1.5"
                  >
                    <Square className="w-3 h-3 fill-current" /> Halt Simulation
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      setActiveScenario(scen.id);
                      runDemoOrder(scen.id);
                    }}
                    className="px-4 py-1.5 bg-[#1A283D] hover:bg-cyan-600 hover:text-white text-cyan-300 border border-cyan-500/40 rounded-lg text-xs font-mono font-bold shadow flex items-center gap-1.5 transition"
                  >
                    <Play className="w-3 h-3 fill-current" /> Inject
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
