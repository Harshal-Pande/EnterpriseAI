import React from 'react';

interface ErrorStateProps {
  title?: string;
  cause: string;
  nextStep?: string;
  errorMessage?: string;
  action?: React.ReactNode;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'System error encountered',
  cause,
  nextStep = 'Verify backend service connectivity or switch to simulated mode.',
  errorMessage,
  action,
  className = '',
}) => {
  return (
    <div
      className={`p-6 rounded-[6px] border border-danger/40 bg-surface text-left ${className}`}
    >
      <h3 className="text-[14px] font-semibold text-danger mb-1">
        {title}
      </h3>
      <p className="text-[13px] text-text-2 leading-normal">
        {cause}
      </p>
      {nextStep && (
        <p className="text-[12px] text-text-3 mt-1">
          {nextStep}
        </p>
      )}
      {errorMessage && (
        <pre className="mt-3 p-2.5 rounded-[4px] bg-surface-sunk border border-border text-danger font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
          {errorMessage}
        </pre>
      )}
      {action && <div className="mt-3.5">{action}</div>}
    </div>
  );
};
