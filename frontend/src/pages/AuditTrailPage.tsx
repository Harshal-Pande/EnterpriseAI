import React from 'react';
import { ShieldCheck, Hash, FileCheck, Cpu, ArrowUpRight, Database } from 'lucide-react';
import { useDemo } from '../state/DemoContext';

export const AuditTrailPage: React.FC = () => {
  const { auditEvents } = useDemo();

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-mono font-bold text-teal-400 uppercase tracking-widest mb-1.5">
            <ShieldCheck className="w-3.5 h-3.5" /> Polygon Layer-2 Audit Anchor
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Immutable Audit Trail</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-lg">
            Cryptographically verified execution logs — designed to anchor to Polygon smart contracts in production.
            This prototype simulates the intended blockchain audit architecture.
          </p>
        </div>
        <div
          className="flex items-center gap-2 px-4 py-3 rounded-xl shrink-0"
          style={{ background: '#0F172A', border: '1px solid rgba(139,92,246,0.25)' }}
        >
          <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />
          <div>
            <div className="text-[10px] text-slate-500 font-mono">Audit Anchor Protocol</div>
            <div className="text-xs font-bold text-purple-300 font-mono">Polygon Testnet / Mainnet</div>
          </div>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          {
            label: 'Mesh Verification Rate',
            value: '99.4%',
            sub:   '+0.12% ↑',
            color: '#10B981',
            icon:  <ShieldCheck className="w-4 h-4" />,
          },
          {
            label: 'Tx Throughput (24h)',
            value: `${(auditEvents.length * 2481 + 12_492).toLocaleString()}`,
            sub:   'Zero Hash Variance Detected',
            color: '#38BDF8',
            icon:  <Hash className="w-4 h-4" />,
          },
          {
            label: 'Smart Contract Status',
            value: 'CONSENSUS',
            sub:   'Contract 0x7f83…a91c',
            color: '#10B981',
            icon:  <Database className="w-4 h-4" />,
          },
        ].map(({ label, value, sub, color, icon }) => (
          <div key={label} className="rounded-xl p-4" style={{ background: '#111827', border: '1px solid #1E293B' }}>
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: 'rgba(16,185,129,0.1)', color }}>
                {icon}
              </div>
              <span className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-wider">{label}</span>
            </div>
            <div className="text-xl font-bold font-mono" style={{ color }}>{value}</div>
            <div className="text-[10px] text-emerald-400 font-mono mt-1">{sub}</div>
          </div>
        ))}
      </div>

      {/* Prototype Disclaimer */}
      <div
        className="flex items-start gap-3 px-4 py-3 rounded-xl text-[11px]"
        style={{ background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.18)' }}
      >
        <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <span className="text-slate-400 leading-relaxed">
          <strong className="text-indigo-300">Prototype Note:</strong>{' '}
          The audit records displayed are simulation outputs. In production, each event hash will be committed
          to a Polygon Mainnet smart contract via the backend Audit Service. The architecture boundary for this
          integration is defined in <code className="font-mono text-indigo-300">apiServices.ts → auditService</code>.
        </span>
      </div>

      {/* Blockchain Timeline */}
      <div className="rounded-xl overflow-hidden" style={{ background: '#0F172A', border: '1px solid #1E293B' }}>
        <div className="px-5 py-3.5 border-b border-[#1E293B] flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Hash className="w-4 h-4 text-teal-400" />
            Chronological Block Timeline
          </h2>
          <span className="text-[10px] text-slate-600 font-mono">{auditEvents.length} blocks</span>
        </div>

        <div className="p-5">
          {/* Vertical timeline */}
          <div className="relative pl-8 space-y-4 before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-px before:bg-[#1E293B]">
            {auditEvents.map((evt, i) => (
              <div key={evt.eventId} className="relative animate-fade-slide" style={{ animationDelay: `${i * 0.04}s` }}>
                {/* Timeline node */}
                <div
                  className="absolute -left-8 top-3 w-6 h-6 rounded-lg flex items-center justify-center z-10"
                  style={{ background: '#111827', border: '1px solid rgba(56,189,248,0.3)' }}
                >
                  <FileCheck className="w-3.5 h-3.5 text-teal-400" />
                </div>

                {/* Block card */}
                <div
                  className="rounded-xl p-4 transition hover:border-slate-700"
                  style={{ background: '#080C14', border: '1px solid #1E293B' }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono font-bold text-sm text-slate-200">Block #{evt.blockNumber}</span>
                      <span
                        className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold"
                        style={{ background: 'rgba(16,185,129,0.1)', color: '#10B981', border: '1px solid rgba(16,185,129,0.25)' }}
                      >
                        <ShieldCheck className="w-3 h-3" /> VERIFIED
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-600">{evt.timestamp}</span>
                  </div>

                  <h3 className="text-[13px] font-bold text-white mb-1.5">{evt.details}</h3>

                  <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <Cpu className="w-3 h-3 text-cyan-400" />
                      Actor: <strong className="text-slate-200">{evt.actor}</strong>
                    </span>
                    <span className="text-slate-700">·</span>
                    <span>
                      Order: <span className="text-cyan-400 font-mono">{evt.orderId}</span>
                    </span>
                    <span className="text-slate-700">·</span>
                    <span>
                      Type: <span className="font-mono text-indigo-300">{evt.type}</span>
                    </span>
                  </div>

                  {/* Tx Hash */}
                  <div
                    className="mt-2.5 flex items-center gap-2 px-3 py-2 rounded-lg overflow-hidden"
                    style={{ background: '#0F172A', border: '1px solid #1E293B' }}
                  >
                    <Hash className="w-3 h-3 text-indigo-400 shrink-0" />
                    <span className="font-mono text-[10px] text-indigo-300 truncate">{evt.txHash}</span>
                    <ArrowUpRight className="w-3 h-3 text-slate-600 shrink-0" />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="text-center mt-6">
            <button
              className="px-6 py-2 rounded-lg text-[11px] font-mono font-bold uppercase tracking-widest transition"
              style={{ background: '#111827', color: '#38BDF8', border: '1px solid rgba(56,189,248,0.2)' }}
            >
              Load Historical Blocks
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
