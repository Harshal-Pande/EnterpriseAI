import React from 'react';
import { ShoppingBag, Play, CheckCircle2, Clock, MapPin, DollarSign, Package } from 'lucide-react';
import { useDemo } from '../../state/DemoContext';
import { StatusBadge } from '../common/StatusBadge';

export const LiveOrderPanel: React.FC = () => {
  const { activeOrder, workflowStage, isSimulating, runDemoOrder } = useDemo();

  const steps = [
    { id: 'RECEIVED', label: 'Order Received' },
    { id: 'SUPERVISOR_ANALYSIS', label: 'Supervisor Analysis' },
    { id: 'INVENTORY_CHECK', label: 'Inventory Check' },
    { id: 'PROCUREMENT_NEGOTIATION', label: 'Procurement Negotiation' },
    { id: 'FINANCE_VALIDATION', label: 'Finance Validation' },
    { id: 'LOGISTICS_FEASIBILITY', label: 'Logistics Feasibility' },
    { id: 'SUPERVISOR_DECISION', label: 'Supervisor Decision' },
    { id: 'COMPLETED', label: 'Order Approved & Audited' },
  ];

  const getStepStatus = (stepId: string) => {
    const stageOrder = steps.map(s => s.id);
    const currentIndex = stageOrder.indexOf(workflowStage);
    const stepIndex = stageOrder.indexOf(stepId);

    if (workflowStage === 'COMPLETED' || activeOrder.status === 'Approved') return 'completed';
    if (currentIndex === stepIndex) return 'active';
    if (currentIndex > stepIndex) return 'completed';
    return 'pending';
  };

  return (
    <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-5 shadow-xl flex flex-col justify-between">
      <div>
        {/* Panel Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#24334D]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600/20 text-blue-400 flex items-center justify-center border border-blue-500/30">
              <ShoppingBag className="w-4.5 h-4.5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-base text-white">{activeOrder.id}</h3>
                <StatusBadge status={activeOrder.status} />
              </div>
              <p className="text-[11px] text-slate-400 font-medium truncate max-w-[240px]">
                {activeOrder.customer}
              </p>
            </div>
          </div>
          <button
            onClick={() => runDemoOrder()}
            disabled={isSimulating}
            className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-md transition"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            {isSimulating ? 'Processing...' : 'Run Demo Order'}
          </button>
        </div>

        {/* Order Meta Cards Grid */}
        <div className="grid grid-cols-2 gap-3 my-4">
          <div className="bg-[#0D1424] p-3 rounded-xl border border-[#1E2C44]">
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-1">
              <Package className="w-3 h-3 text-cyan-400" /> Product & Qty
            </div>
            <div className="font-semibold text-xs text-white truncate">{activeOrder.product}</div>
            <div className="text-[11px] text-cyan-400 font-mono font-medium">{activeOrder.quantity} Units</div>
          </div>

          <div className="bg-[#0D1424] p-3 rounded-xl border border-[#1E2C44]">
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-1">
              <MapPin className="w-3 h-3 text-emerald-400" /> Destination
            </div>
            <div className="font-semibold text-xs text-white truncate">{activeOrder.destination}</div>
            <div className="text-[11px] text-slate-400 font-mono">Central Freight Hub</div>
          </div>

          <div className="bg-[#0D1424] p-3 rounded-xl border border-[#1E2C44]">
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-1">
              <DollarSign className="w-3 h-3 text-pink-400" /> Allocated Budget
            </div>
            <div className="font-bold text-xs text-white font-mono">₹{activeOrder.budget.toLocaleString()}</div>
            <div className="text-[10px] text-emerald-400">Est. Quote: ₹{activeOrder.estimatedCost.toLocaleString()}</div>
          </div>

          <div className="bg-[#0D1424] p-3 rounded-xl border border-[#1E2C44]">
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-1">
              <Clock className="w-3 h-3 text-amber-400" /> Created & Priority
            </div>
            <div className="font-semibold text-xs text-white">{activeOrder.priority} Priority</div>
            <div className="text-[10px] text-slate-400 font-mono">{activeOrder.createdAt.split(' ')[1]}</div>
          </div>
        </div>

        {/* Dynamic Workflow Stage Stepper */}
        <div className="space-y-2 mt-2">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Deterministic Agent Workflow Progression
          </div>
          <div className="space-y-1.5">
            {steps.map((step, idx) => {
              const status = getStepStatus(step.id);
              return (
                <div
                  key={step.id}
                  className={`flex items-center justify-between p-2 rounded-lg text-xs transition-all duration-200 border ${
                    status === 'active'
                      ? 'bg-blue-600/15 border-blue-500/50 text-white font-medium shadow'
                      : status === 'completed'
                      ? 'bg-[#0E1B2B] border-emerald-500/20 text-slate-300'
                      : 'bg-[#0A0F1D] border-transparent text-slate-400 opacity-60'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                        status === 'completed'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : status === 'active'
                          ? 'bg-blue-500/30 text-blue-300 animate-pulse'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {status === 'completed' ? <CheckCircle2 className="w-3.5 h-3.5" /> : idx + 1}
                    </div>
                    <span>{step.label}</span>
                  </div>
                  {status === 'active' && (
                    <span className="text-[10px] font-mono text-cyan-400 animate-pulse">Processing...</span>
                  )}
                  {status === 'completed' && (
                    <span className="text-[10px] font-mono text-emerald-400">PASSED</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
