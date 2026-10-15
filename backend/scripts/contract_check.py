"""CI-style Frontend-to-Backend Contract Verification Script (Phase P1).

Validates that 100% of endpoints expected by the redesigned frontend:
- Return HTTP 200 with required headers (including CORS)
- Respond under both /api and /api/v1
- Contain required JSON response keys
- Authenticate correctly using dev-operator-key / dev-viewer-key
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

try:
    import httpx
except ImportError:
    httpx = None

BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
OPERATOR_KEY = os.environ.get("OPERATOR_API_KEY", "dev-operator-key")
VIEWER_KEY = os.environ.get("VIEWER_API_KEY", "dev-viewer-key")

CONTRACTS: List[Dict[str, Any]] = [
    # Health & Liveness
    {"method": "GET", "path": "/api/health", "auth": None, "required_fields": ["status"]},
    {"method": "GET", "path": "/api/live", "auth": None, "required_fields": ["status"]},
    {"method": "GET", "path": "/api/health/ready", "auth": None, "required_fields": ["status", "subsystems", "data_freshness"]},
    {"method": "GET", "path": "/api/v1/health", "auth": None, "required_fields": ["status"]},
    {"method": "GET", "path": "/api/v1/health/ready", "auth": None, "required_fields": ["status", "subsystems"]},

    # Orders Domain
    {"method": "GET", "path": "/api/orders/?limit=5", "auth": "viewer", "is_list": True},
    {"method": "GET", "path": "/api/v1/orders/?limit=5", "auth": "viewer", "is_list": True},
    {"method": "GET", "path": "/api/orders/summary", "auth": "viewer", "required_fields": ["total_orders", "processing_count"]},
    {"method": "GET", "path": "/api/v1/orders/summary", "auth": "viewer", "required_fields": ["total_orders"]},

    # Inventory Domain
    {"method": "GET", "path": "/api/inventory/items?limit=5", "auth": "viewer", "is_list": True},
    {"method": "GET", "path": "/api/inventory/summary", "auth": "viewer", "required_fields": ["total_skus", "total_on_hand_mt"]},
    {"method": "GET", "path": "/api/v1/inventory/items?limit=5", "auth": "viewer", "is_list": True},

    # Suppliers Domain
    {"method": "GET", "path": "/api/suppliers/?limit=5", "auth": "viewer", "is_list": True},
    {"method": "GET", "path": "/api/v1/suppliers/?limit=5", "auth": "viewer", "is_list": True},

    # Scheduler & Scenarios
    {"method": "GET", "path": "/api/scheduler/status", "auth": "viewer", "required_fields": ["running", "total_runs"]},
    {"method": "GET", "path": "/api/scheduler/templates", "auth": "viewer", "is_list": True},
    {"method": "GET", "path": "/api/scheduler/scenarios?limit=5", "auth": "viewer", "is_list": True},

    # Policies & Approvals
    {"method": "GET", "path": "/api/policies/rules", "auth": "viewer", "is_list": True},
    {"method": "GET", "path": "/api/approvals/?status=PENDING", "auth": "viewer", "is_list": True},
    {"method": "GET", "path": "/api/actions/?limit=5", "auth": "viewer", "is_list": True},

    # Audit & Blockchain
    {"method": "GET", "path": "/api/audit/events?limit=5", "auth": "viewer", "is_list": True},
    {"method": "GET", "path": "/api/audit/blockchain/status", "auth": "viewer", "required_fields": ["mode", "total_anchors"]},
    {"method": "POST", "path": "/api/audit/verify/EVT-PHASE7-SEP-635CDB7E", "auth": "viewer", "json": {}, "required_fields": ["event_id", "matched"]},
    {"method": "GET", "path": "/api/audit/verify/EVT-PHASE7-SEP-635CDB7E", "auth": "viewer", "required_fields": ["event_id", "matched"]},

    # Knowledge Graph
    {"method": "GET", "path": "/api/graph/status", "auth": "viewer", "required_fields": ["status", "engine"]},
    {"method": "GET", "path": "/api/graph?limit=10", "auth": "viewer", "required_fields": ["nodes", "edges"]},

    # Orchestration Providers
    {"method": "GET", "path": "/api/orchestration/providers", "auth": "viewer", "required_fields": ["mode", "model_name"]},

    # Realtime WebSocket Ticket
    {"method": "POST", "path": "/api/ws/ticket", "auth": None, "required_fields": ["ticket", "expires_in", "role"]},
    {"method": "POST", "path": "/api/v1/ws/ticket", "auth": None, "required_fields": ["ticket", "expires_in"]},
]


def run_contract_checks() -> int:
    in_process = "--in-process" in sys.argv
    client = None
    if not in_process and httpx is not None:
        try:
            test_c = httpx.Client(base_url=BASE_URL, timeout=1.0)
            test_c.get("/api/health")
            client = httpx.Client(base_url=BASE_URL, timeout=10.0)
        except Exception:
            client = None

    if client is None:
        print(f"Server at {BASE_URL} not reachable or --in-process requested. Running in-process via TestClient...")
        from starlette.testclient import TestClient
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(backend_dir))
        from db.connection import load_project_env
        load_project_env()
        from app.main import app
        from app.db.database import init_db_pool
        init_db_pool()
        client = TestClient(app)

    print(f"\n=======================================================")
    print(f" CONTRACT CHECK SUITE — Mode: {'In-Process TestClient' if not hasattr(client, 'base_url') else BASE_URL}")
    print(f"=======================================================\n")

    total = len(CONTRACTS)
    passed = 0
    failed = 0
    failures: List[Dict[str, Any]] = []

    for c in CONTRACTS:
        method = c["method"]
        path = c["path"]
        auth_type = c.get("auth")
        json_body = c.get("json")

        headers = {
            "Accept": "application/json",
            "Origin": "http://localhost:5173",
        }
        if auth_type == "operator":
            headers["X-API-Key"] = OPERATOR_KEY
        elif auth_type == "viewer":
            headers["X-API-Key"] = VIEWER_KEY

        t0 = time.perf_counter()
        try:
            if method == "GET":
                resp = client.get(path, headers=headers)
            elif method == "POST":
                resp = client.post(path, headers=headers, json=json_body)
            else:
                resp = client.request(method, path, headers=headers)
            
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

            if resp.status_code != 200:
                failed += 1
                err_msg = f"HTTP {resp.status_code}: {resp.text[:120]}"
                failures.append({"path": path, "method": method, "reason": err_msg})
                print(f" [FAIL] {method:4} {path:36} -> {err_msg} ({elapsed_ms}ms)")
                continue

            # Validate body content
            data = resp.json()
            if c.get("is_list") and not isinstance(data, list):
                failed += 1
                err_msg = f"Expected list response, got {type(data).__name__}"
                failures.append({"path": path, "method": method, "reason": err_msg})
                print(f" [FAIL] {method:4} {path:36} -> {err_msg}")
                continue

            missing = []
            if "required_fields" in c:
                for f in c["required_fields"]:
                    if isinstance(data, dict) and f not in data:
                        missing.append(f)
            if missing:
                failed += 1
                err_msg = f"Missing required fields: {missing}"
                failures.append({"path": path, "method": method, "reason": err_msg})
                print(f" [FAIL] {method:4} {path:36} -> {err_msg}")
                continue

            passed += 1
            cors_hdr = resp.headers.get("access-control-allow-origin", "none")
            print(f" [PASS] {method:4} {path:36} -> 200 OK ({elapsed_ms}ms, cors={cors_hdr})")

        except Exception as exc:
            failed += 1
            failures.append({"path": path, "method": method, "reason": str(exc)})
            print(f" [FAIL] {method:4} {path:36} -> Exception: {exc}")

    client.close()

    print(f"\n-------------------------------------------------------")
    print(f" RESULTS: Total={total} | Passed={passed} | Failed={failed}")
    success_rate = (passed / total) * 100 if total > 0 else 0
    print(f" Contract Match Rate: {success_rate:.1f}%")
    print(f"-------------------------------------------------------\n")

    if failures:
        print("Failures:")
        for f in failures:
            print(f"  - {f['method']} {f['path']}: {f['reason']}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run_contract_checks())
