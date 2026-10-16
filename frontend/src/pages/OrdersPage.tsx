import React, { useState, useEffect, useCallback } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Panel } from '../components/common/Panel';
import { DetailDrawer } from '../components/common/DetailDrawer';
import { useDemo } from '../state/DemoContext';
import {
  apiClient,
  type LifecycleQueuedOrder,
  type LifecycleRunningOrder,
  type LifecycleDoneOrder,
  type CreateOrderRequest,
} from '../services/apiClient';
import {
  Search,
  Plus,
  RefreshCw,
  ListOrdered,
  History,
  CheckCircle2,
  Play,
  Layers,
  Cpu,
  AlertTriangle,
} from 'lucide-react';

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
  const { dataMode } = useDemo();
  const isLive = dataMode === 'live';

  // 3 Distinct Tabs: 'queue' (FIFO pending), 'running' (currently executing), 'done' (processed history)
  const [activeTab, setActiveTab] = useState<'queue' | 'running' | 'done'>('queue');

  // Backend state
  const [queuedOrders, setQueuedOrders] = useState<LifecycleQueuedOrder[]>([]);
  const [runningOrders, setRunningOrders] = useState<LifecycleRunningOrder[]>([]);
  const [doneOrders, setDoneOrders] = useState<LifecycleDoneOrder[]>([]);
  const [isLoadingData, setIsLoadingData] = useState(false);

  // Execution state
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionMessage, setExecutionMessage] = useState<string | null>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState('NORMAL');

  // Filters & selection
  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState<string>('All');

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

  // Fetch live orders across the 3 lifecycle states
  const fetchOrdersData = useCallback(async () => {
    if (!isLive) return;
    setIsLoadingData(true);
    try {
      const [queuedRes, runningRes, doneRes] = await Promise.all([
        apiClient.getLifecycleQueued(100),
        apiClient.getLifecycleRunning(),
        apiClient.getLifecycleDone(100),
      ]);
      setQueuedOrders(queuedRes || []);
      setRunningOrders(runningRes || []);
      setDoneOrders(doneRes || []);
    } catch (_err: any) {
      // Quiet background polling error
    } finally {
      setIsLoadingData(false);
    }
  }, [isLive]);

  useEffect(() => {
    if (isLive) {
      fetchOrdersData();
      const interval = setInterval(fetchOrdersData, 4000);
      return () => clearInterval(interval);
    }
  }, [isLive, fetchOrdersData]);

  // Handle product change in new order drawer
  const handleProductSelect = (prodId: string) => {
    setNewProductId(prodId);
    if (PRODUCT_CATALOG[prodId]) {
      setNewUnitPrice(PRODUCT_CATALOG[prodId].defaultPrice.toString());
    }
  };

  // Submit manual order
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

    const idempotencyKey = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `ord-idem-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

    const payload: CreateOrderRequest = {
      customer_ref: newCustomer.trim(),
      entity_id: newEntity,
      priority: newPriority,
      external_reference: newExtRef.trim() || undefined,
      idempotency_key: idempotencyKey,
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
        setNewCustomer('');
        setNewExtRef('');
        setTimeout(() => {
          setIsNewOrderDrawerOpen(false);
          setOrderSubmitSuccess(null);
          fetchOrdersData();
        }, 1500);
      }
    } catch (err: any) {
      setOrderSubmitError(err?.message || 'Failed to persist order to backend database.');
    } finally {
      setIsSubmittingOrder(false);
    }
  };

  // Run next FIFO queued order
  const handleRunNextOrder = async () => {
    setIsExecuting(true);
    setExecutionError(null);
    setExecutionMessage(null);
    try {
      const res = await apiClient.runNextLifecycleOrder(selectedScenario);
      if (res.executed) {
        if (res.status === 'EXCEPTION') {
          setExecutionMessage(
            `⚠️ Order ${res.order_id} triggered ${res.exception_type}: ${res.exception_cause}. Held in live Exceptions.`
          );
        } else {
          setExecutionMessage(
            `✅ Order ${res.order_id} fulfilled in ${res.duration_ms}ms and anchored in Blockchain Block #${res.block_number}.`
          );
        }
      } else {
        setExecutionMessage(res.message);
      }
      await fetchOrdersData();
    } catch (err: any) {
      setExecutionError(err?.message || 'Failed to pop and run order from queue');
    } finally {
      setIsExecuting(false);
    }
  };

  // Run specific order from queue
  const handleRunSpecificOrder = async (orderId: string) => {
    setIsExecuting(true);
    setExecutionError(null);
    setExecutionMessage(null);
    try {
      const res = await apiClient.runSpecificLifecycleOrder(orderId, selectedScenario);
      if (res.executed) {
        if (res.status === 'EXCEPTION') {
          setExecutionMessage(
            `⚠️ Order ${res.order_id} triggered ${res.exception_type}: ${res.exception_cause}.`
          );
        } else {
          setExecutionMessage(
            `✅ Order ${res.order_id} completed successfully and anchored in Block #${res.block_number}.`
          );
        }
      } else {
        setExecutionMessage(res.message);
      }
      await fetchOrdersData();
    } catch (err: any) {
      setExecutionError(err?.message || `Failed to run order ${orderId}`);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Orders & Requisitions Lifecycle"
        description="Dynamic three-tier order lifecycle: FIFO pending queue, active agent mesh execution, and immutable processed history."
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
              className="inline-flex items-center gap-1.5 h-[32px] px-3.5 bg-accent hover:bg-accent-hover text-white text-[12px] font-medium rounded-[4px] transition-colors cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Order</span>
            </button>
          </div>
        }
      />

      {/* Orchestration Control Strip */}
      <div className="p-4 rounded-[6px] border border-border bg-surface space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-accent" />
              <span className="font-semibold text-[13px] text-text">Orchestration Runner:</span>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-ok/20 text-ok font-semibold">
                FIFO ACTIVE
              </span>
            </div>

            <div className="flex items-center gap-2 text-[12px] text-text-3 border-l border-border pl-3">
              <span>Scenario:</span>
              <select
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
                className="h-[28px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] font-medium focus:outline-none focus:border-accent cursor-pointer"
              >
                <option value="NORMAL">Normal Consensus</option>
                <option value="SUPPLIER_UNAVAILABLE">Supplier Unavailable (Exception)</option>
                <option value="BUDGET_BREACH">Budget Breach (Exception)</option>
                <option value="DELIVERY_DELAY">Delivery Delay (Exception)</option>
                <option value="STOCK_SHORTFALL">Stock Shortfall (Exception)</option>
              </select>
            </div>
          </div>

          <button
            type="button"
            onClick={handleRunNextOrder}
            disabled={isExecuting || queuedOrders.length === 0}
            className="inline-flex items-center gap-2 h-[34px] px-4 bg-accent hover:bg-accent-hover text-white text-[12px] font-semibold rounded-[4px] transition-colors cursor-pointer disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${isExecuting ? 'animate-pulse' : ''}`} />
            <span>{isExecuting ? 'Processing Order...' : '⚡ Run Next Queued Order (FIFO)'}</span>
          </button>
        </div>

        {/* Dynamic Metric Badges */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-border text-[12px]">
          <div
            onClick={() => setActiveTab('queue')}
            className={`p-2.5 rounded border cursor-pointer transition-colors ${
              activeTab === 'queue' ? 'border-accent bg-accent/5' : 'border-border bg-surface-sunk'
            }`}
          >
            <span className="text-text-3 text-[11px] block">Queued Orders (FIFO)</span>
            <span className="font-mono text-text font-bold text-[16px]">
              {queuedOrders.length}
            </span>
          </div>
          <div
            onClick={() => setActiveTab('running')}
            className={`p-2.5 rounded border cursor-pointer transition-colors ${
              activeTab === 'running' ? 'border-accent bg-accent/5' : 'border-border bg-surface-sunk'
            }`}
          >
            <span className="text-text-3 text-[11px] block">Active Running Orders</span>
            <span className={`font-mono font-bold text-[16px] ${runningOrders.length > 0 ? 'text-accent' : 'text-text-3'}`}>
              {runningOrders.length}
            </span>
          </div>
          <div
            onClick={() => setActiveTab('done')}
            className={`p-2.5 rounded border cursor-pointer transition-colors ${
              activeTab === 'done' ? 'border-accent bg-accent/5' : 'border-border bg-surface-sunk'
            }`}
          >
            <span className="text-text-3 text-[11px] block">Processed Orders (History)</span>
            <span className="font-mono text-ok font-bold text-[16px]">
              {doneOrders.length}
            </span>
          </div>
        </div>
      </div>

      {/* Execution Feedback Banners */}
      {executionMessage && (
        <div className="p-3 rounded-[4px] border border-ok/40 bg-ok/10 text-ok text-[12px] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{executionMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setExecutionMessage(null)}
            className="text-text-3 hover:text-text text-[11px]"
          >
            Dismiss
          </button>
        </div>
      )}

      {executionError && (
        <div className="p-3 rounded-[4px] border border-danger/40 bg-danger/10 text-danger text-[12px] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{executionError}</span>
          </div>
          <button
            type="button"
            onClick={() => setExecutionError(null)}
            className="text-text-3 hover:text-text text-[11px]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Tab Switcher */}
      <div className="flex items-center gap-1 border-b border-border pb-1">
        <button
          type="button"
          onClick={() => setActiveTab('queue')}
          className={`flex items-center gap-2 px-4 py-2 text-[13px] font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === 'queue'
              ? 'border-accent text-accent'
              : 'border-transparent text-text-3 hover:text-text'
          }`}
        >
          <ListOrdered className="w-4 h-4" />
          <span>FIFO Queue ({queuedOrders.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('running')}
          className={`flex items-center gap-2 px-4 py-2 text-[13px] font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === 'running'
              ? 'border-accent text-accent'
              : 'border-transparent text-text-3 hover:text-text'
          }`}
        >
          <Cpu className="w-4 h-4" />
          <span>Active Running ({runningOrders.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('done')}
          className={`flex items-center gap-2 px-4 py-2 text-[13px] font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === 'done'
              ? 'border-accent text-accent'
              : 'border-transparent text-text-3 hover:text-text'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Processed Done ({doneOrders.length})</span>
        </button>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[12px]">
        <div className="relative flex-1 max-w-[320px]">
          <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-3" />
          <input
            type="text"
            placeholder="Search by Order ID, customer, product..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-[32px] pl-8 pr-3 rounded-[4px] bg-surface border border-border text-text text-[12px] placeholder:text-text-3 focus:outline-none focus:border-accent"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-text-3">Priority:</span>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="h-[32px] px-2 rounded-[4px] bg-surface border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
          >
            <option value="All">All Priorities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {/* TAB 1: FIFO QUEUE */}
      {activeTab === 'queue' && (
        <Panel
          title="FIFO Order Queue"
          subtitle="Orders waiting for autonomous multi-agent execution. Popped strictly in first-in first-out order."
          padding="none"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-[12px] text-left">
              <thead className="bg-surface-sunk text-text-3 border-b border-border font-medium">
                <tr>
                  <th className="py-2.5 px-3">Position</th>
                  <th className="py-2.5 px-3">Order ID</th>
                  <th className="py-2.5 px-3">Customer Reference</th>
                  <th className="py-2.5 px-3">Product</th>
                  <th className="py-2.5 px-3 text-right">Quantity (Tons)</th>
                  <th className="py-2.5 px-3">Priority</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {queuedOrders
                  .filter((q) => {
                    const matchesSearch =
                      !searchQuery ||
                      q.order_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                      q.customer_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                      q.product_code.toLowerCase().includes(searchQuery.toLowerCase());
                    const matchesPriority =
                      priorityFilter === 'All' || q.priority === priorityFilter;
                    return matchesSearch && matchesPriority;
                  })
                  .map((q, idx) => (
                    <tr key={q.queue_id} className="hover:bg-surface-2 transition-colors">
                      <td className="py-2 px-3 font-mono font-bold text-accent">
                        #{idx + 1}
                      </td>
                      <td className="py-2 px-3 font-mono font-semibold text-text">
                        {q.order_id}
                      </td>
                      <td className="py-2 px-3 text-text font-medium">
                        {q.customer_name}
                      </td>
                      <td className="py-2 px-3 font-mono text-text-2">
                        {q.product_code}
                      </td>
                      <td className="py-2 px-3 font-mono text-right">
                        {q.quantity_tons} MT
                      </td>
                      <td className="py-2 px-3">
                        <span
                          className={`font-mono text-[11px] font-semibold ${
                            q.priority === 'CRITICAL'
                              ? 'text-danger'
                              : q.priority === 'HIGH'
                              ? 'text-warn'
                              : 'text-text-3'
                          }`}
                        >
                          {q.priority}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-surface-sunk text-text-3 border border-border">
                          QUEUED
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleRunSpecificOrder(q.order_id)}
                          disabled={isExecuting}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-surface border border-border hover:border-accent text-accent text-[11px] font-medium transition-colors cursor-pointer disabled:opacity-50"
                        >
                          <Play className="w-3 h-3" />
                          <span>Run Now</span>
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* TAB 2: ACTIVE RUNNING */}
      {activeTab === 'running' && (
        <Panel
          title="Active Running Orders"
          subtitle="Orders popped from queue currently undergoing autonomous agent mesh investigation."
          padding="none"
        >
          {runningOrders.length === 0 ? (
            <div className="p-8 text-center text-text-3 text-[13px]">
              No orders are currently running. Click "Run Next Queued Order" above to pop an order into active execution.
            </div>
          ) : (
            <div className="divide-y divide-border">
              {runningOrders.map((ro) => (
                <div key={ro.running_id} className="p-4 space-y-3 bg-surface hover:bg-surface-2 transition-colors">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-[14px] font-bold text-accent">
                        {ro.order_id}
                      </span>
                      <span className="text-[13px] font-medium text-text">
                        {ro.customer_name}
                      </span>
                      <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-surface-sunk border border-border text-text-2">
                        {ro.product_code} ({ro.quantity_tons} MT)
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`font-mono text-[11px] px-2 py-0.5 rounded font-semibold uppercase ${
                          ro.status === 'EXCEPTION'
                            ? 'bg-danger/20 text-danger border border-danger/30'
                            : 'bg-accent/20 text-accent border border-accent/30 animate-pulse'
                        }`}
                      >
                        {ro.status}
                      </span>
                      <span className="text-[11px] font-mono text-text-3">
                        Stage: {ro.current_stage}
                      </span>
                    </div>
                  </div>

                  {/* Specialist Agent Status Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px]">
                    {['Supervisor', 'Inventory', 'Procurement', 'Finance', 'Logistics'].map((agentName) => (
                      <div key={agentName} className="p-2 rounded bg-surface-sunk border border-border space-y-1">
                        <span className="text-text-3 block">{agentName}</span>
                        <div className="flex items-center gap-1.5 font-mono text-ok font-semibold">
                          <CheckCircle2 className="w-3 h-3 text-ok" />
                          <span>Evaluated</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {ro.last_error && (
                    <div className="p-2.5 rounded bg-danger/10 border border-danger/30 text-danger text-[12px] flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>{ro.last_error}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>
      )}

      {/* TAB 3: PROCESSED HISTORY (DONE) */}
      {activeTab === 'done' && (
        <Panel
          title="Processed Order History (Immutable Archive)"
          subtitle="Orders fulfilled and permanently recorded. These records are archived and will never run again."
          padding="none"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-[12px] text-left">
              <thead className="bg-surface-sunk text-text-3 border-b border-border font-medium">
                <tr>
                  <th className="py-2.5 px-3">Order ID</th>
                  <th className="py-2.5 px-3">Customer Reference</th>
                  <th className="py-2.5 px-3">Product</th>
                  <th className="py-2.5 px-3 text-right">Quantity</th>
                  <th className="py-2.5 px-3">Final Consensus Decision</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">Blockchain Anchor</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {doneOrders
                  .filter((d) => {
                    const matchesSearch =
                      !searchQuery ||
                      d.order_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                      d.customer_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                      d.product_code.toLowerCase().includes(searchQuery.toLowerCase());
                    return matchesSearch;
                  })
                  .map((d) => (
                    <tr key={d.done_id} className="hover:bg-surface-2 transition-colors">
                      <td className="py-2 px-3 font-mono font-semibold text-text">
                        {d.order_id}
                      </td>
                      <td className="py-2 px-3 text-text font-medium">
                        {d.customer_name}
                      </td>
                      <td className="py-2 px-3 font-mono text-text-2">
                        {d.product_code}
                      </td>
                      <td className="py-2 px-3 font-mono text-right">
                        {d.quantity_tons} MT
                      </td>
                      <td className="py-2 px-3 text-text truncate max-w-[260px]">
                        {d.final_decision}
                      </td>
                      <td className="py-2 px-3 font-mono text-text-3">
                        {d.duration_ms}ms
                      </td>
                      <td className="py-2 px-3 font-mono text-[11px]">
                        {d.blockchain_block_number ? (
                          <span className="text-ok font-semibold">
                            Block #{d.blockchain_block_number}
                          </span>
                        ) : (
                          <span className="text-text-3">Anchoring</span>
                        )}
                      </td>
                      <td className="py-2 px-3">
                        <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-ok/20 text-ok font-semibold">
                          COMPLETED
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* Manual Order Creation Drawer */}
      <DetailDrawer
        isOpen={isNewOrderDrawerOpen}
        onClose={() => setIsNewOrderDrawerOpen(false)}
        title="Create New Requisition Order"
        subtitle="Appends order to operational table and auto-enqueues into sequential FIFO queue."
      >
        <form onSubmit={handleCreateOrder} className="space-y-4 text-[13px]">
          <div>
            <label className="block text-text-2 font-medium mb-1">Customer / Reference *</label>
            <input
              type="text"
              required
              placeholder="e.g. Tata Motors Heavy Commercial"
              value={newCustomer}
              onChange={(e) => setNewCustomer(e.target.value)}
              className="w-full h-[32px] px-3 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent"
            />
          </div>

          <div>
            <label className="block text-text-2 font-medium mb-1">Destination Entity</label>
            <select
              value={newEntity}
              onChange={(e) => setNewEntity(e.target.value)}
              className="w-full h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
            >
              {ENTITY_OPTIONS.map((ent) => (
                <option key={ent.id} value={ent.id}>
                  {ent.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-text-2 font-medium mb-1">Product Catalog Selection</label>
            <select
              value={newProductId}
              onChange={(e) => handleProductSelect(e.target.value)}
              className="w-full h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer font-mono"
            >
              {Object.entries(PRODUCT_CATALOG).map(([code, p]) => (
                <option key={code} value={code}>
                  {code} — {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-text-2 font-medium mb-1">Requested Qty (MT) *</label>
              <input
                type="number"
                required
                min="1"
                step="any"
                value={newQty}
                onChange={(e) => setNewQty(e.target.value)}
                className="w-full h-[32px] px-3 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent font-mono"
              />
            </div>
            <div>
              <label className="block text-text-2 font-medium mb-1">Unit Price (INR/MT) *</label>
              <input
                type="number"
                required
                min="1"
                step="any"
                value={newUnitPrice}
                onChange={(e) => setNewUnitPrice(e.target.value)}
                className="w-full h-[32px] px-3 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-text-2 font-medium mb-1">Priority</label>
              <select
                value={newPriority}
                onChange={(e) => setNewPriority(e.target.value as any)}
                className="w-full h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
            <div>
              <label className="block text-text-2 font-medium mb-1">External PO Reference</label>
              <input
                type="text"
                placeholder="Optional PO# (e.g. PO-8890)"
                value={newExtRef}
                onChange={(e) => setNewExtRef(e.target.value)}
                className="w-full h-[32px] px-3 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent font-mono"
              />
            </div>
          </div>

          {orderSubmitSuccess && (
            <div className="p-3 rounded-[4px] border border-ok/40 bg-ok/10 text-ok text-[12px] flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{orderSubmitSuccess}</span>
            </div>
          )}

          {orderSubmitError && (
            <div className="p-3 rounded-[4px] border border-danger/40 bg-danger/10 text-danger text-[12px]">
              {orderSubmitError}
            </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmittingOrder}
              className="w-full h-[36px] bg-accent hover:bg-accent-hover text-white text-[13px] font-semibold rounded-[4px] transition-colors cursor-pointer disabled:opacity-50"
            >
              {isSubmittingOrder ? 'Persisting Order...' : 'Submit & Enqueue Order'}
            </button>
          </div>
        </form>
      </DetailDrawer>
    </div>
  );
};
