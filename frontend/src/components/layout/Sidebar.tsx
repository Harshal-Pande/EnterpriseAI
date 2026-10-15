import React from 'react';
import {
  LayoutDashboard,
  ShoppingBag,
  AlertTriangle,
  Cpu,
  GitBranch,
  Package,
  Scale,
  CircleDollarSign,
  Truck,
  Share2,
  ShieldCheck,
  BarChart3,
  Shield,
  HelpCircle,
  X,
} from 'lucide-react';
import { useDemo } from '../../state/DemoContext';
import { SourceBadge } from '../common/SourceBadge';

export type ScreenId =
  | 'overview'
  | 'orders'
  | 'exceptions'
  | 'mesh'
  | 'orchestration'
  | 'inventory'
  | 'procurement'
  | 'finance'
  | 'logistics'
  | 'graph'
  | 'audit'
  | 'benchmarks'
  | 'security'
  | 'support';

interface SidebarProps {
  currentScreen: ScreenId;
  onNavigate: (screen: ScreenId) => void;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
}

interface NavItemConfig {
  id: ScreenId;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  badgeType?: 'danger' | 'neutral';
}

interface NavGroup {
  label: string;
  items: NavItemConfig[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentScreen,
  onNavigate,
  isOpenMobile = false,
  onCloseMobile,
}) => {
  const { orders, liveOrders, dataMode } = useDemo();

  // Compute real counts from state (never fake counts)
  const activeOrdersList = dataMode === 'live' ? liveOrders : orders;
  const inProgressOrderCount = activeOrdersList.filter(
    (o: any) => (o.status || o.order_status) === 'Processing'
  ).length;

  const openExceptionCount = activeOrdersList.filter(
    (o: any) =>
      (o.status || o.order_status) === 'Exception' ||
      (o.status || o.order_status) === 'Delayed'
  ).length;

  const navGroups: NavGroup[] = [
    {
      label: 'Operate',
      items: [
        {
          id: 'overview',
          label: 'Overview',
          icon: <LayoutDashboard className="w-4 h-4 shrink-0" />,
        },
        {
          id: 'orders',
          label: 'Orders',
          icon: <ShoppingBag className="w-4 h-4 shrink-0" />,
          badge: inProgressOrderCount > 0 ? inProgressOrderCount : undefined,
          badgeType: 'neutral',
        },
        {
          id: 'exceptions',
          label: 'Exceptions',
          icon: <AlertTriangle className="w-4 h-4 shrink-0" />,
          badge: openExceptionCount > 0 ? openExceptionCount : undefined,
          badgeType: 'danger',
        },
      ],
    },
    {
      label: 'Agents',
      items: [
        {
          id: 'mesh',
          label: 'Agent Mesh',
          icon: <Cpu className="w-4 h-4 shrink-0" />,
        },
        {
          id: 'orchestration',
          label: 'Orchestration',
          icon: <GitBranch className="w-4 h-4 shrink-0" />,
        },
      ],
    },
    {
      label: 'Domains',
      items: [
        {
          id: 'inventory',
          label: 'Inventory',
          icon: <Package className="w-4 h-4 shrink-0" />,
        },
        {
          id: 'procurement',
          label: 'Procurement',
          icon: <Scale className="w-4 h-4 shrink-0" />,
        },
        {
          id: 'finance',
          label: 'Finance',
          icon: <CircleDollarSign className="w-4 h-4 shrink-0" />,
        },
        {
          id: 'logistics',
          label: 'Logistics',
          icon: <Truck className="w-4 h-4 shrink-0" />,
        },
      ],
    },
    {
      label: 'Evidence',
      items: [
        {
          id: 'graph',
          label: 'Knowledge Graph',
          icon: <Share2 className="w-4 h-4 shrink-0" />,
        },
        {
          id: 'audit',
          label: 'Audit Trail',
          icon: <ShieldCheck className="w-4 h-4 shrink-0" />,
        },
      ],
    },
    {
      label: 'System',
      items: [
        {
          id: 'benchmarks',
          label: 'Benchmarks',
          icon: <BarChart3 className="w-4 h-4 shrink-0" />,
        },
        {
          id: 'security',
          label: 'Security',
          icon: <Shield className="w-4 h-4 shrink-0" />,
        },
        {
          id: 'support',
          label: 'Support & Docs',
          icon: <HelpCircle className="w-4 h-4 shrink-0" />,
        },
      ],
    },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full bg-surface border-r border-border select-none">
      {/* Brand header */}
      <div className="h-[52px] px-4 flex items-center justify-between border-b border-border shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-5 h-5 rounded-[4px] bg-accent text-white flex items-center justify-center font-mono font-semibold text-[11px] shrink-0">
            EM
          </div>
          <div className="min-w-0">
            <div className="text-[14px] font-semibold text-text leading-none truncate">
              Enterprise AI Mesh
            </div>
            <div className="text-[11px] text-text-3 leading-none mt-1 truncate">
              Supply chain operations
            </div>
          </div>
        </div>
        {onCloseMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            className="md:hidden text-text-3 hover:text-text p-1 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Navigation list */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
        {navGroups.map((group) => (
          <div key={group.label}>
            <div className="px-2 mb-1 text-[11px] font-medium text-text-3 uppercase tracking-wider">
              {group.label}
            </div>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const isActive = currentScreen === item.id;

                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      onNavigate(item.id);
                      onCloseMobile?.();
                    }}
                    className={`w-full h-[36px] px-2.5 rounded-[4px] flex items-center justify-between text-[13px] font-medium transition-colors cursor-pointer relative ${
                      isActive
                        ? 'bg-surface-2 text-text font-semibold'
                        : 'text-text-2 hover:bg-surface-2 hover:text-text'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {/* Active indicator bar */}
                      {isActive && (
                        <span className="absolute left-0 top-1 bottom-1 w-[3px] bg-accent rounded-r" />
                      )}
                      <span className={isActive ? 'text-accent' : 'text-text-3'}>
                        {item.icon}
                      </span>
                      <span className="truncate">{item.label}</span>
                    </div>

                    {item.badge !== undefined && item.badge > 0 && (
                      <span
                        className={`px-1.5 py-0.2 rounded-[4px] font-mono text-[11px] leading-tight shrink-0 ${
                          item.badgeType === 'danger'
                            ? 'bg-danger-soft text-danger border border-danger/30'
                            : 'bg-surface-sunk text-text-3 border border-border'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Sidebar footer */}
      <div className="p-3 border-t border-border bg-surface shrink-0 space-y-2">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-text-3">Data source:</span>
          <SourceBadge variant="tag" />
        </div>
        <div className="text-[11px] text-text-3 font-mono text-right">
          v0.1.0-governed
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop fixed sidebar (232px) */}
      <aside className="hidden md:block w-[232px] shrink-0 h-screen">
        {sidebarContent}
      </aside>

      {/* Mobile drawer overlay */}
      {isOpenMobile && (
        <div className="fixed inset-0 z-50 md:hidden flex" role="dialog" aria-modal="true">
          <div
            className="fixed inset-0 bg-black/50"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <div className="relative w-[240px] max-w-full h-full z-10">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
