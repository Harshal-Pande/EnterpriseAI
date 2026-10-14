"""Pydantic data models for specialist-agent execution records."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

ALLOWED_AGENT_STATUSES = {"PENDING", "RUNNING", "COMPLETED", "FAILED", "SKIPPED"}


class AgentRunCreate(BaseModel):
    scenario_id: str = Field(..., description="Parent workflow / scenario UUID")
    workflow_run_id: Optional[str] = Field(None, description="Workflow run UUID (defaults to scenario_id)")
    agent_name: str = Field(..., description="Specialist agent identifier or class name")
    input_refs: Union[List[Any], Dict[str, Any]] = Field(
        default_factory=list, description="Input references or parameters"
    )
    model_provider: Optional[str] = Field(
        "deterministic", description="Execution provider (e.g. deterministic, rule-based, scripted)"
    )
    model_name: Optional[str] = Field("scripted-agent-v1", description="Model or implementation identifier")
    prompt_version: Optional[str] = Field("v1.0", description="Prompt or logic version")


class AgentRunComplete(BaseModel):
    output: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        default=None, description="Agent execution output structured payload"
    )
    evidence_refs: List[Any] = Field(default_factory=list, description="Associated evidence or data references")


class AgentRunFail(BaseModel):
    error_code: str = Field("EXECUTION_ERROR", description="High-level error code")
    error_message: Optional[str] = Field(None, description="Sanitized error description")
    evidence_refs: List[Any] = Field(default_factory=list, description="Associated evidence or error details")


class AgentRunRecord(BaseModel):
    agent_run_id: str
    scenario_id: str
    workflow_run_id: str
    agent_name: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    input_refs: Union[List[Any], Dict[str, Any]] = Field(default_factory=list)
    output: Optional[Union[Dict[str, Any], List[Any]]] = None
    evidence_refs: List[Any] = Field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None


class AgentRunListResponse(BaseModel):
    total: int
    items: List[AgentRunRecord]
    limit: int
    offset: int
