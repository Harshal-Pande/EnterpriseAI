import React from 'react';
import { Cpu, Package, Scale, CircleDollarSign, Truck } from 'lucide-react';
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
    <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-5 shadow-xl relative overflow-hidden flex flex-col justify-between min-h-[380px]">
      {/* Grid Pattern Overlay matching Screenshot */}
      <div
        className="absolute inset-0 opacity-20 pointer-events-none"
        style={{
          backgroundImage: `radial-gradient(#38BDF8 1px, transparent 1px)`,
          backgroundSize: '20px 20px'
        }}
      />

      {/* Header matching Screenshot */}
      <div className="flex items-center justify-between z-10 mb-2">
        <h2 className="text-base font-bold text-white tracking-tight">
          Live Agent Mesh
        </h2>
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
          <span>Network Synced</span>
        </div>
      </div>

      {/* Node Graph Overlay + HTML Nodes Container */}
      <div className="relative flex-1 flex items-center justify-center my-2">
        {/* Connection Lines (SVG Layer) */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
          <line
            x1="50%"
            y1="50%"
            x2="25%"
            y2="25%"
            stroke={inventory?.active ? '#38BDF8' : '#1E293B'}
            strokeWidth={inventory?.active ? '2' : '1.5'}
            className={inventory?.active ? 'animate-pulse-line' : ''}
          />
          <line
            x1="50%"
            y1="50%"
            x2="75%"
            y2="25%"
            stroke={procurement?.active ? '#F59E0B' : '#1E293B'}
            strokeWidth={procurement?.active ? '2' : '1.5'}
            className={procurement?.active ? 'animate-pulse-line' : ''}
          />
          <line
            x1="50%"
            y1="50%"
            x2="25%"
            y2="75%"
            stroke={finance?.active ? '#EC4899' : '#1E293B'}
            strokeWidth={finance?.active ? '2' : '1.5'}
            className={finance?.active ? 'animate-pulse-line' : ''}
          />
          <line
            x1="50%"
            y1="50%"
            x2="75%"
            y2="75%"
            stroke={logistics?.active ? '#8B5CF6' : '#1E293B'}
            strokeWidth={logistics?.active ? '2' : '1.5'}
            className={logistics?.active ? 'animate-pulse-line' : ''}
          />
        </svg>

        {/* Nodes Positioning matching Screenshot */}
        <div className="relative z-10 w-full max-w-2xl h-[270px]">
          {/* SUPERVISOR AGENT (Center Node) */}
          <div
            onClick={() => setSelectedAgentId('supervisor')}
            className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all duration-200 p-4 rounded-xl border flex flex-col items-center justify-center text-center w-48 shadow-2xl ${
              supervisor?.active || selectedAgentId === 'supervisor'
                ? 'bg-[#18243B] border-cyan-400 ring-2 ring-cyan-400/20'
                : 'bg-[#161F33] border-[#25344F] hover:border-slate-500'
            }`}
          >
            <Cpu className="w-5 h-5 text-cyan-400 mb-1" />
            <div className="font-bold text-xs text-white">Supervisor Agent</div>
            <div className="text-[10px] text-cyan-400 font-mono mt-0.5">Orchestrator</div>
          </div>

          {/* INVENTORY AGENT (Top Left) */}
          <div
            onClick={() => setSelectedAgentId('inventory')}
            className={`absolute top-2 left-[5%] cursor-pointer transition-all duration-200 p-3 rounded-xl border flex flex-col items-center justify-center text-center w-40 shadow-lg ${
              inventory?.active || selectedAgentId === 'inventory'
                ? 'bg-[#18243B] border-l-4 border-l-amber-500 border-cyan-400'
                : 'bg-[#161F33] border-[#25344F] hover:border-slate-500'
            }`}
          >
            <Package className="w-4 h-4 text-slate-300 mb-1" />
            <div className="font-bold text-xs text-white">Inventory Agent</div>
            <div className="text-[10px] text-slate-400 font-mono mt-0.5">
              • {inventory?.active ? 'Evaluating' : 'Idle'}
            </div>
          </div>

          {/* FINANCE AGENT (Top Right) */}
          <div
            onClick={() => setSelectedAgentId('finance')}
            className={`absolute top-2 right-[5%] cursor-pointer transition-all duration-200 p-3 rounded-xl border flex flex-col items-center justify-center text-center w-40 shadow-lg ${
              finance?.active || selectedAgentId === 'finance'
                ? 'bg-[#18243B] border-l-4 border-l-amber-500 border-cyan-400'
                : 'bg-[#161F33] border-[#25344F] hover:border-slate-500'
            }`}
          >
            <CircleDollarSign className="w-4 h-4 text-slate-300 mb-1" />
            <div className="font-bold text-xs text-white">Finance Agent</div>
            <div className="text-[10px] text-slate-400 font-mono mt-0.5">
              • {finance?.active ? 'Sanctioning' : 'Idle'}
            </div>
          </div>

          {/* PROCUREMENT AGENT (Bottom Left) */}
          <div
            onClick={() => setSelectedAgentId('procurement')}
            className={`absolute bottom-2 left-[5%] cursor-pointer transition-all duration-200 p-3 rounded-xl border flex flex-col items-center justify-center text-center w-40 shadow-lg ${
              procurement?.active || selectedAgentId === 'procurement'
                ? 'bg-[#18243B] border-l-4 border-l-amber-500 border-cyan-400'
                : 'bg-[#161F33] border-[#25344F] hover:border-slate-500'
            }`}
          >
            <Scale className="w-4 h-4 text-slate-300 mb-1" />
            <div className="font-bold text-xs text-white">Procurement Agent</div>
            <div className="text-[10px] text-amber-400 font-mono mt-0.5">
              • {procurement?.active ? 'Sourcing' : 'Idle'}
            </div>
          </div>

          {/* LOGISTICS AGENT (Bottom Right) */}
          <div
            onClick={() => setSelectedAgentId('logistics')}
            className={`absolute bottom-2 right-[5%] cursor-pointer transition-all duration-200 p-3 rounded-xl border flex flex-col items-center justify-center text-center w-40 shadow-lg ${
              logistics?.active || selectedAgentId === 'logistics'
                ? 'bg-[#18243B] border-l-4 border-l-amber-500 border-cyan-400'
                : 'bg-[#161F33] border-[#25344F] hover:border-slate-500'
            }`}
          >
            <Truck className="w-4 h-4 text-slate-300 mb-1" />
            <div className="font-bold text-xs text-white">Logistics Agent</div>
            <div className="text-[10px] text-slate-400 font-mono mt-0.5">
              • {logistics?.active ? 'Routing' : 'Idle'}
            </div>
          </div>
        </div>
      </div>

      {/* Footer Stage Indicator */}
      <div className="z-10 bg-[#0C1220] p-2 rounded-lg border border-[#1E293B] flex items-center justify-between text-xs font-mono">
        <span className="text-slate-400">Current Execution Stage:</span>
        <span className="text-cyan-400 font-bold uppercase">{workflowStage}</span>
      </div>
    </div>
  );
};
