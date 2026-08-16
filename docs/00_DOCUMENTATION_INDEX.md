# Enterprise AI Mesh — Documentation Index

This documentation pack is a working engineering record for the repository `Harshal-Pande/EnterpriseAI`.

## Source basis

This pack was prepared from:
1. The current public GitHub repository on the `main` branch.
2. The supplied project synopsis, `Enterprise_AI_Mesh_Synopsis.docx`.
3. Cross-checks between the repository implementation, existing `PROJECT_CONTEXT.md`, `PROJECT_ROADMAP.md`, and the synopsis.

**Important:** This pack deliberately distinguishes implemented prototype/simulation behavior from planned integrations. Do not present simulated blockchain, agent execution, RAG, database access, or benchmarks as production integrations.

## Files

| File | Purpose |
|---|---|
| `PROJECT_CONTEXT_EXTENDED.md` | Consolidated project truth and current implementation state |
| `progress.md` | Chronological progress tracker and phase status |
| `errors.md` | Known issues, implementation gaps, inconsistencies, and risks |
| `memory.md` | Persistent engineering memory for future contributors/AI coding agents |
| `architecture.md` | Current architecture plus target architecture and boundaries |
| `implementation_plan.md` | Recommended execution order from prototype to integrated system |
| `agent_specs.md` | Responsibilities, inputs, outputs, tools, and guardrails for each agent |
| `api_contract.md` | Current starter API and target API contract |
| `data_model.md` | PostgreSQL, pgvector, Neo4j, workflow-state, and audit data model |
| `benchmark.md` | Benchmark methodology and treatment of current demo metrics |
| `testing.md` | Test strategy, acceptance criteria, and validation matrix |
| `setup.md` | Local development and integration setup plan |
| `decisions.md` | Architecture decisions and rationale |
| `demo_scenarios.md` | Canonical demo scenarios and expected behavior |
| `handoff.md` | Practical next-session handoff checklist |

## Current high-level status

The repository is strongest as a **frontend operations-command-center prototype**. The backend, orchestration, database, knowledge graph, and blockchain components are starter implementations. The existing frontend uses local demo state and simulated workflow execution.

The supplied synopsis defines the intended final system as a hybrid multi-agent order-fulfilment platform with Supervisor, Inventory, Procurement, Finance, and Logistics agents; RAG/agent memory; Neo4j; PostgreSQL/pgvector; event-driven communication; blockchain audit; security; deterministic baseline comparison; and monitoring.

## Critical rule

When updating this project, keep three states separate:

- **Implemented:** verified in repository code.
- **Simulated:** visible/demo behavior that imitates a future integration.
- **Planned:** specified in the synopsis or roadmap but not implemented.
