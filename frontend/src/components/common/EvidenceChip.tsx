import React from 'react';

interface EvidenceChipProps {
  label: string;
  onClick?: () => void;
  className?: string;
}

export const EvidenceChip: React.FC<EvidenceChipProps> = ({
  label,
  onClick,
  className = '',
}) => {
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`inline-flex items-center px-1.5 py-0.5 rounded-[4px] border border-border bg-surface-sunk text-text-2 hover:text-text hover:border-border-strong font-mono text-[11px] transition-colors cursor-pointer ${className}`}
        title={`View evidence record: ${label}`}
      >
        {label}
      </button>
    );
  }

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded-[4px] border border-border bg-surface-sunk text-text-2 font-mono text-[11px] select-none ${className}`}
    >
      {label}
    </span>
  );
};
