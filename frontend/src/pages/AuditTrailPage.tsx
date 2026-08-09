import React from 'react';
import { ShieldCheck, Lock, CheckCircle2, Hash } from 'lucide-react';
import { useDemo } from '../state/DemoContext';

export const AuditTrailPage: React.FC = () => {
  const { auditEvents } = useDemo();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-teal-400" /> Blockchain Immutable Audit Ledger
          </h2>
          <p className="text-xs text-slate-400">
            Cryptographically audited multi-agent decision history & transaction verification log
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="px-2.5 py-1 rounded bg-teal-500/10 text-teal-300 border border-teal-500/30 flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" /> Polygon Smart Contract Ready
          </span>
        </div>
      </div>

      {/* Audit Blocks Table */}
      <div className="bg-[#121929] border border-[#24334D] rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-[#24334D] flex items-center justify-between">
          <h3 className="font-bold text-sm text-white flex items-center gap-2">
            <Hash className="w-4 h-4 text-teal-400" /> Verified Audit Blocks ({auditEvents.length})
          </h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/30">
            PROTOTYPE DATA — READY FOR POLYGON TESTNET
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#0B111E] text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-[#24334D]">
              <tr>
                <th className="py-3 px-4">Block #</th>
                <th className="py-3 px-4">Event Type</th>
                <th className="py-3 px-4">Actor Agent</th>
                <th className="py-3 px-4">Order ID</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Transaction Hash</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E293B]">
              {auditEvents.map((evt) => (
                <tr key={evt.eventId} className="hover:bg-[#182338] transition-colors">
                  <td className="py-3.5 px-4 font-bold text-teal-400 font-mono">#{evt.blockNumber}</td>
                  <td className="py-3.5 px-4 font-bold text-white font-mono text-[11px]">{evt.type}</td>
                  <td className="py-3.5 px-4 text-slate-300 font-medium">{evt.actor}</td>
                  <td className="py-3.5 px-4 text-cyan-300 font-mono">{evt.orderId}</td>
                  <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">{evt.timestamp}</td>
                  <td className="py-3.5 px-4 font-mono text-indigo-300 text-[11px]">
                    {evt.txHash.substring(0, 10)}...{evt.txHash.substring(evt.txHash.length - 4)}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-teal-500/15 text-teal-300 border border-teal-500/30 flex items-center gap-1 w-fit">
                      <CheckCircle2 className="w-3 h-3 text-teal-400" /> VERIFIED
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 max-w-xs truncate">{evt.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
