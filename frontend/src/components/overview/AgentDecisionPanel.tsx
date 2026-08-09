import React from 'react';
import { Cpu, ShieldCheck, ArrowRight } from 'lucide-react';
import { useDemo } from '../../state/DemoContext';
import { StatusBadge } from '../common/StatusBadge';

export const AgentDecisionPanel: React.FC = () => {
  const { agents, selectedAgentId } = useDemo();

  const activeAgent = agents.find(a => a.id === selectedAgentId) || agents.find(a => a.active) || agents[0];

  return (
    <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-5 shadow-xl flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#24334D]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
              <Cpu className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-white uppercase tracking-wide">
                Agent Decision & Rationale Inspector
              </h3>
              <p className="text-[11px] text-slate-400">
                Enterprise-safe explainability summary
              </p>
            </div>
          </div>
          <StatusBadge status={activeAgent.status} />
        </div>

        {/* Selected Agent Identity */}
        <div className="my-3 p-3 bg-[#0C1220] rounded-xl border border-[#1E293B] flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-slate-200">{activeAgent.name}</div>
            <div className="text-[11px] text-slate-400 font-mono">{activeAgent.role}</div>
          </div>
          <div className="text-right font-mono text-xs">
            <div className="text-slate-400 text-[10px]">Confidence Rating</div>
            <div className="font-bold text-emerald-400 text-sm">{activeAgent.confidence}%</div>
          </div>
        </div>

        {/* Decision Breakdown Fields */}
        <div className="space-y-2.5 text-xs">
          {/* Current Task */}
          <div className="bg-[#0A0F1D] p-2.5 rounded-lg border border-[#1E2A40]">
            <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-0.5">
              Current Task Assignment
            </div>
            <div className="text-slate-200 font-medium">{activeAgent.currentTask}</div>
          </div>

          {/* Input Signals */}
          <div className="bg-[#0A0F1D] p-2.5 rounded-lg border border-[#1E2A40]">
            <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-0.5">
              Input Signals Received
            </div>
            <div className="text-cyan-300 font-mono text-[11px]">{activeAgent.inputReceived}</div>
          </div>

          {/* Action & Decision */}
          <div className="bg-[#0A0F1D] p-2.5 rounded-lg border border-[#1E2A40]">
            <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-0.5">
              Agent Output Decision
            </div>
            <div className="text-emerald-400 font-semibold">{activeAgent.lastDecision}</div>
          </div>

          {/* Decision Rationale */}
          <div className="bg-[#0D182E] p-3 rounded-lg border border-indigo-500/30">
            <div className="flex items-center gap-1.5 text-[10px] text-indigo-300 font-bold uppercase tracking-wider mb-1">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" /> Concise Decision Rationale Summary
            </div>
            <p className="text-slate-200 text-xs leading-relaxed font-sans">
              "{activeAgent.rationale}"
            </p>
          </div>

          {/* Next Action */}
          <div className="flex items-center justify-between p-2.5 bg-[#0A0F1D] rounded-lg border border-[#1E2A40] text-[11px]">
            <span className="text-slate-400">Next Action:</span>
            <span className="text-amber-400 font-mono font-medium flex items-center gap-1">
              {activeAgent.nextAction} <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
