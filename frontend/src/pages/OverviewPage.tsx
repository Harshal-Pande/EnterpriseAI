import React from 'react';
import { ShoppingBag, Cpu, AlertTriangle, Activity } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { LiveAgentMesh } from '../components/overview/LiveAgentMesh';
import { LiveOrderPanel } from '../components/overview/LiveOrderPanel';
import { AgentDecisionPanel } from '../components/overview/AgentDecisionPanel';
import { ActivityStream } from '../components/overview/ActivityStream';

export const OverviewPage: React.FC = () => {
  const { orders, agents, activityLogs } = useDemo();

  const activeOrdersCount = orders.filter(o => o.status === 'Processing' || o.status === 'Approved' || o.status === 'Awaiting Procurement' || o.status === 'Finance Review').length;
  const agentsOnlineCount = agents.filter(a => a.status === 'ONLINE' || a.status === 'BUSY').length;
  const exceptionsCount = orders.filter(o => o.status === 'Exception').length;

  return (
    <div className="space-y-6">
      {/* Top Banner / Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="bg-[#121929] border border-[#24334D] rounded-xl p-4 flex items-center justify-between shadow-lg">
          <div>
            <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Active Orders</div>
            <div className="text-2xl font-bold text-white font-mono mt-1">{activeOrdersCount}</div>
            <div className="text-[10px] text-cyan-400 mt-0.5">Live Mesh Queue</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-blue-600/20 text-blue-400 flex items-center justify-center border border-blue-500/30">
            <ShoppingBag className="w-5 h-5" />
          </div>
        </div>

        {/* Metric 2 */}
        <div className="bg-[#121929] border border-[#24334D] rounded-xl p-4 flex items-center justify-between shadow-lg">
          <div>
            <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Agents Online</div>
            <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">{agentsOnlineCount} / 5</div>
            <div className="text-[10px] text-emerald-400 mt-0.5">Autonomous Mesh Primed</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-600/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
            <Cpu className="w-5 h-5" />
          </div>
        </div>

        {/* Metric 3 */}
        <div className="bg-[#121929] border border-[#24334D] rounded-xl p-4 flex items-center justify-between shadow-lg">
          <div>
            <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Active Exceptions</div>
            <div className="text-2xl font-bold text-amber-400 font-mono mt-1">{exceptionsCount}</div>
            <div className="text-[10px] text-amber-400 mt-0.5">Auto-Recovery Active</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-600/20 text-amber-400 flex items-center justify-center border border-amber-500/30">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>

        {/* Metric 4 */}
        <div className="bg-[#121929] border border-[#24334D] rounded-xl p-4 flex items-center justify-between shadow-lg">
          <div>
            <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Events Processed Today</div>
            <div className="text-2xl font-bold text-purple-400 font-mono mt-1">{activityLogs.length + 1420}</div>
            <div className="text-[10px] text-purple-400 mt-0.5">Audit Hash Verified</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-purple-600/20 text-purple-400 flex items-center justify-center border border-purple-500/30">
            <Activity className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Main Command Center Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Live Agent Mesh & Activity Stream */}
        <div className="lg:col-span-2 space-y-6">
          <LiveAgentMesh />
          <ActivityStream />
        </div>

        {/* Right Column (1 Col): Live Order Panel & Agent Decision Inspector */}
        <div className="space-y-6">
          <LiveOrderPanel />
          <AgentDecisionPanel />
        </div>
      </div>
    </div>
  );
};
