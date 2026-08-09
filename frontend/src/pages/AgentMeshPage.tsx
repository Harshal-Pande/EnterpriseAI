import React from 'react';
import { Cpu, Server, ShieldCheck } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { StatusBadge } from '../components/common/StatusBadge';

export const AgentMeshPage: React.FC = () => {
  const { agents, selectedAgentId, setSelectedAgentId } = useDemo();

  const selectedAgent = agents.find(a => a.id === selectedAgentId) || agents[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Cpu className="w-5 h-5 text-indigo-400" /> Multi-Agent Topology & Health Operations
        </h2>
        <p className="text-xs text-slate-400">
          Autonomous sub-agent fleet performance, execution workloads, and response latencies
        </p>
      </div>

      {/* Agents Topology Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {agents.map(agent => {
          const isSelected = selectedAgentId === agent.id;
          return (
            <div
              key={agent.id}
              onClick={() => setSelectedAgentId(agent.id)}
              className={`bg-[#121929] border rounded-2xl p-4 cursor-pointer transition-all duration-200 shadow-lg ${
                isSelected
                  ? 'border-indigo-500 ring-2 ring-indigo-500/30 bg-[#162035]'
                  : 'border-[#24334D] hover:border-slate-600'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center font-bold text-xs border border-indigo-500/30">
                  <Cpu className="w-4 h-4" />
                </div>
                <StatusBadge status={agent.status} size="sm" />
              </div>

              <div className="font-bold text-sm text-white mb-0.5">{agent.name}</div>
              <div className="text-[10px] text-slate-400 truncate mb-3">{agent.role}</div>

              {/* Workload Progress */}
              <div className="space-y-1 my-2">
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>Workload</span>
                  <span>{agent.workload}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full"
                    style={{ width: `${agent.workload}%` }}
                  />
                </div>
              </div>

              <div className="pt-2 border-t border-[#1E293B] flex items-center justify-between text-[10px] text-slate-400 font-mono">
                <span>Avg Latency</span>
                <span className="text-cyan-400">{agent.avgResponseMs}ms</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Agent Detail Inspection Panel */}
      <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-[#24334D] pb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">{selectedAgent.name} Inspector</h3>
              <p className="text-xs text-slate-400">{selectedAgent.role}</p>
            </div>
          </div>
          <StatusBadge status={selectedAgent.status} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
          <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
            <div className="text-slate-400 mb-1 font-semibold">Total Tasks Executed</div>
            <div className="text-xl font-bold text-white font-mono">{selectedAgent.tasksCompleted}</div>
          </div>

          <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
            <div className="text-slate-400 mb-1 font-semibold">Average Response Time</div>
            <div className="text-xl font-bold text-cyan-400 font-mono">{selectedAgent.avgResponseMs} ms</div>
          </div>

          <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
            <div className="text-slate-400 mb-1 font-semibold">Confidence Metric</div>
            <div className="text-xl font-bold text-emerald-400 font-mono">{selectedAgent.confidence}%</div>
          </div>

          <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
            <div className="text-slate-400 mb-1 font-semibold">Current Active Task</div>
            <div className="text-xs font-semibold text-slate-200 truncate">{selectedAgent.currentTask}</div>
          </div>
        </div>

        <div className="bg-[#0A0F1D] p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
          <div className="font-bold text-indigo-300 flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
            <ShieldCheck className="w-4 h-4 text-indigo-400" /> Enterprise Explainability Rationale
          </div>
          <p className="text-slate-200 leading-relaxed font-sans">
            "{selectedAgent.rationale}"
          </p>
        </div>
      </div>
    </div>
  );
};
