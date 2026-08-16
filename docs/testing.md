# Enterprise AI Mesh — Testing Strategy

## Testing layers

### 1. Unit tests

Test deterministic domain functions:
- shortage calculation
- supplier scoring
- budget validation
- SLA validation
- exception classification

### 2. Agent contract tests

Each agent must:
- accept valid state;
- reject invalid state;
- return schema-valid output;
- preserve workflow ID;
- include evidence;
- avoid mutating unrelated state.

### 3. Workflow tests

Verify:
- normal flow reaches completion;
- supplier exception reroutes;
- budget breach is rejected/recovered;
- delivery delay triggers fallback;
- multi-exception does not deadlock;
- retries do not duplicate business actions.

### 4. API integration tests

Test:
- order creation;
- workflow start;
- workflow status;
- agent status;
- audit retrieval;
- authentication;
- RBAC denial.

### 5. Database integration tests

Verify:
- order persistence;
- inventory update;
- transaction rollback;
- concurrent update handling;
- vector retrieval;
- graph consistency.

### 6. Blockchain tests

Verify:
- contract deployment;
- event recording;
- retrieval by order;
- transaction receipt;
- event emitted;
- invalid input handling.

### 7. Frontend tests

Verify:
- page navigation;
- API loading/error states;
- workflow event rendering;
- audit display;
- exception scenario rendering.

## Acceptance scenarios

### A — Normal order
Inventory sufficient or procurement succeeds, finance approves, logistics schedules, workflow completes.

### B — Supplier unavailable
Supplier A fails availability check, Procurement chooses Supplier B or C based on policy, Finance revalidates, Logistics continues.

### C — Budget breach
Quote exceeds budget. The system must not silently approve. It must negotiate, select an alternative, or escalate.

### D — Delivery delay
Primary route fails SLA. Logistics chooses an eligible fallback or escalates to Supervisor.

### E — Audit integrity
Every material transition has an application audit event and, after blockchain integration, a verifiable chain reference.

## Non-functional checks

- API latency
- workflow latency
- retry behavior
- idempotency
- memory usage
- database connection stability
- WebSocket reconnect behavior
- security headers
- secret leakage
- deterministic replay
