import React from 'react';

export type GovernanceStatusKey =
  | 'running'
  | 'completed'
  | 'allowed'
  | 'blocked'
  | 'awaiting_approval'
  | 'approved'
  | 'rejected'
  | 'failed'
  | 'simulated'
  | 'unavailable'
  | 'pending';

interface StatusConfig {
  label: string;
  badgeClass: string;
  dotClass: string;
}

const STATUS_CONFIGS: Record<GovernanceStatusKey, StatusConfig> = {
  running: {
    label: 'Running',
    badgeClass: 'bg-info-soft text-info border-info/30',
    dotClass: 'bg-info animate-step-pulse',
  },
  completed: {
    label: 'Completed',
    badgeClass: 'bg-ok-soft text-ok border-ok/30',
    dotClass: 'bg-ok',
  },
  allowed: {
    label: 'Allowed',
    badgeClass: 'bg-ok-soft text-ok border-ok/30',
    dotClass: 'bg-ok',
  },
  blocked: {
    label: 'Blocked',
    badgeClass: 'bg-danger-soft text-danger border-danger/30',
    dotClass: 'bg-danger',
  },
  awaiting_approval: {
    label: 'Awaiting approval',
    badgeClass: 'bg-warn-soft text-warn border-warn/30',
    dotClass: 'bg-warn',
  },
  approved: {
    label: 'Approved',
    badgeClass: 'bg-ok-soft text-ok border-ok/30',
    dotClass: 'bg-ok',
  },
  rejected: {
    label: 'Rejected',
    badgeClass: 'bg-danger-soft text-danger border-danger/30',
    dotClass: 'bg-danger',
  },
  failed: {
    label: 'Failed',
    badgeClass: 'bg-danger-soft text-danger border-danger/30',
    dotClass: 'bg-danger',
  },
  simulated: {
    label: 'Simulated',
    badgeClass: 'bg-sim-soft text-sim border-sim/30',
    dotClass: 'bg-sim',
  },
  unavailable: {
    label: 'Unavailable',
    badgeClass: 'bg-surface-2 text-text-3 border-border-strong/40',
    dotClass: 'bg-text-3',
  },
  pending: {
    label: 'Pending',
    badgeClass: 'bg-surface-2 text-text-2 border-border/60',
    dotClass: 'bg-border-strong',
  },
};

/**
 * Normalizes any legacy or domain status string to the unified 11-key vocabulary.
 */
export function normalizeStatus(rawStatus?: string | null): GovernanceStatusKey {
  if (!rawStatus) return 'pending';
  const s = rawStatus.trim().toLowerCase().replace(/[\s-]+/g, '_');

  // Exact matches
  if (s in STATUS_CONFIGS) return s as GovernanceStatusKey;

  // Running / active states
  if (
    s === 'online' ||
    s === 'busy' ||
    s === 'processing' ||
    s === 'active' ||
    s === 'in_progress' ||
    s.startsWith('supervisor_') ||
    s.startsWith('inventory_') ||
    s.startsWith('procurement_') ||
    s.startsWith('finance_') ||
    s.startsWith('logistics_') ||
    s === 'received'
  ) {
    return 'running';
  }

  // Completed / Ok / Success / Verified
  if (
    s === 'ok' ||
    s === 'success' ||
    s === 'verified' ||
    s === 'selected' ||
    s === 'available' ||
    s === 'order_fulfilled' ||
    s === 'passed'
  ) {
    return 'completed';
  }

  // Approved
  if (s === 'approved') return 'approved';

  // Allowed
  if (s === 'allowed') return 'allowed';

  // Blocked
  if (s === 'blocked') return 'blocked';

  // Awaiting approval / review / waiting
  if (
    s === 'awaiting_approval' ||
    s === 'awaiting_procurement' ||
    s === 'finance_review' ||
    s === 'review' ||
    s === 'waiting' ||
    s === 'low_stock'
  ) {
    return 'awaiting_approval';
  }

  // Rejected / Denied
  if (s === 'rejected' || s === 'rejected_budget') return 'rejected';

  // Failed / Error / Exception / Delayed / Breach
  if (
    s === 'failed' ||
    s === 'error' ||
    s === 'exception' ||
    s === 'shortage' ||
    s === 'reorder_required' ||
    s === 'delayed' ||
    s === 'budget_breach' ||
    s === 'delivery_delay' ||
    s === 'multi_exception'
  ) {
    return 'failed';
  }

  // Simulated
  if (s === 'simulated' || s === 'demo' || s === 'mock') return 'simulated';

  // Unavailable
  if (s === 'unavailable' || s === 'supplier_unavailable' || s === 'unreachable') return 'unavailable';

  return 'pending';
}

export interface StatusBadgeProps {
  status: string | GovernanceStatusKey;
  size?: 'sm' | 'md';
  customLabel?: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  customLabel,
  className = '',
}) => {
  const key = normalizeStatus(status);
  const cfg = STATUS_CONFIGS[key];
  const label = customLabel || cfg.label;

  const heightClass = size === 'sm' ? 'h-[18px] text-[11px] px-1.5' : 'h-[22px] text-[12px] px-2';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium border rounded-[4px] shrink-0 select-none ${heightClass} ${cfg.badgeClass} ${className}`}
      title={label}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${cfg.dotClass}`} />
      <span className="truncate leading-none">{label}</span>
    </span>
  );
};
