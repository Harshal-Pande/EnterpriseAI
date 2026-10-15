import React, { useState, useRef, useEffect } from 'react';
import { useDemo } from '../../state/DemoContext';

export type DataSourceState = 'live' | 'simulated' | 'fallback' | 'stale' | 'unavailable';

interface SourceBadgeProps {
  forcedState?: DataSourceState;
  customLabel?: string;
  variant?: 'compact' | 'tag';
  showPopover?: boolean;
  className?: string;
}

const STATE_CONFIG: Record<
  DataSourceState,
  { label: string; badgeClass: string; dotClass: string }
> = {
  live: {
    label: 'Live · PostgreSQL',
    badgeClass: 'bg-ok-soft text-ok border-ok/40',
    dotClass: 'bg-ok',
  },
  simulated: {
    label: 'Simulated',
    badgeClass: 'bg-sim-soft text-sim border-sim/40',
    dotClass: 'bg-sim',
  },
  fallback: {
    label: 'Fallback',
    badgeClass: 'bg-warn-soft text-warn border-warn/40',
    dotClass: 'bg-warn',
  },
  stale: {
    label: 'Stale',
    badgeClass: 'bg-warn-soft text-warn border-warn/40',
    dotClass: 'bg-warn',
  },
  unavailable: {
    label: 'Unavailable',
    badgeClass: 'bg-danger-soft text-danger border-danger/40',
    dotClass: 'bg-danger',
  },
};

export const SourceBadge: React.FC<SourceBadgeProps> = ({
  forcedState,
  customLabel,
  variant = 'compact',
  showPopover = true,
  className = '',
}) => {
  const {
    dataMode,
    isLiveConnected,
    liveLoading,
    liveError,
    wsConnectionState,
    toggleDataMode,
    refreshLiveData,
  } = useDemo();

  const [isOpen, setIsOpen] = useState(false);
  const [switchError, setSwitchError] = useState<string | null>(null);
  const [isSwitching, setIsSwitching] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Derive truthful state
  const derivedState: DataSourceState = forcedState
    ? forcedState
    : dataMode === 'demo'
    ? 'simulated'
    : isLiveConnected
    ? 'live'
    : 'unavailable';

  const cfg = STATE_CONFIG[derivedState];
  const label = customLabel || cfg.label;

  // Close popover on outside click or Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleToggleMode = async () => {
    setSwitchError(null);
    setIsSwitching(true);
    try {
      toggleDataMode();
      await refreshLiveData();
    } catch (err: any) {
      setSwitchError(err?.message || 'Failed to toggle data mode');
    } finally {
      setIsSwitching(false);
    }
  };

  // Extract host only from backend URL (no secrets or auth keys)
  const apiHost =
    typeof window !== 'undefined'
      ? (import.meta.env.VITE_API_BASE_URL as string)?.replace(/^https?:\/\//, '') || 'localhost:8000'
      : 'localhost:8000';

  if (variant === 'tag') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 h-[18px] px-1.5 text-[11px] font-mono font-medium rounded-[4px] border ${cfg.badgeClass} ${className}`}
      >
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${cfg.dotClass}`} />
        <span>{label}</span>
      </span>
    );
  }

  return (
    <div className={`relative inline-block ${className}`} ref={popoverRef}>
      <button
        type="button"
        onClick={() => showPopover && setIsOpen(!isOpen)}
        className={`inline-flex items-center gap-1.5 h-[24px] px-2 text-[12px] font-medium rounded-[4px] border transition-colors cursor-pointer ${cfg.badgeClass}`}
        title="View data source diagnostics"
        aria-expanded={isOpen}
      >
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${cfg.dotClass}`} />
        <span className="leading-none">{label}</span>
      </button>

      {showPopover && isOpen && (
        <div
          className="absolute right-0 mt-1.5 w-72 rounded-[6px] border border-border bg-surface p-3.5 shadow-lg z-50 text-[12px] text-text"
          style={{ boxShadow: '0 8px 24px rgba(0,0,0,0.14)' }}
        >
          <div className="flex items-center justify-between border-b border-border pb-2 mb-2.5">
            <span className="font-semibold text-text">Data source</span>
            <span
              className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-[4px] text-[11px] font-medium border ${cfg.badgeClass}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${cfg.dotClass}`} />
              {derivedState}
            </span>
          </div>

          <div className="space-y-1.5 text-[12px]">
            <div className="flex justify-between">
              <span className="text-text-3">Mode</span>
              <span className="font-mono text-text capitalize">{dataMode}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-3">Backend host</span>
              <span className="font-mono text-text">{apiHost}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-3">Backend health</span>
              <span className={`font-mono ${isLiveConnected ? 'text-ok' : 'text-danger'}`}>
                {isLiveConnected ? 'Reachable' : 'Unreachable'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-3">Database</span>
              <span className="font-mono text-text">
                {isLiveConnected ? 'Healthy' : 'Disconnected'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-3">Realtime WS</span>
              <span className="font-mono text-text">{wsConnectionState}</span>
            </div>
            {dataMode === 'demo' && (
              <p className="text-[11px] text-text-3 pt-1 border-t border-border mt-2">
                Running offline simulation. Database records and blockchain hashes are not modified.
              </p>
            )}
            {dataMode === 'live' && !isLiveConnected && (
              <p className="text-[11px] text-danger pt-1 border-t border-border mt-2">
                {liveError || 'Backend unreachable. Ensure FastAPI server is running on port 8000.'}
              </p>
            )}
            {switchError && (
              <p className="text-[11px] text-danger pt-1 border-t border-border mt-2 font-mono">
                {switchError}
              </p>
            )}
          </div>

          <div className="mt-3 pt-2.5 border-t border-border flex items-center justify-between">
            <button
              type="button"
              disabled={isSwitching || liveLoading}
              onClick={handleToggleMode}
              className="w-full text-center py-1 px-2 rounded-[4px] bg-surface-2 hover:bg-surface-sunk text-text border border-border text-[12px] font-medium transition-colors disabled:opacity-50 cursor-pointer"
            >
              {isSwitching ? 'Switching...' : dataMode === 'demo' ? 'Switch to live' : 'Switch to simulated'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
