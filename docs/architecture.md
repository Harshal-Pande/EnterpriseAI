# Enterprise AI Mesh — Architecture

## 1. Current architecture

```text
React + TypeScript + Vite
        |
        | currently mostly local demo state
        v
DemoContext / apiServices
        |
        +--> simulated agents/workflow
        +--> simulated audit ledger
        +--> simulated benchmark values

FastAPI starter
        |
        +--> /api/orders
        +--> /api/workflow
        +--> /api/agents
        +--> /api/audit

Backend starter
        |
        +--> SupervisorAgent
        +--> InventoryAgent
        +--> ProcurementAgent
        +--> FinanceAgent
        +--> LogisticsAgent
        |
        +--> WorkflowGraph simulation

Neo4j
        |
        +--> schema.cypher
        +--> sample_data.cypher

Blockchain
        |
        +--> EnterpriseAudit.sol
        +--> not deployed
```

## 2. Target architecture

```text
                         +----------------------+
                         | React Command Center |
                         +----------+-----------+
                                    |
                              HTTPS / WS
                                    |
                         +----------v-----------+
                         |     FastAPI API      |
                         | Auth + RBAC + DTOs   |
                         +----------+-----------+
                                    |
                         +----------v-----------+
                         | Workflow / LangGraph |
                         | Supervisor           |
                         +----+----+----+-------+
                              |    |    |
             +----------------+    |    +----------------+
             v                     v                     v
        Inventory             Procurement            Finance
             |                     |                     |
             +---------------------+---------------------+
                                   |
                              Logistics
                                   |
                +------------------+------------------+
                |                  |                  |
                v                  v                  v
          PostgreSQL           Neo4j/Graph        pgvector/RAG
       transactional data    relationships       business knowledge
                |
                +------------------+
                                   |
                              Audit Service
                                   |
                              Solidity Contract
                                   |
                              Polygon Testnet

Optional asynchronous layer:
FastAPI / agents -> Kafka or NATS -> event consumers -> WebSocket updates
```

## 3. Layer responsibilities

### Frontend
Only presentation, user actions, local UI state, and API consumption. It must not be the source of truth for audit, inventory, finance, or order state.

### API
Authentication, authorization, validation, orchestration entry points, query endpoints, WebSocket gateway, and error normalization.

### Orchestration
LangGraph owns workflow state transitions and agent routing. The Supervisor should make routing decisions but should not duplicate domain validation.

### Agents
Each agent owns a narrow domain capability and calls deterministic tools/services.

### PostgreSQL
Transactional source of truth.

### pgvector
Retrieval index for textual business knowledge and historical decisions.

### Neo4j
Relationship/dependency queries.

### Blockchain
Immutable checkpoint/audit evidence.

## 4. Recommended event model

Every significant event should contain:

```text
event_id
event_type
workflow_id
order_id
agent_id
timestamp
payload
evidence_refs
decision_id
severity
```

The blockchain should receive a compact hash/anchor of the event, not the entire business payload.

## 5. Important architectural decision

The final system is hybrid:

- deterministic services guarantee correctness for arithmetic, limits, stock calculations, and policy checks;
- agents coordinate and reason over context;
- the Supervisor decides which specialist should act next;
- the audit layer records material decisions.
