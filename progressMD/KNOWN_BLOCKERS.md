# Known Blockers: Enterprise AI Mesh

**Tracking Date:** 2026-10-16  

---

### Blocker 1: Live Ethereum Sepolia Testnet Credentials
- **Affected Feature:** Real on-chain audit anchoring to Ethereum Sepolia network via `blockchain_service.py`.
- **Exact Missing Dependency / Configuration:**
  - `SEPOLIA_RPC_URL` (or Infura / Alchemy endpoint)
  - `SEPOLIA_PRIVATE_KEY` (funded testnet signer wallet)
  - `SEPOLIA_CONTRACT_ADDRESS` (deployed `EnterpriseAudit.sol` contract address on Sepolia)
- **Evidence:** Environment variables default to unconfigured or mock endpoints (`DEFAULT_CHAIN_NAME="ethereum-sepolia"`, `UNCONFIGURED_CONTRACT="0x0000000000000000000000000000000000000000"`).
- **Completed Despite Blocker:** Deterministic RFC 8785 canonical digest hashing, Web3 transaction serialization, local simulation provider, state transition logic, and unit tests (21/21 passed).
- **Action Required to Unblock:** Provide valid Sepolia RPC URL, private key with testnet ETH, and deployed contract address in `.env`.
- **Verification to Rerun:** `pytest backend/tests/test_blockchain_anchoring.py -k "testnet"`

---

### Blocker 2: Live Neo4j Graph Database
- **Affected Feature:** Real-time Cypher graph queries and multi-hop entity traversal in `knowledge-graph/` and `app/api/graph.py`.
- **Exact Missing Dependency / Configuration:**
  - Neo4j server daemon (`bolt://localhost:7687` or AuraDB instance)
  - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
- **Evidence:** `test_knowledge_graph.py` utilizes in-memory fallback mock graphs when Neo4j driver connection is unavailable.
- **Completed Despite Blocker:** In-memory graph traversal, schema validation, relationship definitions, and graceful fallback to PostgreSQL entity tables.
- **Action Required to Unblock:** Start local Neo4j Docker container (`docker run -p 7687:7687 neo4j:5`) or provide AuraDB credentials.
- **Verification to Rerun:** `pytest backend/tests/test_knowledge_graph.py` with live bolt connection.

---

### Blocker 3: Live LLM Provider API Keys (Bedrock / OpenRouter / Anthropic)
- **Affected Feature:** Non-simulated LLM generation for agent reasoning in `GovernedOrchestrator`.
- **Evidence:** `SimulationProvider` is active when `OPENROUTER_API_KEY` or AWS Bedrock credentials are not configured.
- **Completed Despite Blocker:** Deterministic business logic, structured Pydantic contract validation, rule-based policy gating, and simulation provider producing compliant structured outputs.
- **Action Required to Unblock:** Configure `OPENROUTER_API_KEY` or AWS Bedrock IAM credentials in `.env`.
- **Verification to Rerun:** Run live agent evaluation cycle against real model endpoint.
