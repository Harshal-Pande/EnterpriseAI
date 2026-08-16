# Enterprise AI Mesh — Demo Scenarios

## Scenario 1 — Normal fulfilment

**Order:** ORD-1042

**Synthetic demo input**
- Product: Industrial Water Pump (WP-800)
- Quantity: 120
- Budget: ₹850,000
- Stock: 42

**Expected flow**
1. Supervisor receives order.
2. Inventory identifies 78-unit shortage.
3. Procurement evaluates suppliers.
4. Finance validates quote.
5. Logistics validates route.
6. Supervisor closes workflow.
7. Audit events are recorded.

## Scenario 2 — Supplier unavailable

Primary supplier is unavailable.

Expected behavior:
- Procurement detects unavailable supplier.
- Supplier alternatives are ranked.
- A feasible alternative is selected.
- Finance revalidates quote.
- Logistics proceeds if SLA remains valid.
- Decision and fallback are recorded.

## Scenario 3 — Budget breach

Supplier quote exceeds budget.

Expected behavior:
- Finance rejects the quote.
- Procurement searches for a compliant alternative or renegotiates.
- Supervisor coordinates retry.
- No unauthorized approval occurs.

## Scenario 4 — Delivery delay

Selected carrier/route cannot meet the requested SLA.

Expected behavior:
- Logistics identifies failure.
- Alternative route/carrier is evaluated.
- Supervisor receives the updated feasibility.
- Workflow either continues or escalates.

## Scenario 5 — Multi-exception

Supplier availability and delivery constraints both fail.

Expected behavior:
- Supervisor coordinates multiple recovery steps.
- Shared state retains the original exception and subsequent decisions.
- Final resolution is explainable and auditable.

## Presentation rule

The UI can demonstrate these scenarios today using simulated state. Until backend integration is complete, describe them as **simulation scenarios**, not autonomous production decisions.
