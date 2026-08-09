import React, { useRef, useEffect, useCallback } from 'react';
import { CheckCircle2, AlertTriangle, Cpu, ShieldCheck } from 'lucide-react';
import { useDemo } from '../../state/DemoContext';
import type { ActivityLog } from '../../types';

const AGENT_COLORS: Record<string, string> = {
  supervisor:  '#6366F1',
  inventory:   '#10B981',
  procurement: '#F59E0B',
  finance:     '#EC4899',
  logistics:   '#8B5CF6',
  AUDIT:       '#14B8A6',
  SYSTEM:      '#38BDF8',
};

function getTypeIcon(type: ActivityLog['type']) {
  switch (type) {
    case 'success': return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />;
    case 'warning': return <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />;
    case 'error':   return <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />;
    case 'info':    return <Cpu className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />;
  }
}

const SCROLL_LOCK_THRESHOLD_PX = 60; // px from bottom → auto-scroll
const MAX_HEIGHT_PX = 460;

export const ActivityStream: React.FC = () => {
  const { activityLogs } = useDemo();
  const listRef       = useRef<HTMLDivElement>(null);
  const isNearBottom  = useRef(true); // tracks whether user is near bottom

  // Track scroll position to decide whether to auto-scroll
  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    isNearBottom.current = distanceFromBottom <= SCROLL_LOCK_THRESHOLD_PX;
  }, []);

  // When new events arrive, auto-scroll only if user was near the bottom
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    if (isNearBottom.current) {
      // Scroll to top because newest events are prepended (index 0)
      el.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [activityLogs.length]);

  return (
    <div
      className="flex flex-col rounded-xl overflow-hidden"
      style={{
        background: '#0B1020',
        border: '1px solid #1E293B',
        // No min-height — height is determined by max-height of scrollable area
      }}
    >
      {/* ── Fixed Header ── */}
      <div
        className="flex items-center justify-between px-5 py-3.5 border-b border-[#1E293B] shrink-0"
        style={{ background: '#0B1020' }}
      >
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-teal-400 shrink-0" />
          <h2 className="text-sm font-bold text-white">Activity Stream</h2>
        </div>
        <div className="flex items-center gap-2">
          {activityLogs.length > 0 && (
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
          )}
          <span className="text-[10px] font-mono text-slate-500">{activityLogs.length} events</span>
        </div>
      </div>

      {/* ── Scrollable Event List ── */}
      <div
        ref={listRef}
        onScroll={handleScroll}
        className="activity-stream-scroll"
        style={{
          maxHeight: `${MAX_HEIGHT_PX}px`,
          overflowY: 'auto',
          overflowX: 'hidden',
          padding: '14px 16px',
        }}
      >
        {activityLogs.length === 0 && (
          <div className="text-center text-slate-600 text-xs py-10">
            No events yet. Run the demo to begin.
          </div>
        )}

        <div className="space-y-2.5">
          {activityLogs.map((log, idx) => (
            <div
              key={log.id}
              className="flex items-start gap-2.5"
              style={{
                animation: idx === 0 ? 'fadeSlideIn 0.2s ease-out forwards' : 'none',
              }}
            >
              {getTypeIcon(log.type)}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span
                    className="text-[11px] font-bold uppercase"
                    style={{ color: AGENT_COLORS[log.agent] ?? '#94A3B8' }}
                  >
                    {log.agent}
                  </span>
                  <span className="text-[10px] text-slate-600 font-mono shrink-0">{log.timestamp}</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-snug mt-0.5 break-words">
                  {log.message}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
