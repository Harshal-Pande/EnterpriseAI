import React from 'react';
import { Scale, ArrowRight } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { StatusBadge } from '../components/common/StatusBadge';

export const ProcurementPage: React.FC = () => {
  const { suppliers } = useDemo();

  const selectedSupplier = suppliers.find(s => s.status === 'SELECTED') || suppliers[1];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Scale className="w-5 h-5 text-amber-400" /> Procurement Agent Negotiation & Scoring Matrix
        </h2>
        <p className="text-xs text-slate-400">
          Autonomous multi-supplier quotation analysis, delivery SLA scoring, and dynamic negotiation
        </p>
      </div>

      {/* Selected Supplier Highlight Box */}
      <div className="bg-gradient-to-r from-[#1E190E] via-[#2A200F] to-[#1E190E] border border-amber-500/40 rounded-2xl p-5 shadow-xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold border border-amber-500/30">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[10px] text-amber-400 font-mono font-bold uppercase tracking-wider">
                Autonomous Procurement Recommendation
              </div>
              <h3 className="font-bold text-base text-white">{selectedSupplier.name} ({selectedSupplier.id})</h3>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-slate-400">Negotiated Score</div>
            <div className="font-bold text-amber-400 text-lg font-mono">{selectedSupplier.score} / 100</div>
          </div>
        </div>

        <div className="p-3 bg-[#0A0F1D] rounded-xl border border-slate-800 text-xs text-slate-200">
          <strong className="text-amber-300">Decision Rationale: </strong>
          {selectedSupplier.notes}
        </div>
      </div>

      {/* Supplier Comparison Matrix Table */}
      <div className="bg-[#121929] border border-[#24334D] rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-[#24334D] flex items-center justify-between">
          <h3 className="font-bold text-sm text-white">Live Supplier Comparison Matrix</h3>
          <span className="text-xs text-slate-400 font-mono">Target Qty: 78 units WP-800</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#0B111E] text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-[#24334D]">
              <tr>
                <th className="py-3 px-4">Supplier Name</th>
                <th className="py-3 px-4">Price / Unit</th>
                <th className="py-3 px-4">Available Qty</th>
                <th className="py-3 px-4">Delivery Days</th>
                <th className="py-3 px-4">Weighted Score</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Negotiation Note</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E293B]">
              {suppliers.map(sup => (
                <tr
                  key={sup.id}
                  className={`transition-colors ${
                    sup.status === 'SELECTED'
                      ? 'bg-amber-500/10 font-medium text-white'
                      : 'hover:bg-[#182338]'
                  }`}
                >
                  <td className="py-3.5 px-4 font-bold text-white flex items-center gap-2">
                    {sup.name}
                  </td>
                  <td className="py-3.5 px-4 font-mono font-semibold text-emerald-400">
                    ₹{sup.pricePerUnit.toLocaleString()}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-cyan-300">
                    {sup.availability > 0 ? `${sup.availability} units` : 'Out of stock (0)'}
                  </td>
                  <td className="py-3.5 px-4 font-mono">{sup.deliveryDays} Days</td>
                  <td className="py-3.5 px-4 font-mono font-bold text-amber-400">{sup.score} / 100</td>
                  <td className="py-3.5 px-4">
                    <StatusBadge status={sup.status} />
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 max-w-xs truncate">{sup.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Negotiation Activity Timeline */}
      <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-5 shadow-xl space-y-3">
        <h3 className="font-bold text-sm text-white uppercase tracking-wider text-xs">
          Multi-Agent Negotiation Timeline
        </h3>

        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-3 p-2.5 bg-[#0B111E] rounded-xl border border-[#1E293B]">
            <span className="font-mono text-slate-500 text-[10px]">Step 1</span>
            <span className="font-bold text-rose-400 w-28">Supplier A</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
            <span className="text-slate-300">Stock check returned 0 available units. Marked UNAVAILABLE.</span>
          </div>

          <div className="flex items-center gap-3 p-2.5 bg-[#0B111E] rounded-xl border border-[#1E293B]">
            <span className="font-mono text-slate-500 text-[10px]">Step 2</span>
            <span className="font-bold text-amber-400 w-28">Supplier B</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
            <span className="text-slate-300">Submitted revised quotation: 150 units @ ₹6,600/unit (2-day SLA).</span>
          </div>

          <div className="flex items-center gap-3 p-2.5 bg-[#0B111E] rounded-xl border border-[#1E293B]">
            <span className="font-mono text-slate-500 text-[10px]">Step 3</span>
            <span className="font-bold text-cyan-400 w-28">Supplier C</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
            <span className="text-slate-300">Offered 1-day express delivery at ₹7,400/unit (12% price premium).</span>
          </div>

          <div className="flex items-center gap-3 p-2.5 bg-[#0D1E36] rounded-xl border border-blue-500/30 font-medium">
            <span className="font-mono text-cyan-400 text-[10px]">FINAL</span>
            <span className="font-bold text-emerald-400 w-28">Procurement Agent</span>
            <ArrowRight className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-white">Selected Supplier B for optimal SLA & budget balance. Transmitted proposal to Finance Agent.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
