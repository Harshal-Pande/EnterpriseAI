import React from 'react';
import { Cpu, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useDemo } from '../../state/DemoContext';
import type { ActivityLog } from '../../types';

export const ActivityStream: React.FC = () => {
  const { activityLogs } = useDemo();

  const getTypeIcon = (type: ActivityLog['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />;
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />;
      default:
        return <Cpu className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />;
    }
  };

  return (
    <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-5 shadow-xl flex flex-col justify-between min-h-[380px]">
      <div className="flex items-center justify-between pb-3 border-b border-[#1E293B]">
        <h2 className="text-base font-bold text-white tracking-tight">
          Activity Stream
        </h2>
        <span className="text-[11px] font-mono text-slate-400">Real-time Feed</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 my-3 pr-1 divide-y divide-[#1E293B]/50">
        {activityLogs.map((log) => (
          <div key={log.id} className="pt-3 first:pt-0 flex items-start gap-3 text-xs">
            {getTypeIcon(log.type)}
            <div className="flex-1 space-y-1">
              <div className="text-slate-200 leading-snug">
                <span className="font-bold text-white capitalize mr-1">{log.agent}</span>
                {log.message}
              </div>
              <div className="text-[10px] text-slate-400 font-mono">
                {log.timestamp}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="text-[10px] text-slate-400 font-mono pt-2 border-t border-[#1E293B] text-right">
        {activityLogs.length} events logged
      </div>
    </div>
  );
};
