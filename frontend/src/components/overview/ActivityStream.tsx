import React from 'react';
import { Activity, AlertCircle, Info, CheckCircle2 } from 'lucide-react';
import { useDemo } from '../../state/DemoContext';
import type { ActivityLog } from '../../types';

export const ActivityStream: React.FC = () => {
  const { activityLogs } = useDemo();

  const getBadgeColor = (agent: ActivityLog['agent']) => {
    switch (agent) {
      case 'supervisor':
        return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30';
      case 'inventory':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      case 'procurement':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      case 'finance':
        return 'bg-pink-500/20 text-pink-300 border-pink-500/30';
      case 'logistics':
        return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
      case 'AUDIT':
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30';
      default:
        return 'bg-slate-700 text-slate-300 border-slate-600';
    }
  };

  const getTypeIcon = (type: ActivityLog['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />;
      case 'warning':
        return <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
      case 'error':
        return <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />;
      default:
        return <Info className="w-3.5 h-3.5 text-blue-400 shrink-0" />;
    }
  };

  return (
    <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-5 shadow-xl flex flex-col justify-between max-h-[380px]">
      <div className="flex items-center justify-between pb-3 border-b border-[#24334D]">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h3 className="font-bold text-sm text-white uppercase tracking-wide">
            Live Inter-Agent Event Stream
          </h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
          REALTIME
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 my-3 pr-1">
        {activityLogs.map((log) => (
          <div
            key={log.id}
            className="flex items-start gap-2.5 p-2 rounded-lg bg-[#0B111E] border border-[#1E293B] hover:border-slate-700 transition-colors text-xs font-mono"
          >
            <span className="text-slate-500 text-[10px] shrink-0 pt-0.5">{log.timestamp}</span>
            {getTypeIcon(log.type)}
            <span
              className={`px-1.5 py-0.5 text-[9px] font-bold rounded uppercase border shrink-0 ${getBadgeColor(
                log.agent
              )}`}
            >
              {log.agent}
            </span>
            <span className="text-slate-200 text-[11px] leading-tight flex-1 font-sans font-medium">
              {log.message}
            </span>
          </div>
        ))}
      </div>

      <div className="text-[10px] text-slate-400 font-mono pt-2 border-t border-[#1E293B] text-right">
        {activityLogs.length} events logged to memory bus
      </div>
    </div>
  );
};
