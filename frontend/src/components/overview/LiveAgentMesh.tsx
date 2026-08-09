import React from 'react';
import { Cpu, Package, Scale, CircleDollarSign, Truck } from 'lucide-react';
import { useDemo } from '../../state/DemoContext';
import type { AgentId } from '../../types';

// Per-agent visual config
const AGENT_CONFIG: Record<AgentId, {
  icon: React.ReactNode;
  color: string;        // text
  borderActive: string; // border when active
  glow: string;         // box-shadow glow when active
  label: string;
  taskLabel: (active: boolean) => string;
}> = {
  supervisor: {
    icon: <Cpu className="w-5 h-5" />,
    color: '#6366F1',
    borderActive: '#6366F1',
    glow: '0 0 20px rgba(99,102,241,0.25)',
    label: 'Supervisor Agent',
    taskLabel: a => a ? 'Orchestrating' : 'Orchestrator',
  },
  inventory: {
    icon: <Package className="w-4 h-4" />,
    color: '#10B981',
    borderActive: '#10B981',
    glow: '0 0 14px rgba(16,185,129,0.2)',
    label: 'Inventory Agent',
    taskLabel: a => a ? '● Evaluating Stock' : '● Monitoring',
  },
  procurement: {
    icon: <Scale className="w-4 h-4" />,
    color: '#F59E0B',
    borderActive: '#F59E0B',
    glow: '0 0 14px rgba(245,158,11,0.2)',
    label: 'Procurement Agent',
    taskLabel: a => a ? '● Sourcing Suppliers' : '● Idle',
  },
  finance: {
    icon: <CircleDollarSign className="w-4 h-4" />,
    color: '#EC4899',
    borderActive: '#EC4899',
    glow: '0 0 14px rgba(236,72,153,0.2)',
    label: 'Finance Agent',
    taskLabel: a => a ? '● Validating Budget' : '● Idle',
  },
  logistics: {
    icon: <Truck className="w-4 h-4" />,
    color: '#8B5CF6',
    borderActive: '#8B5CF6',
    glow: '0 0 14px rgba(139,92,246,0.2)',
    label: 'Logistics Agent',
    taskLabel: a => a ? '● Routing Freight' : '● Idle',
  },
};

interface AgentNodeProps {
  id: AgentId;
  isCenter?: boolean;
  isSelected: boolean;
  isActive: boolean;
  onClick: () => void;
}

const AgentNode: React.FC<AgentNodeProps> = ({ id, isCenter, isSelected, isActive, onClick }) => {
  const cfg = AGENT_CONFIG[id];
  const highlighted = isActive || isSelected;

  return (
    <div
      onClick={onClick}
      className="cursor-pointer transition-all duration-200 flex flex-col items-center gap-1 text-center select-none"
      style={{ userSelect: 'none' }}
    >
      <div
        className="flex flex-col items-center justify-center rounded-xl transition-all duration-200"
        style={{
          background: highlighted ? 'rgba(15,23,42,0.95)' : '#111827',
          border: `${isCenter ? '2px' : '1.5px'} solid ${highlighted ? cfg.borderActive : '#1E293B'}`,
          boxShadow: highlighted ? cfg.glow : 'none',
          padding: isCenter ? '14px 20px' : '10px 14px',
          minWidth: isCenter ? '150px' : '120px',
        }}
      >
        <span style={{ color: highlighted ? cfg.color : '#4B5563' }} className="transition-colors duration-200">
          {cfg.icon}
        </span>
        <div className="mt-1.5 font-bold text-white leading-tight" style={{ fontSize: isCenter ? '12px' : '11px' }}>
          {cfg.label}
        </div>
        <div
          className="mt-0.5 font-mono"
          style={{
            fontSize: '9px',
            color: isActive ? cfg.color : '#475569',
            transition: 'color 0.2s'
          }}
        >
          {cfg.taskLabel(isActive)}
        </div>
      </div>
    </div>
  );
};

export const LiveAgentMesh: React.FC = () => {
  const { agents, workflowStage, setSelectedAgentId, selectedAgentId } = useDemo();

  const getAgent = (id: AgentId) => agents.find(a => a.id === id);
  const supervisor  = getAgent('supervisor');
  const inventory   = getAgent('inventory');
  const procurement = getAgent('procurement');
  const finance     = getAgent('finance');
  const logistics   = getAgent('logistics');

  const lineColor = (active?: boolean, color?: string) =>
    active ? (color ?? '#38BDF8') : '#1E293B';

  return (
    <div
      className="relative flex flex-col rounded-xl overflow-hidden"
      style={{
        background: '#0B1020',
        border: '1px solid #1E293B',
        minHeight: '380px'
      }}
    >
      {/* Dot-grid background */}
      <div
        className="absolute inset-0 canvas-dot-grid opacity-40 pointer-events-none"
      />

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between px-5 py-3.5 border-b border-[#1E293B]">
        <h2 className="text-sm font-bold text-white">Live Agent Mesh</h2>
        <div className="flex items-center gap-2 text-[11px] font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-emerald-400">Network Synced</span>
        </div>
      </div>

      {/* SVG connections + HTML nodes */}
      <div className="relative z-10 flex-1 flex items-center justify-center py-4 px-4">
        {/* SVG connection lines */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Supervisor → Inventory */}
          <line x1="50%" y1="42%" x2="20%" y2="75%"
            stroke={lineColor(inventory?.active, '#10B981')}
            strokeWidth={inventory?.active ? '1.5' : '1'}
            className={inventory?.active ? 'animate-dash-flow' : ''}
            strokeDasharray={inventory?.active ? '5 5' : '0'}
          />
          {/* Supervisor → Procurement */}
          <line x1="50%" y1="42%" x2="80%" y2="75%"
            stroke={lineColor(procurement?.active, '#F59E0B')}
            strokeWidth={procurement?.active ? '1.5' : '1'}
            className={procurement?.active ? 'animate-dash-flow' : ''}
            strokeDasharray={procurement?.active ? '5 5' : '0'}
          />
          {/* Supervisor → Finance */}
          <line x1="50%" y1="42%" x2="50%" y2="78%"
            stroke={lineColor(finance?.active, '#EC4899')}
            strokeWidth={finance?.active ? '1.5' : '1'}
            className={finance?.active ? 'animate-dash-flow' : ''}
            strokeDasharray={finance?.active ? '5 5' : '0'}
          />
          {/* Procurement → Logistics */}
          <line x1="80%" y1="75%" x2="80%" y2="75%"
            stroke={lineColor(logistics?.active, '#8B5CF6')}
            strokeWidth="1"
          />
          {/* Supervisor ring */}
          <circle cx="50%" cy="42%" r="52"
            fill="none"
            stroke={supervisor?.active ? 'rgba(99,102,241,0.15)' : 'transparent'}
            strokeWidth="1"
            className={supervisor?.active ? 'animate-pulse' : ''}
          />
        </svg>

        {/* Node Grid Layout */}
        <div className="relative w-full max-w-xl" style={{ height: '260px' }}>
          {/* Supervisor — top center */}
          <div className="absolute" style={{ top: '0%', left: '50%', transform: 'translateX(-50%)' }}>
            <AgentNode
              id="supervisor"
              isCenter
              isSelected={selectedAgentId === 'supervisor'}
              isActive={!!supervisor?.active}
              onClick={() => setSelectedAgentId('supervisor')}
            />
          </div>

          {/* Inventory — bottom left */}
          <div className="absolute" style={{ bottom: '0%', left: '3%' }}>
            <AgentNode
              id="inventory"
              isSelected={selectedAgentId === 'inventory'}
              isActive={!!inventory?.active}
              onClick={() => setSelectedAgentId('inventory')}
            />
          </div>

          {/* Finance — bottom center */}
          <div className="absolute" style={{ bottom: '0%', left: '50%', transform: 'translateX(-50%)' }}>
            <AgentNode
              id="finance"
              isSelected={selectedAgentId === 'finance'}
              isActive={!!finance?.active}
              onClick={() => setSelectedAgentId('finance')}
            />
          </div>

          {/* Procurement — bottom right */}
          <div className="absolute" style={{ bottom: '0%', right: '3%' }}>
            <AgentNode
              id="procurement"
              isSelected={selectedAgentId === 'procurement'}
              isActive={!!procurement?.active}
              onClick={() => setSelectedAgentId('procurement')}
            />
          </div>

          {/* Logistics — mid right (child of procurement) */}
          <div className="absolute" style={{ top: '50%', right: '3%', transform: 'translateY(-50%)' }}>
            <AgentNode
              id="logistics"
              isSelected={selectedAgentId === 'logistics'}
              isActive={!!logistics?.active}
              onClick={() => setSelectedAgentId('logistics')}
            />
          </div>
        </div>
      </div>

      {/* Footer: current stage */}
      <div
        className="relative z-10 flex items-center justify-between px-5 py-2.5 text-[10px] font-mono border-t border-[#1E293B]"
        style={{ background: 'rgba(8,12,20,0.8)' }}
      >
        <span className="text-slate-500">Execution Stage</span>
        <span className={`font-bold uppercase ${workflowStage === 'IDLE' ? 'text-slate-500' : workflowStage === 'COMPLETED' ? 'text-emerald-400' : 'text-cyan-400'}`}>
          {workflowStage}
        </span>
      </div>
    </div>
  );
};
