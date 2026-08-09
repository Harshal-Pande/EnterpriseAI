import React, { useState } from 'react';
import {
  LayoutDashboard,
  ShoppingBag,
  Cpu,
  Package,
  Scale,
  CircleDollarSign,
  Truck,
  Share2,
  ShieldCheck,
  AlertTriangle,
  BarChart3,
  Settings,
  X
} from 'lucide-react';
import { useDemo } from '../../state/DemoContext';

export type ScreenId =
  | 'overview'
  | 'orders'
  | 'mesh'
  | 'inventory'
  | 'procurement'
  | 'finance'
  | 'logistics'
  | 'graph'
  | 'audit'
  | 'exceptions'
  | 'benchmarks';

interface SidebarProps {
  currentScreen: ScreenId;
  onNavigate: (screen: ScreenId) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentScreen, onNavigate }) => {
  const { isSimulating } = useDemo();
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  const navItems: { id: ScreenId; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'orders', label: 'Orders', icon: <ShoppingBag className="w-4 h-4" /> },
    { id: 'mesh', label: 'Agent Mesh', icon: <Cpu className="w-4 h-4" />, badge: isSimulating ? 'Active' : undefined },
    { id: 'inventory', label: 'Inventory', icon: <Package className="w-4 h-4" /> },
    { id: 'procurement', label: 'Procurement', icon: <Scale className="w-4 h-4" /> },
    { id: 'finance', label: 'Finance', icon: <CircleDollarSign className="w-4 h-4" /> },
    { id: 'logistics', label: 'Logistics', icon: <Truck className="w-4 h-4" /> },
    { id: 'graph', label: 'Knowledge Graph', icon: <Share2 className="w-4 h-4" /> },
    { id: 'audit', label: 'Audit Trail', icon: <ShieldCheck className="w-4 h-4" /> },
    { id: 'exceptions', label: 'Exceptions', icon: <AlertTriangle className="w-4 h-4" /> },
    { id: 'benchmarks', label: 'Benchmarks', icon: <BarChart3 className="w-4 h-4" /> },
  ];

  return (
    <>
      <aside className="w-60 bg-[#0B111E] border-r border-[#1E293B] flex flex-col justify-between select-none h-screen sticky top-0 z-30">
        <div>
          {/* Header Branding */}
          <div className="p-4 border-b border-[#1E293B] flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="font-bold text-sm text-white tracking-wide flex items-center gap-1.5">
                ENTERPRISE <span className="text-cyan-400">AI</span>
              </div>
              <div className="text-[10px] text-slate-400 font-mono uppercase tracking-wider">
                HYBRID MESH v2.4
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-2 space-y-0.5 overflow-y-auto max-h-[calc(100vh-220px)]">
            <div className="px-3 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              Command Modules
            </div>
            {navItems.map(item => {
              const isActive = currentScreen === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <span className={isActive ? 'text-blue-400' : 'text-slate-400'}>{item.icon}</span>
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="px-1.5 py-0.5 text-[9px] bg-blue-500/20 text-blue-300 font-mono rounded animate-pulse">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Footer User & System Status */}
        <div className="p-3 border-t border-[#1E293B] bg-[#080D1A] space-y-2 text-xs">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-[11px] font-medium text-slate-300">Mesh Status: ONLINE</span>
            </div>
            <button
              onClick={() => setShowSettingsModal(true)}
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition"
              title="Settings"
            >
              <Settings className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center gap-2.5 p-2 bg-[#121A2D] rounded-lg border border-[#1E2A40]">
            <div className="w-7 h-7 rounded-full bg-indigo-600/30 text-indigo-300 flex items-center justify-center border border-indigo-500/30 font-semibold text-xs">
              AS
            </div>
            <div className="overflow-hidden">
              <div className="font-semibold text-slate-200 text-[11px] truncate">Dr. A. Sharma</div>
              <div className="text-[10px] text-slate-400 truncate">Lead Examiner / Admin</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Quick Settings Modal */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#121929] border border-[#24334D] rounded-xl w-full max-w-md p-5 text-slate-200 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#24334D] pb-3">
              <div className="flex items-center gap-2">
                <Settings className="w-5 h-5 text-blue-400" />
                <h3 className="font-bold text-base text-white">System Configuration</h3>
              </div>
              <button
                onClick={() => setShowSettingsModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Architecture Environment</label>
                <div className="p-2 bg-[#0A0E1A] rounded border border-slate-700 font-mono text-cyan-400">
                  Hybrid Multi-Agent Mesh v2.4 (Simulated Prototype)
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Audit Ledger Protocol</label>
                <div className="p-2 bg-[#0A0E1A] rounded border border-slate-700 font-mono text-emerald-400">
                  Polygon Smart Contract Ready (Chain ID: 137)
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Vector Store / RAG Engine</label>
                <div className="p-2 bg-[#0A0E1A] rounded border border-slate-700 font-mono text-indigo-400">
                  PostgreSQL / pgvector + Neo4j Knowledge Graph
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setShowSettingsModal(false)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg text-xs"
              >
                Close Settings
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
