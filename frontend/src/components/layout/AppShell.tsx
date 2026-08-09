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
    <div className="flex h-screen w-screen bg-[#090D16] text-slate-100 overflow-hidden font-sans">
      {/* Left Sidebar */}
      <Sidebar currentScreen={currentScreen} onNavigate={onNavigate} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopHeader />
        <main className="flex-1 overflow-y-auto p-6 bg-[#090D16]">
          {children}
        </main>
      </div>
    </div>
  );
};
