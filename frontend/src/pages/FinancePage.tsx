import React from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { StatStrip, type StatItem } from '../components/common/StatStrip';
import { Panel } from '../components/common/Panel';
import { StatusBadge } from '../components/common/StatusBadge';

interface BudgetCategory {
  category: string;
  allocated: number;
  committed: number;
  limit: number;
}

export const FinancePage: React.FC = () => {
  const totalAllocated = 5000000;
  const totalCommitted = 3840000;
  const totalRemaining = totalAllocated - totalCommitted;
  const breachCount = 1;

  const stats: StatItem[] = [
    {
      label: 'Budget allocated (Q4)',
      value: `₹${(totalAllocated / 100000).toFixed(1)}L`,
      context: '₹50,00,000 Cap',
    },
    {
      label: 'Committed expenditure',
      value: `₹${(totalCommitted / 100000).toFixed(1)}L`,
      context: 'PO releases',
      accent: 'info',
    },
    {
      label: 'Remaining headroom',
      value: `₹${(totalRemaining / 100000).toFixed(1)}L`,
      context: 'Safety buffer',
      accent: 'ok',
    },
    {
      label: 'Policy breaches',
      value: breachCount,
      context: 'Awaiting HITL override',
      accent: 'danger',
    },
  ];

  const categories: BudgetCategory[] = [
    {
      category: 'Raw Materials (Steel Slab & Billets)',
      allocated: 2500000,
      committed: 2740000,
      limit: 2500000,
    },
    {
      category: 'Corridor Rail Freight & Logistics',
      allocated: 1200000,
      committed: 820000,
      limit: 1200000,
    },
    {
      category: 'Plant Spares & Roll Mill Maintenance',
      allocated: 800000,
      committed: 450000,
      limit: 800000,
    },
    {
      category: 'Secondary Vendor Emergency Contingency',
      allocated: 500000,
      committed: 120000,
      limit: 500000,
    },
  ];

  const policyChecks = [
    {
      orderId: 'ORD-1042',
      customer: 'Tata Motors Commercial Division',
      rule: 'POL-FIN-02 (Category Raw Material Cap)',
      proposed: 1660000,
      limit: 1420000,
      isBreached: true,
      status: 'blocked',
    },
    {
      orderId: 'ORD-1039',
      customer: 'Mahindra Heavy Auto Works',
      rule: 'POL-FIN-01 (Single Purchase Cap)',
      proposed: 1150000,
      limit: 2500000,
      isBreached: false,
      status: 'allowed',
    },
    {
      orderId: 'ORD-1035',
      customer: 'L&T Heavy Engineering Plant',
      rule: 'POL-FIN-03 (Expedited Freight Margin)',
      proposed: 320000,
      limit: 450000,
      isBreached: false,
      status: 'allowed',
    },
    {
      orderId: 'ORD-1031',
      customer: 'Bharat Forge Industrial Division',
      rule: 'POL-FIN-01 (Single Purchase Cap)',
      proposed: 850000,
      limit: 2500000,
      isBreached: false,
      status: 'allowed',
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Financial Governance & Capital Allocation"
        description="Deterministic spend authorization, category budget ceilings, and policy margin verification."
      />

      {/* Stat Strip */}
      <StatStrip stats={stats} />

      {/* Budget vs Committed Flat Bars */}
      <Panel
        title="Budget vs Committed Expenditure by Category"
        subtitle="Visual utilization with 1px vertical tick at deterministic policy limit"
      >
        <div className="space-y-5">
          {categories.map((cat) => {
            const utilizationPct = Math.min(100, Math.round((cat.committed / cat.allocated) * 100));
            const isOverBudget = cat.committed > cat.allocated;

            return (
              <div key={cat.category} className="space-y-1.5 text-[12px]">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-text">{cat.category}</span>
                  <div className="flex items-center gap-2 font-mono text-[11px]">
                    <span className={isOverBudget ? 'text-danger font-semibold' : 'text-text-2'}>
                      ₹{(cat.committed / 100000).toFixed(2)}L
                    </span>
                    <span className="text-text-3">/ ₹{(cat.allocated / 100000).toFixed(2)}L</span>
                    {isOverBudget && (
                      <span className="px-1.5 py-0.2 rounded-[3px] bg-danger-soft text-danger text-[10px] font-semibold">
                        Over Limit
                      </span>
                    )}
                  </div>
                </div>

                {/* Flat bar with 1px vertical tick at policy limit */}
                <div className="relative w-full h-3 bg-surface-sunk rounded-[3px] overflow-hidden">
                  <div
                    style={{ width: `${utilizationPct}%` }}
                    className={`h-full ${isOverBudget ? 'bg-danger' : 'bg-accent'}`}
                  />
                  {/* 1px vertical tick at 85% safety alert mark */}
                  <div
                    style={{ left: '85%' }}
                    className="absolute top-0 bottom-0 w-[1px] bg-border-strong"
                    title="85% Soft Warning Threshold"
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Panel>

      {/* Policy Checks Table */}
      <Panel
        title="Deterministic Financial Policy Checks"
        subtitle="Automated Python rule evaluations prior to order commitment"
        padding="none"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-[13px]">
            <thead>
              <tr className="bg-surface-2 h-[36px] border-b border-border text-[11px] font-semibold text-text-3 uppercase tracking-wider">
                <th className="px-3 py-1.5">Order ID</th>
                <th className="px-3 py-1.5">Customer</th>
                <th className="px-3 py-1.5">Governance Rule</th>
                <th className="px-3 py-1.5 text-right">Proposed Requisition</th>
                <th className="px-3 py-1.5 text-right">Policy Limit</th>
                <th className="px-3 py-1.5">Rule Outcome</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {policyChecks.map((check) => (
                <tr key={check.orderId} className="h-[40px] hover:bg-surface-2/50 bg-surface">
                  <td className="px-3 py-2 font-mono text-[12px] font-semibold text-text">
                    {check.orderId}
                  </td>
                  <td className="px-3 py-2 text-text font-medium">{check.customer}</td>
                  <td className="px-3 py-2 font-mono text-[11px] text-text-3">{check.rule}</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums text-text">
                    ₹{check.proposed.toLocaleString('en-IN')}
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums text-text-3">
                    ₹{check.limit.toLocaleString('en-IN')}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <StatusBadge status={check.status} size="sm" />
                      {check.isBreached && (
                        <span className="text-[11px] text-danger font-medium">
                          Escalated to Exceptions
                        </span>
                      )}
                    </div>
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
