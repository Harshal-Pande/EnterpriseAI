import React from 'react';
import { Sidebar, type ScreenId } from './Sidebar';
import { TopHeader } from './TopHeader';

interface AppShellProps {
  currentScreen: ScreenId;
  onNavigate: (screen: ScreenId) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ currentScreen, onNavigate, children }) => {
  return (
    <div className="flex h-screen w-screen overflow-hidden" style={{ background: '#080C14' }}>
      {/* Sidebar */}
      <Sidebar currentScreen={currentScreen} onNavigate={onNavigate} />

      {/* Main column */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopHeader />
        <main
          id="main-content"
          className="flex-1 overflow-y-auto overflow-x-hidden p-6"
          style={{ background: '#080C14' }}
        >
          {children}
        </main>
      </div>
    </div>
  );
};
