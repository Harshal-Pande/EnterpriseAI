import React, { useState } from 'react';
import { Panel } from '../common/Panel';
import { StatusBadge } from '../common/StatusBadge';
import { EvidenceChip } from '../common/EvidenceChip';
import { useDemo } from '../../state/DemoContext';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { Order } from '../../types';

interface CaseFileSectionsProps {
  order?: Order;
  isSimulated?: boolean;
  onNavigateToAudit?: () => void;
}

export const CaseFileSections: React.FC<CaseFileSectionsProps> = ({
  order,
  isSimulated = false,
  onNavigateToAudit,
}) => {
  const {
    agents,
    suppliers,
    dataMode,
    decideApproval,
    auditEvents,
    liveApprovals,
  } = useDemo();

  // State for expandable findings
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  // Rejection reason state for governance approval panel
  const [rejectReason, setRejectReason] = useState('');
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);
  const [approvalFeedback, setApprovalFeedback] = useState<string | null>(null);

  const selectedSupplier = suppliers.find((s) => s.status === 'SELECTED') || suppliers[0];

  const handleApprovalAction = async (decision: 'APPROVED' | 'REJECTED') => {
    if (decision === 'REJECTED' && rejectReason.trim().length < 5) {
      setApprovalFeedback('Rejection reason must be at least 5 characters.');
      return;
    }
    setIsSubmittingApproval(true);
    setApprovalFeedback(null);
    try {
      const activeApproval = liveApprovals[0];
      if (activeApproval) {
        await decideApproval(activeApproval.approval_id, decision, rejectReason);
        setApprovalFeedback(`Decision ${decision} recorded successfully.`);
      } else {
        setApprovalFeedback(`Simulated: Decision recorded as ${decision}.`);
      }
    } catch (err: any) {
      setApprovalFeedback(`Error: ${err?.message || 'Failed to submit decision'}`);
    } finally {
      setIsSubmittingApproval(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* ── 1. Specialist Findings ────────────────────────────────────────── */}
      <div id="section-specialists">
        <Panel
          title="1. Specialist Findings & Evidence"
          subtitle="Autonomous domain investigations across inventory, procurement, finance, and logistics"
          isSimulated={isSimulated}
          padding="none"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-[13px]">
              <thead>
                <tr className="bg-surface-2 h-[36px] border-b border-border text-[11px] font-semibold text-text-3 uppercase tracking-wider">
                  <th className="px-3 py-1.5">Specialist Agent</th>
                  <th className="px-3 py-1.5">Status</th>
                  <th className="px-3 py-1.5">Key Finding</th>
                  <th className="px-3 py-1.5">Risk Level</th>
                  <th className="px-3 py-1.5">Evidence Record</th>
                  <th className="px-3 py-1.5">LLM Provider</th>
                  <th className="px-3 py-1.5 text-right">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {agents.map((agent) => {
                  const isExpanded = expandedAgent === agent.id;
                  const isRiskHigh =
                    agent.lastDecision.toLowerCase().includes('shortage') ||
                    agent.lastDecision.toLowerCase().includes('breach') ||
                    agent.lastDecision.toLowerCase().includes('delay');

                  return (
                    <React.Fragment key={agent.id}>
                      <tr
                        onClick={() =>
                          setExpandedAgent(isExpanded ? null : agent.id)
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
                        <td className="px-3 py-2">
                          <StatusBadge status={agent.status} size="sm" />
                        </td>
                        <td className="px-3 py-2 text-text max-w-xs truncate">
                          {agent.lastDecision || agent.currentTask || 'Investigation completed'}
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={`font-mono text-[11px] font-medium ${
                              isRiskHigh ? 'text-danger' : 'text-ok'
                            }`}
                          >
                            {isRiskHigh ? 'HIGH' : 'LOW'}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <EvidenceChip
                            label={
                              agent.id === 'inventory'
                                ? 'lot:SLAB-BOK-01'
                                : agent.id === 'procurement'
                                ? `supplier:${selectedSupplier?.name || 'TATA'}`
                                : agent.id === 'finance'
                                ? 'budget:CAT-RAW-Q4'
                                : agent.id === 'logistics'
                                ? 'route:CORRIDOR-E'
                                : 'eval:SPEC-CONSENSUS'
                            }
                          />
                        </td>
                        <td className="px-3 py-2 font-mono text-[11px] text-text-3">
                          {dataMode === 'live' ? 'Gemini 2.5 Pro' : 'Simulation'}
                        </td>
                        <td className="px-3 py-2 text-right font-mono tabular-nums text-text-2">
                          {agent.avgResponseMs}ms
                        </td>
                      </tr>

                      {/* Expanded row details */}
                      {isExpanded && (
                        <tr className="bg-surface-2/40">
                          <td colSpan={7} className="px-6 py-3 border-b border-border">
                            <div className="space-y-2 text-[12px]">
                              <div>
                                <span className="font-semibold text-text">
                                  Investigative Rationale:
                                </span>{' '}
                                <span className="text-text-2">
                                  {agent.rationale ||
                                    'Deterministic evaluation confirmed material specifications match grade requirements.'}
                                </span>
                              </div>
                              <div className="flex items-center gap-6 text-text-3 font-mono">
                                <span>Input: {agent.inputReceived || 'Order requisition'}</span>
                                <span>Action: {agent.currentAction || 'Evaluated'}</span>
                                <span>Confidence: {agent.confidence}%</span>
                              </div>
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
      </div>

      {/* ── 2. Supervisor Decision ────────────────────────────────────────── */}
      <div id="section-supervisor">
        <Panel
          title="2. Supervisor Decision & Conflict Resolution"
          subtitle="Synthesis of specialist inputs and multi-variable trade-off resolution"
          isSimulated={isSimulated}
        >
          <div className="space-y-3 text-[13px]">
            <div className="p-3 rounded-[4px] bg-surface-2 border border-border">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-semibold text-text">
                  Supervisor Synthesis
                </span>
                <span className="font-mono text-[12px] text-text-2">
                  Confidence: <strong className="text-text font-bold">96%</strong>
                </span>
              </div>
              <p className="text-text-2 leading-relaxed">
                Reviewed 4 specialist outputs. Inventory flagged 15-ton slab shortage at Bokaro plant. Procurement negotiated 40 tons with JSW Steel at ₹41,500/ton, meeting quality parameters. Logistics confirmed route dispatch via Rail Corridor East within promised 48-hour SLA window.
              </p>
            </div>

            <div className="space-y-1.5">
              <div className="text-[12px] font-semibold text-text uppercase tracking-wider">
                Proposed Autonomous Actions
              </div>
              <ul className="list-disc list-inside space-y-1 text-text-2 text-[12px]">
                <li>Dispatch purchase order PO-2026-991 to JSW Steel (40 MT)</li>
                <li>Reserve safety stock lot SLAB-BOK-01 at Bokaro central yard</li>
                <li>Reserve flatbed freight allocation with Concor Rail Logistics</li>
              </ul>
            </div>
          </div>
        </Panel>
      </div>

      {/* ── 3. Policy Result ─────────────────────────────────────────────── */}
      <div id="section-policy">
        <Panel
          title="3. Deterministic Policy Checks"
          subtitle="Hard business governance boundary verification (Python policy engine)"
          isSimulated={isSimulated}
        >
          <div className="space-y-3">
            <div className="divide-y divide-border border border-border rounded-[4px] bg-surface-2/30">
              <div className="p-3 flex items-center justify-between text-[13px]">
                <div>
                  <div className="font-medium text-text">POL-FIN-01: Maximum Single PO Value Limit</div>
                  <div className="text-[12px] text-text-3 font-mono">
                    Proposed: ₹16,60,000 | Limit: ₹25,00,000
                  </div>
                </div>
                <StatusBadge status="allowed" size="sm" customLabel="Passed" />
              </div>

              <div className="p-3 flex items-center justify-between text-[13px]">
                <div>
                  <div className="font-medium text-text">POL-FIN-02: Quarterly Category Raw Material Budget</div>
                  <div className="text-[12px] text-text-3 font-mono">
                    Remaining: ₹14,20,000 | Requisition: ₹16,60,000 (Exceeds by ₹2,40,000)
                  </div>
                </div>
                <StatusBadge status="blocked" size="sm" customLabel="Exceeded" />
              </div>

              <div className="p-3 flex items-center justify-between text-[13px]">
                <div>
                  <div className="font-medium text-text">POL-SUP-01: Approved Tier-1 Vendor Verification</div>
                  <div className="text-[12px] text-text-3 font-mono">
                    Vendor: JSW Steel Limited (ISO 9001 Approved)
                  </div>
                </div>
                <StatusBadge status="allowed" size="sm" customLabel="Passed" />
              </div>

              <div className="p-3 flex items-center justify-between text-[13px]">
                <div>
                  <div className="font-medium text-text">POL-LOG-01: Carrier SLA Maximum Transit Window</div>
                  <div className="text-[12px] text-text-3 font-mono">
                    Target: 48h | Projected ETA: 38h
                  </div>
                </div>
                <StatusBadge status="allowed" size="sm" customLabel="Passed" />
              </div>
            </div>

            <div className="text-[12px] text-text-3 italic pt-1">
              "Models recommend. Deterministic policy decides."
            </div>
          </div>
        </Panel>
      </div>

      {/* ── 4. Governance & Approval ──────────────────────────────────────── */}
      <div id="section-governance">
        <Panel
          title="4. Governance & Human Approval Gate"
          subtitle="Deterministic exception escalation and supervisor authorization"
          isSimulated={isSimulated}
        >
          <div className="space-y-3.5 text-[13px]">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-[4px] bg-surface-2 border border-border">
              <div>
                <div className="font-semibold text-text mb-0.5">
                  Approval Requirement
                </div>
                <div className="text-text-2 text-[12px]">
                  Authorized Role: <strong className="text-text font-medium">Finance Controller / Shift Head</strong>
                </div>
                <div className="text-text-3 text-[11px] mt-0.5">
                  Reason: Raw material requisition breaches Q4 category budget allocation by ₹2,40,000.
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <StatusBadge status="awaiting_approval" />
              </div>
            </div>

            {/* Approval Controls */}
            <div className="space-y-2 pt-1">
              <label className="block text-[12px] font-medium text-text">
                Rejection or Override Justification (mandatory for rejection, min 5 characters):
              </label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Enter justification for approval or detailed rejection rationale..."
                rows={2}
                className="w-full p-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent"
              />

              {approvalFeedback && (
                <div className="text-[12px] font-mono text-accent">
                  {approvalFeedback}
                </div>
              )}

              <div className="flex items-center gap-3 pt-1">
                <button
                  type="button"
                  disabled={isSubmittingApproval}
                  onClick={() => handleApprovalAction('APPROVED')}
                  className="px-4 py-1.5 rounded-[4px] bg-ok hover:bg-ok/90 text-white text-[12px] font-medium transition-colors cursor-pointer disabled:opacity-50"
                >
                  Approve Exception
                </button>
                <button
                  type="button"
                  disabled={isSubmittingApproval || rejectReason.trim().length < 5}
                  onClick={() => handleApprovalAction('REJECTED')}
                  className="px-4 py-1.5 rounded-[4px] bg-danger hover:bg-danger/90 text-white text-[12px] font-medium transition-colors cursor-pointer disabled:bg-surface-2 disabled:text-text-3 disabled:cursor-not-allowed"
                >
                  Reject Requisition
                </button>
              </div>
            </div>
          </div>
        </Panel>
      </div>

      {/* ── 5. What Changed ──────────────────────────────────────────────── */}
      <div id="section-action">
        <Panel
          title="5. What Changed (Persisted State Records)"
          subtitle="Database state mutations applied following governed approval"
          isSimulated={isSimulated}
          padding="none"
        >
          {isSimulated && (
            <div className="p-3 bg-sim-soft border-b border-sim/30 text-sim font-mono text-[12px]">
              Simulated: no database records were changed.
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-[13px]">
              <thead>
                <tr className="bg-surface-2 h-[36px] border-b border-border text-[11px] font-semibold text-text-3 uppercase tracking-wider">
                  <th className="px-3 py-1.5">Target Table</th>
                  <th className="px-3 py-1.5">Record Identifier</th>
                  <th className="px-3 py-1.5">State Before Mutation</th>
                  <th className="px-3 py-1.5">State After Mutation</th>
                  <th className="px-3 py-1.5">Persisted Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                <tr className="h-[40px] bg-surface">
                  <td className="px-3 py-2 font-mono text-[12px] text-text">orders</td>
                  <td className="px-3 py-2 font-mono text-[12px] text-text-2">{order?.id || 'ORD-1042'}</td>
                  <td className="px-3 py-2 font-mono text-[12px] text-text-3">status = "Processing"</td>
                  <td className="px-3 py-2 font-mono text-[12px] text-ok">status = "Approved"</td>
                  <td className="px-3 py-2">
                    <StatusBadge status="completed" size="sm" customLabel="Committed" />
                  </td>
                </tr>
                <tr className="h-[40px] bg-surface">
                  <td className="px-3 py-2 font-mono text-[12px] text-text">purchase_orders</td>
                  <td className="px-3 py-2 font-mono text-[12px] text-text-2">PO-2026-991</td>
                  <td className="px-3 py-2 font-mono text-[12px] text-text-3">(null)</td>
                  <td className="px-3 py-2 font-mono text-[12px] text-text">vendor = "JSW Steel", qty = 40 MT</td>
                  <td className="px-3 py-2">
                    <StatusBadge status="completed" size="sm" customLabel="Inserted" />
                  </td>
                </tr>
                <tr className="h-[40px] bg-surface">
                  <td className="px-3 py-2 font-mono text-[12px] text-text">inventory_allocations</td>
                  <td className="px-3 py-2 font-mono text-[12px] text-text-2">ALLOC-BOK-08</td>
                  <td className="px-3 py-2 font-mono text-[12px] text-text-3">reserved_qty = 0</td>
                  <td className="px-3 py-2 font-mono text-[12px] text-text">reserved_qty = 15 MT</td>
                  <td className="px-3 py-2">
                    <StatusBadge status="completed" size="sm" customLabel="Updated" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      {/* ── 6. Audit Events Timeline ─────────────────────────────────────── */}
      <div id="section-audit">
        <Panel
          title="6. Cryptographic Audit Trail"
          subtitle="RFC 8785 canonical JSON digests anchored on-chain"
          isSimulated={isSimulated}
        >
          <div className="space-y-3">
            <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[1px] before:bg-border">
              {auditEvents.slice(0, 4).map((evt, idx) => (
                <div key={idx} className="relative flex items-start justify-between gap-4">
                  {/* Square marker on timeline rail */}
                  <span className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-[2px] bg-accent border border-surface shrink-0" />

                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-text text-[13px]">
                        {evt.type}
                      </span>
                      <span className="text-[11px] font-mono text-text-3">
                        {evt.actor}
                      </span>
                      <StatusBadge status={evt.status} size="sm" />
                    </div>
                    <p className="text-[12px] text-text-2 mt-0.5">
                      {evt.details}
                    </p>
                  </div>

                  <div className="text-right shrink-0">
                    <div className="text-[11px] font-mono text-text-3">
                      {evt.timestamp}
                    </div>
                    <div className="inline-flex items-center gap-1 font-mono text-[11px] text-accent mt-0.5">
                      <span>{evt.txHash?.slice(0, 10)}…{evt.txHash?.slice(-6)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {onNavigateToAudit && (
              <div className="pt-2 border-t border-border flex justify-end">
                <button
                  type="button"
                  onClick={onNavigateToAudit}
                  className="text-[12px] text-accent hover:underline font-medium cursor-pointer"
                >
                  View complete audit trail & verify digests →
                </button>
              </div>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
};
