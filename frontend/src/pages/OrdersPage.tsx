import React, { useState } from 'react';
import { ShoppingBag, Search, Eye, ShieldCheck, X, Filter } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { StatusBadge } from '../components/common/StatusBadge';
import type { Order, OrderStatus } from '../types';

const PRIORITY_COLORS: Record<string, string> = {
  Critical: 'text-rose-400',
  High:     'text-amber-400',
  Medium:   'text-blue-400',
  Low:      'text-slate-400',
};

const STATUS_FILTERS: (OrderStatus | 'All')[] = ['All', 'Processing', 'Approved', 'Awaiting Procurement', 'Finance Review', 'Exception', 'Completed'];

export const OrdersPage: React.FC = () => {
  const { orders } = useDemo();
  const [searchQuery, setSearchQuery]     = useState('');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [statusFilter, setStatusFilter]   = useState<OrderStatus | 'All'>('All');

  const filtered = orders.filter(o => {
    const matchesSearch = !searchQuery ||
      o.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      o.customer.toLowerCase().includes(searchQuery.toLowerCase()) ||
      o.product.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'All' || o.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Order Management</h1>
          <p className="text-sm text-slate-500 mt-1">Real-time fulfilment registry & agent dispatch tracking</p>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            id="orders-search"
            placeholder="Search order ID, customer, product…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-64 h-9 pl-9 pr-3 text-[12px] text-slate-200 placeholder-slate-600 rounded-lg focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition"
            style={{ background: '#0F172A', border: '1px solid #1E293B' }}
          />
        </div>
      </div>

      {/* Status Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="w-3.5 h-3.5 text-slate-600 shrink-0" />
        {STATUS_FILTERS.map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className="px-3 py-1 rounded-full text-[11px] font-medium transition-all"
            style={{
              background:  statusFilter === s ? 'rgba(56,189,248,0.12)' : '#111827',
              color:       statusFilter === s ? '#38BDF8' : '#64748B',
              border:      `1px solid ${statusFilter === s ? 'rgba(56,189,248,0.3)' : '#1E293B'}`,
            }}
          >
            {s}
          </button>
        ))}
        <span className="text-[11px] text-slate-600 ml-auto">{filtered.length} orders</span>
      </div>

      {/* Table */}
      <div className="rounded-xl overflow-hidden" style={{ background: '#111827', border: '1px solid #1E293B' }}>
        <div className="overflow-x-auto">
          <table className="ent-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Customer</th>
                <th>Product</th>
                <th className="text-right">Qty</th>
                <th className="text-right">Budget</th>
                <th>Status</th>
                <th>Agent</th>
                <th>Priority</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(order => (
                <tr key={order.id}>
                  <td>
                    <span className="font-mono font-bold text-white">{order.id}</span>
                  </td>
                  <td className="text-slate-300 max-w-[180px] truncate">{order.customer}</td>
                  <td className="text-cyan-300 max-w-[160px] truncate">{order.product}</td>
                  <td className="text-right font-mono text-slate-400">{order.quantity}</td>
                  <td className="text-right font-mono font-semibold text-emerald-400">
                    ₹{order.budget.toLocaleString()}
                  </td>
                  <td><StatusBadge status={order.status} /></td>
                  <td>
                    <span className="font-mono text-[11px] uppercase text-indigo-300">{order.currentAgent}</span>
                  </td>
                  <td>
                    <span className={`text-[11px] font-semibold ${PRIORITY_COLORS[order.priority] ?? 'text-slate-400'}`}>
                      {order.priority}
                    </span>
                  </td>
                  <td>
                    <button
                      id={`inspect-${order.id}`}
                      onClick={() => setSelectedOrder(order)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition"
                      style={{
                        background: 'rgba(37,99,235,0.1)',
                        color: '#60A5FA',
                        border: '1px solid rgba(37,99,235,0.2)'
                      }}
                    >
                      <Eye className="w-3 h-3" /> Inspect
                    </button>
                  </td>
                </tr>
              ))}

              {filtered.length === 0 && (
                <tr>
                  <td colSpan={9} className="text-center py-10 text-slate-600 text-xs">
                    No orders match your filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Order Detail Drawer / Modal */}
      {selectedOrder && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)' }}
        >
          <div
            className="w-full max-w-xl rounded-xl shadow-2xl text-slate-200 animate-fade-slide"
            style={{ background: '#0F172A', border: '1px solid #24334D' }}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-[#1E293B]">
              <div className="flex items-center gap-3">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: 'rgba(37,99,235,0.15)', border: '1px solid rgba(37,99,235,0.3)' }}
                >
                  <ShoppingBag className="w-4 h-4 text-blue-400" />
                </div>
                <div>
                  <div className="text-sm font-bold text-white">{selectedOrder.id}</div>
                  <div className="text-[10px] text-slate-500">{selectedOrder.createdAt}</div>
                </div>
                <StatusBadge status={selectedOrder.status} />
              </div>
              <button onClick={() => setSelectedOrder(null)} className="text-slate-500 hover:text-white transition p-1">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              {/* Key fields */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                {[
                  { label: 'Customer',       value: selectedOrder.customer,                           color: '#F8FAFC' },
                  { label: 'Product',        value: selectedOrder.product,                            color: '#67E8F9' },
                  { label: 'Quantity',       value: `${selectedOrder.quantity} units`,                color: '#F8FAFC' },
                  { label: 'Destination',    value: selectedOrder.destination,                        color: '#F8FAFC' },
                  { label: 'Budget Cap',     value: `₹${selectedOrder.budget.toLocaleString()}`,      color: '#34D399' },
                  { label: 'Estimated Cost', value: `₹${selectedOrder.estimatedCost.toLocaleString()}`,color: '#34D399' },
                  { label: 'Priority',       value: selectedOrder.priority,                           color: PRIORITY_COLORS[selectedOrder.priority]?.replace('text-', '#') ?? '#94A3B8' },
                  { label: 'Current Agent',  value: selectedOrder.currentAgent.toUpperCase(),         color: '#A5B4FC' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="rounded-lg p-3" style={{ background: '#080C14', border: '1px solid #1E293B' }}>
                    <div className="text-[10px] text-slate-600 font-mono uppercase tracking-wider mb-0.5">{label}</div>
                    <div className="text-[12px] font-medium" style={{ color }}>{value}</div>
                  </div>
                ))}
              </div>

              {/* Audit Hash */}
              <div className="rounded-lg p-3" style={{ background: '#080C14', border: '1px solid #1E293B' }}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] text-slate-600 font-mono uppercase tracking-wider">Blockchain Audit Token</span>
                  <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono font-bold">
                    <ShieldCheck className="w-3 h-3" /> VERIFIED
                  </span>
                </div>
                <div className="font-mono text-[11px] text-indigo-300 break-all">
                  {selectedOrder.auditHash ?? '0x7f83a91c2049e88b1'}
                </div>
              </div>

              {/* Exception note */}
              {selectedOrder.notes && (
                <div className="rounded-lg p-3" style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)' }}>
                  <div className="text-[10px] font-bold text-rose-400 mb-0.5 uppercase font-mono">Exception Note</div>
                  <div className="text-[11px] text-rose-300">{selectedOrder.notes}</div>
                </div>
              )}

              <div className="flex justify-end pt-1">
                <button
                  onClick={() => setSelectedOrder(null)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold transition"
                  style={{ background: '#1E293B', color: '#F8FAFC' }}
                >
                  Close Inspector
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
