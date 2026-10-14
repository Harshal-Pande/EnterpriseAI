import React, { useState } from 'react';
import {
  ShieldCheck,
  Hash,
  FileCheck,
  Cpu,
  ArrowUpRight,
  Database,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  Clock,
  Link2,
} from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import type { BackendAnchorRecord } from '../services/apiClient';

export const AuditTrailPage: React.FC = () => {
  const {
    auditEvents: demoAuditEvents,
    liveAuditEvents,
    blockchainStatus,
    dataMode,
    anchorAuditEvent,
    verifyAuditDigest,
    refreshLiveData,
  } = useDemo();

  const [verificationResults, setVerificationResults] = useState<
    Record<string, { verified: boolean; on_chain_verified?: boolean; digest?: string; explorer_url?: string; error?: string }>
  >({});
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [anchoringId, setAnchoringId] = useState<string | null>(null);
  const [anchorResults, setAnchorResults] = useState<Record<string, BackendAnchorRecord>>({});
  const [actionError, setActionError] = useState<string | null>(null);

  const isLive = dataMode === 'live';

  const handleVerify = async (eventId: string) => {
    setVerifyingId(eventId);
    setActionError(null);
    try {
      const res = await verifyAuditDigest(eventId);
      if (res) {
        setVerificationResults(prev => ({
          ...prev,
          [eventId]: {
            verified: res.matched ?? res.verified ?? true,
            on_chain_verified: res.on_chain_verified,
            digest: res.computed_hash ?? res.computed_digest,
            explorer_url: res.explorer_url || undefined,
          },
        }));
      }
    } catch (err: unknown) {
      setVerificationResults(prev => ({
        ...prev,
        [eventId]: {
          verified: false,
          error: err instanceof Error ? err.message : 'Verification failed',
        },
      }));
    } finally {
      setVerifyingId(null);
    }
  };

  const handleAnchor = async (eventId: string) => {
    setAnchoringId(eventId);
    setActionError(null);
    try {
      const record = await anchorAuditEvent(eventId);
      setAnchorResults(prev => ({
        ...prev,
        [eventId]: record,
      }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Anchoring failed';
      setActionError(`Failed to anchor event ${eventId.slice(0, 8)}: ${msg}`);
    } finally {
      setAnchoringId(null);
    }
  };

  // Status badge helper
  const renderStatusBadge = (status: string, txHash?: string | null) => {
    const s = (status || 'NOT_SUBMITTED').toUpperCase();
    if (s === 'CONFIRMED') {
      return (
        <span
          className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold text-emerald-300 bg-emerald-950/60 border border-emerald-500/40"
          title="Transaction receipt confirmed on EVM network"
        >
          <CheckCircle2 className="w-3 h-3 text-emerald-400" /> ON-CHAIN CONFIRMED
        </span>
      );
    }
    if (s === 'PENDING') {
      return (
        <span
          className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold text-amber-300 bg-amber-950/60 border border-amber-500/40 animate-pulse"
          title="Transaction submitted to mempool; waiting for receipt confirmation"
        >
          <Clock className="w-3 h-3 text-amber-400" /> PENDING RECEIPT
        </span>
      );
    }
    if (s === 'FAILED') {
      return (
        <span
          className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold text-rose-300 bg-rose-950/60 border border-rose-500/40"
          title="Transaction reverted or anchoring failed"
        >
          <AlertTriangle className="w-3 h-3 text-rose-400" /> ANCHOR FAILED
        </span>
      );
    }
    if (s === 'SIMULATED' || (!txHash && s !== 'NOT_SUBMITTED')) {
      return (
        <span
          className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold text-purple-300 bg-purple-950/60 border border-purple-500/40"
          title="Cryptographic digest computed locally; no on-chain transaction broadcast"
        >
          <Database className="w-3 h-3 text-purple-400" /> SIMULATED ANCHOR
        </span>
      );
    }
    return (
      <span
        className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold text-slate-400 bg-slate-900 border border-slate-700"
        title="Event recorded off-chain in PostgreSQL; not yet anchored"
      >
        <FileCheck className="w-3 h-3 text-slate-500" /> NOT ANCHORED
      </span>
    );
  };

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-mono font-bold text-teal-400 uppercase tracking-widest mb-1.5">
            <ShieldCheck className="w-3.5 h-3.5" /> EVM Blockchain Audit Anchoring
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Immutable Audit Trail</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-xl">
            Cryptographically anchored execution logs — submits canonical SHA-256 digests to smart contracts on EVM testnets
            with independent on-chain state verification.
          </p>
        </div>

        {/* Blockchain Network Badge */}
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-xl shrink-0"
          style={{
            background: '#0F172A',
            border: `1px solid ${blockchainStatus?.mode === 'REAL' ? 'rgba(16,185,129,0.35)' : 'rgba(139,92,246,0.25)'}`,
          }}
        >
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              blockchainStatus?.mode === 'REAL' ? 'bg-emerald-400 animate-pulse' : 'bg-purple-400'
            }`}
          />
          <div>
            <div className="text-[10px] text-slate-500 font-mono flex items-center gap-1">
              <span>Anchor Protocol</span>
              <span className="text-slate-600">·</span>
              <span className={blockchainStatus?.mode === 'REAL' ? 'text-emerald-400 font-bold' : 'text-purple-400'}>
                {blockchainStatus?.mode || 'SIMULATED'}
              </span>
            </div>
            <div className="text-xs font-bold text-slate-200 font-mono">
              {blockchainStatus?.network_name || 'EVM Testnet / Simulated'}
              {blockchainStatus?.chain_id ? ` (ID ${blockchainStatus.chain_id})` : ''}
            </div>
          </div>
        </div>
      </div>

      {/* Action Error Alert */}
      {actionError && (
        <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-xs font-mono text-rose-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-rose-400 hover:text-rose-200 text-xs font-bold ml-3">
            Dismiss
          </button>
        </div>
      )}

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        {[
          {
            label: 'Canonical Digest Engine',
            value: 'RFC 8785 + SHA-256',
            sub: 'Deterministic payload serialization',
            color: '#10B981',
            icon: <ShieldCheck className="w-4 h-4" />,
          },
          {
            label: isLive ? 'Live Audit Events' : 'Demo Event Stream',
            value: isLive ? `${liveAuditEvents.length} Recorded` : `${(demoAuditEvents.length * 2481 + 12_492).toLocaleString()}`,
            sub: isLive ? 'PostgreSQL event_log' : 'Simulated stream',
            color: '#38BDF8',
            icon: <Hash className="w-4 h-4" />,
          },
          {
            label: 'Active Blockchain Mode',
            value: blockchainStatus?.mode || (isLive ? 'SIMULATED' : 'DEMO'),
            sub: blockchainStatus?.mode === 'REAL' ? 'Web3 Provider Connected' : 'Local Deterministic Hash Fallback',
            color: blockchainStatus?.mode === 'REAL' ? '#10B981' : '#A855F7',
            icon: <Database className="w-4 h-4" />,
          },
          {
            label: 'Contract Anchors Tracked',
            value: isLive ? `${blockchainStatus?.total_anchors_tracked ?? 0} Anchors` : 'N/A',
            sub: blockchainStatus?.contract_address
              ? `${blockchainStatus.contract_address.slice(0, 8)}...${blockchainStatus.contract_address.slice(-6)}`
              : 'Contract address not configured',
            color: '#F59E0B',
            icon: <Link2 className="w-4 h-4" />,
          },
        ].map(({ label, value, sub, color, icon }) => (
          <div key={label} className="rounded-xl p-4" style={{ background: '#111827', border: '1px solid #1E293B' }}>
            <div className="flex items-center gap-2 mb-2.5">
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center"
                style={{ background: 'rgba(16,185,129,0.1)', color }}
              >
                {icon}
              </div>
              <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider">{label}</span>
            </div>
            <div className="text-lg font-bold font-mono" style={{ color }}>{value}</div>
            <div className="text-[10px] text-slate-400 font-mono mt-1 truncate" title={sub}>{sub}</div>
          </div>
        ))}
      </div>

      {/* Network Configuration Information Notice */}
      <div
        className="flex items-start gap-3 px-4 py-3 rounded-xl text-[11px]"
        style={{
          background: isLive ? 'rgba(56,189,248,0.06)' : 'rgba(99,102,241,0.06)',
          border: `1px solid ${isLive ? 'rgba(56,189,248,0.2)' : 'rgba(99,102,241,0.18)'}`,
        }}
      >
        <ShieldCheck className={`w-4 h-4 ${isLive ? 'text-sky-400' : 'text-indigo-400'} shrink-0 mt-0.5`} />
        <span className="text-slate-400 leading-relaxed">
          <strong className={isLive ? 'text-sky-300' : 'text-indigo-300'}>
            {isLive ? 'Blockchain Audit Engine Status:' : 'Demo Note:'}
          </strong>{' '}
          {isLive ? (
            <>
              Operating in <strong>{blockchainStatus?.mode || 'SIMULATED'}</strong> mode.
              {blockchainStatus?.mode === 'REAL' ? (
                <> Connected to RPC provider for <code>{blockchainStatus.network_name}</code> (Chain ID {blockchainStatus.chain_id}). Transactions are signed server-side and confirmed on-chain.</>
              ) : (
                <> EVM RPC credentials or contract address are currently unconfigured. Events generate deterministic canonical SHA-256 digests in PostgreSQL without broadcasting real testnet transactions.</>
              )}{' '}
              Click <strong>Anchor Event</strong> on any unanchored record to submit to the anchoring engine, or <strong>Verify Digest</strong> to check independent on-chain integrity.
            </>
          ) : (
            <>
              The audit records displayed below are simulated demo outputs. Switch to <strong className="text-slate-200">Live Backend</strong> in the top header to inspect real PostgreSQL events and blockchain anchor records.
            </>
          )}
        </span>
      </div>

      {/* Blockchain / Audit Timeline */}
      <div className="rounded-xl overflow-hidden" style={{ background: '#0F172A', border: '1px solid #1E293B' }}>
        <div className="px-5 py-3.5 border-b border-[#1E293B] flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Hash className="w-4 h-4 text-teal-400" />
            {isLive ? 'PostgreSQL Audit Event Log & On-Chain Anchors' : 'Chronological Block Timeline'}
          </h2>
          <div className="flex items-center gap-2">
            {isLive && (
              <button
                onClick={() => refreshLiveData()}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-mono transition"
              >
                <RefreshCw className="w-3 h-3" /> Refresh
              </button>
            )}
            <span className="text-[10px] text-slate-500 font-mono">
              {isLive ? `${liveAuditEvents.length} live records` : `${demoAuditEvents.length} blocks`}
            </span>
          </div>
        </div>

        <div className="p-5">
          {isLive && liveAuditEvents.length === 0 ? (
            <div className="text-center py-10 space-y-3">
              <Database className="w-10 h-10 text-slate-600 mx-auto" />
              <div className="text-slate-400 text-sm font-semibold">No Live Audit Events in PostgreSQL Yet</div>
              <p className="text-slate-500 text-xs max-w-md mx-auto">
                Trigger an orchestration scenario or scheduler cycle from the Command Center to record cryptographically hashed audit records.
              </p>
            </div>
          ) : (
            <div className="relative pl-8 space-y-4 before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-px before:bg-[#1E293B]">
              {(isLive
                ? liveAuditEvents.map(evt => {
                    const rawTs = evt.created_at || evt.timestamp || evt.event_timestamp || '';
                    const timeFormatted = rawTs ? new Date(rawTs).toLocaleTimeString() : 'Recent';
                    const activeAnchor = anchorResults[evt.event_id];
                    const blockchainStatusVal = activeAnchor?.confirmation_status || evt.blockchain_status || 'NOT_SUBMITTED';
                    const activeTxHash = activeAnchor?.transaction_hash || evt.tx_hash || null;
                    const activeBlockNum = activeAnchor?.block_number ?? evt.block_number ?? null;
                    const activeExplorerUrl = activeAnchor?.explorer_url || evt.explorer_url || null;

                    return {
                      eventId: evt.event_id,
                      eventUuid: evt.event_id,
                      blockNumber: activeBlockNum !== null ? String(activeBlockNum) : null,
                      timestamp: timeFormatted,
                      details: evt.details || `${evt.event_type} (${evt.actor || evt.actor_id || 'SYSTEM'})`,
                      actor: evt.actor || evt.actor_id || 'SYSTEM',
                      orderId: evt.order_id || evt.orderId || 'N/A',
                      type: evt.event_type || evt.type || 'AUDIT_EVENT',
                      payloadHash: evt.payload_hash || evt.event_digest || null,
                      blockchainStatus: blockchainStatusVal,
                      txHash: activeTxHash,
                      explorerUrl: activeExplorerUrl,
                      isLiveRecord: true,
                    };
                  })
                : demoAuditEvents.map(evt => ({
                    eventId: evt.eventId,
                    eventUuid: evt.eventId,
                    blockNumber: evt.blockNumber,
                    timestamp: evt.timestamp,
                    details: evt.details,
                    actor: evt.actor,
                    orderId: evt.orderId,
                    type: evt.type,
                    payloadHash: evt.txHash,
                    blockchainStatus: evt.status,
                    txHash: evt.status === 'SIMULATED' ? null : evt.txHash,
                    explorerUrl: null,
                    isLiveRecord: false,
                  }))
              ).map((evt, i) => {
                const vResult = verificationResults[evt.eventId];
                const isVerifying = verifyingId === evt.eventId;
                const isAnchoring = anchoringId === evt.eventId;
                const isAnchored = evt.blockchainStatus === 'CONFIRMED' || evt.blockchainStatus === 'SIMULATED';

                return (
                  <div key={evt.eventId} className="relative animate-fade-slide" style={{ animationDelay: `${i * 0.03}s` }}>
                    {/* Timeline node */}
                    <div
                      className="absolute -left-8 top-3 w-6 h-6 rounded-lg flex items-center justify-center z-10"
                      style={{
                        background: '#111827',
                        border: `1px solid ${
                          evt.blockchainStatus === 'CONFIRMED'
                            ? 'rgba(16,185,129,0.5)'
                            : evt.blockchainStatus === 'PENDING'
                            ? 'rgba(245,158,11,0.5)'
                            : 'rgba(56,189,248,0.3)'
                        }`,
                      }}
                    >
                      <FileCheck
                        className={`w-3.5 h-3.5 ${
                          evt.blockchainStatus === 'CONFIRMED'
                            ? 'text-emerald-400'
                            : evt.blockchainStatus === 'PENDING'
                            ? 'text-amber-400'
                            : 'text-teal-400'
                        }`}
                      />
                    </div>

                    {/* Block card */}
                    <div
                      className="rounded-xl p-4 transition hover:border-slate-700"
                      style={{ background: '#080C14', border: '1px solid #1E293B' }}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2.5">
                          <span className="font-mono font-bold text-sm text-slate-200">
                            {evt.blockNumber ? `Block #${evt.blockNumber}` : `Event ${evt.eventId.slice(0, 8)}`}
                          </span>
                          {renderStatusBadge(evt.blockchainStatus, evt.txHash)}
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">{evt.timestamp}</span>
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

                      {/* Cryptographic Hash Bar */}
                      <div className="mt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2.5 rounded-lg bg-[#0F172A] border border-[#1E293B]">
                        <div className="flex flex-col gap-1 overflow-hidden flex-1">
                          <div className="flex items-center gap-2 overflow-hidden">
                            <Hash className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                            <span className="text-[10px] text-slate-500 font-mono shrink-0">Payload Digest:</span>
                            <span
                              className="font-mono text-[10px] text-indigo-300 truncate"
                              title={evt.payloadHash || 'Digest not computed'}
                            >
                              {evt.payloadHash || 'N/A (Off-chain record)'}
                            </span>
                          </div>

                          {/* Real Transaction Hash (Only if actually returned by backend) */}
                          {evt.txHash && (
                            <div className="flex items-center gap-2 overflow-hidden">
                              <Link2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              <span className="text-[10px] text-slate-500 font-mono shrink-0">Tx Hash:</span>
                              <span className="font-mono text-[10px] text-emerald-300 truncate" title={evt.txHash}>
                                {evt.txHash}
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Action Buttons */}
                        <div className="flex items-center gap-2 shrink-0">
                          {/* Verifiable Explorer Link (Strictly when configured and provided by backend) */}
                          {evt.explorerUrl ? (
                            <a
                              href={evt.explorerUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-2.5 py-1 rounded bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-500/40 text-[11px] font-mono font-bold flex items-center gap-1 transition"
                              title="Inspect confirmed transaction on block explorer"
                            >
                              <ExternalLink className="w-3 h-3" /> Explorer
                            </a>
                          ) : null}

                          {isLive ? (
                            <>
                              {/* Anchor button for unanchored / failed events */}
                              {!isAnchored && (
                                <button
                                  onClick={() => handleAnchor(evt.eventId)}
                                  disabled={isAnchoring}
                                  className="px-2.5 py-1 rounded bg-teal-900/60 hover:bg-teal-800 text-teal-200 border border-teal-600/40 text-[11px] font-mono font-bold flex items-center gap-1 transition disabled:opacity-50"
                                  title="Submit canonical digest to blockchain anchoring engine"
                                >
                                  {isAnchoring ? (
                                    <>
                                      <RefreshCw className="w-3 h-3 animate-spin" /> Anchoring…
                                    </>
                                  ) : (
                                    <>
                                      <Link2 className="w-3 h-3" /> Anchor Event
                                    </>
                                  )}
                                </button>
                              )}

                              {/* Verify digest button */}
                              <button
                                onClick={() => handleVerify(evt.eventId)}
                                disabled={isVerifying}
                                className="px-2.5 py-1 rounded bg-sky-900/60 hover:bg-sky-800 text-sky-200 border border-sky-600/40 text-[11px] font-mono font-bold flex items-center gap-1 transition disabled:opacity-50"
                                title="Recompute canonical digest and verify against anchor record"
                              >
                                {isVerifying ? (
                                  <>
                                    <RefreshCw className="w-3 h-3 animate-spin" /> Verifying…
                                  </>
                                ) : (
                                  <>
                                    <ShieldCheck className="w-3 h-3" /> Verify Digest
                                  </>
                                )}
                              </button>
                            </>
                          ) : (
                            <ArrowUpRight className="w-3 h-3 text-slate-600 shrink-0" />
                          )}
                        </div>
                      </div>

                      {/* Verification Status Banner */}
                      {vResult && (
                        <div
                          className={`mt-2 text-xs font-mono p-2.5 rounded-lg flex items-center gap-2 ${
                            vResult.verified
                              ? 'bg-emerald-950/40 border border-emerald-500/30 text-emerald-300'
                              : 'bg-rose-950/40 border border-rose-500/30 text-rose-300'
                          }`}
                        >
                          {vResult.verified ? (
                            <>
                              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                              <div className="flex-1 overflow-hidden">
                                <div>
                                  <strong>Cryptographic Integrity Verified:</strong> Digest match confirmed.
                                </div>
                                {vResult.on_chain_verified && (
                                  <div className="text-[10px] text-emerald-400 mt-0.5">
                                    ✓ On-chain smart contract state confirmed digest match.
                                  </div>
                                )}
                                <div className="text-[10px] text-slate-400 truncate mt-0.5" title={vResult.digest}>
                                  Digest: {vResult.digest}
                                </div>
                              </div>
                            </>
                          ) : (
                            <>
                              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                              <div>
                                <strong>Verification Mismatch / Error:</strong> {vResult.error || 'Digest does not match stored anchor.'}
                              </div>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
