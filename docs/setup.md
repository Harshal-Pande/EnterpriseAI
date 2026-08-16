# Enterprise AI Mesh — Local Setup

## Current frontend prototype

```bash
cd frontend
npm install
npm run dev
```

Production build:

```bash
npm run build
```

The repository README documents the same Vite workflow.

## Current backend starter

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On Windows PowerShell, use:

```powershell
.venv\Scripts\Activate.ps1
```

## Important dependency note

The current `backend/requirements.txt` only installs FastAPI, Uvicorn, and Pydantic. LangGraph, LangChain, Neo4j, psycopg2, and Web3 dependencies are commented out.

Do not assume those integrations are installed.

## Recommended environment variables

Do not commit secrets.

```text
APP_ENV=development
API_HOST=127.0.0.1
API_PORT=8000
DATABASE_URL=postgresql://...
NEO4J_URI=bolt://...
NEO4J_USERNAME=...
NEO4J_PASSWORD=...
VECTOR_DIMENSION=...
LLM_PROVIDER=...
LLM_API_KEY=...
BLOCKCHAIN_RPC_URL=...
BLOCKCHAIN_CHAIN_ID=...
BLOCKCHAIN_CONTRACT_ADDRESS=...
BLOCKCHAIN_PRIVATE_KEY=...
JWT_SECRET=...
```

## Recommended service startup order

1. PostgreSQL
2. Neo4j
3. FastAPI
4. event bus, if enabled
5. frontend
6. blockchain interaction service, if enabled

## Development modes

### Demo mode
Frontend runs with local synthetic data.

### Integrated mode
Frontend uses FastAPI, which uses PostgreSQL/Neo4j and real workflow execution.

Keep these modes explicit. Avoid silent fallback from integrated mode to fake data.
