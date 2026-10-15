"""Safely inspect environment configuration without leaking secrets (P0 Audit)."""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db.connection import load_project_env

load_project_env()

keys = [
    "APP_ENVIRONMENT",
    "DATABASE_URL",
    "TEST_DATABASE_URL",
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_1",
    "GEMINI_API_KEY_2",
    "GEMINI_API_KEY_3",
    "GEMINI_API_KEY_4",
    "GEMINI_API_KEY_5",
    "GEMINI_API_KEY_6",
    "GEMINI_API_KEY_7",
    "OPENROUTER_API_KEY",
    "LLM_PROVIDER_MODE",
    "LLM_DEFAULT_PROVIDER",
    "LLM_FALLBACK_PROVIDER",
    "SIMULATE_BLOCKCHAIN",
    "CONTRACT_ADDRESS",
    "ETH_RPC_URL",
    "BLOCKCHAIN_PRIVATE_KEY",
    "NEO4J_URI",
    "REDIS_URL",
    "JWT_SECRET",
    "OPERATOR_API_KEY",
    "ADMIN_API_KEY",
    "VIEWER_API_KEY",
    "CORS_ALLOWED_ORIGINS",
]

print("--- SAFE ENVIRONMENT INVENTORY ---")
for k in keys:
    val = os.environ.get(k)
    if val:
        masked = f"SET (length={len(val)})"
        if k in ("APP_ENVIRONMENT", "LLM_PROVIDER_MODE", "LLM_DEFAULT_PROVIDER", "LLM_FALLBACK_PROVIDER", "SIMULATE_BLOCKCHAIN", "CORS_ALLOWED_ORIGINS"):
            masked = f"SET: {val}"
        elif "DATABASE_URL" in k:
            from urllib.parse import urlparse
            p = urlparse(val)
            masked = f"SET: db='{p.path.lstrip('/')}' host='{p.hostname}' port={p.port}"
        print(f"  {k}: {masked}")
    else:
        print(f"  {k}: NOT SET")
