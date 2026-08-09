import React from 'react';
import { Play, RotateCcw, Cpu, Sparkles } from 'lucide-react';
import { useDemo } from '../../state/DemoContext';
import type { DemoScenario } from '../../types';

export const TopHeader: React.FC = () => {
  const {
    isSimulating,
    workflowStage,
    activeScenario,
    setActiveScenario,
    runDemoOrder,
    resetDemo
  } = useDemo();

  const scenarios: { id: DemoScenario; label: string }[] = [
    { id: 'normal', label: '1. Normal Order Flow' },
    { id: 'supplier_unavailable', label: '2. Scenario 1 — Supplier Unavailable' },
    { id: 'budget_breach', label: '3. Scenario 2 — Budget Breach' },
    { id: 'delivery_delay', label: '4. Scenario 3 — Delivery Delay' },
    { id: 'multi_exception', label: '5. Scenario 4 — Multi-Exception Recovery' },
  ];

  return (
    <header className="bg-[#0B111E]/90 backdrop-blur-md border-b border-[#1E293B] px-6 py-3 sticky top-0 z-20 flex flex-wrap items-center justify-between gap-4">
      {/* Title & Subtitle */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
            ENTERPRISE AI MESH
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30 font-mono">
              PROTOTYPE
            </span>
          </h1>
        </div>
        <p className="text-xs text-slate-400 font-medium">
          Autonomous Order Fulfilment & Decision Intelligence System
        </p>
      </div>

      {/* Global DEMO MODE Control Bar */}
      <div className="flex items-center gap-3 bg-[#131C2E] border border-[#24334D] p-1.5 rounded-xl shadow-lg">
        <div className="flex items-center gap-1.5 px-2 text-xs font-semibold text-slate-300">
          <Sparkles className="w-4 h-4 text-cyan-400 animate-pulse" />
          <span className="text-[11px] uppercase tracking-wider text-slate-400">Demo Mode:</span>
        </div>

        {/* Scenario Dropdown */}
        <select
          value={activeScenario}
          onChange={(e) => setActiveScenario(e.target.value as DemoScenario)}
          disabled={isSimulating}
          className="bg-[#0A0F1D] text-slate-200 border border-[#2B3A54] rounded-lg px-3 py-1.5 text-xs font-medium focus:outline-none focus:border-blue-500 disabled:opacity-50 cursor-pointer"
        >
          {scenarios.map(s => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>

        {/* Reset Button */}
        <button
          onClick={resetDemo}
          disabled={isSimulating}
          className="p-1.5 bg-[#1B263B] hover:bg-[#253552] text-slate-300 rounded-lg text-xs font-medium transition disabled:opacity-40 flex items-center gap-1"
          title="Reset Simulation State"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        {/* Run Demo Order Button */}
        <button
          onClick={() => runDemoOrder()}
          disabled={isSimulating}
          className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold text-white shadow-md transition-all ${
            isSimulating
              ? 'bg-amber-600/80 cursor-wait'
              : 'bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 shadow-blue-500/25'
          }`}
        >
          {isSimulating ? (
            <>
              <Cpu className="w-4 h-4 animate-spin text-amber-300" />
              <span>Simulating ({workflowStage})...</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Run Demo Order</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
};
