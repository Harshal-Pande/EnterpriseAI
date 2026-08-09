import React from 'react';
import { BarChart3, Zap, Clock, ShieldCheck, AlertCircle } from 'lucide-react';

export const BenchmarksPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" /> Multi-Agent Performance Benchmarking
          </h2>
          <p className="text-xs text-slate-400">
            Comparative analysis: Traditional Sequential Rule Pipeline vs Enterprise AI Hybrid Mesh
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 text-xs font-mono font-bold flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 text-amber-400" /> DEMO DATA — NOT FINAL BENCHMARK RESULTS
          </span>
        </div>
      </div>

      {/* Primary Comparison Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Metric 1 */}
        <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-5 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Order Fulfilment Latency</div>
            <Clock className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-[10px] text-slate-400">Traditional Pipeline</div>
              <div className="text-lg font-bold text-slate-400 font-mono">4,800 ms</div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-cyan-400 font-bold">Enterprise AI Mesh</div>
              <div className="text-2xl font-bold text-cyan-400 font-mono">1,520 ms</div>
            </div>
          </div>
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-cyan-300 font-mono text-xs text-center font-bold">
            68.3% LATENCY REDUCTION
          </div>
        </div>

        {/* Metric 2 */}
        <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-5 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Exception Recovery Success</div>
            <Zap className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-[10px] text-slate-400">Traditional Pipeline</div>
              <div className="text-lg font-bold text-slate-400 font-mono">18.5 %</div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-emerald-400 font-bold">Enterprise AI Mesh</div>
              <div className="text-2xl font-bold text-emerald-400 font-mono">98.4 %</div>
            </div>
          </div>
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-300 font-mono text-xs text-center font-bold">
            +79.9% AUTONOMOUS RECOVERY
          </div>
        </div>

        {/* Metric 3 */}
        <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-5 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Audit & Explainability Score</div>
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-[10px] text-slate-400">Traditional Pipeline</div>
              <div className="text-lg font-bold text-slate-400 font-mono">12.0 %</div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-indigo-400 font-bold">Enterprise AI Mesh</div>
              <div className="text-2xl font-bold text-indigo-400 font-mono">94.5 %</div>
            </div>
          </div>
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/30 rounded-lg text-indigo-300 font-mono text-xs text-center font-bold">
            BLOCKCHAIN AUDITED EXPLAINABILITY
          </div>
        </div>
      </div>

      {/* Detailed Benchmark Summary Table */}
      <div className="bg-[#121929] border border-[#24334D] rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-[#24334D]">
          <h3 className="font-bold text-sm text-white">System Architecture Comparison Matrix</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#0B111E] text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-[#24334D]">
              <tr>
                <th className="py-3 px-4">Evaluation Metric</th>
                <th className="py-3 px-4">Deterministic Pipeline</th>
                <th className="py-3 px-4">Enterprise AI Mesh</th>
                <th className="py-3 px-4">Delta / Advantage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E293B] font-mono">
              <tr className="hover:bg-[#182338]">
                <td className="py-3.5 px-4 font-bold text-white font-sans">Average Order Processing Latency</td>
                <td className="py-3.5 px-4 text-slate-400">4,800 ms</td>
                <td className="py-3.5 px-4 text-cyan-400 font-bold">1,520 ms</td>
                <td className="py-3.5 px-4 text-emerald-400 font-bold">3.15x Faster</td>
              </tr>
              <tr className="hover:bg-[#182338]">
                <td className="py-3.5 px-4 font-bold text-white font-sans">Processing Cost per Order</td>
                <td className="py-3.5 px-4 text-slate-400">₹1,450</td>
                <td className="py-3.5 px-4 text-pink-400 font-bold">₹840</td>
                <td className="py-3.5 px-4 text-emerald-400 font-bold">-42% Overhead</td>
              </tr>
              <tr className="hover:bg-[#182338]">
                <td className="py-3.5 px-4 font-bold text-white font-sans">Supplier Outage Recovery Time</td>
                <td className="py-3.5 px-4 text-slate-400">14,400 sec (Manual)</td>
                <td className="py-3.5 px-4 text-emerald-400 font-bold">8.5 sec (Autonomous)</td>
                <td className="py-3.5 px-4 text-emerald-400 font-bold">1694x Faster Recovery</td>
              </tr>
              <tr className="hover:bg-[#182338]">
                <td className="py-3.5 px-4 font-bold text-white font-sans">Cryptographic Audit Compliance</td>
                <td className="py-3.5 px-4 text-rose-400">None (Database Logs)</td>
                <td className="py-3.5 px-4 text-teal-400 font-bold">Polygon Smart Contract Verified</td>
                <td className="py-3.5 px-4 text-teal-400 font-bold">Tamper-Proof Ledger</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
