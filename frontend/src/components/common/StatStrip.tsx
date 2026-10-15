import React from 'react';

export interface StatItem {
  label: string;
  value: string | number;
  context?: string | React.ReactNode;
  accent?: 'default' | 'ok' | 'warn' | 'danger' | 'info';
}

interface StatStripProps {
  stats: StatItem[];
  className?: string;
}

export const StatStrip: React.FC<StatStripProps> = ({ stats, className = '' }) => {
  const getAccentColor = (accent?: StatItem['accent']) => {
    switch (accent) {
      case 'ok':
        return 'text-ok';
      case 'warn':
        return 'text-warn';
      case 'danger':
        return 'text-danger';
      case 'info':
        return 'text-info';
      default:
        return 'text-text';
    }
  };

  return (
    <div
      className={`rounded-[6px] border border-border bg-surface grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 divide-y sm:divide-y-0 sm:divide-x divide-border overflow-hidden ${className}`}
    >
      {stats.map((stat, idx) => (
        <div key={idx} className="p-3.5 flex flex-col justify-between">
          <span className="text-[12px] text-text-3 font-medium truncate mb-1">
            {stat.label}
          </span>
          <div
            className={`text-[24px] font-semibold font-mono tabular-nums leading-none tracking-tight my-0.5 ${getAccentColor(
              stat.accent
            )}`}
          >
            {stat.value}
          </div>
          {stat.context && (
            <div className="text-[12px] text-text-2 truncate mt-1 leading-tight">
              {stat.context}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
