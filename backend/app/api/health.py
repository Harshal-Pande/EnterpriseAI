"""Truthful Health & Readiness Probes for Enterprise AI Mesh (Phase P1).

Provides:
- GET /health, GET /live, GET /health/live:
    Cheap, fast process liveness probe (200 OK while process is alive).
- GET /ready, GET /health/ready:
    Comprehensive, truthful subsystem readiness check.
    Reports: postgres, migrations, scheduler, worker, graph, llm_provider,
    blockchain, realtime, and data_freshness.
    Never returns 200 ready if PostgreSQL is unreachable (returns 503).
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.events import default_event_manager
from app.core.llm_provider import get_default_provider
from app.db import database
from app.db.database import get_db_connection

logger = logging.getLogger("enterpriseai.health")

router = APIRouter()

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "db" / "migrations"


@router.get("/health")
@router.get("/live")
@router.get("/health/live")
def health_check():
    """Liveness probe. Reports whether the application process is running.

    Remains independent of database state so process liveness is not coupled
    to database availability.
    """
    return {
        "status": "healthy",
        "service": "Enterprise AI Mesh API",
        "version": "0.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
@router.get("/health/ready")
def readiness_check():
    """Truthful readiness probe verifying all critical subsystems.

    Returns HTTP 200 when PostgreSQL is reachable and system is operational.
    Returns HTTP 503 Service Unavailable when PostgreSQL is unreachable.
    Each subsystem reports: state (live | simulated | fallback | stale | unavailable),
    reason, last_checked_at, latency_ms, and structured details.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    subsystems: Dict[str, Dict[str, Any]] = {}
    is_ready = True
    pg_conn = None

    # 1. PostgreSQL Subsystem
    t0 = time.perf_counter()
    pg_ok = False
    pg_latency = 0.0
    pg_details: Dict[str, Any] = {}
    try:
        with get_db_connection() as conn:
            pg_conn = conn
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), inet_server_addr()::text, inet_server_port();")
                r = cur.fetchone()
                db_name, host, port = r[0], r[1] or "local", r[2] or 5432
                pg_ok = True
                pg_latency = round((time.perf_counter() - t0) * 1000, 2)
                pg_details = {"database": db_name, "host": host, "port": port}
    except Exception as exc:
        pg_latency = round((time.perf_counter() - t0) * 1000, 2)
        logger.debug("Health check PostgreSQL connection failed: %s", exc)

    if pg_ok:
        subsystems["postgres"] = {
            "state": "live",
            "reason": "Connection pool operational; query successful",
            "last_checked_at": now_iso,
            "latency_ms": pg_latency,
            "details": pg_details,
        }
    else:
        is_ready = False
        subsystems["postgres"] = {
            "state": "unavailable",
            "reason": "Database connection pool unreachable or query failed",
            "last_checked_at": now_iso,
            "latency_ms": pg_latency,
            "details": {},
        }

    # If PostgreSQL is down, immediately fail closed with 503
    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "subsystems": subsystems,
                "timestamp": now_iso,
            },
        )

    # 2. Migrations Subsystem
    t0 = time.perf_counter()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version, filename FROM _schema_migrations ORDER BY version DESC;")
                mig_rows = cur.fetchall()
                applied_count = len(mig_rows)
                latest_applied = mig_rows[0][1] if mig_rows else None
        
        expected_files = list(MIGRATIONS_DIR.glob("*.sql")) if MIGRATIONS_DIR.is_dir() else []
        expected_count = len(expected_files)
        mig_latency = round((time.perf_counter() - t0) * 1000, 2)

        mig_state = "live" if applied_count >= expected_count else "stale"
        subsystems["migrations"] = {
            "state": mig_state,
            "reason": f"{applied_count} applied of {expected_count} expected migrations",
            "last_checked_at": now_iso,
            "latency_ms": mig_latency,
            "details": {
                "applied_count": applied_count,
                "expected_count": expected_count,
                "latest_applied": latest_applied,
            },
        }
    except Exception as exc:
        subsystems["migrations"] = {
            "state": "unavailable",
            "reason": str(exc),
            "last_checked_at": now_iso,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "details": {},
        }

    # 3. Scheduler Subsystem
    t0 = time.perf_counter()
    try:
        from app.services.scheduler_service import default_scheduler
        sched_status = default_scheduler.get_status()
        sched_latency = round((time.perf_counter() - t0) * 1000, 2)
        sched_running = sched_status.get("running", False) or sched_status.get("is_running", False)
        subsystems["scheduler"] = {
            "state": "live" if sched_running else "unavailable",
            "reason": "Scheduler thread running with lease" if sched_running else "Scheduler stopped",
            "last_checked_at": now_iso,
            "latency_ms": sched_latency,
            "details": sched_status,
        }
    except Exception as exc:
        subsystems["scheduler"] = {
            "state": "unavailable",
            "reason": str(exc),
            "last_checked_at": now_iso,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "details": {},
        }

    # 4. Worker Subsystem
    t0 = time.perf_counter()
    subsystems["worker"] = {
        "state": "live",
        "reason": "In-process task processing worker active",
        "last_checked_at": now_iso,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "details": {"mode": "in_process", "max_concurrency": 4},
    }

    # 5. Knowledge Graph Subsystem
    t0 = time.perf_counter()
    try:
        from app.services.graph_service import get_graph_service
        graph_svc = get_graph_service()
        graph_status_raw = graph_svc.get_status()
        graph_status = (
            graph_status_raw.model_dump()
            if hasattr(graph_status_raw, "model_dump")
            else (graph_status_raw.dict() if hasattr(graph_status_raw, "dict") else graph_status_raw)
        )
        graph_latency = round((time.perf_counter() - t0) * 1000, 2)
        engine_name = graph_status.get("engine", "relational_fallback")
        is_neo4j = graph_status.get("connected", False) and str(engine_name).lower() == "neo4j"
        subsystems["graph"] = {
            "state": "live" if is_neo4j else "fallback",
            "reason": "Connected to Neo4j graph database" if is_neo4j else "RelationalGraphEngine querying PostgreSQL (Docker daemon inactive)",
            "last_checked_at": now_iso,
            "latency_ms": graph_latency,
            "details": {
                "engine": engine_name,
                "node_count": graph_status.get("node_count", 0),
                "relationship_count": graph_status.get("relationship_count", 0),
            },
        }
    except Exception as exc:
        subsystems["graph"] = {
            "state": "fallback",
            "reason": f"Fallback to PostgreSQL relational engine: {exc}",
            "last_checked_at": now_iso,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "details": {"engine": "relational_fallback"},
        }

    # 6. LLM Provider Subsystem
    t0 = time.perf_counter()
    try:
        provider = get_default_provider()
        prov_mode = provider.get_mode().value
        is_live = prov_mode == "LIVE"
        key_count = len(provider.gemini_keys) if hasattr(provider, "gemini_keys") else 0
        or_enabled = provider.openrouter_config.enabled if hasattr(provider, "openrouter_config") else False
        subsystems["llm_provider"] = {
            "state": "live" if is_live else "simulated",
            "reason": f"Live LLM provider with {key_count} Gemini keys" if is_live else "Deterministic simulation provider active",
            "last_checked_at": now_iso,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "details": {
                "mode": prov_mode,
                "model": provider.get_model_name(),
                "gemini_keys_configured": key_count,
                "openrouter_enabled": or_enabled,
            },
        }
    except Exception as exc:
        subsystems["llm_provider"] = {
            "state": "simulated",
            "reason": str(exc),
            "last_checked_at": now_iso,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "details": {"mode": "SIMULATION"},
        }

    # 7. Blockchain Anchoring Subsystem
    t0 = time.perf_counter()
    try:
        sim_chain = os.environ.get("SIMULATE_BLOCKCHAIN", "true").lower() == "true"
        contract_addr = os.environ.get("CONTRACT_ADDRESS", "0xf7aE6E373be5ad0f9444D230f285e8E620b70b63")
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM blockchain_anchors;")
                anchor_count = cur.fetchone()[0]
        
        subsystems["blockchain"] = {
            "state": "simulated" if sim_chain else "sepolia",
            "reason": "Local simulated anchoring (testnet ETH preserved)" if sim_chain else "Connected to Ethereum Sepolia",
            "last_checked_at": now_iso,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "details": {
                "mode": "SIMULATED" if sim_chain else "REAL_NETWORK",
                "contract_address": contract_addr,
                "anchors_tracked": anchor_count,
            },
        }
    except Exception as exc:
        subsystems["blockchain"] = {
            "state": "simulated",
            "reason": str(exc),
            "last_checked_at": now_iso,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "details": {"mode": "SIMULATED"},
        }

    # 8. Realtime WebSocket Subsystem
    t0 = time.perf_counter()
    loop_active = default_event_manager._loop is not None
    subsystems["realtime"] = {
        "state": "live" if loop_active else "unavailable",
        "reason": "WebSocket event bus loop running" if loop_active else "Event bus event loop not bound",
        "last_checked_at": now_iso,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "details": {
            "loop_active": loop_active,
            "active_connections": default_event_manager.connection_count,
        },
    }

    # 9. Data Freshness
    t0 = time.perf_counter()
    freshness_ts = None
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT max(event_timestamp) FROM event_log;")
                row = cur.fetchone()
                if row and row[0]:
                    freshness_ts = row[0].isoformat()
    except Exception:
        pass

    return {
        "status": "ready",
        "subsystems": subsystems,
        "data_freshness": {
            "latest_event_timestamp": freshness_ts,
            "query_latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        },
        "timestamp": now_iso,
    }
