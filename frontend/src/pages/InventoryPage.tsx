import React, { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { StatStrip, type StatItem } from '../components/common/StatStrip';
import { Panel } from '../components/common/Panel';
import { DataTable, type Column } from '../components/common/DataTable';
import { StatusBadge } from '../components/common/StatusBadge';
import { DetailDrawer } from '../components/common/DetailDrawer';
import { KeyValueList } from '../components/common/KeyValueList';
import { useDemo } from '../state/DemoContext';

interface DisplayInventoryRow {
  sku: string;
  description: string;
  warehouse: string;
  onHand: number;
  reserved: number;
  available: number;
  reorderLevel: number;
  status: string;
  rawLots?: { lotId: string; qty: number; grade: string; mfgDate: string }[];
}

export const InventoryPage: React.FC = () => {
  const { inventory, dataMode, liveInventory } = useDemo();
  const [selectedItem, setSelectedItem] = useState<DisplayInventoryRow | null>(null);

  const inventoryRows: DisplayInventoryRow[] =
    dataMode === 'live' && liveInventory.length > 0
      ? liveInventory.map((li) => ({
          sku: li.item_id || 'SKU-SLAB-01',
          description: li.item_name || 'Hot Rolled Steel Slab (IS 2062)',
          warehouse: li.warehouse_id || 'WH-BOK-01 (Bokaro Central)',
          onHand: li.on_hand_qty || 150,
          reserved: li.reserved_qty || 25,
          available: li.available_qty || 125,
          reorderLevel: li.reorder_point_qty || 40,
          status: li.stock_status === 'REORDER_REQUIRED' ? 'failed' : li.stock_status === 'LOW_STOCK' ? 'awaiting_approval' : 'completed',
          rawLots: [
            { lotId: 'LOT-BOK-881', qty: 60, grade: 'IS 2062 E250', mfgDate: '2026-10-10' },
            { lotId: 'LOT-BOK-882', qty: 65, grade: 'IS 2062 E250', mfgDate: '2026-10-12' },
          ],
        }))
      : inventory.map((item) => ({
          sku: item.id,
          description: item.productName,
          warehouse: 'WH-BOK-01 (Bokaro Mill Yard)',
          onHand: item.currentStock + 15,
          reserved: 15,
          available: item.currentStock,
          reorderLevel: item.reorderThreshold,
          status: item.status === 'REORDER_REQUIRED' ? 'failed' : item.status === 'LOW_STOCK' ? 'awaiting_approval' : 'completed',
          rawLots: [
            { lotId: `LOT-${item.id}-01`, qty: Math.floor(item.currentStock * 0.6), grade: 'Commercial Prime', mfgDate: '2026-10-08' },
            { lotId: `LOT-${item.id}-02`, qty: Math.ceil(item.currentStock * 0.4), grade: 'Commercial Prime', mfgDate: '2026-10-11' },
          ],
        }));

  // Calculate StatStrip metrics
  const skusTracked = inventoryRows.length;
  const belowReorder = inventoryRows.filter((r) => r.available <= r.reorderLevel).length;
  const totalReserved = inventoryRows.reduce((acc, r) => acc + r.reserved, 0);
  const shortagesCount = inventoryRows.filter((r) => r.status === 'failed').length;

  const stats: StatItem[] = [
    { label: 'SKUs tracked', value: skusTracked, context: 'Active material lines' },
    { label: 'Below reorder level', value: belowReorder, context: 'Procurement notified', accent: belowReorder > 0 ? 'warn' : 'default' },
    { label: 'Reserved inventory', value: `${totalReserved} MT`, context: 'Active order commitments' },
    { label: 'Shortages flagged', value: shortagesCount, context: 'Critical deficit', accent: shortagesCount > 0 ? 'danger' : 'default' },
  ];

  const columns: Column<DisplayInventoryRow>[] = [
    {
      key: 'sku',
      header: 'SKU Code',
      render: (r) => <span className="font-mono text-[12px] font-semibold text-text">{r.sku}</span>,
    },
    {
      key: 'description',
      header: 'Description / Grade',
      render: (r) => <span className="font-medium text-text text-[13px]">{r.description}</span>,
    },
    {
      key: 'warehouse',
      header: 'Warehouse Site',
      render: (r) => <span className="font-mono text-[11px] text-text-3">{r.warehouse}</span>,
    },
    {
      key: 'onHand',
      header: 'On Hand',
      isNumeric: true,
      render: (r) => <span>{r.onHand} MT</span>,
    },
    {
      key: 'reserved',
      header: 'Reserved',
      isNumeric: true,
      render: (r) => <span className="text-text-2">{r.reserved} MT</span>,
    },
    {
      key: 'available',
      header: 'Available',
      isNumeric: true,
      render: (r) => {
        // Compute stock ratio for thin 4px bar
        const ratio = Math.min(100, Math.round((r.available / (r.reorderLevel * 2)) * 100));
        const barColor = r.status === 'failed' ? 'bg-danger' : r.status === 'awaiting_approval' ? 'bg-warn' : 'bg-ok';

        return (
          <div className="flex flex-col items-end">
            <span className="font-mono font-medium">{r.available} MT</span>
            <div className="w-16 h-1 bg-surface-sunk rounded-full overflow-hidden mt-1">
              <div
                style={{ width: `${ratio}%` }}
                className={`h-full rounded-full ${barColor}`}
              />
            </div>
          </div>
        );
      },
    },
    {
      key: 'reorderLevel',
      header: 'Reorder Level',
      isNumeric: true,
      render: (r) => <span className="font-mono text-text-3">{r.reorderLevel} MT</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (r) => {
        const label = r.status === 'failed' ? 'Shortage' : r.status === 'awaiting_approval' ? 'Low Stock' : 'OK';
        return <StatusBadge status={r.status} size="sm" customLabel={label} />;
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Warehouse Inventory & Stock Telemetry"
        description="Physical stock levels, dynamic reservations, safety thresholds, and autonomous shortage alerts."
      />

      {/* Stat Strip */}
      <StatStrip stats={stats} />

      {/* Inventory DataTable */}
      <Panel
        title={`Material Inventory Registry (${inventoryRows.length} items)`}
        subtitle="Click any row to inspect production lots, recent stock movements, and linked requisitions"
        padding="none"
      >
        <DataTable<DisplayInventoryRow>
          columns={columns}
          data={inventoryRows}
          keyExtractor={(r) => r.sku}
          onRowClick={(r) => setSelectedItem(r)}
        />
      </Panel>

      {/* Stock Detail Drawer */}
      <DetailDrawer
        isOpen={selectedItem != null}
        onClose={() => setSelectedItem(null)}
        title={selectedItem ? `SKU Detail: ${selectedItem.sku}` : 'SKU Detail'}
        subtitle={selectedItem ? selectedItem.description : undefined}
      >
        {selectedItem && (
          <div className="space-y-4">
            <Panel title="Stock Summary & Thresholds">
              <KeyValueList
                items={[
                  { label: 'Primary Warehouse', value: selectedItem.warehouse },
                  { label: 'On Hand Physical Stock', value: `${selectedItem.onHand} MT`, isMono: true },
                  { label: 'Committed / Reserved', value: `${selectedItem.reserved} MT`, isMono: true },
                  { label: 'Net Available Stock', value: `${selectedItem.available} MT`, isMono: true },
                  { label: 'Reorder Point Trigger', value: `${selectedItem.reorderLevel} MT`, isMono: true },
                  {
                    label: 'Replenishment Policy',
                    value: 'Automatic PO Draft upon available < reorder point',
                  },
                ]}
              />
            </Panel>

            <Panel title="Associated Production Lots" padding="none">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-[12px]">
                  <thead>
                    <tr className="bg-surface-2 h-[32px] border-b border-border text-[11px] font-semibold text-text-3 uppercase tracking-wider">
                      <th className="px-3 py-1">Lot ID</th>
                      <th className="px-3 py-1 text-right">Qty</th>
                      <th className="px-3 py-1">Specification</th>
                      <th className="px-3 py-1 text-right">Mfg Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {selectedItem.rawLots?.map((lot) => (
                      <tr key={lot.lotId} className="h-[36px] bg-surface">
                        <td className="px-3 py-1.5 font-mono text-text font-medium">{lot.lotId}</td>
                        <td className="px-3 py-1.5 text-right font-mono tabular-nums text-text">{lot.qty} MT</td>
                        <td className="px-3 py-1.5 text-text-2">{lot.grade}</td>
                        <td className="px-3 py-1.5 text-right font-mono text-text-3">{lot.mfgDate}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <Panel title="Recent Stock Movements">
              <div className="space-y-2 text-[12px] text-text-2">
                <div className="flex justify-between border-b border-border pb-1.5">
                  <span>Reserved 15 MT for Order ORD-1042</span>
                  <span className="font-mono text-text-3">Today, 19:15</span>
                </div>
                <div className="flex justify-between border-b border-border pb-1.5">
                  <span>Inbound receipt 40 MT from Bokaro Blast Furnace #2</span>
                  <span className="font-mono text-text-3">Yesterday, 14:20</span>
                </div>
                <div className="flex justify-between">
                  <span>Dispatched 20 MT to Pune Assembly Plant</span>
                  <span className="font-mono text-text-3">13 Oct 2026</span>
                </div>
              </div>
            </Panel>
          </div>
        )}
      </DetailDrawer>
    </div>
  );
};
