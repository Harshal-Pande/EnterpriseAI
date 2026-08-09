import React from 'react';
import { Truck, MapPin, Navigation, Clock, CheckCircle2, AlertTriangle } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { StatusBadge } from '../components/common/StatusBadge';

export const LogisticsPage: React.FC = () => {
  const { activeOrder, agents, workflowStage, activeScenario } = useDemo();

  const logisticsAgent = agents.find(a => a.id === 'logistics');
  const hasDelay = activeScenario === 'delivery_delay' || activeScenario === 'multi_exception';
  const isRoutingStage = workflowStage === 'LOGISTICS_FEASIBILITY';

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="pb-5 border-b border-[#1E293B]">
        <h1 className="text-2xl font-extrabold text-white tracking-tight">Logistics Route Feasibility</h1>
        <p className="text-sm text-slate-500 mt-1">
          Autonomous freight route optimization, weather corridor analysis, and carrier SLA validation
        </p>
      </div>

      {/* Delay Exception Banner */}
      {hasDelay && (
        <div
          className="flex items-center gap-4 px-5 py-4 rounded-xl animate-fade-slide"
          style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)' }}
        >
          <AlertTriangle className="w-5 h-5 text-amber-400 animate-pulse shrink-0" />
          <div>
            <div className="text-[11px] font-bold text-amber-300 uppercase tracking-wider">
              ⚡ EXCEPTION DETECTED — DELIVERY DELAY ON NH-53
            </div>
            <div className="text-[11px] text-slate-300 mt-0.5">
              Heavy rainfall alert on Pune-Nagpur Highway. Standard road transit delayed <strong>+48h</strong>.
              Logistics Agent rerouting to Express Rail Cargo.
            </div>
          </div>
          <span
            className="ml-auto shrink-0 px-3 py-1 rounded-full text-[10px] font-mono font-bold"
            style={{ background: 'rgba(245,158,11,0.15)', color: '#FCD34D', border: '1px solid rgba(245,158,11,0.3)' }}
          >
            REROUTING
          </span>
        </div>
      )}

      {/* Active Stage Indicator */}
      {isRoutingStage && (
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-xl"
          style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.25)' }}
        >
          <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping shrink-0" />
          <span className="text-[11px] font-bold text-purple-300 font-mono uppercase tracking-wider">
            Logistics Agent Active — Evaluating Transit Corridor
          </span>
        </div>
      )}

      {/* Corridor Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'Origin Hub',
            value: 'Bharat Heavy (Pune)',
            icon:  <MapPin className="w-4 h-4" />,
            color: '#F59E0B',
            iconBg:'rgba(245,158,11,0.1)'
          },
          {
            label: 'Destination',
            value: activeOrder.destination,
            icon:  <Navigation className="w-4 h-4" />,
            color: '#10B981',
            iconBg:'rgba(16,185,129,0.1)'
          },
          {
            label: 'Transit Time',
            value: hasDelay ? '4 Days (Rerouted)' : '2 Business Days',
            icon:  <Clock className="w-4 h-4" />,
            color: hasDelay ? '#F59E0B' : '#38BDF8',
            iconBg: hasDelay ? 'rgba(245,158,11,0.1)' : 'rgba(56,189,248,0.1)'
          },
          {
            label: 'Route Feasibility',
            value: hasDelay ? 'REROUTED' : 'APPROVED',
            icon:  hasDelay ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />,
            color: hasDelay ? '#F59E0B' : '#10B981',
            iconBg: hasDelay ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)'
          },
        ].map(({ label, value, icon, color, iconBg }) => (
          <div key={label} className="rounded-xl p-4" style={{ background: '#111827', border: '1px solid #1E293B' }}>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: iconBg, color }}>
                {icon}
              </div>
              <span className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-wider">{label}</span>
            </div>
            <div className="text-sm font-bold" style={{ color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Corridor Summary Card */}
      <div className="rounded-xl overflow-hidden" style={{ background: '#0F172A', border: '1px solid rgba(139,92,246,0.2)' }}>
        <div
          className="flex items-center justify-between px-5 py-4 border-b"
          style={{ borderColor: 'rgba(139,92,246,0.15)', background: 'rgba(139,92,246,0.05)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.25)' }}
            >
              <Truck className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <div className="text-sm font-bold text-white">Transit Corridor Feasibility Report</div>
              <div className="text-[11px] text-slate-400">Order: {activeOrder.id}</div>
            </div>
          </div>
          <StatusBadge status={hasDelay ? 'REROUTED' : 'APPROVED'} />
        </div>

        {/* Carrier Options */}
        <div className="p-5 space-y-3">
          <div className="text-[10px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-3">
            Carrier Options & SLA Matrix
          </div>

          {/* Option 1 */}
          <div
            className="flex items-center justify-between p-4 rounded-xl"
            style={{
              background: hasDelay ? '#080C14' : 'rgba(16,185,129,0.05)',
              border: `1px solid ${hasDelay ? '#1E293B' : 'rgba(16,185,129,0.2)'}`,
              opacity: hasDelay ? 0.5 : 1
            }}
          >
            <div className="flex items-center gap-3">
              {!hasDelay && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />}
              {hasDelay && <span className="w-2 h-2 rounded-full bg-slate-600" />}
              <div>
                <div className="font-bold text-sm text-white">Option 1: Express Road Freight</div>
                <div className="text-[11px] text-slate-400 font-mono">
                  BlueDart Industrial Cargo · 480 km (NH-53) · ₹28,000
                </div>
              </div>
            </div>
            <div className="text-right shrink-0">
              <div className={`font-bold font-mono text-sm ${hasDelay ? 'text-rose-400 line-through' : 'text-emerald-400'}`}>
                2 Days
              </div>
              <div className={`text-[10px] font-mono ${hasDelay ? 'text-rose-400' : 'text-emerald-400'}`}>
                {hasDelay ? 'DELAYED +48h' : 'SLA 99.2% · SELECTED'}
              </div>
            </div>
          </div>

          {/* Option 2 */}
          <div
            className="flex items-center justify-between p-4 rounded-xl"
            style={{
              background: hasDelay ? 'rgba(16,185,129,0.05)' : '#080C14',
              border: `1px solid ${hasDelay ? 'rgba(16,185,129,0.2)' : '#1E293B'}`
            }}
          >
            <div className="flex items-center gap-3">
              {hasDelay && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />}
              <div>
                <div className={`font-bold text-sm ${hasDelay ? 'text-white' : 'text-slate-400'}`}>
                  Option 2: Express Rail Freight {hasDelay && '⇒ REROUTED'}
                </div>
                <div className="text-[11px] text-slate-400 font-mono">
                  Indian Railways Container Corp · 510 km · ₹31,500
                </div>
              </div>
            </div>
            <div className="text-right shrink-0">
              <div className={`font-bold font-mono text-sm ${hasDelay ? 'text-emerald-400' : 'text-slate-500'}`}>
                {hasDelay ? '2 Days (On Track)' : '2 Days'}
              </div>
              <div className={`text-[10px] font-mono ${hasDelay ? 'text-emerald-400' : 'text-slate-600'}`}>
                {hasDelay ? 'SLA 96.5% · SELECTED' : 'AVAILABLE FALLBACK'}
              </div>
            </div>
          </div>
        </div>

        {/* Agent Rationale */}
        {logisticsAgent && (
          <div className="px-5 pb-5">
            <div
              className="rounded-xl p-4"
              style={{ background: 'rgba(139,92,246,0.05)', border: '1px solid rgba(139,92,246,0.18)' }}
            >
              <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-widest text-purple-400 mb-2">
                <Truck className="w-3 h-3" /> Logistics Agent Decision Rationale
              </div>
              <p className="text-[12px] text-slate-200 leading-relaxed">{logisticsAgent.rationale}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
