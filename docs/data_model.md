# Enterprise AI Mesh — Data Model

## PostgreSQL transactional model

The existing schema notes propose:

### orders
- id
- customer_id
- status
- created_at
- updated_at

### inventory
- id
- item_name
- quantity
- warehouse_id

### suppliers
- id
- name
- rating
- api_endpoint

### audit_events
- id
- order_id
- event_type
- tx_hash
- timestamp

## Recommended extensions

### orders
Add:
- product_id
- quantity
- destination_id
- budget
- priority
- workflow_id
- current_agent
- final_cost
- completed_at

### inventory
Add:
- product_id
- warehouse_id
- available_quantity
- reserved_quantity
- reorder_threshold
- updated_at

### suppliers
Add:
- reliability_score
- price_policy
- sla_days
- availability_status

### workflow_runs
- workflow_id
- order_id
- state_version
- status
- started_at
- completed_at
- failure_code

### agent_executions
- execution_id
- workflow_id
- agent_id
- input_hash
- output_hash
- started_at
- completed_at
- tool_calls
- model
- token_usage

## pgvector

Use embeddings for retrieval over:
- supplier contracts
- procurement policies
- product specifications
- logistics SLAs
- previous negotiation summaries
- exception-resolution knowledge

Store:
- document ID
- chunk ID
- text/metadata
- embedding
- source reference
- version

## Neo4j

Core entities:
- Customer
- Order
- Product
- Supplier
- Warehouse
- InventoryItem
- ProcurementDecision
- FinancialApproval
- LogisticsRoute
- AuditEvent
- Agent

Core relationships from the repository:
- Customer -[:PLACED]-> Order
- Order -[:REQUIRES]-> Product
- Warehouse -[:STORES]-> InventoryItem
- InventoryItem -[:IS_OF_TYPE]-> Product
- Supplier -[:SUPPLIES]-> Product
- Agent -[:MADE]-> ProcurementDecision
- ProcurementDecision -[:APPROVED_BY]-> FinancialApproval
- Order -[:DELIVERED_VIA]-> LogisticsRoute
- Order -[:HAS_AUDIT]-> AuditEvent

## Identifier policy

Use distinct namespaces:
- `ORD-*` order
- `PROD-*` product
- `CUST-*` customer
- `SUP-*` supplier
- `WH-*` warehouse
- `WF-*` workflow
- `AG-*` agent
- `EVT-*` event

Do not use product model numbers as order IDs.
