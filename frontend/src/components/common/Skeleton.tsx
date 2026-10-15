import React from 'react';

interface SkeletonProps {
  width?: string;
  height?: string;
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = '16px',
  className = '',
}) => {
  return (
    <div
      style={{ width, height }}
      className={`bg-surface-2 rounded-[3px] shrink-0 ${className}`}
      aria-hidden="true"
    />
  );
};
