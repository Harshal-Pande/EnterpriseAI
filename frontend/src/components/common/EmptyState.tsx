import React from 'react';

interface EmptyStateProps {
  title?: string;
  cause: string;
  nextStep?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No records found',
  cause,
  nextStep,
  action,
  className = '',
}) => {
  return (
    <div
      className={`p-8 text-center rounded-[6px] border border-border bg-surface flex flex-col items-center justify-center ${className}`}
    >
      <h3 className="text-[14px] font-semibold text-text mb-1">
        {title}
      </h3>
      <p className="text-[13px] text-text-2 max-w-md leading-normal">
        {cause}
      </p>
      {nextStep && (
        <p className="text-[12px] text-text-3 mt-1 max-w-md">
          {nextStep}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
};
