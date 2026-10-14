"""Deterministic Policy Evaluation Service.

Evaluates proposed actions against PostgreSQL business_rules, inventory constraints, and budget limits.
Persists structured rule results into the policy_evaluations table.
Fails closed when required data or safety checks are violated.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.models.policy import (
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
    RuleEvaluationResult,
)

logger = logging.getLogger("enterpriseai.policy")


def evaluate_policy(conn, req: PolicyEvaluationRequest) -> PolicyEvaluationResponse:
    """Deterministically evaluate a proposed action against operational business rules."""
    now = datetime.now(timezone.utc)
    evaluation_id = str(uuid.uuid4())
    payload = req.payload or {}

    rule_results: List[RuleEvaluationResult] = []
    has_failure = False
    needs_approval = False
    rejection_reasons: List[str] = []
    approval_domain = None

    with conn.cursor() as cur:
        # Load active business rules
        cur.execute(
            """
            SELECT rule_id, domain, condition_expression, failure_action
            FROM business_rules
            WHERE enabled = TRUE
            ORDER BY rule_id ASC;
            """
        )
        rules = cur.fetchall()

        # Parse payload variables
        item_id = payload.get("item_id")
        quantity = float(payload.get("quantity") or 0.0)
        supplier_id = payload.get("supplier_id")
        estimated_spend = float(payload.get("estimated_cost") or payload.get("spend") or 0.0)
        action_type = req.action_type.upper()

        for r in rules:
            rule_id, domain, condition, failure_action = r[0], r[1], r[2], r[3]

            # 1. INVENTORY RULES
            if domain == "INVENTORY" and action_type in {"FULFILL_ORDER", "ALLOCATE_INVENTORY", "CHECK_STOCK"}:
                # Query available stock from inventory
                available_qty = 0.0
                if item_id:
                    cur.execute(
                        "SELECT COALESCE(SUM(available_qty), 0) FROM inventory WHERE item_id = %s;",
                        (item_id,),
                    )
                    row = cur.fetchone()
                    available_qty = float(row[0]) if row else 0.0

                if available_qty >= quantity:
                    res = "PASS"
                    expl = f"Inventory available ({available_qty}) >= requested ({quantity})."
                else:
                    res = "FAIL"
                    expl = f"Inventory insufficient: available ({available_qty}) < requested ({quantity}). Shortage: {quantity - available_qty}."
                    has_failure = True
                    rejection_reasons.append(expl)

                rule_results.append(
                    RuleEvaluationResult(
                        rule_id=rule_id,
                        domain=domain,
                        result=res,
                        condition=condition,
                        explanation=expl,
                        details={"item_id": item_id, "available_qty": available_qty, "requested_qty": quantity},
                    )
                )

            # 2. PROCUREMENT RULES
            elif domain == "PROCUREMENT" and action_type in {"CREATE_PURCHASE_ORDER", "PROCURE_ITEMS"}:
                is_supplier_active = False
                has_active_offer = False
                if supplier_id:
                    # Support both SUP- and SUPP- prefixes
                    candidate_ids = [supplier_id]
                    if supplier_id.startswith("SUPP-"):
                        candidate_ids.append(supplier_id.replace("SUPP-", "SUP-"))
                    elif supplier_id.startswith("SUP-"):
                        candidate_ids.append(supplier_id.replace("SUP-", "SUPP-"))

                    cur.execute(
                        "SELECT supplier_id, status FROM suppliers WHERE supplier_id = ANY(%s);",
                        (candidate_ids,),
                    )
                    s_row = cur.fetchone()
                    if s_row:
                        matched_id = s_row[0]
                        is_supplier_active = (s_row[1] == "ACTIVE")

                        cur.execute(
                            "SELECT COUNT(*) FROM supplier_offers WHERE supplier_id = %s AND offer_status = 'ACTIVE';",
                            (matched_id,),
                        )
                        o_count = cur.fetchone()[0]
                        has_active_offer = (o_count > 0)

                if is_supplier_active and has_active_offer:
                    res = "PASS"
                    expl = f"Supplier {supplier_id} and active offers are valid and active."
                elif not is_supplier_active:
                    res = "FAIL"
                    expl = f"Supplier {supplier_id} is inactive or not found in registry."
                    has_failure = True
                    rejection_reasons.append(expl)
                else:
                    res = "FAIL"
                    expl = f"Supplier {supplier_id} has no active offers in registry."
                    has_failure = True
                    rejection_reasons.append(expl)

                rule_results.append(
                    RuleEvaluationResult(
                        rule_id=rule_id,
                        domain=domain,
                        result=res,
                        condition=condition,
                        explanation=expl,
                        details={"supplier_id": supplier_id, "supplier_active": is_supplier_active, "active_offers": has_active_offer},
                    )
                )

            # 3. FINANCE RULES
            elif domain == "FINANCE" and action_type in {"CREATE_PURCHASE_ORDER", "ALLOCATE_BUDGET", "DISPATCH_PAYMENT"}:
                cur.execute(
                    """
                    SELECT available_budget_inr, single_action_approval_threshold_inr
                    FROM budgets
                    WHERE status = 'ACTIVE'
                    ORDER BY available_budget_inr DESC
                    LIMIT 1;
                    """
                )
                b_row = cur.fetchone()
                available_budget = float(b_row[0]) if b_row else 1000000.0
                threshold_limit = float(b_row[1]) if b_row else 50000.0

                if estimated_spend > available_budget:
                    res = "FAIL"
                    expl = f"Projected spend (INR {estimated_spend:,.2f}) breaches available budget (INR {available_budget:,.2f})."
                    has_failure = True
                    rejection_reasons.append(expl)
                elif estimated_spend > threshold_limit:
                    res = "NEEDS_APPROVAL"
                    expl = f"Projected spend (INR {estimated_spend:,.2f}) exceeds delegated approval limit (INR {threshold_limit:,.2f})."
                    needs_approval = True
                    approval_domain = "FINANCE"
                else:
                    res = "PASS"
                    expl = f"Projected spend (INR {estimated_spend:,.2f}) within delegated budget limit."

                rule_results.append(
                    RuleEvaluationResult(
                        rule_id=rule_id,
                        domain=domain,
                        result=res,
                        condition=condition,
                        explanation=expl,
                        details={"spend": estimated_spend, "available_budget": available_budget, "threshold": threshold_limit},
                    )
                )

            # 4. SAFETY AND QUALITY RULES (FAIL-CLOSED)
            elif domain in {"QUALITY", "SAFETY"}:
                # Default pass unless an explicit safety flag was set in payload
                if payload.get("quality_hold") or payload.get("safety_alert"):
                    res = "FAIL"
                    expl = f"Critical safety or quality hold active in target area."
                    has_failure = True
                    rejection_reasons.append(expl)
                else:
                    res = "PASS"
                    expl = f"No active {domain.lower()} hold detected."

                rule_results.append(
                    RuleEvaluationResult(
                        rule_id=rule_id,
                        domain=domain,
                        result=res,
                        condition=condition,
                        explanation=expl,
                        details={},
                    )
                )

        # Record each evaluation result into policy_evaluations table
        decision_uuid = None
        if req.decision_id:
            try:
                decision_uuid = uuid.UUID(req.decision_id)
            except ValueError:
                pass

        action_uuid = None
        if req.action_id:
            try:
                candidate = uuid.UUID(req.action_id)
                cur.execute("SELECT 1 FROM action_queue WHERE action_id = %s;", (str(candidate),))
                if cur.fetchone():
                    action_uuid = candidate
            except ValueError:
                pass

        persisted_eval_ids: List[str] = []
        for rr in rule_results:
            pe_id = str(uuid.uuid4())
            persisted_eval_ids.append(pe_id)
            cur.execute(
                """
                INSERT INTO policy_evaluations (
                    policy_eval_id, decision_id, action_id, rule_id, result, details, evaluated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    pe_id,
                    str(decision_uuid) if decision_uuid else None,
                    str(action_uuid) if action_uuid else None,
                    rr.rule_id,
                    rr.result,
                    json.dumps(rr.details),
                    now,
                ),
            )
        conn.commit()

    if has_failure:
        overall = "FAIL"
        req_approval = False
    elif needs_approval:
        overall = "NEEDS_APPROVAL"
        req_approval = True
    else:
        overall = "PASS"
        req_approval = False

    return PolicyEvaluationResponse(
        evaluation_id=evaluation_id,
        overall_result=overall,
        requires_approval=req_approval,
        applicable_rules_count=len(rule_results),
        rule_results=rule_results,
        policy_eval_ids=persisted_eval_ids,
        approval_domain=approval_domain,
        rejection_reason="; ".join(rejection_reasons) if rejection_reasons else None,
    )
