import React from 'react';
import { CircleDollarSign, CheckCircle2, ShieldCheck } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { StatusBadge } from '../components/common/StatusBadge';

export const FinancePage: React.FC = () => {
  const { activeOrder } = useDemo();

  const maxBudget = activeOrder.budget;
  const requestedAmount = activeOrder.estimatedCost;
  const remainingBudget = maxBudget - requestedAmount;
  const utilizationPct = Math.round((requestedAmount / maxBudget) * 100);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <CircleDollarSign className="w-5 h-5 text-pink-400" /> Finance Agent Validation & Risk Governance
        </h2>
        <p className="text-xs text-slate-400">
          Autonomous financial reserve validation, budget cap compliance, and expenditure authorization
        </p>
      </div>

      {/* Financial Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#121929] border border-[#24334D] rounded-xl p-4 shadow-lg">
          <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Allocated Cap Budget</div>
          <div className="text-2xl font-bold text-white font-mono mt-1">₹{maxBudget.toLocaleString()}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Approved Order Threshold</div>
        </div>

        <div className="bg-[#121929] border border-[#24334D] rounded-xl p-4 shadow-lg">
          <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Sanctioned Quote Value</div>
          <div className="text-2xl font-bold text-pink-400 font-mono mt-1">₹{requestedAmount.toLocaleString()}</div>
          <div className="text-[10px] text-pink-400 mt-0.5">Supplier B Negotiated Price</div>
        </div>

        <div className="bg-[#121929] border border-[#24334D] rounded-xl p-4 shadow-lg">
          <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Remaining Reserve Headroom</div>
          <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">₹{remainingBudget.toLocaleString()}</div>
          <div className="text-[10px] text-emerald-400 mt-0.5">Safety Reserve (6.8%)</div>
        </div>

        <div className="bg-[#121929] border border-[#24334D] rounded-xl p-4 shadow-lg">
          <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Budget Utilization</div>
          <div className="text-2xl font-bold text-cyan-400 font-mono mt-1">{utilizationPct}%</div>
          <div className="text-[10px] text-cyan-400 mt-0.5">Within Compliance Threshold</div>
        </div>
      </div>

      {/* Finance Agent Approval Decision Card */}
      <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-[#24334D] pb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-pink-600/20 text-pink-400 flex items-center justify-center border border-pink-500/30">
              <CircleDollarSign className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">Finance Agent Approval Verdict</h3>
              <p className="text-xs text-slate-400">Order ID: {activeOrder.id}</p>
            </div>
          </div>
          <StatusBadge status="APPROVED" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Compliance Checklist */}
          <div className="bg-[#0A0F1D] p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
            <div className="font-bold text-slate-300 uppercase tracking-wider text-[10px] mb-2">
              Financial Compliance Checklist
            </div>
            <div className="flex items-center justify-between text-slate-200 py-1 border-b border-slate-800">
              <span>Sanction Cap Limit Check</span>
              <span className="text-emerald-400 font-mono flex items-center gap-1 font-bold">
                <CheckCircle2 className="w-3.5 h-3.5" /> PASSED
              </span>
            </div>
            <div className="flex items-center justify-between text-slate-200 py-1 border-b border-slate-800">
              <span>Corporate Liquidity Reserve</span>
              <span className="text-emerald-400 font-mono flex items-center gap-1 font-bold">
                <CheckCircle2 className="w-3.5 h-3.5" /> PASSED
              </span>
            </div>
            <div className="flex items-center justify-between text-slate-200 py-1 border-b border-slate-800">
              <span>Vendor Payment Term Terms (30 days)</span>
              <span className="text-emerald-400 font-mono flex items-center gap-1 font-bold">
                <CheckCircle2 className="w-3.5 h-3.5" /> VERIFIED
              </span>
            </div>
            <div className="flex items-center justify-between text-slate-200 py-1">
              <span>Financial Risk Exposure Score</span>
              <span className="text-cyan-400 font-mono font-bold">1.4% (LOW)</span>
            </div>
          </div>

          {/* Decision Rationale */}
          <div className="bg-[#1C0F1B] p-4 rounded-xl border border-pink-500/30 space-y-2 text-xs">
            <div className="font-bold text-pink-300 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-pink-400" /> Finance Agent Decision Rationale
            </div>
            <p className="text-slate-200 leading-relaxed font-sans">
              "The requested procurement quote of ₹7,92,000 for 120 units of WP-800 pumps has been validated against Tata Steels' allocated budget of ₹8,50,000. The expenditure leaves a healthy reserve of ₹58,000 (6.8%) and complies with all corporate governance thresholds. Sanction token granted to Logistics Agent."
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
