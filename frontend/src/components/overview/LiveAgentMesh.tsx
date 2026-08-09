import React from 'react';
import { Cpu, Package, Scale, CircleDollarSign, Truck, Activity } from 'lucide-react';
import { useDemo } from '../../state/DemoContext';
import type { AgentId } from '../../types';

export const LiveAgentMesh: React.FC = () => {
  const { agents, workflowStage, setSelectedAgentId, selectedAgentId } = useDemo();

  const getAgent = (id: AgentId) => agents.find(a => a.id === id);

  const supervisor = getAgent('supervisor');
  const inventory = getAgent('inventory');
  const procurement = getAgent('procurement');
  const finance = getAgent('finance');
  const logistics = getAgent('logistics');

  return (
    <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-5 shadow-xl relative overflow-hidden flex flex-col justify-between min-h-[380px]">
      {/* Background Grid Pattern */}
      <div
        className="absolute inset-0 opacity-15 pointer-events-none"
        style={{
          backgroundImage: `radial-[#38BDF8] 1px, transparent 1px)`,
          backgroundSize: '24px 24px'
        }}
      />

      {/* Header */}
      <div className="flex items-center justify-between z-10 mb-2">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            Live Agent Mesh Topology
          </h2>
          <p className="text-[11px] text-slate-400">
            Real-time inter-agent communication & orchestration canvas
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="flex items-center gap-1.5 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span>Mesh Active</span>
          </div>
        </div>
      </div>

      {/* Node Graph SVG Overlay + HTML Nodes Container */}
      <div className="relative flex-1 flex items-center justify-center my-4">
        {/* Connection Lines (SVG Layer) */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
          {/* Center to Top-Left (Inventory) */}
          <line
            x1="50%"
            y1="50%"
            x2="22%"
            y2="25%"
            stroke={inventory?.active ? '#10B981' : '#1E293B'}
            strokeWidth={inventory?.active ? '3' : '1.5'}
            className={inventory?.active ? 'animate-pulse-line' : ''}
          />
          {/* Center to Top-Right (Procurement) */}
          <line
            x1="50%"
            y1="50%"
            x2="78%"
            y2="25%"
            stroke={procurement?.active ? '#F59E0B' : '#1E293B'}
            strokeWidth={procurement?.active ? '3' : '1.5'}
            className={procurement?.active ? 'animate-pulse-line' : ''}
          />
          {/* Center to Bottom-Left (Finance) */}
          <line
            x1="50%"
            y1="50%"
            x2="22%"
            y2="75%"
            stroke={finance?.active ? '#EC4899' : '#1E293B'}
            strokeWidth={finance?.active ? '3' : '1.5'}
            className={finance?.active ? 'animate-pulse-line' : ''}
          />
          {/* Center to Bottom-Right (Logistics) */}
          <line
            x1="50%"
            y1="50%"
            x2="78%"
            y2="75%"
            stroke={logistics?.active ? '#8B5CF6' : '#1E293B'}
            strokeWidth={logistics?.active ? '3' : '1.5'}
            className={logistics?.active ? 'animate-pulse-line' : ''}
          />
        </svg>

        {/* Nodes Positioning */}
        <div className="relative z-10 w-full max-w-2xl h-[280px]">
          {/* SUPERVISOR (Center Node) */}
          <div
            onClick={() => setSelectedAgentId('supervisor')}
            className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all duration-300 p-4 rounded-2xl border flex flex-col items-center justify-center text-center w-48 shadow-2xl ${
              supervisor?.active || selectedAgentId === 'supervisor'
                ? 'bg-gradient-to-b from-indigo-900/90 to-indigo-950/90 border-indigo-400 ring-4 ring-indigo-500/20 shadow-indigo-500/30'
                : 'bg-[#151E32] border-[#253552] hover:border-indigo-400/50'
            }`}
          >
            <div className="w-10 h-10 rounded-xl bg-indigo-600/30 text-indigo-400 flex items-center justify-center mb-1.5 border border-indigo-500/40">
              <Cpu className={`w-6 h-6 ${supervisor?.active ? 'animate-spin' : ''}`} />
            </div>
            <div className="font-bold text-xs text-white">SUPERVISOR AGENT</div>
            <div className="text-[10px] text-indigo-300 font-mono mt-0.5 truncate max-w-[170px]">
              {supervisor?.active ? 'Synthesizing Decision...' : 'Orchestration Active'}
            </div>
            {supervisor?.active && (
              <span className="mt-1.5 px-2 py-0.5 text-[9px] bg-indigo-500/20 text-indigo-300 rounded-full font-mono border border-indigo-500/40 animate-pulse">
                PROCESSING
              </span>
            )}
          </div>

          {/* INVENTORY AGENT (Top Left) */}
          <div
            onClick={() => setSelectedAgentId('inventory')}
            className={`absolute top-2 left-[5%] cursor-pointer transition-all duration-300 p-3 rounded-xl border flex items-center gap-3 w-52 shadow-lg ${
              inventory?.active || selectedAgentId === 'inventory'
                ? 'bg-[#0E2720] border-emerald-500 ring-2 ring-emerald-500/30 shadow-emerald-500/20'
                : 'bg-[#151E32] border-[#253552] hover:border-emerald-500/50'
            }`}
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 border border-emerald-500/30">
              <Package className="w-4 h-4" />
            </div>
            <div className="overflow-hidden">
              <div className="font-bold text-[11px] text-slate-200">INVENTORY AGENT</div>
              <div className="text-[10px] text-slate-400 truncate">
                {inventory?.active ? 'Checking Shortage...' : 'Monitoring Stock'}
              </div>
            </div>
          </div>

          {/* PROCUREMENT AGENT (Top Right) */}
          <div
            onClick={() => setSelectedAgentId('procurement')}
            className={`absolute top-2 right-[5%] cursor-pointer transition-all duration-300 p-3 rounded-xl border flex items-center gap-3 w-52 shadow-lg ${
              procurement?.active || selectedAgentId === 'procurement'
                ? 'bg-[#271E0E] border-amber-500 ring-2 ring-amber-500/30 shadow-amber-500/20'
                : 'bg-[#151E32] border-[#253552] hover:border-amber-500/50'
            }`}
          >
            <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0 border border-amber-500/30">
              <Scale className="w-4 h-4" />
            </div>
            <div className="overflow-hidden">
              <div className="font-bold text-[11px] text-slate-200">PROCUREMENT AGENT</div>
              <div className="text-[10px] text-slate-400 truncate">
                {procurement?.active ? 'Negotiating Vendors...' : 'Evaluating Suppliers'}
              </div>
            </div>
          </div>

          {/* FINANCE AGENT (Bottom Left) */}
          <div
            onClick={() => setSelectedAgentId('finance')}
            className={`absolute bottom-2 left-[5%] cursor-pointer transition-all duration-300 p-3 rounded-xl border flex items-center gap-3 w-52 shadow-lg ${
              finance?.active || selectedAgentId === 'finance'
                ? 'bg-[#280E1E] border-pink-500 ring-2 ring-pink-500/30 shadow-pink-500/20'
                : 'bg-[#151E32] border-[#253552] hover:border-pink-500/50'
            }`}
          >
            <div className="w-8 h-8 rounded-lg bg-pink-500/20 text-pink-400 flex items-center justify-center shrink-0 border border-pink-500/30">
              <CircleDollarSign className="w-4 h-4" />
            </div>
            <div className="overflow-hidden">
              <div className="font-bold text-[11px] text-slate-200">FINANCE AGENT</div>
              <div className="text-[10px] text-slate-400 truncate">
                {finance?.active ? 'Validating Budget...' : 'Sanction Reserve'}
              </div>
            </div>
          </div>

          {/* LOGISTICS AGENT (Bottom Right) */}
          <div
            onClick={() => setSelectedAgentId('logistics')}
            className={`absolute bottom-2 right-[5%] cursor-pointer transition-all duration-300 p-3 rounded-xl border flex items-center gap-3 w-52 shadow-lg ${
              logistics?.active || selectedAgentId === 'logistics'
                ? 'bg-[#1D0E28] border-purple-500 ring-2 ring-purple-500/30 shadow-purple-500/20'
                : 'bg-[#151E32] border-[#253552] hover:border-purple-500/50'
            }`}
          >
            <div className="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center shrink-0 border border-purple-500/30">
              <Truck className="w-4 h-4" />
            </div>
            <div className="overflow-hidden">
              <div className="font-bold text-[11px] text-slate-200">LOGISTICS AGENT</div>
              <div className="text-[10px] text-slate-400 truncate">
                {logistics?.active ? 'Simulating Corridor...' : 'Delivery SLA'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Banner showing active workflow stage */}
      <div className="z-10 bg-[#0C1220] p-2.5 rounded-xl border border-[#1E293B] flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <span className="text-slate-400">Current Stage:</span>
          <span className="font-mono font-bold text-cyan-400 uppercase tracking-wide">
            {workflowStage}
          </span>
        </div>
        <div className="text-[11px] text-slate-400">
          Click any agent node above to inspect its live state & rationale
        </div>
      </div>
    </div>
  );
};
