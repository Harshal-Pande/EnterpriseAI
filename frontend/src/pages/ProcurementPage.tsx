import React from 'react';
import { Scale, ArrowRight, CheckCircle2, XCircle, Star } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { StatusBadge } from '../components/common/StatusBadge';

const SCORE_COLOR = (score: number) => {
  if (score >= 90) return '#10B981';
  if (score >= 70) return '#F59E0B';
  return '#EF4444';
};

export const ProcurementPage: React.FC = () => {
  const { suppliers } = useDemo();
  const selectedSupplier = suppliers.find(s => s.status === 'SELECTED') ?? suppliers[1];

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="pb-5 border-b border-[#1E293B]">
        <h1 className="text-2xl font-extrabold text-white tracking-tight">Procurement Intelligence</h1>
        <p className="text-sm text-slate-500 mt-1">
          Autonomous supplier evaluation, multi-vendor negotiation, and SLA-weighted selection matrix
        </p>
      </div>

      {/* Selected Supplier Highlight */}
      <div
        className="rounded-xl p-5"
        style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.25)' }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.3)' }}
            >
              <Scale className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <div className="text-[10px] font-mono font-bold text-amber-400 uppercase tracking-widest">
                Autonomous Procurement Recommendation
              </div>
              <div className="text-sm font-bold text-white mt-0.5">
                {selectedSupplier.name} ({selectedSupplier.id})
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <div className="text-right">
              <div className="text-[10px] text-slate-500">Negotiated Score</div>
              <div className="text-xl font-bold font-mono text-amber-400">{selectedSupplier.score}/100</div>
            </div>
            <StatusBadge status={selectedSupplier.status} />
          </div>
        </div>

        <div
          className="mt-4 px-4 py-3 rounded-lg text-[12px] text-slate-200"
          style={{ background: '#080C14', border: '1px solid #1E293B' }}
        >
          <span className="text-amber-300 font-semibold">Decision Rationale: </span>
          {selectedSupplier.notes}
        </div>
      </div>

      {/* Supplier Comparison Matrix */}
      <div className="rounded-xl overflow-hidden" style={{ background: '#111827', border: '1px solid #1E293B' }}>
        <div className="px-5 py-3.5 border-b border-[#1E293B] flex items-center justify-between">
          <h2 className="text-sm font-bold text-white">Supplier Comparison Matrix</h2>
          <span className="text-[10px] font-mono text-slate-600">Target: 78 units WP-800</span>
        </div>
        <div className="overflow-x-auto">
          <table className="ent-table">
            <thead>
              <tr>
                <th>Supplier</th>
                <th className="text-right">Price/Unit</th>
                <th className="text-right">Available Qty</th>
                <th className="text-right">Lead Time</th>
                <th className="text-right">Weighted Score</th>
                <th>Status</th>
                <th>Agent Note</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map(sup => {
                const isSelected = sup.status === 'SELECTED';
                const isUnavail  = sup.status === 'UNAVAILABLE' || sup.status === 'REJECTED_BUDGET';
                return (
                  <tr
                    key={sup.id}
                    style={isSelected ? { background: 'rgba(245,158,11,0.05)' } : {}}
                  >
                    <td>
                      <div className="flex items-center gap-2">
                        {isSelected && <Star className="w-3 h-3 text-amber-400 shrink-0" />}
                        <span className={`font-bold ${isSelected ? 'text-white' : isUnavail ? 'text-slate-600' : 'text-slate-300'}`}>
                          {sup.name}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-600 font-mono">{sup.id}</div>
                    </td>
                    <td className="text-right">
                      <span className={`font-mono font-bold ${isUnavail ? 'text-slate-600' : 'text-emerald-400'}`}>
                        ₹{sup.pricePerUnit.toLocaleString()}
                      </span>
                    </td>
                    <td className="text-right font-mono">
                      <span className={sup.availability === 0 ? 'text-rose-400' : 'text-cyan-300'}>
                        {sup.availability > 0 ? `${sup.availability} units` : 'Out of Stock'}
                      </span>
                    </td>
                    <td className="text-right font-mono text-slate-400">
                      {sup.deliveryDays} day{sup.deliveryDays !== 1 ? 's' : ''}
                    </td>
                    <td className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: '#1E293B' }}>
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${sup.score}%`, background: SCORE_COLOR(sup.score) }}
                          />
                        </div>
                        <span className="font-mono font-bold text-xs" style={{ color: SCORE_COLOR(sup.score) }}>
                          {sup.score}
                        </span>
                      </div>
                    </td>
                    <td><StatusBadge status={sup.status} /></td>
                    <td className="text-slate-400 max-w-[200px] truncate text-[11px]">{sup.notes}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Negotiation Timeline */}
      <div className="rounded-xl overflow-hidden" style={{ background: '#0F172A', border: '1px solid #1E293B' }}>
        <div className="px-5 py-3.5 border-b border-[#1E293B]">
          <h2 className="text-sm font-bold text-white">Procurement Agent Negotiation Timeline</h2>
        </div>
        <div className="p-5 space-y-3">
          {[
            { step: '01', agent: 'Supplier A', color: '#EF4444', outcome: 'Stock check returned 0 available units. Marked UNAVAILABLE by Procurement Agent.', icon: <XCircle className="w-3.5 h-3.5" /> },
            { step: '02', agent: 'Supplier B', color: '#F59E0B', outcome: 'Submitted revised quotation: 150 units @ ₹6,600/unit (2-day SLA). Accepted by agent.', icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
            { step: '03', agent: 'Supplier C', color: '#94A3B8', outcome: 'Offered 1-day express delivery at ₹7,400/unit. 12% price premium flagged.', icon: null },
            { step: 'FINAL', agent: 'Procurement Agent', color: '#10B981', outcome: 'Selected Supplier B for optimal SLA & budget balance. Proposal transmitted to Finance Agent.', icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
          ].map(({ step, agent, color, outcome, icon }) => (
            <div
              key={step}
              className="flex items-start gap-3 p-3.5 rounded-lg"
              style={{
                background: step === 'FINAL' ? 'rgba(16,185,129,0.05)' : '#080C14',
                border: `1px solid ${step === 'FINAL' ? 'rgba(16,185,129,0.2)' : '#1E293B'}`
              }}
            >
              <span className="font-mono text-[9px] font-bold text-slate-600 uppercase w-10 shrink-0 mt-0.5">{step}</span>
              <div style={{ color }} className="flex items-center gap-1.5 font-bold text-xs w-32 shrink-0">
                {icon} {agent}
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-slate-700 shrink-0 mt-0.5" />
              <p className="text-[11px] text-slate-300 leading-snug">{outcome}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
