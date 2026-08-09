import React, { useState } from 'react';
import { ShoppingBag, Search, Eye, ShieldCheck, X } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { StatusBadge } from '../components/common/StatusBadge';
import type { Order } from '../types';

export const OrdersPage: React.FC = () => {
  const { orders } = useDemo();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);

  const filteredOrders = orders.filter(o =>
    o.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    o.customer.toLowerCase().includes(searchQuery.toLowerCase()) ||
    o.product.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <ShoppingBag className="w-5 h-5 text-blue-400" /> Order Management Registry
          </h2>
          <p className="text-xs text-slate-400">
            Real-time supply chain fulfilment orders & agent dispatch tracking
          </p>
        </div>

        {/* Search */}
        <div className="relative w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search orders, customers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#121929] border border-[#24334D] rounded-xl pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-[#121929] border border-[#24334D] rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#0B111E] text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-[#24334D]">
              <tr>
                <th className="py-3 px-4">Order ID</th>
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4">Product</th>
                <th className="py-3 px-4">Quantity</th>
                <th className="py-3 px-4">Value</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Current Agent</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E293B]">
              {filteredOrders.map(order => (
                <tr key={order.id} className="hover:bg-[#182338] transition-colors">
                  <td className="py-3.5 px-4 font-bold text-white font-mono">{order.id}</td>
                  <td className="py-3.5 px-4 font-medium text-slate-200">{order.customer}</td>
                  <td className="py-3.5 px-4 text-cyan-300">{order.product}</td>
                  <td className="py-3.5 px-4 font-mono">{order.quantity} units</td>
                  <td className="py-3.5 px-4 font-mono font-semibold text-emerald-400">
                    ₹{order.budget.toLocaleString()}
                  </td>
                  <td className="py-3.5 px-4">
                    <StatusBadge status={order.status} />
                  </td>
                  <td className="py-3.5 px-4 uppercase font-mono text-[11px] text-indigo-300">
                    {order.currentAgent}
                  </td>
                  <td className="py-3.5 px-4 font-semibold text-amber-400">{order.priority}</td>
                  <td className="py-3.5 px-4">
                    <button
                      onClick={() => setSelectedOrder(order)}
                      className="px-2.5 py-1 bg-blue-600/20 text-blue-400 hover:bg-blue-600 hover:text-white rounded-md transition font-medium text-[11px] flex items-center gap-1"
                    >
                      <Eye className="w-3.5 h-3.5" /> Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Order Detail Modal / Drawer */}
      {selectedOrder && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#121929] border border-[#24334D] rounded-2xl w-full max-w-2xl p-6 text-slate-200 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-[#24334D] pb-3">
              <div className="flex items-center gap-3">
                <h3 className="font-bold text-lg text-white">Order Details: {selectedOrder.id}</h3>
                <StatusBadge status={selectedOrder.status} />
              </div>
              <button
                onClick={() => setSelectedOrder(null)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
                <div className="text-slate-400 font-semibold mb-1">Customer</div>
                <div className="text-white font-medium">{selectedOrder.customer}</div>
              </div>

              <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
                <div className="text-slate-400 font-semibold mb-1">Product & Qty</div>
                <div className="text-cyan-300 font-medium">{selectedOrder.product} ({selectedOrder.quantity} units)</div>
              </div>

              <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
                <div className="text-slate-400 font-semibold mb-1">Allocated Budget</div>
                <div className="text-emerald-400 font-bold font-mono">₹{selectedOrder.budget.toLocaleString()}</div>
              </div>

              <div className="bg-[#0A0F1D] p-3 rounded-xl border border-slate-800">
                <div className="text-slate-400 font-semibold mb-1">Fulfillment Hub</div>
                <div className="text-white">{selectedOrder.destination}</div>
              </div>
            </div>

            <div className="bg-[#0A0F1D] p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs border-b border-slate-800 pb-2">
                <span className="text-slate-400 font-semibold">Blockchain Audit Ledger Token</span>
                <span className="text-emerald-400 font-mono flex items-center gap-1">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" /> VERIFIED
                </span>
              </div>
              <div className="font-mono text-xs text-indigo-300 break-all bg-[#080C14] p-2 rounded border border-slate-700">
                TxHash: {selectedOrder.auditHash || '0x7f83a91c2049e88b1'}
              </div>
            </div>

            {selectedOrder.notes && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300">
                <strong>Exception Note:</strong> {selectedOrder.notes}
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedOrder(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
