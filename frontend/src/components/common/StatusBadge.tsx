import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const getColors = (st: string) => {
    const s = st.toUpperCase();
    if (s === 'ONLINE' || s === 'APPROVED' || s === 'COMPLETED' || s === 'VERIFIED' || s === 'OK' || s === 'SELECTED') {
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    }
    if (s === 'BUSY' || s === 'PROCESSING' || s === 'INVENTORY_CHECK' || s === 'PROCUREMENT_NEGOTIATION' || s === 'FINANCE_VALIDATION' || s === 'LOGISTICS_FEASIBILITY' || s === 'SUPERVISOR_DECISION') {
      return 'bg-blue-500/10 text-blue-400 border-blue-500/30 animate-pulse';
    }
    if (s === 'WAITING' || s === 'LOW_STOCK' || s === 'AWAITING PROCUREMENT' || s === 'FINANCE REVIEW' || s === 'PENDING') {
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    }
    if (s === 'ERROR' || s === 'EXCEPTION' || s === 'REORDER_REQUIRED' || s === 'UNAVAILABLE' || s === 'REJECTED_BUDGET' || s === 'DELAYED') {
      return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    }
    return 'bg-slate-800 text-slate-400 border-slate-700';
  };

  const px = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium border rounded-full ${px} ${getColors(status)}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
      {status}
    </span>
  );
};
