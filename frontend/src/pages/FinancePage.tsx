import React from 'react';
import { CircleDollarSign, CheckCircle2, ShieldCheck, TrendingUp, AlertTriangle } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { StatusBadge } from '../components/common/StatusBadge';

export const FinancePage: React.FC = () => {
  const { activeOrder, agents } = useDemo();

  const financeAgent   = agents.find(a => a.id === 'finance');
  const maxBudget      = activeOrder.budget;
  const requestedAmt   = activeOrder.estimatedCost;
  const remaining      = maxBudget - requestedAmt;
  const utilizationPct = Math.round((requestedAmt / maxBudget) * 100);
  const isOver         = requestedAmt > maxBudget;

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="pb-5 border-b border-[#1E293B]">
        <h1 className="text-2xl font-extrabold text-white tracking-tight">Finance Validation & Risk Governance</h1>
        <p className="text-sm text-slate-500 mt-1">
          Autonomous financial reserve validation, budget cap compliance, and expenditure authorization
        </p>
      </div>

      {/* Budget Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label:  'Allocated Cap',
            value:  `₹${maxBudget.toLocaleString()}`,
            sub:    'Approved Order Threshold',
            color:  '#F8FAFC',
            icon:   <CircleDollarSign className="w-4 h-4" />,
            iconBg: 'rgba(236,72,153,0.1)',
            iconC:  '#EC4899'
          },
          {
            label:  'Sanctioned Quote',
            value:  `₹${requestedAmt.toLocaleString()}`,
            sub:    'Procurement Estimate',
            color:  '#EC4899',
            icon:   <TrendingUp className="w-4 h-4" />,
            iconBg: 'rgba(236,72,153,0.1)',
            iconC:  '#EC4899'
          },
          {
            label:  'Reserve Headroom',
            value:  `₹${remaining.toLocaleString()}`,
            sub:    `Safety Reserve (${(100 - utilizationPct)}%)`,
            color:  remaining >= 0 ? '#10B981' : '#EF4444',
            icon:   remaining >= 0 ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />,
            iconBg: remaining >= 0 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
            iconC:  remaining >= 0 ? '#10B981' : '#EF4444'
          },
          {
            label:  'Budget Utilization',
            value:  `${utilizationPct}%`,
            sub:    isOver ? '⚠ Budget Breach!' : 'Within Compliance',
            color:  isOver ? '#EF4444' : '#38BDF8',
            icon:   <ShieldCheck className="w-4 h-4" />,
            iconBg: 'rgba(56,189,248,0.1)',
            iconC:  '#38BDF8'
          },
        ].map(({ label, value, sub, color, icon, iconBg, iconC }) => (
          <div key={label} className="rounded-xl p-4" style={{ background: '#111827', border: '1px solid #1E293B' }}>
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: iconBg, color: iconC }}>
                {icon}
              </div>
              <span className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-wider">{label}</span>
            </div>
            <div className="text-xl font-bold font-mono" style={{ color }}>{value}</div>
            <div className="text-[10px] text-slate-500 mt-1" style={{ color: sub.startsWith('⚠') ? '#F59E0B' : undefined }}>{sub}</div>
          </div>
        ))}
      </div>

      {/* Budget Utilization Bar */}
      <div className="rounded-xl px-5 py-4" style={{ background: '#111827', border: '1px solid #1E293B' }}>
        <div className="flex items-center justify-between mb-2 text-[11px] font-mono">
          <span className="text-slate-500">Budget Utilization</span>
          <span className={isOver ? 'text-rose-400 font-bold' : 'text-emerald-400 font-bold'}>{utilizationPct}%</span>
        </div>
        <div className="h-3 rounded-full overflow-hidden" style={{ background: '#1E293B' }}>
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(utilizationPct, 100)}%`,
              background: isOver
                ? 'linear-gradient(90deg, #EF4444, #DC2626)'
                : utilizationPct > 85
                ? 'linear-gradient(90deg, #F59E0B, #D97706)'
                : 'linear-gradient(90deg, #10B981, #059669)'
            }}
          />
        </div>
        <div className="flex justify-between text-[10px] font-mono text-slate-600 mt-1.5">
          <span>₹0</span>
          <span className="text-rose-500">Cap: ₹{maxBudget.toLocaleString()}</span>
        </div>
      </div>

      {/* Finance Agent Approval Verdict */}
      <div className="rounded-xl overflow-hidden" style={{ background: '#0F172A', border: '1px solid rgba(236,72,153,0.2)' }}>
        <div
          className="flex items-center justify-between px-5 py-4 border-b"
          style={{ borderColor: 'rgba(236,72,153,0.15)', background: 'rgba(236,72,153,0.05)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(236,72,153,0.12)', border: '1px solid rgba(236,72,153,0.25)' }}
            >
              <CircleDollarSign className="w-5 h-5 text-pink-400" />
            </div>
            <div>
              <div className="text-sm font-bold text-white">Finance Agent Approval Verdict</div>
              <div className="text-[11px] text-slate-400">Order: {activeOrder.id}</div>
            </div>
          </div>
          <StatusBadge status="APPROVED" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-5">
          {/* Compliance Checklist */}
          <div className="rounded-xl p-4 space-y-2" style={{ background: '#080C14', border: '1px solid #1E293B' }}>
            <div className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-3">
              Financial Compliance Checklist
            </div>
            {[
              { label: 'Sanction Cap Limit Check',        pass: !isOver },
              { label: 'Corporate Liquidity Reserve',      pass: true    },
              { label: 'Vendor Payment Terms (Net-30)',    pass: true    },
              { label: 'Dual-Approval Authorization',      pass: true    },
              { label: 'Financial Risk Score < 5%',        pass: true    },
            ].map(({ label, pass }) => (
              <div key={label} className="flex items-center justify-between text-[11px] py-1 border-b border-[#1E293B] last:border-0">
                <span className="text-slate-300">{label}</span>
                <span className={`flex items-center gap-1 font-mono font-bold text-[10px] ${pass ? 'text-emerald-400' : 'text-rose-400'}`}>
                  <CheckCircle2 className="w-3 h-3" />
                  {pass ? 'PASSED' : 'FAILED'}
                </span>
              </div>
            ))}
            <div className="flex items-center justify-between text-[11px] pt-1">
              <span className="text-slate-300">Financial Risk Exposure</span>
              <span className="font-mono font-bold text-cyan-400 text-[10px]">1.4% (LOW)</span>
            </div>
          </div>

          {/* Decision Rationale */}
          <div
            className="rounded-xl p-4"
            style={{ background: 'rgba(236,72,153,0.05)', border: '1px solid rgba(236,72,153,0.18)' }}
          >
            <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-widest text-pink-400 mb-3">
              <ShieldCheck className="w-3 h-3" /> Finance Agent Decision Rationale
            </div>
            <p className="text-[12px] text-slate-200 leading-relaxed">
              {financeAgent?.rationale ??
                `The requested procurement quote of ₹${requestedAmt.toLocaleString()} for 120 units of WP-800 pumps has been validated against Tata Steels' allocated budget of ₹${maxBudget.toLocaleString()}. The expenditure leaves a healthy reserve of ₹${remaining.toLocaleString()} (6.8%) and complies with all corporate governance thresholds. Sanction token granted to Logistics Agent.`
              }
            </p>
            {financeAgent && (
              <div className="mt-3 text-[10px] font-mono text-pink-400">
                Confidence Level: {financeAgent.confidence}%
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
