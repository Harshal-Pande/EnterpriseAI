import React from 'react';
import { AlertTriangle, Play, CheckCircle2 } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import type { DemoScenario } from '../types';

export const ExceptionsPage: React.FC = () => {
  const { activeScenario, setActiveScenario, runDemoOrder, isSimulating } = useDemo();

  const scenarios: {
    id: DemoScenario;
    title: string;
    description: string;
    flow: string[];
  }[] = [
    {
      id: 'supplier_unavailable',
      title: 'Scenario 1 — Primary Supplier Stock Outage',
      description: 'Primary Supplier A reports 0 inventory. Procurement Agent detects outage and autonomously negotiates with Supplier B.',
      flow: [
        'Supplier A stock depleted (0 units)',
        'Procurement Agent detects outage signal',
        'Multi-supplier scoring engine re-evaluates Supplier B & C',
        'Supplier B selected (Score: 94%)',
        'Supervisor updates global execution graph'
      ]
    },
    {
      id: 'budget_breach',
      title: 'Scenario 2 — Financial Budget Cap Breach',
      description: 'Initial supplier quotation exceeds allocated order budget. Finance Agent rejects quote and forces procurement re-negotiation.',
      flow: [
        'Supplier C submits ₹8,88,000 quote',
        'Finance Agent flags budget breach (Limit ₹8,50,000)',
        'Finance rejects quote & demands re-negotiation',
        'Procurement re-routes to Supplier B (₹7,92,000)',
        'Finance Agent sanctions revised quote'
      ]
    },
    {
      id: 'delivery_delay',
      title: 'Scenario 3 — Transit Highway Disruption',
      description: 'Logistics Agent detects weather road block on NH-53 (+48h delay). Automatically re-routes transit via Express Rail Freight.',
      flow: [
        'Road weather alert on NH-53 highway (+48h delay)',
        'Logistics Agent flags SLA violation risk',
        'Carrier engine evaluates Express Rail Cargo',
        'Rail transit route approved (2-day SLA guaranteed)',
        'Supervisor updates dispatch schedule'
      ]
    },
    {
      id: 'multi_exception',
      title: 'Scenario 4 — Compound Multi-Exception Recovery',
      description: 'Triggers simultaneous supplier stock outage AND road delay. Demonstrates full multi-agent autonomous resilience and recovery.',
      flow: [
        'Supplier A offline AND NH-53 highway blocked',
        'Procurement & Logistics Agents detect dual fault',
        'Autonomous inter-agent negotiation cycle',
        'Supplier B selected + Rail Freight re-routed',
        'Supervisor verifies final multi-agent recovery'
      ]
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" /> Multi-Agent Exception Recovery & Resilience Engine
        </h2>
        <p className="text-xs text-slate-400">
          Simulate supply chain bottlenecks, supplier outages, and budget breaches to demonstrate autonomous agent recovery
        </p>
      </div>

      {/* Scenarios Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {scenarios.map(scen => {
          const isSelected = activeScenario === scen.id;
          return (
            <div
              key={scen.id}
              className={`bg-[#121929] border rounded-2xl p-5 shadow-xl transition-all duration-200 flex flex-col justify-between ${
                isSelected
                  ? 'border-amber-500 ring-2 ring-amber-500/30 bg-[#172136]'
                  : 'border-[#24334D] hover:border-slate-600'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="px-2.5 py-0.5 text-[10px] font-bold font-mono rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    RESILIENCE TEST
                  </span>
                  {isSelected && (
                    <span className="text-[10px] font-mono text-emerald-400 font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> SELECTED FOR DEMO
                    </span>
                  )}
                </div>

                <h3 className="font-bold text-sm text-white mb-1.5">{scen.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">{scen.description}</p>

                {/* Step Flow List */}
                <div className="space-y-1.5 bg-[#0B111E] p-3 rounded-xl border border-[#1E293B] text-[11px]">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                    Recovery Workflow Sequence
                  </div>
                  {scen.flow.map((step, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-slate-300">
                      <span className="w-4 h-4 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center text-[9px] font-bold shrink-0">
                        {idx + 1}
                      </span>
                      <span className="truncate">{step}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-4 mt-4 border-t border-[#1E293B] flex items-center justify-between">
                <button
                  onClick={() => setActiveScenario(scen.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    isSelected
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {isSelected ? 'Active Scenario' : 'Select Scenario'}
                </button>

                <button
                  onClick={() => {
                    setActiveScenario(scen.id);
                    runDemoOrder(scen.id);
                  }}
                  disabled={isSimulating}
                  className="px-4 py-1.5 bg-gradient-to-r from-amber-600 to-rose-600 hover:from-amber-500 hover:to-rose-500 text-white rounded-lg text-xs font-bold shadow-md flex items-center gap-1.5 disabled:opacity-40"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  {isSimulating && activeScenario === scen.id ? 'Running Exception...' : 'Run Scenario'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
