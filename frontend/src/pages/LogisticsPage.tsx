import React, { useState, useMemo } from 'react';
import { useDemo } from '../state/DemoContext';
import { PageHeader } from '../components/common/PageHeader';
import { SourceBadge } from '../components/common/SourceBadge';
import { Panel } from '../components/common/Panel';
import { DataTable, type Column } from '../components/common/DataTable';
import { StatusBadge } from '../components/common/StatusBadge';
import { DetailDrawer } from '../components/common/DetailDrawer';
import { KeyValueList } from '../components/common/KeyValueList';

interface ShipmentEvent {
  time: string;
  location: string;
  status: string;
  detail: string;
}

interface ShipmentRecord {
  id: string;
  orderId: string;
  carrier: string;
  origin: string;
  destination: string;
  eta: string;
  promised: string;
  delayDays: number;
  slaDays: number;
  status: 'running' | 'completed' | 'delayed' | 'pending';
  events: ShipmentEvent[];
}

export const LogisticsPage: React.FC = () => {
  const { activeOrder, orders, activeScenario } = useDemo();
  const [selectedShipment, setSelectedShipment] = useState<ShipmentRecord | null>(null);

  const hasDelay = activeScenario === 'delivery_delay' || activeScenario === 'multi_exception';

  // Construct shipments derived from system orders
  const shipments: ShipmentRecord[] = useMemo(() => {
    const list: ShipmentRecord[] = [
      {
        id: 'SHP-8841',
        orderId: activeOrder.id,
        carrier: hasDelay ? 'Concor Express Rail (Rerouted)' : 'BlueDart Industrial Cargo',
        origin: 'Pune Mill (Gate 4)',
        destination: activeOrder.destination || 'L&T Heavy Engineering, Hazira',
        eta: hasDelay ? '18 Oct 2026, 16:00' : '16 Oct 2026, 12:00',
        promised: '16 Oct 2026, 14:00',
        delayDays: hasDelay ? 2 : 0,
        slaDays: 2,
        status: hasDelay ? 'delayed' : 'running',
        events: hasDelay
          ? [
              { time: '15 Oct 2026, 08:30', location: 'Pune Mill', status: 'Dispatched', detail: 'Cargo loaded onto initial road hauler' },
              { time: '15 Oct 2026, 11:15', location: 'NH-53 Checkpost', status: 'Corridor Alert', detail: 'Severe waterlogging alert issued for Pune-Nagpur corridor' },
              { time: '15 Oct 2026, 12:45', location: 'Autonomous Dispatch', status: 'Rerouted', detail: 'Logistics specialist switched carrier from Road to Concor Rail Freight' },
              { time: '15 Oct 2026, 15:20', location: 'Pune Rail ICD', status: 'Transshipped', detail: 'Container transferred to Concor rakes for direct transit to Hazira' },
            ]
          : [
              { time: '15 Oct 2026, 08:30', location: 'Pune Mill', status: 'Dispatched', detail: 'Cargo cleared outbound inspection' },
              { time: '15 Oct 2026, 13:00', location: 'Nashik Transit Hub', status: 'In Transit', detail: 'Vehicle telemetry nominal, on scheduled route' },
            ],
      },
      ...orders.filter(o => o.id !== activeOrder.id).slice(0, 5).map((ord, idx) => {
        const isDelayed = ord.status === 'Delayed';
        const delay = isDelayed ? 3 : 0;
        return {
          id: `SHP-88${42 + idx}`,
          orderId: ord.id,
          carrier: idx % 2 === 0 ? 'VRL Logistics Heavy' : 'TCI Freight Rail',
          origin: idx % 2 === 0 ? 'Jamshedpur Works' : 'Bhilai Central Depot',
          destination: ord.destination,
          eta: isDelayed ? '20 Oct 2026, 18:00' : '17 Oct 2026, 10:00',
          promised: '17 Oct 2026, 14:00',
          delayDays: delay,
          slaDays: 2,
          status: isDelayed ? ('delayed' as const) : ('running' as const),
          events: [
            { time: '14 Oct 2026, 09:00', location: 'Origin Depot', status: 'Dispatched', detail: 'Consignment booked and en route' },
            { time: '15 Oct 2026, 04:00', location: 'Intermodal Yard', status: isDelayed ? 'Congested' : 'In Transit', detail: isDelayed ? 'Yard congestion causing 72h transshipment delay' : 'Moving on schedule' },
          ],
        };
      }),
    ];
    return list;
  }, [activeOrder, orders, hasDelay]);

  // Orders at risk
  const ordersAtRisk = useMemo(() => {
    const list = [];
    if (hasDelay) {
      list.push({
        orderId: activeOrder.id,
        severity: 'high',
        carrier: 'BlueDart Industrial Cargo / Concor',
        corridor: 'Pune - Hazira (NH-53 corridor)',
        reason: 'Heavy rainfall and highway flooding on NH-53 projected +48h road delay; autonomous mitigation rerouted shipment to Concor Rail.',
      });
    }
    const delayedOthers = orders.filter(o => o.id !== activeOrder.id && o.status === 'Delayed');
    for (const d of delayedOthers) {
      list.push({
        orderId: d.id,
        severity: 'critical',
        carrier: 'VRL Logistics Heavy',
        corridor: 'Jamshedpur - Mumbai Industrial Corridor',
        reason: 'Intermodal terminal freight congestion exceeding 72h SLA buffer; human dispatcher intervention required.',
      });
    }
    return list;
  }, [hasDelay, activeOrder, orders]);

  const columns: Column<ShipmentRecord>[] = [
    {
      key: 'id',
      header: 'Shipment',
      render: s => <span className="font-mono text-13 font-medium text-text">{s.id}</span>,
    },
    {
      key: 'orderId',
      header: 'Order',
      render: s => <span className="font-mono text-12 text-text-2">{s.orderId}</span>,
    },
    {
      key: 'carrier',
      header: 'Carrier',
      render: s => <span className="text-13 text-text truncate max-w-[180px] block">{s.carrier}</span>,
    },
    {
      key: 'origin',
      header: 'Origin',
      render: s => <span className="text-12 text-text-2">{s.origin}</span>,
    },
    {
      key: 'destination',
      header: 'Destination',
      render: s => <span className="text-12 text-text-2">{s.destination}</span>,
    },
    {
      key: 'promised',
      header: 'Promised',
      render: s => <span className="text-12 font-mono text-text-3">{s.promised}</span>,
    },
    {
      key: 'eta',
      header: 'ETA',
      render: s => <span className="text-12 font-mono text-text-2">{s.eta}</span>,
    },
    {
      key: 'delayDays',
      header: 'Delay',
      align: 'right',
      render: s => {
        if (s.delayDays === 0) {
          return <span className="font-mono text-12 text-ok">On time</span>;
        }
        const isCritical = s.delayDays > s.slaDays;
        return (
          <span
            className={`font-mono text-12 font-medium ${
              isCritical ? 'text-danger' : 'text-warn'
            }`}
          >
            +{s.delayDays}d {isCritical ? '(Over SLA)' : ''}
          </span>
        );
      },
    },
    {
      key: 'status',
      header: 'Status',
      render: s => {
        if (s.status === 'delayed') return <StatusBadge status="blocked" size="sm" />;
        if (s.status === 'running') return <StatusBadge status="running" size="sm" />;
        return <StatusBadge status="completed" size="sm" />;
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Logistics & Dispatch"
        description="Shipment tracking, carrier route feasibility, and corridor delay mitigation."
        actions={<SourceBadge />}
      />

      {/* Delivery Risk Panel */}
      <Panel
        title="Delivery Risk"
        subtitle="Active orders with corridor disruptions or carrier SLA breaches"
      >
        {ordersAtRisk.length === 0 ? (
          <p className="text-13 text-text-3 py-2">
            All active shipments are currently operating within promised transit corridors and SLAs.
          </p>
        ) : (
          <div className="space-y-3">
            {ordersAtRisk.map(risk => (
              <div
                key={risk.orderId}
                className="p-3 rounded-[4px] border border-border bg-surface-2 flex flex-col md:flex-row md:items-center justify-between gap-2"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block w-2 h-2 rounded-full ${
                        risk.severity === 'critical' ? 'bg-danger' : 'bg-warn'
                      }`}
                    />
                    <span className="font-mono text-12 font-medium text-text">
                      {risk.orderId}
                    </span>
                    <span className="text-12 text-text-3">· {risk.corridor}</span>
                  </div>
                  <p className="text-13 text-text-2 leading-relaxed">
                    {risk.reason}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <span className="text-11 font-mono text-text-3">
                    Carrier: {risk.carrier}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {/* Shipments Table */}
      <Panel
        title="Active Shipments"
        subtitle={`${shipments.length} consignments tracked across production and distribution hubs`}
        padding="none"
      >
        <DataTable<ShipmentRecord>
          columns={columns}
          data={shipments}
          keyExtractor={s => s.id}
          onRowClick={shipment => setSelectedShipment(shipment)}
          emptyMessage="No active shipments tracked in the system."
        />
      </Panel>

      {/* Shipment Detail Drawer */}
      <DetailDrawer
        isOpen={!!selectedShipment}
        onClose={() => setSelectedShipment(null)}
        title={selectedShipment ? `Shipment ${selectedShipment.id}` : 'Shipment Details'}
        subtitle={selectedShipment ? `Consignment linked to order ${selectedShipment.orderId}` : undefined}
      >
        {selectedShipment && (
          <div className="space-y-6">
            <div>
              <h3 className="text-13 font-semibold text-text mb-3">Shipment Parameters</h3>
              <KeyValueList
                items={[
                  { label: 'Shipment ID', value: selectedShipment.id, isMono: true, rawCopyValue: selectedShipment.id },
                  { label: 'Order ID', value: selectedShipment.orderId, isMono: true, rawCopyValue: selectedShipment.orderId },
                  { label: 'Carrier', value: selectedShipment.carrier },
                  { label: 'Origin', value: selectedShipment.origin },
                  { label: 'Destination', value: selectedShipment.destination },
                  { label: 'Promised Delivery', value: selectedShipment.promised, isMono: true },
                  { label: 'Estimated Arrival', value: selectedShipment.eta, isMono: true },
                  {
                    label: 'Delay Status',
                    value:
                      selectedShipment.delayDays > 0
                        ? `+${selectedShipment.delayDays} day(s) against ${selectedShipment.slaDays}-day SLA`
                        : 'On schedule',
                  },
                ]}
              />
            </div>

            <div>
              <h3 className="text-13 font-semibold text-text mb-3">Carrier Events Timeline</h3>
              <div className="relative pl-4 space-y-4 border-l border-border">
                {selectedShipment.events.map((evt, idx) => (
                  <div key={idx} className="relative">
                    <span className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-border-strong border-2 border-surface" />
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-12 font-medium text-text">{evt.status}</span>
                      <span className="text-11 font-mono text-text-3">{evt.time}</span>
                    </div>
                    <div className="text-12 text-text-3">{evt.location}</div>
                    <div className="text-12 text-text-2 mt-0.5">{evt.detail}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </DetailDrawer>
    </div>
  );
};
