import React from 'react';
import { Truck, MapPin, Navigation, Clock, CheckCircle2 } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { StatusBadge } from '../components/common/StatusBadge';

export const LogisticsPage: React.FC = () => {
  const { activeOrder } = useDemo();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Truck className="w-5 h-5 text-purple-400" /> Logistics Agent Route Feasibility & Dispatch Engine
        </h2>
        <p className="text-xs text-slate-400">
          Autonomous freight route optimization, weather corridor simulation, and carrier SLA validation
        </p>
      </div>

      {/* Corridor Summary Card */}
      <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-5 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-[#24334D] pb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-600/20 text-purple-400 flex items-center justify-center border border-purple-500/30">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">Transit Corridor Feasibility Report</h3>
              <p className="text-xs text-slate-400">Order ID: {activeOrder.id}</p>
            </div>
          </div>
          <StatusBadge status="APPROVED" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
          <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
            <div className="text-slate-400 font-semibold mb-1 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-amber-400" /> Origin Warehouse
            </div>
            <div className="text-white font-bold">Bharat Heavy Solutions (Pune Hub)</div>
          </div>

          <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
            <div className="text-slate-400 font-semibold mb-1 flex items-center gap-1">
              <Navigation className="w-3.5 h-3.5 text-emerald-400" /> Destination Hub
            </div>
            <div className="text-white font-bold">{activeOrder.destination}</div>
          </div>

          <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
            <div className="text-slate-400 font-semibold mb-1 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-cyan-400" /> Estimated Transit Time
            </div>
            <div className="text-cyan-400 font-bold font-mono text-sm">2 Business Days (48h)</div>
          </div>

          <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
            <div className="text-slate-400 font-semibold mb-1">Route Status</div>
            <div className="text-emerald-400 font-bold font-mono flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" /> FEASIBLE & CLEAR
            </div>
          </div>
        </div>

        {/* Carrier Options Table */}
        <div className="space-y-2 pt-2">
          <div className="text-xs font-bold text-slate-300 uppercase tracking-wider text-[10px]">
            Carrier Options & Feasibility Matrix
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between p-3 bg-[#0B111E] rounded-xl border border-emerald-500/30 text-white font-medium">
              <div className="flex items-center gap-3">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
                <div>
                  <div className="font-bold">Option 1: Express Road Freight (Primary Choice)</div>
                  <div className="text-[11px] text-slate-400">Carrier: BlueDart Industrial Cargo | Distance: 480 km (NH-53)</div>
                </div>
              </div>
              <div className="text-right font-mono">
                <div className="text-emerald-400 font-bold">2 Days (SLA: 99.2%)</div>
                <div className="text-[10px] text-slate-400">SELECTED</div>
              </div>
            </div>

            <div className="flex items-center justify-between p-3 bg-[#0B111E] rounded-xl border border-[#1E293B] text-slate-300">
              <div>
                <div className="font-bold">Option 2: Dedicated Rail Express</div>
                <div className="text-[11px] text-slate-400">Carrier: Indian Railways Container Corp | Distance: 510 km</div>
              </div>
              <div className="text-right font-mono">
                <div className="text-cyan-400 font-bold">2 Days (SLA: 96.5%)</div>
                <div className="text-[10px] text-slate-400">AVAILABLE FALLBACK</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
