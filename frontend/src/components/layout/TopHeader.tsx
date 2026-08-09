import React from 'react';
import { Play, RotateCcw, Cpu, Search, Bell, Settings, HelpCircle } from 'lucide-react';
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
    <header className="bg-[#090D16] border-b border-[#1B2638] px-6 py-3 sticky top-0 z-20 flex items-center justify-between gap-4 font-sans">
      {/* Title & Global Search matching Screenshot */}
      <div className="flex items-center gap-8 flex-1">
        <h1 className="text-xl font-bold tracking-tight text-white shrink-0">
          Enterprise AI Mesh
        </h1>

        {/* Global Search Bar */}
        <div className="relative max-w-md w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search parameters, entities, order IDs..."
            className="w-full bg-[#101726] border border-[#233148] rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
      </div>

      {/* Right Controls: System Status + Action Controls + User Profile */}
      <div className="flex items-center gap-4">
        {/* System Status Optimal Badge */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-[#101F29] border border-emerald-500/30 rounded-lg text-emerald-400 text-xs font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>System Status: Optimal</span>
        </div>

        {/* Icons */}
        <div className="flex items-center gap-2 text-slate-400 border-r border-[#1B2638] pr-3">
          <button className="p-1.5 hover:text-white rounded-lg hover:bg-[#101726] transition" title="Notifications">
            <Bell className="w-4 h-4" />
          </button>
          <button className="p-1.5 hover:text-white rounded-lg hover:bg-[#101726] transition" title="Settings">
            <Settings className="w-4 h-4" />
          </button>
          <button className="p-1.5 hover:text-white rounded-lg hover:bg-[#101726] transition" title="Help">
            <HelpCircle className="w-4 h-4" />
          </button>
        </div>

        {/* Global Demo Controls */}
        <div className="flex items-center gap-2 bg-[#101726] border border-[#233148] p-1 rounded-xl">
          <select
            value={activeScenario}
            onChange={(e) => setActiveScenario(e.target.value as DemoScenario)}
            disabled={isSimulating}
            className="bg-[#090D16] text-slate-200 border border-[#1B2638] rounded-lg px-2.5 py-1 text-xs font-medium focus:outline-none disabled:opacity-50 cursor-pointer"
          >
            {scenarios.map(s => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>

          <button
            onClick={resetDemo}
            disabled={isSimulating}
            className="p-1.5 bg-[#1B2638] hover:bg-[#25344F] text-slate-300 rounded-lg text-xs transition disabled:opacity-40"
            title="Reset Simulation State"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => runDemoOrder()}
            disabled={isSimulating}
            className={`flex items-center gap-1.5 px-3.5 py-1 rounded-lg text-xs font-semibold text-slate-900 bg-[#E0F8FF] hover:bg-white shadow-md transition-all ${
              isSimulating ? 'opacity-80 cursor-wait' : ''
            }`}
          >
            {isSimulating ? (
              <>
                <Cpu className="w-3.5 h-3.5 animate-spin text-slate-900" />
                <span>({workflowStage})</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 fill-current" />
                <span>Run Demo Order</span>
              </>
            )}
          </button>
        </div>

        {/* User Profile Avatar matching Screenshot */}
        <div className="w-8 h-8 rounded-full overflow-hidden border border-slate-700 bg-indigo-900/50 flex items-center justify-center font-bold text-xs text-cyan-300 shrink-0">
          AS
        </div>
      </div>
    </header>
  );
};
