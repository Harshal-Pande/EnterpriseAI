import React, { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Panel } from '../components/common/Panel';
import { DataTable, type Column } from '../components/common/DataTable';
import { StatusBadge } from '../components/common/StatusBadge';
import { useDemo } from '../state/DemoContext';

interface DisplaySupplier {
  id: string;
  name: string;
  availability: number;
  reliability: number;
  leadTimeDays: number;
  unitPrice: number;
  score: number;
  status: string;
  isUnavailable?: boolean;
  unavailableReason?: string;
}

interface RequisitionOffer {
  vendorId: string;
  vendorName: string;
  quotedPrice: number;
  landedCost: number;
  leadTime: number;
  isLowestLanded: boolean;
  status: string;
}

export const ProcurementPage: React.FC = () => {
  const { suppliers: demoSuppliers, liveSuppliers, dataMode } = useDemo();
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>('SUP-001');

  const supplierList: DisplaySupplier[] =
    dataMode === 'live' && liveSuppliers.length > 0
      ? liveSuppliers.map((s, idx) => ({
          id: s.supplier_id || `SUP-00${idx + 1}`,
          name: s.name || `Vendor ${idx + 1}`,
          availability: s.is_active ? 150 : 0,
          reliability: Math.round((s.rating || 4.2) * 20),
          leadTimeDays: s.lead_time_days || 3,
          unitPrice: 41000 + idx * 800,
          score: Math.round((s.rating || 4.2) * 20),
          status: s.is_active ? (idx === 0 ? 'completed' : 'allowed') : 'unavailable',
          isUnavailable: !s.is_active,
          unavailableReason: !s.is_active ? 'Blast furnace scheduled maintenance outage' : undefined,
        }))
      : demoSuppliers.map((s) => ({
          id: s.id,
          name: s.name,
          availability: s.availability,
          reliability: s.score,
          leadTimeDays: s.deliveryDays,
          unitPrice: s.pricePerUnit,
          score: s.score,
          status: s.status === 'SELECTED' ? 'completed' : s.status === 'UNAVAILABLE' ? 'unavailable' : 'allowed',
          isUnavailable: s.status === 'UNAVAILABLE',
          unavailableReason: s.status === 'UNAVAILABLE' ? 'Inventory stockout at Bokaro slab depot' : undefined,
        }));

  const activeSupplier = supplierList.find((s) => s.id === selectedSupplierId) || supplierList[0];

  const requisitionOffers: RequisitionOffer[] = [
    {
      vendorId: 'SUP-002',
      vendorName: 'JSW Steel Limited',
      quotedPrice: 41500,
      landedCost: 42200,
      leadTime: 2,
      isLowestLanded: true,
      status: 'recommended',
    },
    {
      vendorId: 'SUP-001',
      vendorName: 'Tata Steel Industrial',
      quotedPrice: 42800,
      landedCost: 43500,
      leadTime: 3,
      isLowestLanded: false,
      status: 'counter_offered',
    },
    {
      vendorId: 'SUP-003',
      vendorName: 'Jindal Steel & Power',
      quotedPrice: 43200,
      landedCost: 44100,
      leadTime: 4,
      isLowestLanded: false,
      status: 'evaluated',
    },
  ];

  const supplierColumns: Column<DisplaySupplier>[] = [
    {
      key: 'name',
      header: 'Supplier Name',
      render: (s) => (
        <div>
          <div className="font-medium text-text">{s.name}</div>
          {s.isUnavailable && (
            <div className="text-[11px] text-danger bg-danger-soft px-1.5 py-0.2 rounded-[3px] inline-block mt-0.5">
              Unavailable: {s.unavailableReason || 'Stockout'}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'availability',
      header: 'Available (MT)',
      isNumeric: true,
      render: (s) => <span>{s.availability} MT</span>,
    },
    {
      key: 'reliability',
      header: 'Reliability %',
      isNumeric: true,
      render: (s) => (
        <span className={s.reliability >= 85 ? 'text-ok font-medium' : 'text-warn'}>
          {s.reliability}%
        </span>
      ),
    },
    {
      key: 'leadTimeDays',
      header: 'Lead Time',
      isNumeric: true,
      render: (s) => <span>{s.leadTimeDays} days</span>,
    },
    {
      key: 'unitPrice',
      header: 'Unit Price (INR/MT)',
      isNumeric: true,
      render: (s) => (
        <span>
          {new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0,
          }).format(s.unitPrice)}
        </span>
      ),
    },
    {
      key: 'score',
      header: 'Matrix Score',
      isNumeric: true,
      render: (s) => (
        <span className="font-mono font-semibold text-text">{s.score} / 100</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (s) => <StatusBadge status={s.status} size="sm" />,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Procurement & Vendor Intelligence"
        description="Autonomous quotation analysis, dynamic counter-offer bidding, and landed-cost optimization."
      />

      {/* Main Grid: Suppliers Table */}
      <Panel
        title={`Qualified Steel Suppliers (${supplierList.length})`}
        subtitle="SLA performance matrix and real-time quotation availability"
        padding="none"
      >
        <DataTable<DisplaySupplier>
          columns={supplierColumns}
          data={supplierList}
          keyExtractor={(s) => s.id}
          selectedId={activeSupplier?.id}
          onRowClick={(s) => setSelectedSupplierId(s.id)}
        />
      </Panel>

      {/* Requisition Offer Comparison & Negotiation Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Requisition Offers Comparison (2 cols) */}
        <div className="lg:col-span-2">
          <Panel
            title="Offers for Active Requisition (40 MT Steel Slab)"
            subtitle="Autonomous bidding quotes ranked by landed cost"
            padding="none"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-[13px]">
                <thead>
                  <tr className="bg-surface-2 h-[36px] border-b border-border text-[11px] font-semibold text-text-3 uppercase tracking-wider">
                    <th className="px-3 py-1.5">Bidding Vendor</th>
                    <th className="px-3 py-1.5 text-right">Quoted / MT</th>
                    <th className="px-3 py-1.5 text-right">Landed Cost / MT</th>
                    <th className="px-3 py-1.5 text-right">Transit Lead Time</th>
                    <th className="px-3 py-1.5">Evaluation Outcome</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {requisitionOffers.map((offer) => (
                    <tr
                      key={offer.vendorId}
                      className={`h-[40px] relative transition-colors ${
                        offer.isLowestLanded
                          ? 'bg-ok-soft/30 font-medium'
                          : 'bg-surface hover:bg-surface-2/40'
                      }`}
                    >
                      <td className="px-3 py-2 text-text relative">
                        {/* 3px ok left border on lowest landed cost */}
                        {offer.isLowestLanded && (
                          <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-ok" />
                        )}
                        <div className="flex items-center gap-2">
                          <span>{offer.vendorName}</span>
                          {offer.isLowestLanded && (
                            <span className="px-1.5 py-0.2 rounded-[3px] bg-ok text-white font-mono text-[10px] font-semibold">
                              Lowest landed cost
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums text-text-2">
                        ₹{offer.quotedPrice.toLocaleString('en-IN')}
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums font-semibold text-text">
                        ₹{offer.landedCost.toLocaleString('en-IN')}
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums text-text-3">
                        {offer.leadTime} days
                      </td>
                      <td className="px-3 py-2">
                        <StatusBadge
                          status={offer.isLowestLanded ? 'approved' : 'pending'}
                          size="sm"
                          customLabel={offer.isLowestLanded ? 'Selected' : 'Evaluated'}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        {/* Right: Negotiation History Timeline (1 col) */}
        <div>
          <Panel
            title="Negotiation History"
            subtitle="Automated agent dialogue"
          >
            <div className="space-y-3 text-[12px]">
              <div className="border-l-2 border-border pl-3 space-y-1 relative">
                <span className="w-1.5 h-1.5 rounded-full bg-accent absolute -left-[4px] top-1" />
                <div className="flex justify-between text-text-3 font-mono text-[11px]">
                  <span>Round 2 — Accepted</span>
                  <span>19:15:05</span>
                </div>
                <p className="text-text font-medium leading-tight">
                  JSW Steel counter-offered ₹41,500/MT (discount ₹800/MT for 40 MT volume).
                </p>
              </div>

              <div className="border-l-2 border-border pl-3 space-y-1 relative">
                <span className="w-1.5 h-1.5 rounded-full bg-border-strong absolute -left-[4px] top-1" />
                <div className="flex justify-between text-text-3 font-mono text-[11px]">
                  <span>Round 1 — Initial RFP</span>
                  <span>19:15:02</span>
                </div>
                <p className="text-text-2 leading-tight">
                  Procurement agent requested quotes from 3 vendors for urgent 40 MT slab requirement.
                </p>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};
