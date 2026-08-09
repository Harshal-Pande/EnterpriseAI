import React, { useState } from 'react';
import { DemoProvider } from './state/DemoContext';
import { AppShell } from './components/layout/AppShell';
import type { ScreenId } from './components/layout/Sidebar';

import { OverviewPage } from './pages/OverviewPage';
import { OrdersPage } from './pages/OrdersPage';
import { AgentMeshPage } from './pages/AgentMeshPage';
import { InventoryPage } from './pages/InventoryPage';
import { ProcurementPage } from './pages/ProcurementPage';
import { FinancePage } from './pages/FinancePage';
import { LogisticsPage } from './pages/LogisticsPage';
import { KnowledgeGraphPage } from './pages/KnowledgeGraphPage';
import { AuditTrailPage } from './pages/AuditTrailPage';
import { ExceptionsPage } from './pages/ExceptionsPage';
import { BenchmarksPage } from './pages/BenchmarksPage';

export const AppContent: React.FC = () => {
  const [currentScreen, setCurrentScreen] = useState<ScreenId>('overview');

  const renderScreen = () => {
    switch (currentScreen) {
      case 'overview':
        return <OverviewPage />;
      case 'orders':
        return <OrdersPage />;
      case 'mesh':
        return <AgentMeshPage />;
      case 'inventory':
        return <InventoryPage />;
      case 'procurement':
        return <ProcurementPage />;
      case 'finance':
        return <FinancePage />;
      case 'logistics':
        return <LogisticsPage />;
      case 'graph':
        return <KnowledgeGraphPage />;
      case 'audit':
        return <AuditTrailPage />;
      case 'exceptions':
        return <ExceptionsPage />;
      case 'benchmarks':
        return <BenchmarksPage />;
      default:
        return <OverviewPage />;
    }
  };

  return (
    <AppShell currentScreen={currentScreen} onNavigate={setCurrentScreen}>
      {renderScreen()}
    </AppShell>
  );
};

export function App() {
  return (
    <DemoProvider>
      <AppContent />
    </DemoProvider>
  );
}

export default App;
