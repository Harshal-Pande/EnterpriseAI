import React from 'react';

export interface TabItem {
  id: string;
  label: string;
  badge?: string | number;
}

interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  className = '',
}) => {
  return (
    <nav
      className={`flex items-center gap-6 border-b border-border h-[36px] ${className}`}
      role="tablist"
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`h-full relative flex items-center gap-1.5 text-[13px] font-medium transition-colors cursor-pointer ${
              isActive
                ? 'text-text'
                : 'text-text-3 hover:text-text-2'
            }`}
          >
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span className="px-1.5 py-0.2 rounded-[4px] bg-surface-2 text-[11px] font-mono text-text-3">
                {tab.badge}
              </span>
            )}
            {/* 2px accent underline indicator */}
            {isActive && (
              <span className="absolute bottom-[-1px] left-0 right-0 h-[2px] bg-accent" />
            )}
          </button>
        );
      })}
    </nav>
  );
};
