import React, { useRef, useEffect } from 'react';
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
    case 'info':    return <Cpu className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />;
  }
}

export const ActivityStream: React.FC = () => {
  const { activityLogs } = useDemo();
  const listRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to top when new log arrives (newest first)
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = 0;
    }
  }, [activityLogs.length]);

  return (
    <div
      className="flex flex-col rounded-xl overflow-hidden"
      style={{
        background: '#0B1020',
        border: '1px solid #1E293B',
        minHeight: '380px'
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1E293B] shrink-0">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-teal-400" />
          <h2 className="text-sm font-bold text-white">Activity Stream</h2>
        </div>
        <span className="text-[10px] font-mono text-slate-500">{activityLogs.length} events</span>
      </div>

      {/* Feed */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto p-4 space-y-2"
        style={{ maxHeight: '320px' }}
      >
        {activityLogs.length === 0 && (
          <div className="text-center text-slate-600 text-xs py-8">
            No events yet. Run the demo to begin.
          </div>
        )}
        {activityLogs.map((log, idx) => (
          <div
            key={log.id}
            className="flex items-start gap-2.5 animate-fade-slide"
            style={{ animationDelay: `${idx * 0.02}s` }}
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
                <span className="text-[10px] text-slate-400 font-mono">{log.timestamp}</span>
              </div>
              <p className="text-[11px] text-slate-300 leading-snug mt-0.5">
                {log.message}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
