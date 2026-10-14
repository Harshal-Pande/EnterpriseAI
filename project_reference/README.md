# Enterprise AI Supply Chain Control Room — Starter Data Pack v2

## Files
- `enterprise_ai_industrial_dataset_v2.xlsx`: PRMS-style structured workbook with reference tables, transaction tables, event history schemas and a detailed column dictionary.
- `schema_core.sql`: PostgreSQL foundation for scenario queue, agent runs, decisions, actions, event log, blockchain anchors and scheduler state.
- `simulation_config.json`: five-minute scheduler and safety configuration template.

## Dataset conventions
The workbook models a fictional integrated steel company, Eastern Alloy & Steel (EAS). It is inspired by a large steel operator's operational complexity but contains synthetic data only. It is not Tata Steel's actual data.

The workbook deliberately follows the reference workbook's data-modeling style:
- explicit reference/master tables;
- separate transaction/header and line tables;
- detailed status and policy fields;
- event logs and evidence records;
- supplier contracts, goods receipts, quality events, legal/approval boundaries;
- a data dictionary and column dictionary.

## Suggested load order
1. Reference tables (`ref_*`, products, departments, entities, warehouses, users, roles).
2. Operational master/configuration tables (supplier offers, budgets, production lines, shifts, BOM, reorder policies, business rules, scenario templates).
3. Transactional data (inventory, orders/order lines, production batches, purchase orders, goods receipts, shipments, quality, maintenance, energy, safety).
4. Runtime tables (scenario instances, agent runs, decisions, action queue, event log, blockchain anchors).

## Five-minute loop
The backend scheduler should create a new `scenario_instances` record every 300 seconds. Agent processing should run asynchronously and must not block the next scheduled scenario. Persist a unique idempotency key for each scheduled slot/template selection. Apply scenario changes as overlays rather than mutating seed data.

## Automation boundaries
Synthetic demo scenarios can run automatically. Real purchases, payments, shipment commitments, production stops/starts, quality release and safety-sensitive actions must be gated by explicit policy and designated human approval. Use allowlisted, reversible actions for auto-execution.

## Blockchain
The `blockchain_anchors` sheet/table is a schema, not proof of a live connection. Populate chain ID, contract address, transaction hash and block number only from the existing deployment and actual receipts. Anchor hashes/minimal metadata; do not publish confidential operational data on-chain.

## Important next step
Inspect the existing repository and deployed contract before connecting this pack. Align field names and API contracts to existing code rather than replacing working modules blindly.
