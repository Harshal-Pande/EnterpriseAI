import React from 'react';
import { Sun, Moon, Menu } from 'lucide-react';
import { useDemo } from '../../state/DemoContext';
import { useTheme } from '../../state/ThemeContext';
import { SourceBadge } from '../common/SourceBadge';
import type { DemoScenario } from '../../types';
import type { ScreenId } from './Sidebar';

interface TopHeaderProps {
  currentScreen?: ScreenId;
  onOpenMobileNav?: () => void;
}

const SCENARIO_OPTIONS: { id: DemoScenario; label: string }[] = [
  { id: 'normal', label: 'Normal fulfilment' },
  { id: 'supplier_unavailable', label: 'Supplier unavailable' },
  { id: 'budget_breach', label: 'Budget overrun' },
  { id: 'delivery_delay', label: 'Delivery delay' },
  { id: 'multi_exception', label: 'Combined failure' },
];

const SCREEN_TITLES: Record<ScreenId, string> = {
  overview: 'Operations Overview',
  orders: 'Orders',
  exceptions: 'Exceptions & Approvals',
  mesh: 'Agent Mesh Diagnostics',
  orchestration: 'Governed Orchestration',
  inventory: 'Warehouse Inventory',
  procurement: 'Procurement & Bidding',
  finance: 'Financial Governance',
  logistics: 'Logistics & Transit',
  graph: 'Enterprise Knowledge Graph',
  audit: 'Cryptographic Audit Trail',
  benchmarks: 'Mesh Telemetry Benchmarks',
  security: 'Security & Posture',
  support: 'Support & Docs',
};

export const TopHeader: React.FC<TopHeaderProps> = ({
  currentScreen = 'overview',
  onOpenMobileNav,
}) => {
  const {
    dataMode,
    activeScenario,
    setActiveScenario,
    runDemoOrder,
    isSimulating,
    wsConnectionState,
    activeOrder,
    isLiveConnected,
    isOrchestrating,
    executeLiveOrchestration,
    activeLiveOrderId,
  } = useDemo();

  const { resolvedTheme, toggleTheme } = useTheme();

  const isExecuting = isSimulating || isOrchestrating;

  // Realtime WS Status text and color
  const wsStatusConfig = {
    CONNECTED: { text: 'Realtime connected', dotClass: 'bg-ok' },
    CONNECTING: { text: 'Reconnecting', dotClass: 'bg-warn' },
    RECONNECTING: { text: 'Reconnecting', dotClass: 'bg-warn' },
    DISCONNECTED: { text: 'Realtime off', dotClass: 'bg-text-3' },
    UNAUTHORIZED: { text: 'Realtime unauthorized', dotClass: 'bg-danger' },
  }[wsConnectionState] || { text: 'Realtime off', dotClass: 'bg-text-3' };

  // Run Order Handler
  const handleRunOrder = () => {
    if (isExecuting) return;
    if (dataMode === 'live') {
      executeLiveOrchestration(activeLiveOrderId || undefined, activeScenario);
    } else {
      runDemoOrder(activeScenario);
    }
  };

  const isLiveDisabled = dataMode === 'live' && !isLiveConnected;
  const disabledReason = isLiveDisabled
    ? 'Backend unreachable. Connect backend to run live orchestration.'
    : isExecuting
    ? 'Workflow run currently in progress.'
    : '';

  const activeCaseId = dataMode === 'live' ? activeLiveOrderId : activeOrder?.id;

  return (
    <header className="h-[52px] px-4 shrink-0 flex items-center justify-between border-b border-border bg-surface text-text sticky top-0 z-20 select-none">
      {/* Left: Mobile Nav Button + Breadcrumb */}
      <div className="flex items-center gap-3 min-w-0">
        {onOpenMobileNav && (
          <button
            type="button"
            onClick={onOpenMobileNav}
            className="md:hidden p-1 text-text-3 hover:text-text rounded-[4px] cursor-pointer"
            title="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[14px] font-semibold text-text truncate">
            {SCREEN_TITLES[currentScreen] || 'Operations'}
          </span>
          {activeCaseId && (
            <>
              <span className="text-text-3 text-[12px]">/</span>
              <span className="text-[12px] font-mono text-text-2 truncate">
                {activeCaseId}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Right: Controls & Diagnostics */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Data Source Indicator */}
        <SourceBadge variant="compact" />

        {/* Scenario Selector & Run Order Button */}
        <div className="hidden sm:flex items-center gap-2">
          <select
            value={activeScenario}
            onChange={(e) => setActiveScenario(e.target.value as DemoScenario)}
            disabled={isExecuting}
            className="h-[32px] px-2 text-[12px] bg-surface-sunk text-text border border-border rounded-[4px] focus:outline-none focus:border-accent cursor-pointer disabled:opacity-50"
            title="Select scenario to run"
          >
            {SCENARIO_OPTIONS.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={handleRunOrder}
            disabled={isExecuting || isLiveDisabled}
            title={disabledReason || 'Run selected scenario'}
            className="h-[32px] px-3 bg-accent hover:bg-accent-hover text-white text-[12px] font-medium rounded-[4px] transition-colors disabled:bg-surface-2 disabled:text-text-3 disabled:cursor-not-allowed cursor-pointer shrink-0"
          >
            {isExecuting ? 'Running...' : 'Run order'}
          </button>
        </div>

        {/* WebSocket Realtime Status */}
        <div
          className="hidden lg:flex items-center gap-1.5 text-[12px] text-text-2 border-l border-border pl-3"
          title={`WebSocket Status: ${wsConnectionState}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${wsStatusConfig.dotClass}`} />
          <span className="text-text-3 text-[11px] whitespace-nowrap">
            {wsStatusConfig.text}
          </span>
        </div>

        {/* Theme Toggle (Sun/Moon) */}
        <div className="border-l border-border pl-3">
          <button
            type="button"
            onClick={toggleTheme}
            className="w-8 h-8 flex items-center justify-center rounded-[4px] text-text-2 hover:text-text hover:bg-surface-2 transition-colors cursor-pointer"
            title={
              resolvedTheme === 'dark'
                ? 'Switch to light theme'
                : 'Switch to dark theme'
            }
            aria-label="Toggle theme"
          >
            {resolvedTheme === 'dark' ? (
              <Sun className="w-4 h-4" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
