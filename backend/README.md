# Enterprise AI Mesh Backend

This is the backend for the Enterprise AI Mesh project.
Currently, this is a **starter implementation** to establish the repository architecture.

## Stack
- FastAPI
- LangGraph (planned for Agent orchestration)
- PostgreSQL / pgvector (planned for persistence)
- Neo4j (planned for Knowledge Graph queries)
- Web3.py (planned for blockchain interactions)

## Running Locally
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
