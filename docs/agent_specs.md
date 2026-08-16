# Enterprise AI Mesh — Agent Specifications

## Shared principles

Every agent:
- receives typed workflow state;
- returns a structured decision/result;
- records evidence;
- must be idempotent where possible;
- must not directly mutate unrelated domains;
- must not invent business facts;
- must expose confidence separately from factual evidence.

## Supervisor Agent

**Role:** Workflow planner and decision arbiter.

### Inputs
- order
- current workflow state
- agent results
- exception state
- policy/evidence references

### Responsibilities
- validate workflow stage;
- route to the correct specialist;
- handle cross-agent exceptions;
- decide whether to retry, reroute, or escalate;
- produce a final execution plan.

### Must not
- perform inventory arithmetic itself;
- approve finance without Finance rules;
- select suppliers without Procurement evidence.

## Inventory Agent

**Role:** Stock level and shortage monitoring.

### Inputs
- order quantity
- product ID
- warehouse inventory

### Outputs
- available quantity
- shortage quantity
- reorder signal
- evidence references

### Deterministic rule
`shortage = max(required_quantity - available_quantity, 0)`

## Procurement Agent

**Role:** Supplier comparison and negotiation.

### Inputs
- shortage
- supplier candidates
- price
- availability
- SLA
- supplier policies

### Outputs
- ranked candidates
- selected supplier
- quote
- rationale
- fallback supplier

### Guardrail
Supplier selection should be reproducible from explicit scoring rules even if an LLM generates the explanation.

## Finance Agent

**Role:** Budget validation and approval.

### Inputs
- order budget
- supplier quote
- policies
- risk constraints

### Outputs
- approved/rejected
- allocated budget
- remaining headroom
- policy evidence
- escalation reason

### Guardrail
The LLM must never be the calculator for financial limits.

## Logistics Agent

**Role:** Route feasibility and delivery scheduling.

### Inputs
- supplier location
- destination
- shipment size
- carrier SLA
- route constraints

### Outputs
- selected route
- ETA
- carrier
- feasibility
- fallback route

## Agent communication contract

Recommended message:

```json
{
  "workflow_id": "WF-...",
  "order_id": "ORD-1042",
  "source_agent": "inventory",
  "target_agent": "procurement",
  "message_type": "INVENTORY_SHORTAGE",
  "payload": {},
  "evidence_refs": [],
  "timestamp": "..."
}
```
