"""Pydantic data models and transition rules for persistent workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

# Valid statuses defined by scenario_instances CHECK constraint in 002_runtime_schema.sql
ALLOWED_WORKFLOW_STATUSES: Set[str] = {
    "QUEUED",
    "CREATED",
    "TRIAGED",
    "INVESTIGATING",
    "DECISION_READY",
    "RUNNING",
    "WAITING_APPROVAL",
    "AWAITING_APPROVAL",
    "EXECUTING",
    "RESOLVED",
    "REJECTED",
    "FAILED",
    "FAILED_SAFE",
    "CANCELLED",
    "NEEDS_HUMAN_REVIEW",
}

# Terminal states from which no further transitions are allowed
TERMINAL_STATUSES: Set[str] = {
    "RESOLVED",
    "REJECTED",
    "FAILED",
    "FAILED_SAFE",
    "CANCELLED",
}

# Explicit validated transition graph
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    "QUEUED": {"RUNNING", "CANCELLED", "TRIAGED"},
    "CREATED": {"TRIAGED", "RUNNING", "CANCELLED"},
    "TRIAGED": {"INVESTIGATING", "RUNNING", "CANCELLED"},
    "INVESTIGATING": {
        "DECISION_READY",
        "WAITING_APPROVAL",
        "AWAITING_APPROVAL",
        "RUNNING",
        "RESOLVED",
        "FAILED",
        "CANCELLED",
    },
    "DECISION_READY": {
        "WAITING_APPROVAL",
        "AWAITING_APPROVAL",
        "EXECUTING",
        "RESOLVED",
        "REJECTED",
        "FAILED",
        "CANCELLED",
    },
    "RUNNING": {
        "WAITING_APPROVAL",
        "AWAITING_APPROVAL",
        "EXECUTING",
        "RESOLVED",
        "FAILED",
        "FAILED_SAFE",
        "CANCELLED",
        "NEEDS_HUMAN_REVIEW",
    },
    "WAITING_APPROVAL": {"EXECUTING", "RESOLVED", "REJECTED", "CANCELLED", "RUNNING"},
    "AWAITING_APPROVAL": {"EXECUTING", "RESOLVED", "REJECTED", "CANCELLED", "RUNNING"},
    "EXECUTING": {"RESOLVED", "FAILED", "FAILED_SAFE", "NEEDS_HUMAN_REVIEW", "CANCELLED"},
    "NEEDS_HUMAN_REVIEW": {"RESOLVED", "REJECTED", "CANCELLED", "RUNNING"},
    "RESOLVED": set(),
    "REJECTED": set(),
    "FAILED": set(),
    "FAILED_SAFE": set(),
    "CANCELLED": set(),
}


def validate_status_transition(current_status: str, target_status: str) -> tuple[bool, str]:
    """Validate if target_status is a valid progression from current_status.

    Returns (is_valid, reason_or_error_message).
    """
    curr = current_status.upper()
    target = target_status.upper()

    if target not in ALLOWED_WORKFLOW_STATUSES:
        return False, f"Unknown status '{target_status}'. Allowed statuses: {sorted(ALLOWED_WORKFLOW_STATUSES)}"

    if curr in TERMINAL_STATUSES:
        return False, f"Workflow is in terminal state '{curr}' and cannot be transitioned to '{target}'"

    allowed_next = VALID_TRANSITIONS.get(curr, set())
    if target not in allowed_next:
        return (
            False,
            f"Invalid state transition from '{curr}' to '{target}'. Allowed target states: {sorted(allowed_next) if allowed_next else 'None'}",
        )

    return True, "Valid transition"


class WorkflowCreateRequest(BaseModel):
    scenario_template_id: str = Field(
        default="TPL-010",
        description="Scenario template identifier (e.g. TPL-010 NORMAL_OPERATIONS, TPL-001 INVENTORY_SHORTAGE)",
    )
    linked_order_id: Optional[str] = Field(None, description="Associated order identifier (e.g. ORD-1001)")
    linked_batch_id: Optional[str] = Field(None, description="Associated batch identifier (e.g. BATCH-201)")
    severity: str = Field(default="LOW", description="Severity level: LOW, MEDIUM, HIGH, CRITICAL")
    input_overlay: Dict[str, Any] = Field(default_factory=dict, description="Structured input or parameters")
    idempotency_key: Optional[str] = Field(
        None, description="Client-provided idempotency key to prevent duplicate creation"
    )
    data_mode: str = Field(default="SYNTHETIC", description="Data mode: SYNTHETIC, LIVE, REPLAY")
    execute_immediately: bool = Field(
        default=False, description="Whether to execute specialist agents immediately after creation"
    )


class WorkflowTransitionRequest(BaseModel):
    new_status: str = Field(..., description="Target workflow status")
    reason_code: Optional[str] = Field("MANUAL_UPDATE", description="Reason or trigger for transition")
    actor_id: Optional[str] = Field("WorkflowEngine", description="Actor initiating transition")
    actor_type: Optional[str] = Field("SYSTEM", description="Actor type: SYSTEM, AGENT, USER")
    resolution_summary: Optional[str] = Field(None, description="Summary or error message on resolution/failure")
    note: Optional[str] = Field(None, description="Optional transition note")


class WorkflowInstance(BaseModel):
    workflow_id: str
    scenario_id: str
    workflow_run_id: str
    scenario_template_id: str
    status: str
    severity: str
    linked_order_id: Optional[str] = None
    linked_batch_id: Optional[str] = None
    input_overlay: Dict[str, Any] = Field(default_factory=dict)
    resolution_summary: Optional[str] = None
    idempotency_key: str
    data_mode: str
    created_at: str
    scheduled_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    current_agent: Optional[str] = None
    agent_runs_count: int = 0


class WorkflowListResponse(BaseModel):
    total: int
    items: List[WorkflowInstance]
    limit: int
    offset: int
