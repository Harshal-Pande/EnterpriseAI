# Synthetic Data & Master Data Report (Phase P3 Reference)

## 1. Current Operational Data Limitations (Baseline)
- **Orders:** 200 orders, exactly 1 order line per order (200 total lines). No multi-line orders exist.
- **Customers:** No customer master table; orders only contain a text reference `customer_ref`.
- **Suppliers:** 8 suppliers in catalog.
- **Supplier Offers:** Only 6 offers covering 4 distinct items. Single-source items and missing alternatives exist across most products.
- **Bill of Materials:** Only 5 BOM lines; lacks multi-tier hierarchy (raw -> intermediate pig iron/slab/billet -> finished steel coils/plates).
- **Shipments & Logistics:** 120 shipments, but no carrier master table, no lane/corridor table with realistic distances and transit days.
- **Budgets:** 4 departmental budgets; easily exhausted or not applicable to varied departments.

## 2. Synthetic Data V3 Expansion Goals
1. **Deterministic Seeded Generator:** `backend/data/synth/generate.py` with reproducible seed, producing byte-identical CSVs and `manifest.json`.
2. **Anchor Dates to Current Time:** `SIM_REFERENCE_DATE = 2026-10-15`. Orders promised in future (some 1-3 days out for urgency), completed orders in past.
3. **Volume Targets:**
   - Products: 25-40 SKUs across finished goods (HR coil, CR coil, plates, TMT Fe500D) and raw materials (iron ore fines, coking coal, limestone, dolomite).
   - Customers: 60-120 accounts with Pareto distribution across sectors (Automotive OEM, Infrastructure EPC, Tube & Pipe).
   - Orders: ~1,500 to 2,500 orders with 1 to 6 lines per order (lognormal distribution).
   - Suppliers: 25 to 40 suppliers with varied risk bands and reliability ratings (0.72 to 0.99).
   - Offers: 150 to 300 active/expiring offers with realistic category pricing.
   - Carriers & Lanes: Master carrier table and lane catalog (origin, destination, mode, transit days, tonne-km cost).
   - Inventory Movements: Full ledger tracking allocations and changes to on-hand/reserved stock.
4. **Idempotence & Safety:**
   - All synthetic rows tagged with `data_origin='SYNTHETIC_V3'`.
   - Never touches or overwrites the original 1,327 workbook-derived seed rows.
   - Loaded and validated in `enterprise_ai_disposable_test` first, approved via Gate G2 before operational database load.
