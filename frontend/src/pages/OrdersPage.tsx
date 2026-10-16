import React, { useState, useEffect, useCallback } from 'react';
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
import {
  apiClient,
  type BackendOrderQueueItem,
  type BackendOrder,
  type CreateOrderRequest,
} from '../services/apiClient';
import { Search, ArrowLeft, Plus, RefreshCw, ListOrdered, History, CheckCircle2 } from 'lucide-react';
import type { Order, OrderStatus } from '../types';

const PRODUCT_CATALOG: Record<string, { name: string; defaultPrice: number; uom: string }> = {
  'PRD-HRC': { name: 'Hot Rolled Coil (IS 2062)', defaultPrice: 72000, uom: 'MT' },
  'PRD-CRC': { name: 'Cold Rolled Coil (CR1)', defaultPrice: 84500, uom: 'MT' },
  'PRD-REB': { name: 'High-Strength Rebar (Fe 500D)', defaultPrice: 61000, uom: 'MT' },
  'PRD-PLT': { name: 'Heavy Structural Steel Plate', defaultPrice: 79000, uom: 'MT' },
};

const ENTITY_OPTIONS = [
  { id: 'EAS-EAST', label: 'EAS-EAST — Eastern Steel Works (Bokaro/Jamshedpur)' },
  { id: 'EAS-WEST', label: 'EAS-WEST — Western Automotive Hub (Pune)' },
  { id: 'EAS-PORT', label: 'EAS-PORT — Maritime Terminal (Paradip Port)' },
  { id: 'EAS-HQ', label: 'EAS-HQ — Enterprise Control Hub (Kolkata)' },
];

export const OrdersPage: React.FC = () => {
  const { orders, dataMode, isLiveConnected } = useDemo();
  const isLive = dataMode === 'live';

  // Tabs: 'queue' (100 Pending) vs 'history' (100 Capped)
  const [activeTab, setActiveTab] = useState<'queue' | 'history'>('queue');

  // Backend state for Live mode
  const [queueItems, setQueueItems] = useState<BackendOrderQueueItem[]>([]);
  const [historyOrders, setHistoryOrders] = useState<BackendOrder[]>([]);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Filters & selection
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [priorityFilter, setPriorityFilter] = useState<string>('All');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);

  // New Order Drawer & Form
  const [isNewOrderDrawerOpen, setIsNewOrderDrawerOpen] = useState(false);
  const [newCustomer, setNewCustomer] = useState('');
  const [newEntity, setNewEntity] = useState('EAS-EAST');
  const [newProductId, setNewProductId] = useState('PRD-HRC');
  const [newQty, setNewQty] = useState('45');
  const [newUnitPrice, setNewUnitPrice] = useState('72000');
  const [newPriority, setNewPriority] = useState<'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'>('MEDIUM');
  const [newExtRef, setNewExtRef] = useState('');
  const [isSubmittingOrder, setIsSubmittingOrder] = useState(false);
  const [orderSubmitSuccess, setOrderSubmitSuccess] = useState<string | null>(null);
  const [orderSubmitError, setOrderSubmitError] = useState<string | null>(null);

  // Fetch live queue and history from backend
  const fetchOrdersData = useCallback(async () => {
    if (!isLive) return;
    setIsLoadingData(true);
    setLoadError(null);
    try {
      const [queueRes, historyRes] = await Promise.all([
        apiClient.getOrderQueue(100),
        apiClient.getOrderHistory(100),
      ]);
      setQueueItems(queueRes || []);
      setHistoryOrders(historyRes || []);
    } catch (err: any) {
      setLoadError(err?.message || 'Failed to load order queue or history from backend');
    } finally {
      setIsLoadingData(false);
    }
  }, [isLive]);

  useEffect(() => {
    if (isLive) {
      fetchOrdersData();
    }
  }, [isLive, fetchOrdersData]);

  // Handle product change to update default unit price
  const handleProductSelect = (prodId: string) => {
    setNewProductId(prodId);
    if (PRODUCT_CATALOG[prodId]) {
      setNewUnitPrice(PRODUCT_CATALOG[prodId].defaultPrice.toString());
    }
  };

  // Submit manual order to POST /api/orders/
  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCustomer.trim()) {
      setOrderSubmitError('Customer name/reference is required.');
      return;
    }
    const qtyNum = parseFloat(newQty);
    if (isNaN(qtyNum) || qtyNum <= 0) {
      setOrderSubmitError('Quantity must be greater than zero.');
      return;
    }
    const unitPriceNum = parseFloat(newUnitPrice);
    if (isNaN(unitPriceNum) || unitPriceNum <= 0) {
      setOrderSubmitError('Unit price must be greater than zero.');
      return;
    }

    setIsSubmittingOrder(true);
    setOrderSubmitError(null);
    setOrderSubmitSuccess(null);

    const payload: CreateOrderRequest = {
      customer_ref: newCustomer.trim(),
      entity_id: newEntity,
      priority: newPriority,
      external_reference: newExtRef.trim() || undefined,
      lines: [
        {
          product_id: newProductId,
          requested_qty: qtyNum,
          unit_price_inr: unitPriceNum,
          uom: PRODUCT_CATALOG[newProductId]?.uom || 'MT',
        },
      ],
    };

    try {
      if (isLive) {
        const res = await apiClient.createOrder(payload);
        setOrderSubmitSuccess(
          `Order ${res.order_id} created successfully! Enqueued at position #${res.queue_position}.`
        );
        // Reset form and reload
        setNewCustomer('');
        setNewExtRef('');
        setTimeout(() => {
          setIsNewOrderDrawerOpen(false);
          setOrderSubmitSuccess(null);
          fetchOrdersData();
        }, 1800);
      } else {
        setOrderSubmitSuccess('Order simulated in demo memory mode.');
        setTimeout(() => {
          setIsNewOrderDrawerOpen(false);
          setOrderSubmitSuccess(null);
        }, 1200);
      }
    } catch (err: any) {
      setOrderSubmitError(err?.message || 'Failed to persist order to backend database.');
    } finally {
      setIsSubmittingOrder(false);
    }
  };

  // Map queue items to Order structure for DataTable
  const queueDisplayList: Order[] = isLive
    ? queueItems.map((q) => ({
        id: q.order_id,
        customer: q.customer_ref || 'Industrial Client',
        product: 'Industrial Steel Product',
        quantity: 50,
        destination: q.entity_id || 'EAS-EAST',
        budget: q.total_amount_inr || 2500000,
        estimatedCost: q.total_amount_inr || 2400000,
        status: (q.status === 'COMPLETED'
          ? 'Completed'
          : q.status === 'PROCESSING'
          ? 'Processing'
          : q.status === 'WAITING_EXCEPTION'
          ? 'Exception'
          : 'Approved') as OrderStatus,
        priority: (q.priority === 'CRITICAL'
          ? 'Critical'
          : q.priority === 'HIGH'
          ? 'High'
          : q.priority === 'MEDIUM'
          ? 'Medium'
          : 'Low') as any,
        currentAgent: 'supervisor',
        createdAt: q.enqueued_at ? q.enqueued_at.split('T')[0] : '2026-10-16',
      }))
    : orders;

  // Map history orders to Order structure
  const historyDisplayList: Order[] = isLive
    ? historyOrders.map((ho) => ({
        id: ho.order_id,
        customer: ho.customer_name,
        product: 'Structural / Flat Steel',
        quantity: 40,
        destination: 'Eastern Processing Hub',
        budget: ho.total_amount_inr || 3200000,
        estimatedCost: ho.total_amount_inr || 3100000,
        status: 'Completed' as OrderStatus,
        priority: (ho.priority === 'CRITICAL'
          ? 'Critical'
          : ho.priority === 'HIGH'
          ? 'High'
          : ho.priority === 'MEDIUM'
          ? 'Medium'
          : 'Low') as any,
        currentAgent: 'supervisor',
        createdAt: ho.order_date ? ho.order_date.split('T')[0] : '2026-10-15',
      }))
    : orders.slice(0, 10);

  const activeDisplayList = activeTab === 'queue' ? queueDisplayList : historyDisplayList;

  const filteredOrders = activeDisplayList.filter((o) => {
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
      render: (o, idx) => (
        <div className="flex items-center gap-2">
          {activeTab === 'queue' && isLive && (
            <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-surface-2 text-text-3 font-semibold">
              #{idx + 1}
            </span>
          )}
          <span className="font-mono text-[12px] font-semibold text-text">{o.id}</span>
        </div>
      ),
    },
    {
      key: 'customer',
      header: 'Customer Reference',
      render: (o) => <span className="text-text font-medium">{o.customer}</span>,
    },
    {
      key: 'destination',
      header: 'Entity / Destination',
      render: (o) => <span className="font-mono text-[11px] text-text-2">{o.destination}</span>,
    },
    {
      key: 'budget',
      header: 'Value (INR)',
      isNumeric: true,
      render: (o) => (
        <span className="font-mono">
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
      header: 'Engine',
      render: () => (
        <SourceBadge forcedState={isLive ? 'live' : 'simulated'} variant="tag" />
      ),
    },
  ];

  // Full-width Case File View if an order row was clicked
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
          isSimulated={!isLive}
        />

        <PipelineStepper />

        <CaseFileSections order={selectedOrder} isSimulated={!isLive} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Orders & Requisitions"
        description="Dual view: 100-item sequential processing queue and 100-record capped execution history."
        actions={
          <div className="flex items-center gap-2">
            {isLive && (
              <button
                type="button"
                onClick={fetchOrdersData}
                disabled={isLoadingData}
                className="inline-flex items-center gap-1.5 h-[32px] px-3 bg-surface border border-border hover:border-accent text-text text-[12px] font-medium rounded-[4px] transition-colors cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingData ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => setIsNewOrderDrawerOpen(true)}
              className="inline-flex items-center gap-1.5 h-[32px] px-3 bg-accent hover:bg-accent-hover text-white text-[12px] font-medium rounded-[4px] transition-colors cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>New order</span>
            </button>
          </div>
        }
      />

      {/* Mode / Connection Alert if offline */}
      {isLive && !isLiveConnected && (
        <div className="p-3 rounded-[6px] bg-danger/10 border border-danger/30 text-danger text-[12px]">
          Backend is disconnected or unreachable on port 8000. Displaying cached state.
        </div>
      )}

      {loadError && (
        <div className="p-3 rounded-[6px] bg-danger/10 border border-danger/30 text-danger text-[12px]">
          {loadError}
        </div>
      )}

      {/* Dual Tab Switcher */}
      <div className="flex items-center gap-3 border-b border-border pb-2">
        <button
          type="button"
          onClick={() => setActiveTab('queue')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-[4px] text-[13px] font-medium transition-colors cursor-pointer ${
            activeTab === 'queue'
              ? 'bg-accent text-white shadow-sm'
              : 'bg-surface hover:bg-surface-2 text-text-2 border border-border'
          }`}
        >
          <ListOrdered className="w-4 h-4" />
          <span>Processing Queue</span>
          {isLive && queueItems.length > 0 && (
            <span
              className={`text-[11px] font-mono px-1.5 py-0.2 rounded-full ${
                activeTab === 'queue' ? 'bg-white/20 text-white' : 'bg-surface-sunk text-text-3'
              }`}
            >
              {queueItems.length}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('history')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-[4px] text-[13px] font-medium transition-colors cursor-pointer ${
            activeTab === 'history'
              ? 'bg-accent text-white shadow-sm'
              : 'bg-surface hover:bg-surface-2 text-text-2 border border-border'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Processed History (Cap 100)</span>
          {isLive && historyOrders.length > 0 && (
            <span
              className={`text-[11px] font-mono px-1.5 py-0.2 rounded-full ${
                activeTab === 'history' ? 'bg-white/20 text-white' : 'bg-surface-sunk text-text-3'
              }`}
            >
              {historyOrders.length}
            </span>
          )}
        </button>
      </div>

      {/* Filter Bar */}
      <div className="p-3.5 rounded-[6px] border border-border bg-surface flex flex-col md:flex-row md:items-center justify-between gap-3 text-[13px]">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-3" />
          <input
            type="text"
            placeholder="Search by order ID, customer or product..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-[32px] pl-8 pr-3 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] placeholder:text-text-3 focus:outline-none focus:border-accent"
          />
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="text-text-3 text-[12px]">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
            >
              <option value="All">All Statuses</option>
              <option value="Approved">Approved / Queued</option>
              <option value="Processing">Processing</option>
              <option value="Exception">Exception</option>
              <option value="Completed">Completed</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-text-3 text-[12px]">Priority:</span>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
            >
              <option value="All">All Priorities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>
        </div>
      </div>

      {/* Orders Table Panel */}
      <Panel
        title={
          activeTab === 'queue'
            ? `Pending Order Processing Queue (${filteredOrders.length})`
            : `Processed History — Capped Most Recent 100 Orders (${filteredOrders.length})`
        }
        subtitle="Click any row to open the complete case file and governance evidence"
        padding="none"
      >
        <DataTable<Order>
          columns={columns}
          data={filteredOrders}
          keyExtractor={(o) => o.id}
          isLoading={isLoadingData}
          onRowClick={(o) => setSelectedOrder(o)}
          emptyMessage="No orders match the current filter criteria."
        />
      </Panel>

      {/* New Order Drawer */}
      <DetailDrawer
        isOpen={isNewOrderDrawerOpen}
        onClose={() => {
          setIsNewOrderDrawerOpen(false);
          setOrderSubmitError(null);
          setOrderSubmitSuccess(null);
        }}
        title="Create New Requisition"
        subtitle="Dispatch transactional order with lines into PostgreSQL and the processing queue"
      >
        <form onSubmit={handleCreateOrder} className="space-y-4">
          <div>
            <label className="block text-[12px] font-medium text-text mb-1">
              Customer Name / Reference *
            </label>
            <input
              type="text"
              required
              value={newCustomer}
              onChange={(e) => setNewCustomer(e.target.value)}
              placeholder="e.g. Tata Motors Commercial Vehicles"
              className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent"
            />
          </div>

          <div>
            <label className="block text-[12px] font-medium text-text mb-1">
              Target Entity / Manufacturing Hub *
            </label>
            <select
              value={newEntity}
              onChange={(e) => setNewEntity(e.target.value)}
              className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
            >
              {ENTITY_OPTIONS.map((ent) => (
                <option key={ent.id} value={ent.id}>
                  {ent.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[12px] font-medium text-text mb-1">
              Product Specification *
            </label>
            <select
              value={newProductId}
              onChange={(e) => handleProductSelect(e.target.value)}
              className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
            >
              {Object.entries(PRODUCT_CATALOG).map(([id, info]) => (
                <option key={id} value={id}>
                  {id} — {info.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[12px] font-medium text-text mb-1">
                Quantity (MT) *
              </label>
              <input
                type="number"
                required
                min="1"
                step="0.5"
                value={newQty}
                onChange={(e) => setNewQty(e.target.value)}
                className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] font-mono focus:outline-none focus:border-accent"
              />
            </div>

            <div>
              <label className="block text-[12px] font-medium text-text mb-1">
                Unit Price (INR/MT) *
              </label>
              <input
                type="number"
                required
                min="1000"
                step="100"
                value={newUnitPrice}
                onChange={(e) => setNewUnitPrice(e.target.value)}
                className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] font-mono focus:outline-none focus:border-accent"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[12px] font-medium text-text mb-1">
                Priority Level *
              </label>
              <select
                value={newPriority}
                onChange={(e) => setNewPriority(e.target.value as any)}
                className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>

            <div>
              <label className="block text-[12px] font-medium text-text mb-1">
                External PO Ref
              </label>
              <input
                type="text"
                value={newExtRef}
                onChange={(e) => setNewExtRef(e.target.value)}
                placeholder="e.g. PO-IND-2026-99"
                className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] font-mono focus:outline-none focus:border-accent"
              />
            </div>
          </div>

          {/* Computed Estimated Spend Summary */}
          <div className="p-2.5 rounded bg-surface-sunk border border-border text-[11px] space-y-1">
            <div className="flex justify-between text-text-3">
              <span>Estimated Order Total:</span>
              <span className="font-mono text-text font-semibold">
                {new Intl.NumberFormat('en-IN', {
                  style: 'currency',
                  currency: 'INR',
                  maximumFractionDigits: 0,
                }).format((parseFloat(newQty) || 0) * (parseFloat(newUnitPrice) || 0))}
              </span>
            </div>
            <div className="flex justify-between text-text-3">
              <span>Origin Assignment:</span>
              <span className="font-mono text-accent">MANUAL_OPERATOR</span>
            </div>
          </div>

          {orderSubmitError && (
            <div className="p-2.5 rounded bg-danger/10 border border-danger/30 text-danger text-[11px]">
              {orderSubmitError}
            </div>
          )}

          {orderSubmitSuccess && (
            <div className="p-2.5 rounded bg-ok/10 border border-ok/30 text-ok text-[11px] flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
              <span>{orderSubmitSuccess}</span>
            </div>
          )}

          <div className="pt-3 border-t border-border">
            <button
              type="submit"
              disabled={isSubmittingOrder || !newCustomer.trim()}
              className="w-full h-[36px] rounded-[4px] bg-accent hover:bg-accent-hover text-white text-[12px] font-medium transition-colors cursor-pointer disabled:bg-surface-2 disabled:text-text-3 disabled:cursor-not-allowed"
            >
              {isSubmittingOrder ? 'Persisting Order to Database...' : 'Submit Order & Enqueue'}
            </button>
          </div>
        </form>
      </DetailDrawer>
    </div>
  );
};
