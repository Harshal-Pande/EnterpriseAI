import React from 'react';
import { Cpu, ShoppingBag, AlertTriangle, Activity, Play } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { LiveAgentMesh } from '../components/overview/LiveAgentMesh';
import { LiveOrderPanel } from '../components/overview/LiveOrderPanel';
import { AgentDecisionPanel } from '../components/overview/AgentDecisionPanel';
import { ActivityStream } from '../components/overview/ActivityStream';

export const OverviewPage: React.FC = () => {
  const { orders, agents, activityLogs, runDemoOrder, isSimulating } = useDemo();

  const activeOrdersCount = orders.filter(o => o.status === 'Processing' || o.status === 'Approved' || o.status === 'Awaiting Procurement' || o.status === 'Finance Review').length;
  const agentsOnlineCount = agents.filter(a => a.status === 'ONLINE' || a.status === 'BUSY').length;
  const exceptionsCount = orders.filter(o => o.status === 'Exception').length;

  return (
    <div className="space-y-6 font-sans">
      {/* Top Title & Primary Action Bar matching Screenshot 4 */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1B2638] pb-5">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Command Center Overview
          </h1>
          <p className="text-sm text-slate-400 font-medium mt-1">
            Autonomous Order Fulfilment & Decision Intelligence
          </p>
        </div>

        <button
          onClick={() => runDemoOrder()}
          disabled={isSimulating}
          className="px-5 py-2.5 bg-[#E0F8FF] hover:bg-white text-slate-900 font-bold rounded-lg text-xs tracking-wide shadow-lg transition flex items-center gap-2 font-mono shrink-0 self-start md:self-auto"
        >
          <Play className="w-4 h-4 fill-current" />
          <span>Run Demo Order</span>
        </button>
      </div>

      {/* 4 Metric Cards Row matching Screenshot 4 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-4 shadow-lg flex items-center gap-4">
          <div className="text-slate-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] text-slate-400 font-mono font-bold uppercase tracking-wider">
              AGENTS ONLINE
            </div>
            <div className="text-2xl font-bold text-white font-mono mt-0.5">
              {agentsOnlineCount}/5
            </div>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-4 shadow-lg flex items-center gap-4">
          <div className="text-slate-400">
            <ShoppingBag className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] text-slate-400 font-mono font-bold uppercase tracking-wider">
              ACTIVE ORDERS
            </div>
            <div className="text-2xl font-bold text-white font-mono mt-0.5">
              {activeOrdersCount}
            </div>
          </div>
        </div>

        {/* Metric 3: ATTENTION (Yellow/Amber Accent Border matching Screenshot 4) */}
        <div className="bg-[#111827] border border-[#1E293B] border-l-4 border-l-amber-500 rounded-xl p-4 shadow-lg flex items-center gap-4">
          <div className="text-amber-400">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] text-amber-400 font-mono font-bold uppercase tracking-wider">
              ATTENTION
            </div>
            <div className="text-2xl font-bold text-amber-400 font-mono mt-0.5">
              {exceptionsCount || 2}
            </div>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-4 shadow-lg flex items-center gap-4">
          <div className="text-slate-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] text-slate-400 font-mono font-bold uppercase tracking-wider">
              EVENTS (24H)
            </div>
            <div className="text-2xl font-bold text-white font-mono mt-0.5">
              {activityLogs.length + 48}
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Live Agent Mesh & Activity Stream matching Screenshot 4 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <LiveAgentMesh />
        </div>
        <div>
          <ActivityStream />
        </div>
      </div>

      {/* Secondary Row: Order Runner & Agent Rationale Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LiveOrderPanel />
        <AgentDecisionPanel />
      </div>
    </div>
  );
};
