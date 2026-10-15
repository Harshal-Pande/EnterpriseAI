import React from 'react';
import { SourceBadge, type DataSourceState } from './SourceBadge';

interface PageHeaderProps {
  title: string;
  description?: string;
  sourceState?: DataSourceState;
  showSourceBadge?: boolean;
  actions?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  sourceState,
  showSourceBadge = true,
  actions,
  className = '',
}) => {
  return (
    <header className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6 ${className}`}>
      <div>
        <h1 className="text-[22px] font-semibold text-text tracking-tight leading-tight">
          {title}
        </h1>
        {description && (
          <p className="text-[14px] text-text-2 mt-0.5 leading-normal">
            {description}
          </p>
        )}
      </div>
      {(showSourceBadge || actions) && (
        <div className="flex items-center gap-3 shrink-0">
          {actions}
          {showSourceBadge && <SourceBadge forcedState={sourceState} />}
        </div>
      )}
    </header>
  );
};
