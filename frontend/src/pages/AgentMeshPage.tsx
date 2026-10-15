import React, { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Panel } from '../components/common/Panel';
import { StatusBadge } from '../components/common/StatusBadge';
import { useDemo } from '../state/DemoContext';
import { ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';

export const AgentMeshPage: React.FC = () => {
  const { agents, dataMode } = useDemo();
  const [expandedAgentId, setExpandedAgentId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (id: string, text: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const interAgentMessages = [
    { time: '19:15:02', from: 'SUPERVISOR', to: 'INVENTORY', type: 'TASK_DISPATCH', summary: 'Check Bokaro slab stock for 25 MT order ORD-1042' },
    { time: '19:15:03', from: 'INVENTORY', to: 'SUPERVISOR', type: 'FINDING_REPORT', summary: '10 MT available, 15 MT shortage detected; safety stock reserved' },
    { time: '19:15:04', from: 'SUPERVISOR', to: 'PROCUREMENT', type: 'NEGOTIATION_TRIGGER', summary: 'Request 40 MT quote from secondary suppliers' },
    { time: '19:15:05', from: 'PROCUREMENT', to: 'FINANCE', type: 'QUOTE_VALIDATION', summary: 'JSW Steel quoted ₹41,500/MT (Total ₹16.6L)' },
    { time: '19:15:06', from: 'FINANCE', to: 'SUPERVISOR', type: 'POLICY_ALERT', summary: 'Overrun of ₹2.4L exceeds Q4 raw material limit POL-FIN-02' },
    { time: '19:15:07', from: 'SUPERVISOR', to: 'LOGISTICS', type: 'FEASIBILITY_CHECK', summary: 'Evaluate 48-hour rail freight feasibility' },
    { time: '19:15:08', from: 'LOGISTICS', to: 'SUPERVISOR', type: 'FEASIBILITY_REPORT', summary: 'Confirmed Rail Corridor East via Concor; 38h transit' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Agent Mesh Diagnostics"
        description="Structured performance telemetry, inter-agent consensus logs, and execution parameters."
      />

      {/* Restrained Static Schematic (Max 160px height, 1px lines, no animation) */}
      <Panel title="Coordination Schematic" subtitle="Hierarchical supervisor-specialist delegation">
        <div className="h-[120px] flex items-center justify-center p-2">
          <div className="w-full max-w-2xl flex flex-col items-center">
            {/* Supervisor Node */}
            <div className="px-4 py-1.5 rounded-[4px] border border-border bg-surface-2 text-text font-semibold text-[12px] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-accent" />
              <span>Supervisor Agent</span>
            </div>

            {/* Connecting lines */}
            <div className="w-[1px] h-4 bg-border" />
            <div className="w-3/4 h-[1px] bg-border relative">
              <div className="absolute left-0 top-0 w-[1px] h-3 bg-border" />
              <div className="absolute left-1/3 top-0 w-[1px] h-3 bg-border" />
              <div className="absolute left-2/3 top-0 w-[1px] h-3 bg-border" />
              <div className="absolute right-0 top-0 w-[1px] h-3 bg-border" />
            </div>

            {/* Specialist Nodes */}
            <div className="w-full flex justify-between gap-2 pt-3 text-[11px] font-medium text-text-2">
              <div className="flex-1 text-center py-1 px-2 rounded-[4px] border border-border bg-surface">
                Inventory
              </div>
              <div className="flex-1 text-center py-1 px-2 rounded-[4px] border border-border bg-surface">
                Procurement
              </div>
              <div className="flex-1 text-center py-1 px-2 rounded-[4px] border border-border bg-surface">
                Finance
              </div>
              <div className="flex-1 text-center py-1 px-2 rounded-[4px] border border-border bg-surface">
                Logistics
              </div>
            </div>
          </div>
        </div>
      </Panel>

      {/* Agent Fleet Performance Table */}
      <Panel
        title="Agent Performance Telemetry"
        subtitle="Click any row to expand recent structured output and execution parameters"
        padding="none"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-surface-2 h-[36px] border-b border-border text-[11px] font-semibold text-text-3 uppercase tracking-wider">
                <th className="px-3 py-1.5">Agent</th>
                <th className="px-3 py-1.5">Role</th>
                <th className="px-3 py-1.5">State</th>
                <th className="px-3 py-1.5 text-right">Runs Today</th>
                <th className="px-3 py-1.5 text-right">Avg Latency</th>
                <th className="px-3 py-1.5 text-right">Timeouts</th>
                <th className="px-3 py-1.5">Provider</th>
                <th className="px-3 py-1.5">Last Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {agents.map((agent) => {
                const isExpanded = expandedAgentId === agent.id;

                const structuredOutput = {
                  agent_id: agent.id,
                  task: agent.currentTask || 'Requisition evaluation',
                  decision: agent.lastDecision,
                  confidence_score: agent.confidence,
                  rationale: agent.rationale,
                  parameters: {
                    latency_ms: agent.avgResponseMs,
                    workload_pct: agent.workload,
                    completed_count: agent.tasksCompleted,
                  },
                };

                return (
                  <React.Fragment key={agent.id}>
                    <tr
                      onClick={() =>
                        setExpandedAgentId(isExpanded ? null : agent.id)
                      }
                      className="h-[40px] hover:bg-surface-2/60 bg-surface cursor-pointer transition-colors"
                    >
                      <td className="px-3 py-2 font-medium text-text">
                        <div className="flex items-center gap-1.5">
                          {isExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5 text-text-3" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5 text-text-3" />
                          )}
                          <span className="capitalize">{agent.name}</span>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-text-2 text-[12px] max-w-xs truncate">
                        {agent.role}
                      </td>
                      <td className="px-3 py-2">
                        <StatusBadge status={agent.status} size="sm" />
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums text-text-2">
                        {agent.tasksCompleted}
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums text-text">
                        {agent.avgResponseMs}ms
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums text-text-3">
                        0
                      </td>
                      <td className="px-3 py-2 font-mono text-[11px] text-text-3">
                        {dataMode === 'live' ? 'Gemini 2.5' : 'Simulation'}
                      </td>
                      <td className="px-3 py-2 text-[12px] text-text-3">
                        None
                      </td>
                    </tr>

                    {/* Expandable JSON output */}
                    {isExpanded && (
                      <tr className="bg-surface-2/30">
                        <td colSpan={8} className="p-4 border-b border-border">
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-[12px] font-semibold text-text">
                                Last Structured Output (JSON)
                              </span>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleCopy(agent.id, JSON.stringify(structuredOutput, null, 2));
                                }}
                                className="inline-flex items-center gap-1 text-[11px] text-text-3 hover:text-text cursor-pointer"
                              >
                                {copiedId === agent.id ? (
                                  <>
                                    <Check className="w-3.5 h-3.5 text-ok" />
                                    <span className="text-ok">Copied</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy className="w-3.5 h-3.5" />
                                    <span>Copy JSON</span>
                                  </>
                                )}
                              </button>
                            </div>
                            <pre className="p-3 rounded-[4px] bg-surface-sunk border border-border text-text font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
{JSON.stringify(structuredOutput, null, 2)}
                            </pre>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Inter-Agent Messages Table */}
      <Panel
        title="Inter-Agent Consensus & Communication Logs"
        subtitle="Chronological message sequence exchanged across the active orchestration cycle"
        padding="none"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-surface-2 h-[36px] border-b border-border text-[11px] font-semibold text-text-3 uppercase tracking-wider">
                <th className="px-3 py-1.5">Timestamp</th>
                <th className="px-3 py-1.5">From</th>
                <th className="px-3 py-1.5">To</th>
                <th className="px-3 py-1.5">Message Type</th>
                <th className="px-3 py-1.5">Summary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {interAgentMessages.map((msg, idx) => (
                <tr key={idx} className="h-[38px] hover:bg-surface-2/40 bg-surface">
                  <td className="px-3 py-1.5 font-mono text-[11px] text-text-3">
                    {msg.time}
                  </td>
                  <td className="px-3 py-1.5 font-mono text-[11px] text-text font-semibold">
                    {msg.from}
                  </td>
                  <td className="px-3 py-1.5 font-mono text-[11px] text-text-2">
                    {msg.to}
                  </td>
                  <td className="px-3 py-1.5">
                    <span className="px-1.5 py-0.5 rounded-[4px] bg-surface-sunk border border-border text-[10px] font-mono text-text-3">
                      {msg.type}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-text-2 text-[12px]">
                    {msg.summary}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
};
