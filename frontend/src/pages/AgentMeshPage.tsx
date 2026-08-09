import React from 'react';
import { Cpu, Server, ShieldCheck, Activity, Clock } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { StatusBadge } from '../components/common/StatusBadge';
import type { AgentId } from '../types';

const AGENT_STYLE: Record<AgentId, { color: string; bg: string; border: string; label: string }> = {
  supervisor:  { color: '#6366F1', bg: 'rgba(99,102,241,0.1)',  border: 'rgba(99,102,241,0.25)',  label: 'Supervisor'   },
  inventory:   { color: '#10B981', bg: 'rgba(16,185,129,0.1)',  border: 'rgba(16,185,129,0.25)',  label: 'Inventory'    },
  procurement: { color: '#F59E0B', bg: 'rgba(245,158,11,0.1)',  border: 'rgba(245,158,11,0.25)',  label: 'Procurement'  },
  finance:     { color: '#EC4899', bg: 'rgba(236,72,153,0.1)',  border: 'rgba(236,72,153,0.25)',  label: 'Finance'      },
  logistics:   { color: '#8B5CF6', bg: 'rgba(139,92,246,0.1)', border: 'rgba(139,92,246,0.25)',  label: 'Logistics'    },
};

export const AgentMeshPage: React.FC = () => {
  const { agents, selectedAgentId, setSelectedAgentId } = useDemo();
  const selectedAgent = agents.find(a => a.id === selectedAgentId) ?? agents[0];
  const style = AGENT_STYLE[selectedAgent.id];

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="pb-5 border-b border-[#1E293B]">
        <h1 className="text-2xl font-extrabold text-white tracking-tight">Agent Mesh Operations</h1>
        <p className="text-sm text-slate-500 mt-1">Autonomous sub-agent fleet topology, workloads, and execution telemetry</p>
      </div>

      {/* Agent Fleet Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {agents.map(agent => {
          const s = AGENT_STYLE[agent.id];
          const isSelected = selectedAgentId === agent.id;
          return (
            <div
              key={agent.id}
              id={`agent-card-${agent.id}`}
              onClick={() => setSelectedAgentId(agent.id)}
              className="rounded-xl p-4 cursor-pointer transition-all duration-150"
              style={{
                background: isSelected ? s.bg : '#111827',
                border: `1px solid ${isSelected ? s.border : '#1E293B'}`,
                boxShadow: isSelected ? `0 0 20px ${s.bg}` : 'none'
              }}
            >
              {/* Icon + Status */}
              <div className="flex items-center justify-between mb-3">
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center"
                  style={{ background: s.bg, border: `1px solid ${s.border}` }}
                >
                  <Cpu className="w-4.5 h-4.5" style={{ color: s.color }} />
                </div>
                <StatusBadge status={agent.status} size="sm" />
              </div>

              {/* Name + Role */}
              <div className="font-bold text-sm text-white mb-0.5">{agent.name}</div>
              <div className="text-[10px] text-slate-500 truncate mb-3">{agent.role}</div>

              {/* Workload bar */}
              <div className="space-y-1 mb-3">
                <div className="flex justify-between text-[10px] font-mono text-slate-500">
                  <span>Workload</span>
                  <span style={{ color: s.color }}>{agent.workload}%</span>
                </div>
                <div className="h-1 rounded-full overflow-hidden" style={{ background: '#1E293B' }}>
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${agent.workload}%`, background: s.color }}
                  />
                </div>
              </div>

              {/* Latency + Tasks */}
              <div className="flex items-center justify-between text-[10px] font-mono border-t border-[#1E293B] pt-2">
                <span className="text-slate-600">Avg Latency</span>
                <span className="text-cyan-400">{agent.avgResponseMs}ms</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-mono mt-1">
                <span className="text-slate-600">Tasks Done</span>
                <span className="text-white">{agent.tasksCompleted.toLocaleString()}</span>
              </div>

              {/* Active indicator */}
              {agent.active && (
                <div className="mt-2 flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase" style={{ color: s.color }}>
                  <span className="w-1.5 h-1.5 rounded-full animate-ping" style={{ background: s.color }} />
                  Processing Task
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Inspector Panel */}
      <div
        className="rounded-xl overflow-hidden"
        style={{ background: '#0F172A', border: `1px solid ${style.border}` }}
      >
        {/* Inspector Header */}
        <div
          className="flex items-center justify-between px-5 py-4 border-b"
          style={{ borderColor: style.border, background: style.bg }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(0,0,0,0.3)', border: `1px solid ${style.border}` }}
            >
              <Server className="w-5 h-5" style={{ color: style.color }} />
            </div>
            <div>
              <div className="text-sm font-bold text-white">{selectedAgent.name} — Inspector</div>
              <div className="text-[11px] text-slate-400">{selectedAgent.role}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={selectedAgent.status} />
          </div>
        </div>

        {/* Metrics Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-5">
          {[
            { label: 'Tasks Executed',       value: selectedAgent.tasksCompleted.toLocaleString(), icon: <Activity className="w-4 h-4" />,     color: style.color },
            { label: 'Avg Response Time',     value: `${selectedAgent.avgResponseMs} ms`,           icon: <Clock className="w-4 h-4" />,         color: '#38BDF8'   },
            { label: 'Confidence Level',      value: `${selectedAgent.confidence}%`,                icon: <ShieldCheck className="w-4 h-4" />,   color: '#10B981'   },
            { label: 'Workload',             value: `${selectedAgent.workload}%`,                   icon: <Cpu className="w-4 h-4" />,           color: '#F59E0B'   },
          ].map(({ label, value, icon, color }) => (
            <div key={label} className="rounded-lg p-3" style={{ background: '#080C14', border: '1px solid #1E293B' }}>
              <div className="flex items-center gap-1.5 text-[10px] text-slate-600 font-mono uppercase mb-1.5">
                <span style={{ color }}>{icon}</span>
                {label}
              </div>
              <div className="text-xl font-bold font-mono" style={{ color }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Decision fields */}
        <div className="px-5 pb-5 space-y-3">
          {[
            { label: 'Current Task',   value: selectedAgent.currentTask,     mono: false },
            { label: 'Input Received', value: selectedAgent.inputReceived,   mono: true  },
            { label: 'Last Decision',  value: selectedAgent.lastDecision,    mono: false, accent: style.color },
            { label: 'Next Action',    value: selectedAgent.nextAction,      mono: false, accent: '#F59E0B'   },
          ].map(({ label, value, mono, accent }) => (
            <div key={label} className="rounded-lg px-4 py-3" style={{ background: '#080C14', border: '1px solid #1E293B' }}>
              <div className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-1">{label}</div>
              <div className={`text-[11px] leading-snug ${mono ? 'font-mono' : ''}`} style={{ color: accent ?? '#CBD5E1' }}>
                {value}
              </div>
            </div>
          ))}

          {/* Rationale */}
          <div
            className="rounded-lg px-4 py-3"
            style={{ background: style.bg, border: `1px solid ${style.border}` }}
          >
            <div className="flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-widest mb-1.5"
              style={{ color: style.color }}
            >
              <ShieldCheck className="w-3 h-3" /> Explainability Rationale
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              "{selectedAgent.rationale}"
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
