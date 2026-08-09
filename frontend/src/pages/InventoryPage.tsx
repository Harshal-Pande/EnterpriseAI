import React from 'react';
import { Package, AlertTriangle } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { StatusBadge } from '../components/common/StatusBadge';

export const InventoryPage: React.FC = () => {
  const { inventory } = useDemo();

  const criticalItems = inventory.filter(i => i.status === 'REORDER_REQUIRED');
  const lowItems      = inventory.filter(i => i.status === 'LOW_STOCK');

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Inventory Telemetry</h1>
          <p className="text-sm text-slate-500 mt-1">Real-time stock balances, reorder thresholds, and shortage detection</p>
        </div>
        <div className="flex items-center gap-2 text-[11px] font-mono">
          <span className="px-3 py-1.5 rounded-lg text-rose-300 font-bold"
            style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>
            {criticalItems.length} Reorder Required
          </span>
          <span className="px-3 py-1.5 rounded-lg text-amber-300 font-bold"
            style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}>
            {lowItems.length} Low Stock
          </span>
        </div>
      </div>

      {/* Reorder Alert Banner */}
      {criticalItems.length > 0 && (
        <div
          className="flex items-center gap-4 px-5 py-4 rounded-xl"
          style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)' }}
        >
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.3)' }}
          >
            <AlertTriangle className="w-5 h-5 text-amber-400 animate-pulse" />
          </div>
          <div>
            <div className="text-[11px] font-bold text-amber-300 uppercase tracking-wider">
              ⚡ Reorder Signal Active — Inventory Agent Dispatched
            </div>
            <div className="text-[11px] text-slate-300 mt-0.5">
              Shortage of <strong>78 units</strong> detected for{' '}
              <em>Industrial Water Pump (WP-800)</em>. Procurement Agent notified.
            </div>
          </div>
          <span
            className="ml-auto shrink-0 px-3 py-1 rounded-full text-[10px] font-mono font-bold"
            style={{ background: 'rgba(245,158,11,0.15)', color: '#FCD34D', border: '1px solid rgba(245,158,11,0.3)' }}
          >
            SIGNAL DISPATCHED
          </span>
        </div>
      )}

      {/* Inventory Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total SKUs Monitored',   value: inventory.length,           color: '#38BDF8' },
          { label: 'Reorder Required',        value: criticalItems.length,        color: '#EF4444' },
          { label: 'Low Stock Alerts',        value: lowItems.length,             color: '#F59E0B' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl p-4 text-center" style={{ background: '#111827', border: '1px solid #1E293B' }}>
            <div className="text-2xl font-bold font-mono" style={{ color }}>{value}</div>
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mt-1">{label}</div>
          </div>
        ))}
      </div>

      {/* Inventory Table */}
      <div className="rounded-xl overflow-hidden" style={{ background: '#111827', border: '1px solid #1E293B' }}>
        <div className="px-5 py-3.5 border-b border-[#1E293B] flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Package className="w-4 h-4 text-emerald-400" />
            Stock Level Matrix
          </h2>
          <span className="text-[10px] text-slate-600 font-mono">{inventory.length} items tracked</span>
        </div>
        <div className="overflow-x-auto">
          <table className="ent-table">
            <thead>
              <tr>
                <th>Item ID</th>
                <th>Product Name</th>
                <th className="text-right">In Stock</th>
                <th className="text-right">Required</th>
                <th className="text-right">Reorder Threshold</th>
                <th className="text-right">Shortage</th>
                <th>Status</th>
                <th>Fill Rate</th>
              </tr>
            </thead>
            <tbody>
              {inventory.map(item => {
                const fillRate = Math.min(100, Math.round((item.currentStock / item.required) * 100));
                const isCritical = item.status === 'REORDER_REQUIRED';
                const isLow = item.status === 'LOW_STOCK';
                return (
                  <tr
                    key={item.id}
                    style={isCritical ? { background: 'rgba(239,68,68,0.03)' } : isLow ? { background: 'rgba(245,158,11,0.03)' } : {}}
                  >
                    <td><span className="font-mono font-bold text-white">{item.id}</span></td>
                    <td className="text-slate-300">{item.productName}</td>
                    <td className="text-right">
                      <span className={`font-mono font-bold ${isCritical ? 'text-rose-400' : isLow ? 'text-amber-400' : 'text-emerald-400'}`}>
                        {item.currentStock}
                      </span>
                    </td>
                    <td className="text-right font-mono text-slate-400">{item.required}</td>
                    <td className="text-right font-mono text-slate-500">{item.reorderThreshold}</td>
                    <td className="text-right">
                      <span className={`font-mono font-bold ${item.shortage > 0 ? 'text-rose-400' : 'text-slate-500'}`}>
                        {item.shortage > 0 ? `-${item.shortage}` : '—'}
                      </span>
                    </td>
                    <td><StatusBadge status={item.status} /></td>
                    <td>
                      <div className="flex items-center gap-2 min-w-[80px]">
                        <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: '#1E293B' }}>
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${fillRate}%`,
                              background: fillRate < 50 ? '#EF4444' : fillRate < 80 ? '#F59E0B' : '#10B981'
                            }}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-slate-500 shrink-0">{fillRate}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
