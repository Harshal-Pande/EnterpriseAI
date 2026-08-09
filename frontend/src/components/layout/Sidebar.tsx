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
  Shield,
  HelpCircle,
  Settings,
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

interface NavItem {
  id: ScreenId;
  label: string;
  icon: React.ReactNode;
  badge?: string | number;
  badgeColor?: 'cyan' | 'amber' | 'rose';
}

export const Sidebar: React.FC<SidebarProps> = ({ currentScreen, onNavigate }) => {
  const { isSimulating, agents, orders } = useDemo();
  const [showAboutModal, setShowAboutModal] = useState(false);

  const busyAgentCount = agents.filter(a => a.status === 'BUSY').length;
  const exceptionCount = orders.filter(o => o.status === 'Exception').length;

  const navItems: NavItem[] = [
    { id: 'overview',    label: 'Overview',        icon: <LayoutDashboard className="w-[15px] h-[15px]" /> },
    { id: 'orders',      label: 'Orders',           icon: <ShoppingBag className="w-[15px] h-[15px]" /> },
    {
      id: 'mesh',
      label: 'Agent Mesh',
      icon: <Cpu className="w-[15px] h-[15px]" />,
      badge: isSimulating ? busyAgentCount || undefined : undefined,
      badgeColor: 'cyan'
    },
    { id: 'inventory',   label: 'Inventory',        icon: <Package className="w-[15px] h-[15px]" /> },
    { id: 'procurement', label: 'Procurement',       icon: <Scale className="w-[15px] h-[15px]" /> },
    { id: 'finance',     label: 'Finance',           icon: <CircleDollarSign className="w-[15px] h-[15px]" /> },
    { id: 'logistics',   label: 'Logistics',         icon: <Truck className="w-[15px] h-[15px]" /> },
    { id: 'graph',       label: 'Knowledge Graph',   icon: <Share2 className="w-[15px] h-[15px]" /> },
    { id: 'audit',       label: 'Audit Trail',       icon: <ShieldCheck className="w-[15px] h-[15px]" /> },
    {
      id: 'exceptions',
      label: 'Exceptions',
      icon: <AlertTriangle className="w-[15px] h-[15px]" />,
      badge: exceptionCount > 0 ? exceptionCount : undefined,
      badgeColor: 'rose'
    },
    { id: 'benchmarks',  label: 'Benchmarks',        icon: <BarChart3 className="w-[15px] h-[15px]" /> },
  ];

  const badgeClass = {
    cyan:  'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
    amber: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    rose:  'bg-rose-500/15 text-rose-300 border-rose-500/30',
  };

  return (
    <>
      <aside
        className="w-[228px] shrink-0 flex flex-col h-screen sticky top-0 z-30 select-none"
        style={{
          background: '#07090F',
          borderRight: '1px solid #1A2438'
        }}
      >
        {/* ── Brand Header ── */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-[#1A2438]">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{
              background: 'linear-gradient(135deg, #1A2A44 0%, #0F1D33 100%)',
              border: '1px solid rgba(56,189,248,0.25)',
              boxShadow: '0 0 12px rgba(56,189,248,0.08)'
            }}
          >
            <Layers className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <div className="text-[13px] font-bold text-white tracking-tight leading-none">
              Core Mesh
            </div>
            <div className="text-[10px] text-slate-500 font-mono mt-0.5">
              v2.4.0-stable
            </div>
          </div>
        </div>

        {/* ── Nav Section Label ── */}
        <div className="px-4 pt-4 pb-1.5">
          <span className="text-[9px] font-bold font-mono text-slate-600 uppercase tracking-[0.12em]">
            Operations
          </span>
        </div>

        {/* ── Navigation Items ── */}
        <nav className="flex-1 px-2 space-y-0.5 overflow-y-auto pb-2">
          {navItems.map((item) => {
            const isActive = currentScreen === item.id;
            return (
              <button
                key={item.id}
                id={`nav-${item.id}`}
                onClick={() => onNavigate(item.id)}
                className={`
                  w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-[12.5px] font-medium
                  transition-all duration-100 group
                  ${isActive
                    ? 'text-white'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                  }
                `}
                style={isActive ? {
                  background: 'rgba(56,189,248,0.08)',
                  borderLeft: '2px solid #38BDF8',
                  paddingLeft: '10px',
                  color: '#E2F8FF'
                } : { borderLeft: '2px solid transparent' }}
              >
                <span className="flex items-center gap-2.5">
                  <span className={isActive ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-400 transition-colors'}>
                    {item.icon}
                  </span>
                  {item.label}
                </span>

                {item.badge !== undefined && (
                  <span className={`px-1.5 py-0.5 text-[9px] font-mono font-bold border rounded leading-none ${
                    badgeClass[item.badgeColor ?? 'cyan']
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* ── System Status Indicator ── */}
        {isSimulating && (
          <div className="mx-3 mb-2 px-3 py-2 rounded-lg border border-cyan-500/20 bg-cyan-500/5">
            <div className="flex items-center gap-2 text-[10px] font-mono text-cyan-400">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping shrink-0"></span>
              Simulation Active
            </div>
            <div className="text-[9px] text-slate-500 mt-0.5 font-mono">
              Multi-agent workflow running
            </div>
          </div>
        )}

        {/* ── Footer Links ── */}
        <div className="border-t border-[#1A2438] px-2 py-3 space-y-0.5">
          <button
            onClick={() => setShowAboutModal(true)}
            id="nav-security"
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[12px] text-slate-500 hover:text-slate-300 hover:bg-white/[0.04] transition-all"
          >
            <Shield className="w-[14px] h-[14px]" />
            <span>Security</span>
          </button>
          <button
            onClick={() => setShowAboutModal(true)}
            id="nav-support"
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[12px] text-slate-500 hover:text-slate-300 hover:bg-white/[0.04] transition-all"
          >
            <HelpCircle className="w-[14px] h-[14px]" />
            <span>Support & Docs</span>
          </button>
        </div>
      </aside>

      {/* ── System Info Modal ── */}
      {showAboutModal && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)' }}
        >
          <div
            className="w-full max-w-md rounded-xl shadow-2xl text-slate-200"
            style={{ background: '#0F172A', border: '1px solid #24334D' }}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-[#24334D]">
              <div className="flex items-center gap-2.5">
                <Settings className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">System Configuration</h3>
              </div>
              <button
                onClick={() => setShowAboutModal(false)}
                className="text-slate-500 hover:text-white transition p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              {[
                { label: 'Architecture Environment', value: 'Core Mesh Operations Console v2.4.0-stable', color: 'text-cyan-400' },
                { label: 'Audit Ledger', value: 'Polygon Testnet — Layer-2 Anchor (Prototype)', color: 'text-teal-400' },
                { label: 'Knowledge Graph Engine', value: 'Neo4j Cypher — Dependency Layer (Planned)', color: 'text-indigo-400' },
                { label: 'Database', value: 'PostgreSQL + pgvector (FastAPI Backend Planned)', color: 'text-purple-400' },
                { label: 'Multi-Agent Framework', value: 'LangGraph Orchestration Layer (Planned)', color: 'text-emerald-400' },
              ].map(({ label, value, color }) => (
                <div key={label}>
                  <div className="text-slate-500 mb-1 font-mono text-[10px] uppercase tracking-wider">{label}</div>
                  <div className={`font-mono ${color} bg-[#080C14] border border-[#1E293B] rounded px-3 py-2`}>
                    {value}
                  </div>
                </div>
              ))}

              <div className="pt-2 flex justify-end">
                <button
                  onClick={() => setShowAboutModal(false)}
                  className="px-4 py-2 bg-[#1E293B] hover:bg-[#253348] text-white text-xs rounded-lg font-medium transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
