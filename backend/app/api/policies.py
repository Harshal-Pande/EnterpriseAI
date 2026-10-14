"""Policy Engine API endpoints.

Provides:
- POST /api/policies/evaluate : Evaluate proposed actions against deterministic business rules
- GET /api/policies/rules : Retrieve active business rules registry
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.db.database import get_db
from app.models.policy import PolicyEvaluationRequest, PolicyEvaluationResponse
from app.services.policy_service import evaluate_policy

logger = logging.getLogger("enterpriseai.api.policies")

router = APIRouter()


@router.post("/evaluate", response_model=PolicyEvaluationResponse)
def evaluate_action_policy(
    req: PolicyEvaluationRequest,
    conn=Depends(get_db),
):
    """Deterministically evaluate a proposed action against operational business rules."""
    return evaluate_policy(conn, req)


@router.get("/rules")
def list_business_rules(conn=Depends(get_db)) -> List[Dict[str, Any]]:
    """List operational business rules from the PostgreSQL database."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT rule_id, domain, condition_expression, failure_action, severity, automation_mode, enabled
            FROM business_rules
            ORDER BY domain ASC, rule_id ASC;
            """
        )
        rows = cur.fetchall()
        return [
            {
                "rule_id": r[0],
                "domain": r[1],
                "condition_expression": r[2],
                "failure_action": r[3],
                "severity": r[4],
                "automation_mode": r[5],
                "enabled": r[6],
            }
            for r in rows
        ]
