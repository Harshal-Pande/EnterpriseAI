import React from 'react';
import { SourceBadge } from './SourceBadge';

export interface PanelProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  padding?: 'normal' | 'none' | 'dense';
  isSimulated?: boolean;
  className?: string;
  headerClassName?: string;
  bodyClassName?: string;
}

export const Panel: React.FC<PanelProps> = ({
  title,
  subtitle,
  actions,
  children,
  padding = 'normal',
  isSimulated = false,
  className = '',
  headerClassName = '',
  bodyClassName = '',
}) => {
  const hasHeader = Boolean(title || subtitle || actions || isSimulated);

  const paddingClass =
    padding === 'none' ? 'p-0' : padding === 'dense' ? 'p-3' : 'p-4';

  return (
    <section
      className={`rounded-[6px] border border-border bg-surface text-text overflow-hidden ${className}`}
    >
      {hasHeader && (
        <div
          className={`flex items-center justify-between gap-3 px-4 py-2.5 border-b border-border bg-surface ${headerClassName}`}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            {typeof title === 'string' ? (
              <h2 className="text-[15px] font-semibold text-text tracking-tight truncate leading-tight">
                {title}
              </h2>
            ) : (
              title
            )}
            {subtitle && (
              <span className="text-[12px] text-text-3 truncate">
                {subtitle}
              </span>
            )}
            {isSimulated && (
              <SourceBadge forcedState="simulated" variant="tag" />
            )}
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
        </div>
      )}
      <div className={`${paddingClass} ${bodyClassName}`}>{children}</div>
    </section>
  );
};
