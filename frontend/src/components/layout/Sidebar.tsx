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
  Shield,
  HelpCircle,
  X,
  Layers
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
      <aside className="w-60 bg-[#090D16] border-r border-[#1B2638] flex flex-col justify-between select-none h-screen sticky top-0 z-30 font-sans">
        <div>
          {/* Header Branding matching Screenshot */}
          <div className="p-4 border-b border-[#1B2638] flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#141F33] border border-cyan-500/30 text-cyan-400 flex items-center justify-center shadow-lg shadow-cyan-500/10">
              <Layers className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <div className="font-bold text-sm text-slate-100 tracking-tight">
                Core Mesh
              </div>
              <div className="text-[10px] text-slate-400 font-mono">
                v2.4.0-stable
              </div>
            </div>
          </div>

          {/* Navigation Links matching Screenshot */}
          <nav className="p-3 space-y-1 overflow-y-auto max-h-[calc(100vh-220px)]">
            {navItems.map(item => {
              const isActive = currentScreen === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-[#152033] text-cyan-400 border-l-2 border-cyan-400 shadow-sm font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#101726]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={isActive ? 'text-cyan-400' : 'text-slate-400'}>{item.icon}</span>
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="px-1.5 py-0.5 text-[9px] bg-cyan-500/20 text-cyan-300 font-mono rounded animate-pulse">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Footer Security & Support links */}
        <div className="p-4 border-t border-[#1B2638] bg-[#070A12] space-y-2 text-xs">
          <button
            onClick={() => setShowSettingsModal(true)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-[#101726] transition text-left text-xs"
          >
            <Shield className="w-4 h-4 text-slate-400" />
            <span>Security</span>
          </button>
          <button
            onClick={() => setShowSettingsModal(true)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-[#101726] transition text-left text-xs"
          >
            <HelpCircle className="w-4 h-4 text-slate-400" />
            <span>Support</span>
          </button>
        </div>
      </aside>

      {/* Settings Modal */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#101726] border border-[#233148] rounded-xl w-full max-w-md p-5 text-slate-200 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#233148] pb-3">
              <div className="flex items-center gap-2">
                <Settings className="w-5 h-5 text-cyan-400" />
                <h3 className="font-bold text-base text-white">System Operations Configuration</h3>
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
                <div className="p-2 bg-[#090D16] rounded border border-[#1B2638] font-mono text-cyan-400">
                  Core Mesh Operations Console v2.4.0-stable
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Audit Ledger Protocol</label>
                <div className="p-2 bg-[#090D16] rounded border border-[#1B2638] font-mono text-emerald-400">
                  Polygon Mainnet / Testnet Layer-2 Anchor
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Database & Knowledge Graph</label>
                <div className="p-2 bg-[#090D16] rounded border border-[#1B2638] font-mono text-indigo-400">
                  PostgreSQL / pgvector + Neo4j Cypher Engine
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setShowSettingsModal(false)}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg text-xs"
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
