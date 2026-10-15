import React, { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Panel } from '../components/common/Panel';
import { DataTable, type Column } from '../components/common/DataTable';
import { StatusBadge } from '../components/common/StatusBadge';
import { DetailDrawer } from '../components/common/DetailDrawer';
import { CaseHeader } from '../components/case/CaseHeader';
import { CaseFileSections } from '../components/case/CaseFileSections';
import { useDemo } from '../state/DemoContext';
import type { Order } from '../types';

export interface ExceptionItem {
  id: string;
  orderId: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  type: 'Supplier unavailable' | 'Budget overrun' | 'Delivery delay' | 'Combined';
  cause: string;
  owner: string;
  age: string;
  status: string;
  orderRef?: Order;
}

export const ExceptionsPage: React.FC = () => {
  const {
    orders,
    dataMode,
    liveApprovals,
  } = useDemo();

  const [typeFilter, setTypeFilter] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [selectedException, setSelectedException] = useState<ExceptionItem | null>(null);

  // Derive unified exception queue from liveApprovals or fallback demo orders
  const exceptionQueue: ExceptionItem[] =
    dataMode === 'live' && liveApprovals.length > 0
      ? liveApprovals.map((app) => ({
          id: app.approval_id,
          orderId: app.scenario_id || 'ORD-1042',
          severity: 'High',
          type: app.domain?.toLowerCase().includes('budget') ? 'Budget overrun' : 'Supplier unavailable',
          cause: app.reason || 'Deterministic policy check flagged limit breach',
          owner: app.required_role || 'Finance Head',
          age: app.requested_at ? app.requested_at.split('T')[1]?.slice(0, 5) || '15m ago' : '10m ago',
          status: app.status.toLowerCase(),
          orderRef: orders[0],
        }))
      : [
          {
            id: 'EXC-2026-081',
            orderId: 'ORD-1042',
            severity: 'High',
            type: 'Budget overrun',
            cause: 'Requisition cost ₹16.6L exceeds allocated raw-material category budget of ₹14.2L',
            owner: 'Finance Controller',
            age: '12m ago',
            status: 'awaiting_approval',
            orderRef: orders.find((o) => o.id === 'ORD-1042') || orders[0],
          },
          {
            id: 'EXC-2026-080',
            orderId: 'ORD-1035',
            severity: 'Critical',
            type: 'Supplier unavailable',
            cause: 'Primary Bokaro steel mill reported 15 MT slab inventory stockout',
            owner: 'Procurement Lead',
            age: '45m ago',
            status: 'awaiting_approval',
            orderRef: orders[1] || orders[0],
          },
          {
            id: 'EXC-2026-079',
            orderId: 'ORD-1029',
            severity: 'Medium',
            type: 'Delivery delay',
            cause: 'Freight corridor weather bottleneck adds 36 hours beyond promised customer SLA',
            owner: 'Logistics Supervisor',
            age: '2h ago',
            status: 'approved',
            orderRef: orders[2] || orders[0],
          },
          {
            id: 'EXC-2026-078',
            orderId: 'ORD-1021',
            severity: 'High',
            type: 'Combined',
            cause: 'Supplier outage paired with corridor freight delay requiring alternative rail allocation',
            owner: 'Operations Director',
            age: '3h ago',
            status: 'rejected',
            orderRef: orders[3] || orders[0],
          },
        ];

  const filteredQueue = exceptionQueue.filter((item) => {
    const matchesType = typeFilter === 'All' || item.type === typeFilter;
    const matchesStatus =
      statusFilter === 'All' || item.status.toLowerCase() === statusFilter.toLowerCase();
    return matchesType && matchesStatus;
  });

  const columns: Column<ExceptionItem>[] = [
    {
      key: 'severity',
      header: 'Severity',
      render: (item) => {
        const squareColor = {
          Critical: 'bg-danger',
          High: 'bg-warn',
          Medium: 'bg-info',
          Low: 'bg-text-3',
        }[item.severity];

        return (
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-[2px] shrink-0 ${squareColor}`} />
            <span className="font-medium text-[12px]">{item.severity}</span>
          </div>
        );
      },
    },
    {
      key: 'type',
      header: 'Exception Type',
      render: (item) => <span className="font-medium text-text">{item.type}</span>,
    },
    {
      key: 'orderId',
      header: 'Order ID',
      render: (item) => (
        <span className="font-mono text-[12px] text-text-2 font-semibold">
          {item.orderId}
        </span>
      ),
    },
    {
      key: 'cause',
      header: 'Cause (One Line)',
      render: (item) => (
        <span className="text-text-2 text-[12px] max-w-md truncate block">
          {item.cause}
        </span>
      ),
    },
    {
      key: 'owner',
      header: 'Owner / Role',
      render: (item) => <span className="text-text-3 text-[12px]">{item.owner}</span>,
    },
    {
      key: 'age',
      header: 'Age',
      render: (item) => (
        <span className="font-mono text-[11px] text-text-3">{item.age}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <StatusBadge status={item.status} size="sm" />,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Exceptions & Human Governance Gates"
        description="Deterministic policy violation queue requiring operator review, override justification, or rejection."
      />

      {/* Filter Bar */}
      <div className="p-3.5 rounded-[6px] border border-border bg-surface flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[12px]">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="text-text-3">Exception Type:</span>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
            >
              <option value="All">All types</option>
              <option value="Supplier unavailable">Supplier unavailable</option>
              <option value="Budget overrun">Budget overrun</option>
              <option value="Delivery delay">Delivery delay</option>
              <option value="Combined">Combined</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-text-3">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
            >
              <option value="All">All statuses</option>
              <option value="awaiting_approval">Awaiting approval</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>

        <div className="text-[12px] text-text-3 font-mono">
          Pending Review: <strong className="text-warn">{filteredQueue.filter(i => i.status === 'awaiting_approval').length}</strong>
        </div>
      </div>

      {/* Exception Queue Table */}
      <Panel
        title={`Exception Queue (${filteredQueue.length} records)`}
        subtitle="Click any row to open the Case File focused on the Governance panel"
        padding="none"
      >
        <DataTable<ExceptionItem>
          columns={columns}
          data={filteredQueue}
          keyExtractor={(item) => item.id}
          onRowClick={(item) => setSelectedException(item)}
          emptyMessage="No exceptions pending operator review."
        />
      </Panel>

      {/* Case File Inspection Drawer focused on Governance */}
      <DetailDrawer
        isOpen={selectedException != null}
        onClose={() => setSelectedException(null)}
        title={selectedException ? `Exception Case: ${selectedException.id}` : 'Exception Case'}
        subtitle={selectedException ? `Order ${selectedException.orderId} • ${selectedException.type}` : undefined}
        width="680px"
      >
        {selectedException && (
          <div className="space-y-4">
            <CaseHeader
              orderId={selectedException.orderId}
              customer={selectedException.orderRef?.customer || 'Automotive Division'}
              status={selectedException.status}
              scenario={selectedException.type}
              isSimulated={dataMode === 'demo'}
            />

            <CaseFileSections
              order={selectedException.orderRef}
              isSimulated={dataMode === 'demo'}
            />
          </div>
        )}
      </DetailDrawer>
    </div>
  );
};
