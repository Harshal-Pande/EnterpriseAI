import React from 'react';
import { ShieldCheck, CheckCircle2, Hash, FileCheck, Cpu, ArrowUpRight } from 'lucide-react';
import { useDemo } from '../state/DemoContext';

export const AuditTrailPage: React.FC = () => {
  const { auditEvents } = useDemo();

  return (
    <div className="space-y-6 font-sans">
      {/* Header matching Screenshots 3 & 5 */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1B2638] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 font-bold tracking-wider uppercase mb-1">
            <ShieldCheck className="w-4 h-4 text-cyan-400" /> ANCHORED TO POLYGON AUDIT LAYER
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Immutable Audit Trail
          </h1>
          <p className="text-xs text-slate-400 font-medium max-w-2xl mt-1 leading-relaxed">
            Cryptographically verified execution logs anchored to Polygon Layer-2. Monitoring autonomous mesh transactions, PO approvals, and state changes.
          </p>
        </div>

        <div className="bg-[#101726] border border-[#233148] p-3 rounded-xl flex items-center gap-3 shrink-0">
          <div className="w-2 h-2 rounded-full bg-purple-400 animate-ping"></div>
          <div>
            <div className="text-[10px] text-slate-400 font-mono">Network Anchors</div>
            <div className="text-xs font-bold text-purple-300 font-mono">Polygon Mainnet / Testnet</div>
          </div>
        </div>
      </div>

      {/* Metrics Row matching Screenshot 3 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-5 shadow-xl space-y-2">
          <div className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider">
            MESH VERIFICATION RATE
          </div>
          <div className="flex items-baseline gap-3">
            <div className="text-3xl font-extrabold text-white font-mono">99.4%</div>
            <div className="text-xs font-mono text-emerald-400 font-semibold flex items-center">
              +0.12% <ArrowUpRight className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-[11px] text-slate-400 font-mono pt-1">
            Latest Block: #184729 • Latency 1.2s
          </div>
        </div>

        <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-5 shadow-xl space-y-2">
          <div className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider">
            TRANSACTION THROUGHPUT (24H)
          </div>
          <div className="flex items-baseline gap-3">
            <div className="text-3xl font-extrabold text-cyan-400 font-mono">12,492</div>
            <div className="text-xs font-mono text-cyan-400">Tx Executed</div>
          </div>
          <div className="text-[11px] text-slate-400 font-mono pt-1">
            Zero Hash Variance Detected
          </div>
        </div>

        <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-5 shadow-xl space-y-2">
          <div className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider">
            SMART CONTRACT VERDICT
          </div>
          <div className="text-lg font-bold text-emerald-400 font-mono flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            CONSENSUS VERIFIED
          </div>
          <div className="text-[11px] text-slate-400 font-mono pt-1">
            Polygon Smart Contract #0x7f...a91c
          </div>
        </div>
      </div>

      {/* Block Timeline matching Screenshot 5 */}
      <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-6 shadow-2xl space-y-6">
        <div className="flex items-center justify-between border-b border-[#1E293B] pb-4">
          <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
            <Hash className="w-5 h-5 text-teal-400" /> Chronological Blockchain Blocks
          </h2>
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Search by Tx Hash or Order ID..."
              className="bg-[#090D16] border border-[#233148] rounded-lg px-3 py-1.5 text-xs font-mono text-slate-200 w-64 focus:outline-none"
            />
          </div>
        </div>

        {/* Timeline Stack */}
        <div className="space-y-6 relative pl-6 before:absolute before:left-3 before:top-3 before:bottom-3 before:w-0.5 before:bg-[#1E293B]">
          {auditEvents.map((evt) => (
            <div key={evt.eventId} className="relative flex items-start gap-4">
              {/* Timeline Dot Icon */}
              <div className="absolute -left-6 top-1.5 w-6 h-6 rounded-lg bg-[#162035] border border-cyan-500/40 text-cyan-400 flex items-center justify-center shrink-0 shadow-lg">
                <FileCheck className="w-3.5 h-3.5" />
              </div>

              {/* Block Card matching Screenshot 5 */}
              <div className="flex-1 bg-[#090D16] border border-[#1E293B] rounded-xl p-4 shadow-lg hover:border-slate-700 transition space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-sm text-slate-200 font-mono">
                      Block #{evt.blockNumber}
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" /> VERIFIED
                    </span>
                  </div>
                  <span className="text-slate-500 text-xs font-mono">{evt.timestamp}</span>
                </div>

                <h3 className="text-base font-bold text-white">{evt.details}</h3>

                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Actor: <strong className="text-slate-200">{evt.actor}</strong></span>
                  <span className="text-slate-600">•</span>
                  <span>Order ID: <strong className="text-cyan-400 font-mono">{evt.orderId}</strong></span>
                </div>

                <div className="p-2 bg-[#101726] rounded border border-[#233148] font-mono text-xs text-indigo-300 break-all">
                  Tx: {evt.txHash}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="pt-4 flex justify-center border-t border-[#1E293B]">
          <button className="px-6 py-2 bg-[#162035] hover:bg-[#1E2C4A] text-cyan-300 font-mono text-xs rounded-lg border border-cyan-500/30 transition uppercase font-bold tracking-wider">
            LOAD HISTORICAL BLOCKS
          </button>
        </div>
      </div>
    </div>
  );
};
