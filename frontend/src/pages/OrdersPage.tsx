import React, { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Panel } from '../components/common/Panel';
import { DataTable, type Column } from '../components/common/DataTable';
import { StatusBadge } from '../components/common/StatusBadge';
import { SourceBadge } from '../components/common/SourceBadge';
import { DetailDrawer } from '../components/common/DetailDrawer';
import { CaseHeader } from '../components/case/CaseHeader';
import { PipelineStepper } from '../components/case/PipelineStepper';
import { CaseFileSections } from '../components/case/CaseFileSections';
import { useDemo } from '../state/DemoContext';
import { Search, ArrowLeft, Plus } from 'lucide-react';
import type { Order, OrderStatus } from '../types';

export const OrdersPage: React.FC = () => {
  const { orders, dataMode, liveOrders, liveLoading, isLiveConnected } = useDemo();

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [priorityFilter, setPriorityFilter] = useState<string>('All');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [isNewOrderDrawerOpen, setIsNewOrderDrawerOpen] = useState(false);

  // New order form fields
  const [newCustomer, setNewCustomer] = useState('');
  const [newProduct, setNewProduct] = useState('Hot Rolled Steel Coils (IS 2062 E250)');
  const [newQty, setNewQty] = useState('25');
  const [newDestination, setNewDestination] = useState('Pune Automotive Cluster');
  const [newBudget, setNewBudget] = useState('1250000');
  const [newPriority, setNewPriority] = useState<'Low' | 'Medium' | 'High' | 'Critical'>('Medium');

  const activeOrdersList: Order[] =
    dataMode === 'live' && liveOrders.length > 0
      ? liveOrders.map((lo) => ({
          id: lo.order_id,
          customer: lo.customer_name,
          product: 'Hot Rolled Steel Coils (IS 2062)',
          quantity: 25,
          destination: 'Pune Automotive Cluster',
          budget: lo.total_amount_inr || 1250000,
          estimatedCost: lo.total_amount_inr || 1220000,
          status: (lo.order_status === 'SHIPPED' || lo.order_status === 'DELIVERED'
            ? 'Completed'
            : lo.order_status === 'PROCESSING' || lo.order_status === 'CONFIRMED'
            ? 'Processing'
            : lo.order_status === 'EXCEPTION'
            ? 'Exception'
            : 'Approved') as OrderStatus,
          priority: (lo.priority === 'CRITICAL'
            ? 'Critical'
            : lo.priority === 'HIGH'
            ? 'High'
            : lo.priority === 'MEDIUM'
            ? 'Medium'
            : 'Low') as any,
          currentAgent: 'supervisor',
          createdAt: lo.order_date ? lo.order_date.split('T')[0] : '2026-10-15',
        }))
      : orders;

  const filteredOrders = activeOrdersList.filter((o) => {
    const matchesSearch =
      !searchQuery ||
      o.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      o.customer.toLowerCase().includes(searchQuery.toLowerCase()) ||
      o.product.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'All' || o.status === statusFilter;
    const matchesPriority = priorityFilter === 'All' || o.priority === priorityFilter;
    return matchesSearch && matchesStatus && matchesPriority;
  });

  const columns: Column<Order>[] = [
    {
      key: 'id',
      header: 'Order ID',
      render: (o) => (
        <span className="font-mono text-[12px] font-semibold text-text">
          {o.id}
        </span>
      ),
    },
    {
      key: 'customer',
      header: 'Customer',
      render: (o) => <span className="text-text font-medium">{o.customer}</span>,
    },
    {
      key: 'product',
      header: 'Product / Grade',
      render: (o) => (
        <span className="text-text-2 text-[12px] max-w-xs truncate block">
          {o.product}
        </span>
      ),
    },
    {
      key: 'quantity',
      header: 'Qty (MT)',
      isNumeric: true,
      render: (o) => <span>{o.quantity} MT</span>,
    },
    {
      key: 'budget',
      header: 'Budget (INR)',
      isNumeric: true,
      render: (o) => (
        <span>
          {new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0,
          }).format(o.budget)}
        </span>
      ),
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (o) => (
        <span
          className={`font-mono text-[11px] font-medium ${
            o.priority === 'Critical'
              ? 'text-danger'
              : o.priority === 'High'
              ? 'text-warn'
              : 'text-text-3'
          }`}
        >
          {o.priority}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (o) => <StatusBadge status={o.status} size="sm" />,
    },
    {
      key: 'source',
      header: 'Source',
      render: () => (
        <SourceBadge forcedState={dataMode === 'live' ? 'live' : 'simulated'} variant="tag" />
      ),
    },
  ];

  // If a case is selected, render the full-width Case File View
  if (selectedOrder) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <button
            type="button"
            onClick={() => setSelectedOrder(null)}
            className="inline-flex items-center gap-1.5 text-[13px] text-accent hover:underline font-medium cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Orders List</span>
          </button>
          <div className="flex items-center gap-2">
            <span className="text-[12px] text-text-3">Viewing Case File:</span>
            <span className="font-mono text-[13px] font-semibold text-text">
              {selectedOrder.id}
            </span>
          </div>
        </div>

        <CaseHeader
          orderId={selectedOrder.id}
          customer={selectedOrder.customer}
          status={selectedOrder.status}
          priority={selectedOrder.priority}
          isSimulated={dataMode === 'demo'}
        />

        <PipelineStepper />

        <CaseFileSections order={selectedOrder} isSimulated={dataMode === 'demo'} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Orders & Requisitions"
        description="Fulfillment tracking, requisition dispatch, and case file investigation."
        actions={
          <button
            type="button"
            onClick={() => setIsNewOrderDrawerOpen(true)}
            className="inline-flex items-center gap-1.5 h-[32px] px-3 bg-accent hover:bg-accent-hover text-white text-[12px] font-medium rounded-[4px] transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New order</span>
          </button>
        }
      />

      {/* Filter Bar */}
      <div className="p-3 rounded-[6px] border border-border bg-surface flex flex-col md:flex-row md:items-center justify-between gap-3 text-[12px]">
        {/* Search Input */}
        <div className="relative flex-1 max-w-sm">
          <Search className="w-3.5 h-3.5 text-text-3 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search order ID, customer, product..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-[32px] pl-8 pr-3 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent"
          />
        </div>

        {/* Dropdowns */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="text-text-3">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
            >
              <option value="All">All statuses</option>
              <option value="Processing">Processing</option>
              <option value="Approved">Approved</option>
              <option value="Exception">Exception</option>
              <option value="Delayed">Delayed</option>
              <option value="Completed">Completed</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-text-3">Priority:</span>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
            >
              <option value="All">All priorities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>
        </div>
      </div>

      {/* Orders DataTable */}
      <Panel
        title={`All Orders (${filteredOrders.length})`}
        subtitle="Click any row to open the full-width case file view"
        padding="none"
      >
        <DataTable<Order>
          columns={columns}
          data={filteredOrders}
          keyExtractor={(o) => o.id}
          isLoading={liveLoading}
          onRowClick={(o) => setSelectedOrder(o)}
          emptyMessage="No orders match the current search and filter criteria."
        />
      </Panel>

      {/* New Order DetailDrawer */}
      <DetailDrawer
        isOpen={isNewOrderDrawerOpen}
        onClose={() => setIsNewOrderDrawerOpen(false)}
        title="Create New Requisition"
        subtitle="Dispatch custom order into the governed multi-agent mesh"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-[12px] font-medium text-text mb-1">
              Customer Name:
            </label>
            <input
              type="text"
              value={newCustomer}
              onChange={(e) => setNewCustomer(e.target.value)}
              placeholder="e.g. Tata Motors Commercial Division"
              className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent"
            />
          </div>

          <div>
            <label className="block text-[12px] font-medium text-text mb-1">
              Product Grade / Specification:
            </label>
            <input
              type="text"
              value={newProduct}
              onChange={(e) => setNewProduct(e.target.value)}
              className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[12px] font-medium text-text mb-1">
                Quantity (MT):
              </label>
              <input
                type="number"
                value={newQty}
                onChange={(e) => setNewQty(e.target.value)}
                className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] font-mono focus:outline-none focus:border-accent"
              />
            </div>

            <div>
              <label className="block text-[12px] font-medium text-text mb-1">
                Budget Limit (INR):
              </label>
              <input
                type="number"
                value={newBudget}
                onChange={(e) => setNewBudget(e.target.value)}
                className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] font-mono focus:outline-none focus:border-accent"
              />
            </div>
          </div>

          <div>
            <label className="block text-[12px] font-medium text-text mb-1">
              Destination Hub:
            </label>
            <input
              type="text"
              value={newDestination}
              onChange={(e) => setNewDestination(e.target.value)}
              className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent"
            />
          </div>

          <div>
            <label className="block text-[12px] font-medium text-text mb-1">
              Priority Classification:
            </label>
            <select
              value={newPriority}
              onChange={(e) => setNewPriority(e.target.value as any)}
              className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent"
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
              <option value="Critical">Critical</option>
            </select>
          </div>

          {/* Submission Notice & Controls */}
          <div className="pt-3 border-t border-border space-y-2">
            {dataMode === 'demo' ? (
              <p className="text-[11px] text-text-3 leading-normal">
                Mode is Simulated. Switch to Live mode with PostgreSQL backend to commit persistent orders.
              </p>
            ) : !isLiveConnected ? (
              <p className="text-[11px] text-danger leading-normal">
                Backend unreachable on port 8000. Start the backend service to submit orders.
              </p>
            ) : null}

            <button
              type="button"
              disabled={dataMode !== 'live' || !isLiveConnected || !newCustomer.trim()}
              title={
                dataMode !== 'live'
                  ? 'Switch to live mode to commit orders'
                  : !isLiveConnected
                  ? 'Backend unreachable'
                  : !newCustomer.trim()
                  ? 'Customer name is required'
                  : 'Dispatch order'
              }
              className="w-full h-[36px] rounded-[4px] bg-accent hover:bg-accent-hover text-white text-[12px] font-medium transition-colors cursor-pointer disabled:bg-surface-2 disabled:text-text-3 disabled:cursor-not-allowed"
            >
              Dispatch Requisition to Mesh
            </button>
          </div>
        </div>
      </DetailDrawer>
    </div>
  );
};
