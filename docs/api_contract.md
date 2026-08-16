# Enterprise AI Mesh — API Contract

## Current starter endpoints

### Health
`GET /api/...`

The exact health route should be checked in the backend router before final deployment.

### Orders
`GET /api/orders/`
Returns a starter order list.

`POST /api/orders/`
Accepts a generic dictionary and returns a hardcoded created order ID.

### Workflow
`GET /api/workflow/{workflow_id}`
Returns starter workflow status.

### Agents
`GET /api/agents/`
Returns hardcoded agent statuses.

### Audit
`GET /api/audit/`
Returns a starter audit event with a synthetic transaction hash.

## Target API

### Orders

`POST /api/v1/orders`

Request:
```json
{
  "customer_id": "CUST-001",
  "product_id": "PROD-WP800",
  "quantity": 120,
  "destination_id": "WH-NAGPUR",
  "budget": 850000,
  "priority": "HIGH"
}
```

Response:
```json
{
  "order_id": "ORD-1042",
  "workflow_id": "WF-...",
  "status": "RECEIVED"
}
```

### Workflow

`POST /api/v1/workflows`

Starts an execution.

`GET /api/v1/workflows/{workflow_id}`

Returns current state and decision history.

`POST /api/v1/workflows/{workflow_id}/cancel`

Cancels an eligible workflow.

### Agents

`GET /api/v1/agents`

Returns health/capability information.

`GET /api/v1/agents/{agent_id}/executions`

Returns execution history.

### Audit

`GET /api/v1/orders/{order_id}/audit`

Returns application audit events and blockchain references.

### Knowledge

`GET /api/v1/knowledge/search?q=...`

RAG retrieval endpoint.

`GET /api/v1/graph/orders/{order_id}`

Returns relevant Neo4j subgraph.

### Real-time

`WS /api/v1/ws/workflows/{workflow_id}`

Streams workflow events.

## Error format

```json
{
  "error": {
    "code": "SUPPLIER_UNAVAILABLE",
    "message": "Selected supplier is unavailable",
    "retryable": true,
    "workflow_id": "WF-...",
    "component": "procurement",
    "timestamp": "..."
  }
}
```
