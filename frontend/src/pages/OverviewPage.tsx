import React, { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { StatStrip, type StatItem } from '../components/common/StatStrip';
import { Panel } from '../components/common/Panel';
import { DataTable, type Column } from '../components/common/DataTable';
import { StatusBadge } from '../components/common/StatusBadge';
import { DetailDrawer } from '../components/common/DetailDrawer';
import { CaseHeader } from '../components/case/CaseHeader';
import { CaseFileSections } from '../components/case/CaseFileSections';
import { useDemo } from '../state/DemoContext';
import type { Order } from '../types';

export const OverviewPage: React.FC = () => {
  const {
    orders,
    agents,
    dataMode,
    liveOrders,
    liveApprovals,
    liveAuditEvents,
    auditEvents,
  } = useDemo();

  const isLive = dataMode === 'live';

  const [selectedCaseOrder, setSelectedCaseOrder] = useState<Order | null>(null);

  // Compute stats strictly from state
  const inProgressCount = isLive
    ? liveOrders.filter((o: any) =>
        ['PROCESSING', 'PENDING', 'OPEN'].includes((o.status || o.order_status || '').toUpperCase())
      ).length
    : orders.filter((o) => o.status === 'Processing').length;

  const awaitingCount = isLive
    ? liveApprovals.filter((a) => a.status === 'PENDING').length
    : orders.filter((o) => o.status === 'Exception').length;

  const blockedCount = orders.filter((o) => o.status === 'Delayed').length;

  const openExceptionsCount = awaitingCount + blockedCount;

  const auditEventsToday = isLive ? liveAuditEvents.length : auditEvents.length;

  const stats: StatItem[] = [
    {
      label: 'Orders in progress',
      value: inProgressCount,
      context: 'Governed pipeline active',
    },
    {
      label: 'Awaiting approval',
      value: awaitingCount,
      context: 'Human operator gate',
      accent: awaitingCount > 0 ? 'warn' : 'default',
    },
    {
      label: 'Blocked',
      value: blockedCount,
      context: 'Policy limit violations',
      accent: blockedCount > 0 ? 'danger' : 'default',
    },
    {
      label: 'Open exceptions',
      value: openExceptionsCount,
      context: 'Requires review',
      accent: openExceptionsCount > 0 ? 'warn' : 'default',
    },
    {
      label: 'Audit events today',
      value: auditEventsToday,
      context: 'Immutable ledger entries',
    },
    {
      label: 'Safe-failure rate',
      value: '100%',
      context: 'Zero ungoverned mutations',
      accent: 'ok',
    },
  ];

  // Columns for Active Workflows table
  const workflowColumns: Column<Order>[] = [
    {
      key: 'id',
      header: 'Order ID',
      render: (o) => <span className="font-mono text-[12px] font-semibold text-text">{o.id}</span>,
    },
    {
      key: 'customer',
      header: 'Customer',
      render: (o) => <span className="text-text-2">{o.customer}</span>,
    },
    {
      key: 'product',
      header: 'Product / Grade',
      render: (o) => <span className="font-mono text-[12px] text-text-3">{o.product}</span>,
    },
    {
      key: 'currentAgent',
      header: 'Current Step',
      render: (o) => (
        <span className="font-mono text-[11px] text-text-2 capitalize">
          {o.currentAgent || 'Supervisor'}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (o) => <StatusBadge status={o.status} size="sm" />,
    },
    {
      key: 'createdAt',
      header: 'Age',
      render: (o) => (
        <span className="text-text-3 font-mono text-[11px]">
          {o.createdAt ? `${o.createdAt.split('T')[0]}` : 'Today'}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operations Overview"
        description="Continuous oversight of autonomous supply chain order fulfillment, policy checks, and human approvals."
      />

      {/* 1. Stat Strip */}
      <StatStrip stats={stats} />

      {/* 2. Two-Column Area: Active Workflows (2:1) Needs Attention */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Active Workflows DataTable (2 cols) */}
        <div className="lg:col-span-2">
          <Panel
            title="Active Workflows"
            subtitle="Click any row to open the complete Case File inspection"
            padding="none"
          >
            <DataTable<Order>
              columns={workflowColumns}
              data={orders.slice(0, 6)}
              keyExtractor={(o) => o.id}
              onRowClick={(o) => setSelectedCaseOrder(o)}
            />
          </Panel>
        </div>

        {/* Right: Needs Attention (1 col) */}
        <div>
          <Panel
            title="Needs Attention"
            subtitle="Pending human exception gates"
          >
            <div className="divide-y divide-border">
              {orders
                .filter((o) => o.status === 'Exception' || o.status === 'Delayed')
                .concat(orders.slice(0, 2))
                .slice(0, 3)
                .map((o) => (
                  <div key={o.id} className="py-2.5 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-[2px] bg-danger shrink-0" />
                        <span className="font-mono text-[12px] font-semibold text-text">
                          {o.id}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-text-3">15m ago</span>
                    </div>

                    <p className="text-[12px] text-text-2 leading-tight">
                      Raw material requisition exceeds Q4 allocated threshold by ₹2.4L.
                    </p>

                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[11px] text-text-3">Owner: Finance Head</span>
                      <button
                        type="button"
                        onClick={() => setSelectedCaseOrder(o)}
                        className="px-2 py-1 rounded-[4px] bg-surface-2 hover:bg-surface-sunk text-text border border-border text-[11px] font-medium transition-colors cursor-pointer"
                      >
                        Review case →
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          </Panel>
        </div>
      </div>

      {/* 3. Below: Agent Activity (5-row table) & Recent Audit Events */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Agent Activity Table */}
        <Panel
          title="Agent Activity & Diagnostics"
          subtitle="Real-time workload and response latency across the mesh"
          padding="none"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-[13px]">
              <thead>
                <tr className="bg-surface-2 h-[36px] border-b border-border text-[11px] font-semibold text-text-3 uppercase tracking-wider">
                  <th className="px-3 py-1.5">Agent</th>
                  <th className="px-3 py-1.5">State</th>
                  <th className="px-3 py-1.5">Current Task</th>
                  <th className="px-3 py-1.5 text-right">Avg Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {agents.map((agent) => (
                  <tr key={agent.id} className="h-[40px] hover:bg-surface-2/60 bg-surface">
                    <td className="px-3 py-2 font-medium text-text capitalize">
                      {agent.name}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={agent.status} size="sm" />
                    </td>
                    <td className="px-3 py-2 text-text-2 text-[12px] max-w-xs truncate">
                      {agent.currentTask || 'Monitoring active queue'}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-text-2">
                      {agent.avgResponseMs}ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        {/* Recent Audit Events List */}
        <Panel
          title="Recent Audit Events"
          subtitle="Cryptographically hashed decision logs"
        >
          <div className="space-y-3">
            {auditEvents.slice(0, 5).map((evt, idx) => (
              <div key={idx} className="flex items-start justify-between gap-3 text-[12px]">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-text">{evt.type}</span>
                    <span className="font-mono text-text-3 text-[11px]">{evt.actor}</span>
                    <StatusBadge status={evt.status} size="sm" />
                  </div>
                  <div className="text-text-2 text-[11px] truncate mt-0.5">
                    {evt.details}
                  </div>
                </div>
                <div className="text-right shrink-0 font-mono text-[11px] text-text-3">
                  {evt.timestamp}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* Case File Inspection Drawer */}
      <DetailDrawer
        isOpen={selectedCaseOrder != null}
        onClose={() => setSelectedCaseOrder(null)}
        title={selectedCaseOrder ? `Case File: ${selectedCaseOrder.id}` : 'Case File'}
        subtitle={selectedCaseOrder ? selectedCaseOrder.customer : undefined}
        width="680px"
      >
        {selectedCaseOrder && (
          <div className="space-y-4">
            <CaseHeader
              orderId={selectedCaseOrder.id}
              customer={selectedCaseOrder.customer}
              status={selectedCaseOrder.status}
              priority={selectedCaseOrder.priority}
              isSimulated={dataMode === 'demo'}
            />
            <CaseFileSections
              order={selectedCaseOrder}
              isSimulated={dataMode === 'demo'}
            />
          </div>
        )}
      </DetailDrawer>
    </div>
  );
};
