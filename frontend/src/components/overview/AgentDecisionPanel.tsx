import React from 'react';
import { Brain, ArrowRight, ShieldCheck } from 'lucide-react';
import { useDemo } from '../../state/DemoContext';

const AGENT_COLORS: Record<string, { primary: string; bg: string; border: string }> = {
  supervisor:  { primary: '#6366F1', bg: 'rgba(99,102,241,0.1)',  border: 'rgba(99,102,241,0.25)'  },
  inventory:   { primary: '#10B981', bg: 'rgba(16,185,129,0.1)',  border: 'rgba(16,185,129,0.25)'  },
  procurement: { primary: '#F59E0B', bg: 'rgba(245,158,11,0.1)',  border: 'rgba(245,158,11,0.25)'  },
  finance:     { primary: '#EC4899', bg: 'rgba(236,72,153,0.1)',  border: 'rgba(236,72,153,0.25)'  },
  logistics:   { primary: '#8B5CF6', bg: 'rgba(139,92,246,0.1)', border: 'rgba(139,92,246,0.25)'  },
};

export const AgentDecisionPanel: React.FC = () => {
  const { agents, selectedAgentId } = useDemo();

  const agent = agents.find(a => a.id === selectedAgentId)
             ?? agents.find(a => a.active)
             ?? agents[0];

  const colors = AGENT_COLORS[agent.id] ?? { primary: '#94A3B8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.2)' };

  return (
    <div
      className="flex flex-col rounded-xl overflow-hidden"
      style={{ background: '#0F172A', border: '1px solid #1E293B' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1E293B] shrink-0">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: colors.bg, border: `1px solid ${colors.border}` }}
          >
            <Brain className="w-3.5 h-3.5" style={{ color: colors.primary }} />
          </div>
          <div>
            <div className="text-sm font-bold text-white">Decision Inspector</div>
            <div className="text-[10px] text-slate-500">Agent reasoning & explainability</div>
          </div>
        </div>
        <span
          className="px-2.5 py-1 rounded-full text-[10px] font-bold font-mono"
          style={{ background: colors.bg, color: colors.primary, border: `1px solid ${colors.border}` }}
        >
          {agent.status}
        </span>
      </div>

      {/* Agent identity strip */}
      <div
        className="mx-4 mt-3 px-3 py-2.5 rounded-lg flex items-center justify-between"
        style={{ background: colors.bg, border: `1px solid ${colors.border}` }}
      >
        <div>
          <div className="text-xs font-bold text-white">{agent.name}</div>
          <div className="text-[10px] text-slate-400 font-mono mt-0.5">{agent.role}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-slate-500 font-mono">Confidence</div>
          <div className="text-sm font-bold font-mono" style={{ color: colors.primary }}>{agent.confidence}%</div>
        </div>
      </div>

      {/* Decision fields */}
      <div className="p-4 space-y-2 flex-1">
        {[
          { label: 'Current Task',       value: agent.currentTask,    mono: false },
          { label: 'Input Received',     value: agent.inputReceived,  mono: true  },
          { label: 'Agent Decision',     value: agent.lastDecision,   mono: false, highlight: true },
        ].map(({ label, value, mono, highlight }) => (
          <div
            key={label}
            className="rounded-lg px-3 py-2.5"
            style={{ background: '#080C14', border: '1px solid #1E293B' }}
          >
            <div className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-1">{label}</div>
            <div
              className={`text-[11px] leading-snug ${mono ? 'font-mono' : ''}`}
              style={{ color: highlight ? colors.primary : '#CBD5E1' }}
            >
              {value}
            </div>
          </div>
        ))}

        {/* Rationale block */}
        <div
          className="rounded-lg px-3 py-2.5"
          style={{ background: colors.bg, border: `1px solid ${colors.border}` }}
        >
          <div className="flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-widest mb-1.5"
            style={{ color: colors.primary }}
          >
            <ShieldCheck className="w-3 h-3" />
            Decision Rationale
          </div>
          <p className="text-[11px] text-slate-300 leading-relaxed">
            "{agent.rationale}"
          </p>
        </div>

        {/* Next action */}
        <div
          className="flex items-center justify-between rounded-lg px-3 py-2"
          style={{ background: '#080C14', border: '1px solid #1E293B' }}
        >
          <span className="text-[10px] text-slate-500 font-mono">Next Action:</span>
          <span className="flex items-center gap-1 text-[10px] font-mono font-medium text-amber-400">
            {agent.nextAction} <ArrowRight className="w-3 h-3" />
          </span>
        </div>
      </div>
    </div>
  );
};
