# Enterprise AI Mesh — Benchmark Plan

## Goal

Compare the multi-agent system with an equivalent deterministic pipeline on the same synthetic order-fulfilment workload.

## Metrics

1. End-to-end latency.
2. Processing cost.
3. Exception-handling success rate.
4. Exception recovery time.
5. Explainability score.
6. Failure rate.
7. Number of agent steps.
8. Number of LLM calls.
9. Token usage.
10. Tool-call count.

## Baseline

The deterministic baseline must perform the same business stages using fixed rules:

`Order → Inventory → Procurement → Finance → Logistics`

It must receive the same inputs as the agent system.

## Test groups

### Normal
No exception.

### Supplier unavailable
Primary supplier unavailable. System should select an eligible alternative.

### Budget breach
Initial supplier quote exceeds the order budget. System should reject/re-negotiate/escalate.

### Delivery delay
Primary route/carrier violates the SLA. System should select a feasible fallback or escalate.

### Multi-exception
Two or more exception types occur in the same workflow.

## Experimental protocol

- Use the same synthetic dataset for both systems.
- Run each scenario multiple times.
- Warm and cold runs should be reported separately if relevant.
- Record environment information.
- Record model and prompt version for LLM runs.
- Record database/broker/blockchain conditions.
- Report median and percentile latency, not only one run.

## Important warning about current frontend metrics

The current frontend benchmark service returns fixed demo values:

- latency: traditional 4800 ms vs agent mesh 1520 ms
- processing cost: ₹1450 vs ₹840
- exception handling rate: 18.5 vs 98.4
- explainability: 12.0 vs 94.5
- recovery time: 14400 sec vs 8.5 sec

These are **demo values in code**, not a completed empirical benchmark. They must not be presented as measured research results.

## Recommended result table

| Scenario | System | Runs | Median latency | P95 latency | Success | Recovery time | Cost |
|---|---|---:|---:|---:|---:|---:|---:|
| Normal | Baseline |  |  |  |  | N/A |  |
| Normal | AI Mesh |  |  |  |  | N/A |  |
| Supplier unavailable | Baseline |  |  |  |  |  |  |
| Supplier unavailable | AI Mesh |  |  |  |  |  |  |
| Budget breach | Baseline |  |  |  |  |  |  |
| Budget breach | AI Mesh |  |  |  |  |  |  |
| Delivery delay | Baseline |  |  |  |  |  |  |
| Delivery delay | AI Mesh |  |  |  |  |  |  |
