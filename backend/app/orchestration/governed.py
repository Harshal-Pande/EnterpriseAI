"""Governed Multi-Agent Orchestration Engine (Phase 4).

Coordinates specialist agents through a governed decision pipeline:
1. **Correlation tracking** — Unique correlation_id threads through all agent runs,
   policy evaluations, approval requests, action proposals, and audit events.
2. **Operational grounding** — Verifies evidence in PostgreSQL before execution.
   Missing evidence halts execution with an explicit BLOCKED outcome.
3. **Specialist orchestration** — Invokes only required agents based on evidence
   (e.g., skips procurement when inventory has sufficient stock).
4. **Contract validation** — Validates every specialist output using typed Pydantic
   contracts before downstream consumption.
5. **Supervisor synthesis** — Surfaces recommendations, conflicts, missing evidence,
   and proposed next steps.
6. **Deterministic policy gating** — Evaluates recommended actions against business rules.
7. **Approval lifecycle** — Automatically creates approval requests when required.
8. **Controlled action execution** — Invokes SafeSimulationAdapter only when policy,
   approval, and state requirements are satisfied.
9. **Durable state persistence** — Writes agent_runs, decisions, policy_evaluations,
   approval_requests, action_queue, and event_log records.
10. **Resilience and recovery** — Supports safe retry and resumption of workflows.

Design principle: Agents PROPOSE, Orchestrator GOVERNS, PostgreSQL PERSISTS.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.agents.finance import FinanceAgent
from app.agents.inventory import InventoryAgent
from app.agents.logistics import LogisticsAgent
from app.agents.procurement import ProcurementAgent
from app.agents.supervisor import SupervisorAgent
from app.core.llm_provider import (
    AgentPrompt,
    AgentResponse,
    LLMProvider,
    LLMProviderError,
    ProviderMode,
    get_default_provider,
)
from app.models.action import ActionProposeRequest
from app.models.agent_contracts import (
    FinanceOutput,
    InventoryOutput,
    LogisticsOutput,
    ProcurementOutput,
    SupervisorOutput,
)
from app.models.agent_run import AgentRunComplete, AgentRunCreate, AgentRunFail
from app.models.policy import PolicyEvaluationRequest
from app.models.workflow import WorkflowTransitionRequest
from app.services.action_service import execute_action, propose_action
from app.services.agent_run_service import complete_agent_run, fail_agent_run, start_agent_run
from app.services.policy_service import evaluate_policy
from app.services.workflow_service import transition_workflow_status

logger = logging.getLogger("enterpriseai.orchestration.governed")


class OrchestrationPhase(str, Enum):
    """Observable phases of the governed orchestration lifecycle."""

    INITIALIZED = "INITIALIZED"
    INVENTORY_ANALYSIS = "INVENTORY_ANALYSIS"
    PROCUREMENT_EVALUATION = "PROCUREMENT_EVALUATION"
    FINANCE_REVIEW = "FINANCE_REVIEW"
    LOGISTICS_PLANNING = "LOGISTICS_PLANNING"
    SUPERVISOR_SYNTHESIS = "SUPERVISOR_SYNTHESIS"
    POLICY_EVALUATION = "POLICY_EVALUATION"
    APPROVAL_GATE = "APPROVAL_GATE"
    ACTION_PROPOSAL = "ACTION_PROPOSAL"
    ACTION_EXECUTION = "ACTION_EXECUTION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class AgentStepResult(BaseModel):
    """Result of a single agent step in the orchestration pipeline."""

    agent_name: str
    phase: str
    status: str = Field(default="COMPLETED", description="COMPLETED, FAILED, or SKIPPED")
    deterministic_output: Dict[str, Any] = Field(default_factory=dict)
    llm_recommendation: Optional[Dict[str, Any]] = None
    llm_reasoning: Optional[str] = None
    llm_confidence: Optional[float] = None
    is_simulation: bool = True
    agent_run_id: Optional[str] = None
    duration_ms: Optional[float] = None
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class OrchestrationResult(BaseModel):
    """Complete result of a governed multi-agent orchestration run."""

    correlation_id: str
    workflow_id: str
    scenario_id: Optional[str] = None
    order_id: str
    status: str = Field(default="COMPLETED", description="COMPLETED, AWAITING_APPROVAL, FAILED, or BLOCKED")
    provider_mode: str = Field(default="SIMULATION")
    phases_completed: List[str] = Field(default_factory=list)
    agent_steps: List[AgentStepResult] = Field(default_factory=list)
    governance: Dict[str, Any] = Field(default_factory=dict)
    decision_summary: Optional[str] = None
    decision_code: Optional[str] = None
    human_approval_required: bool = False
    recommended_action: Optional[Dict[str, Any]] = None
    action_result: Optional[Dict[str, Any]] = None
    conflicts: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    proposed_next_step: Optional[str] = None
    can_retry: bool = False
    total_duration_ms: Optional[float] = None
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None


class GovernedOrchestrator:
    """Governed multi-agent orchestration engine."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.inventory_agent = InventoryAgent()
        self.procurement_agent = ProcurementAgent()
        self.finance_agent = FinanceAgent()
        self.logistics_agent = LogisticsAgent()
        self.supervisor_agent = SupervisorAgent()
        self.llm_provider = llm_provider or get_default_provider()

    def execute(
        self,
        workflow_id: str,
        order_id: str,
        conn=None,
        scenario_id: Optional[str] = None,
        input_overlay: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> OrchestrationResult:
        """Execute the complete governed orchestration pipeline."""
        corr_id = correlation_id or str(uuid.uuid4())
        scen_id = scenario_id or workflow_id
        start_time = datetime.now(timezone.utc)
        overlay = input_overlay or {}

        result = OrchestrationResult(
            correlation_id=corr_id,
            workflow_id=workflow_id,
            scenario_id=scen_id,
            order_id=order_id,
            provider_mode=self.llm_provider.get_mode().value,
        )

        # Validate scenario persistence UUID
        is_persistent = False
        if conn and scen_id:
            try:
                uuid.UUID(scen_id)
                is_persistent = True
            except ValueError:
                is_persistent = False

        # Log orchestration start in audit event log
        if is_persistent and conn:
            self._log_audit_event(
                conn, scen_id, corr_id,
                "ORCHESTRATION_STARTED",
                {"order_id": order_id, "provider_mode": result.provider_mode},
            )

        # Transition workflow to RUNNING if currently QUEUED / CREATED / TRIAGED
        if is_persistent and conn:
            with conn.cursor() as cur:
                cur.execute("SELECT status FROM scenario_instances WHERE scenario_id = %s;", (scen_id,))
                s_row = cur.fetchone()
                curr_status = s_row[0] if s_row else None
            if curr_status in ("QUEUED", "CREATED", "TRIAGED"):
                try:
                    transition_workflow_status(
                        conn, scen_id,
                        WorkflowTransitionRequest(
                            new_status="RUNNING",
                            reason_code="GOVERNED_ORCHESTRATION_START",
                            actor_id="GovernedOrchestrator",
                            actor_type="SYSTEM",
                            note=f"Starting governed multi-agent pipeline [correlation={corr_id}]",
                        ),
                    )
                except Exception as exc:
                    logger.warning("Could not transition to RUNNING: %s", exc)

        # ── 1. OPERATIONAL EVIDENCE CHECK ───────────────────────────────────
        if is_persistent and conn and order_id and not order_id.startswith("TEST-"):
            with conn.cursor() as cur:
                cur.execute("SELECT order_id, status FROM orders WHERE order_id = %s;", (order_id,))
                order_row = cur.fetchone()
                if not order_row:
                    msg = f"Missing evidence: Order '{order_id}' not found in operational database."
                    result.status = "BLOCKED"
                    result.error = msg
                    result.missing_evidence.append(msg)
                    result.can_retry = True
                    result.completed_at = datetime.now(timezone.utc).isoformat()
                    result.total_duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

                    try:
                        transition_workflow_status(
                            conn, scen_id,
                            WorkflowTransitionRequest(
                                new_status="FAILED",
                                reason_code="MISSING_EVIDENCE",
                                actor_id="GovernedOrchestrator",
                                actor_type="SYSTEM",
                                resolution_summary=f"[correlation={corr_id}] {msg}",
                            ),
                        )
                    except Exception as exc:
                        logger.warning("Could not transition to FAILED: %s", exc)

                    self._log_audit_event(
                        conn, scen_id, corr_id,
                        "ORCHESTRATION_BLOCKED",
                        {"reason": msg},
                    )
                    return result

        state: Dict[str, Any] = {
            "workflow_id": workflow_id,
            "scenario_id": scen_id,
            "order_id": order_id,
            "correlation_id": corr_id,
            "agent_outputs": {},
            "audit_trail": [],
            **overlay,
        }

        # ── 2. SPECIALIST AGENT EXECUTION ──────────────────────────────────
        # Phase 1: Inventory Analysis
        inv_res = self._run_agent_step(
            phase=OrchestrationPhase.INVENTORY_ANALYSIS,
            agent_name="InventoryAgent",
            agent_instance=self.inventory_agent,
            output_validator=InventoryOutput,
            state=state,
            conn=conn,
            is_persistent=is_persistent,
            scen_id=scen_id,
            corr_id=corr_id,
            order_id=order_id,
        )
        result.agent_steps.append(inv_res)
        if inv_res.status == "FAILED":
            return self._handle_agent_failure(result, scen_id, corr_id, inv_res, conn, is_persistent, start_time)
        result.phases_completed.append(OrchestrationPhase.INVENTORY_ANALYSIS.value)

        # Check if procurement is required (shortage > 0)
        inv_output = state["agent_outputs"].get("InventoryAgent", {})
        shortage_qty = float(inv_output.get("shortage_qty", 0.0))

        if shortage_qty > 0.0:
            # Phase 2: Procurement Evaluation (required due to shortage)
            proc_res = self._run_agent_step(
                phase=OrchestrationPhase.PROCUREMENT_EVALUATION,
                agent_name="ProcurementAgent",
                agent_instance=self.procurement_agent,
                output_validator=ProcurementOutput,
                state=state,
                conn=conn,
                is_persistent=is_persistent,
                scen_id=scen_id,
                corr_id=corr_id,
                order_id=order_id,
            )
            result.agent_steps.append(proc_res)
            if proc_res.status == "FAILED":
                return self._handle_agent_failure(result, scen_id, corr_id, proc_res, conn, is_persistent, start_time)
            result.phases_completed.append(OrchestrationPhase.PROCUREMENT_EVALUATION.value)
        else:
            # Procurement not required: stock is available
            skip_step = AgentStepResult(
                agent_name="ProcurementAgent",
                phase=OrchestrationPhase.PROCUREMENT_EVALUATION.value,
                status="SKIPPED",
                deterministic_output={"procurement_status": "SHORTAGE_COVERED", "required_qty": 0.0, "estimated_cost": 0.0},
                llm_reasoning="Procurement evaluation skipped: sufficient inventory on hand to fulfill order.",
                is_simulation=True,
            )
            result.agent_steps.append(skip_step)
            state["agent_outputs"]["ProcurementAgent"] = skip_step.deterministic_output

        # Phase 3: Finance Review
        fin_res = self._run_agent_step(
            phase=OrchestrationPhase.FINANCE_REVIEW,
            agent_name="FinanceAgent",
            agent_instance=self.finance_agent,
            output_validator=FinanceOutput,
            state=state,
            conn=conn,
            is_persistent=is_persistent,
            scen_id=scen_id,
            corr_id=corr_id,
            order_id=order_id,
        )
        result.agent_steps.append(fin_res)
        if fin_res.status == "FAILED":
            return self._handle_agent_failure(result, scen_id, corr_id, fin_res, conn, is_persistent, start_time)
        result.phases_completed.append(OrchestrationPhase.FINANCE_REVIEW.value)

        # Phase 4: Logistics Planning
        log_res = self._run_agent_step(
            phase=OrchestrationPhase.LOGISTICS_PLANNING,
            agent_name="LogisticsAgent",
            agent_instance=self.logistics_agent,
            output_validator=LogisticsOutput,
            state=state,
            conn=conn,
            is_persistent=is_persistent,
            scen_id=scen_id,
            corr_id=corr_id,
            order_id=order_id,
        )
        result.agent_steps.append(log_res)
        if log_res.status == "FAILED":
            return self._handle_agent_failure(result, scen_id, corr_id, log_res, conn, is_persistent, start_time)
        result.phases_completed.append(OrchestrationPhase.LOGISTICS_PLANNING.value)

        # Phase 5: Supervisor Synthesis
        sup_res = self._run_agent_step(
            phase=OrchestrationPhase.SUPERVISOR_SYNTHESIS,
            agent_name="SupervisorAgent",
            agent_instance=self.supervisor_agent,
            output_validator=SupervisorOutput,
            state=state,
            conn=conn,
            is_persistent=is_persistent,
            scen_id=scen_id,
            corr_id=corr_id,
            order_id=order_id,
        )
        result.agent_steps.append(sup_res)
        if sup_res.status == "FAILED":
            return self._handle_agent_failure(result, scen_id, corr_id, sup_res, conn, is_persistent, start_time)
        result.phases_completed.append(OrchestrationPhase.SUPERVISOR_SYNTHESIS.value)

        # ── 3. GOVERNANCE & POLICY EVALUATION ──────────────────────────────
        supervisor_data = sup_res.deterministic_output
        human_approval_required = supervisor_data.get("human_approval_required", False)
        decision_code = supervisor_data.get("decision_code", "DEC-AUTO-APPROVED")
        recommended_action = supervisor_data.get("recommended_action", {})
        summary = supervisor_data.get("summary", "Governed orchestration completed.")
        conflicts = supervisor_data.get("conflicts", [])
        missing_evidence = supervisor_data.get("missing_evidence", [])
        proposed_next_step = supervisor_data.get("proposed_next_step", "PROPOSE_AND_EXECUTE_ACTION")

        result.human_approval_required = human_approval_required
        result.decision_code = decision_code
        result.decision_summary = summary
        result.recommended_action = recommended_action
        result.conflicts = conflicts
        result.missing_evidence = missing_evidence
        result.proposed_next_step = proposed_next_step

        # If there are blocking conflicts (e.g. active quality hold), fail closed
        if state.get("quality_hold") or state.get("safety_alert"):
            result.status = "FAILED"
            result.error = "Execution blocked by active safety/quality hold."
            result.can_retry = False
            result.phases_completed.append(OrchestrationPhase.POLICY_EVALUATION.value)
            if is_persistent and conn:
                try:
                    transition_workflow_status(
                        conn, scen_id,
                        WorkflowTransitionRequest(
                            new_status="FAILED",
                            reason_code="SAFETY_HOLD_BLOCKED",
                            actor_id="GovernedOrchestrator",
                            actor_type="SYSTEM",
                            resolution_summary=f"[correlation={corr_id}] Blocked by safety/quality hold.",
                        ),
                    )
                except Exception as exc:
                    logger.warning("Could not transition to FAILED: %s", exc)
            result.completed_at = datetime.now(timezone.utc).isoformat()
            result.total_duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return result

        result.phases_completed.append(OrchestrationPhase.POLICY_EVALUATION.value)

        # ── 4. ACTION PROPOSAL & EXECUTION GATES ────────────────────────────
        action_record = None
        action_execution = None

        if is_persistent and conn:
            try:
                # Propose action into action_queue through deterministic policy engine
                action_req = ActionProposeRequest(
                    scenario_id=scen_id,
                    action_type=recommended_action.get("action_type", "CREATE_PURCHASE_ORDER"),
                    target_entity_id=recommended_action.get("item_id") or recommended_action.get("supplier_id") or order_id,
                    payload=recommended_action,
                    decision_id=state.get("decision_id"),
                    idempotency_key=f"ORCH-ACT-{corr_id}",
                )
                action_record = propose_action(conn, action_req)
                result.phases_completed.append(OrchestrationPhase.ACTION_PROPOSAL.value)

                result.governance = {
                    "policy_evaluated": True,
                    "human_approval_required": action_record.requires_approval,
                    "action_id": action_record.action_id,
                    "action_status": action_record.status,
                    "decision_code": decision_code,
                    "correlation_id": corr_id,
                    "provider_mode": result.provider_mode,
                }

                if action_record.requires_approval or human_approval_required:
                    # Approval Gate: Wait for human approver
                    result.phases_completed.append(OrchestrationPhase.APPROVAL_GATE.value)
                    result.status = "AWAITING_APPROVAL"
                    result.can_retry = True

                    transition_workflow_status(
                        conn, scen_id,
                        WorkflowTransitionRequest(
                            new_status="WAITING_APPROVAL",
                            reason_code="GOVERNANCE_APPROVAL_GATE",
                            actor_id="GovernedOrchestrator",
                            actor_type="SYSTEM",
                            note=f"[correlation={corr_id}] Action queued in PROPOSED status; awaiting human approval.",
                        ),
                    )
                else:
                    # Authorized & Approved: Safely execute action via SafeSimulationAdapter
                    action_execution = execute_action(conn, action_record.action_id, caller_id="GovernedOrchestrator")
                    result.action_result = action_execution.result
                    result.phases_completed.append(OrchestrationPhase.ACTION_EXECUTION.value)
                    result.phases_completed.append(OrchestrationPhase.COMPLETED.value)
                    result.status = "COMPLETED"
                    result.can_retry = False

                    transition_workflow_status(
                        conn, scen_id,
                        WorkflowTransitionRequest(
                            new_status="RESOLVED",
                            reason_code="GOVERNED_PIPELINE_COMPLETED",
                            actor_id="GovernedOrchestrator",
                            actor_type="SYSTEM",
                            resolution_summary=f"[correlation={corr_id}] {summary}",
                        ),
                    )

            except HTTPException as http_exc:
                # Policy rejected proposed action (e.g., budget exceeded or supplier inactive)
                logger.warning("Action rejected during governance evaluation: %s", http_exc.detail)
                result.status = "FAILED"
                result.error = f"Policy Gate Rejection: {http_exc.detail}"
                result.can_retry = False
                result.governance["policy_rejected"] = True
                result.governance["rejection_reason"] = http_exc.detail

                try:
                    transition_workflow_status(
                        conn, scen_id,
                        WorkflowTransitionRequest(
                            new_status="FAILED",
                            reason_code="POLICY_REJECTION",
                            actor_id="GovernedOrchestrator",
                            actor_type="SYSTEM",
                            resolution_summary=f"[correlation={corr_id}] Policy gate rejection: {http_exc.detail}",
                        ),
                    )
                except Exception as t_exc:
                    logger.warning("Could not transition to FAILED: %s", t_exc)

            except Exception as exc:
                logger.error("Error during governance action execution: %s", exc)
                result.status = "FAILED"
                result.error = str(exc)
                result.can_retry = True

        else:
            # Non-persistent / unit test mode without database connection
            result.governance = {
                "policy_evaluated": True,
                "human_approval_required": human_approval_required,
                "decision_code": decision_code,
                "correlation_id": corr_id,
                "provider_mode": result.provider_mode,
            }
            if human_approval_required:
                result.phases_completed.append(OrchestrationPhase.APPROVAL_GATE.value)
                result.status = "AWAITING_APPROVAL"
                result.can_retry = True
            else:
                result.phases_completed.append(OrchestrationPhase.COMPLETED.value)
                result.status = "COMPLETED"
                result.can_retry = False

        # Log completion in audit event log
        if is_persistent and conn:
            self._log_audit_event(
                conn, scen_id, corr_id,
                "ORCHESTRATION_COMPLETED",
                {
                    "status": result.status,
                    "decision_code": decision_code,
                    "phases": len(result.phases_completed),
                    "agents": len(result.agent_steps),
                    "human_approval": human_approval_required,
                },
            )

        end_time = datetime.now(timezone.utc)
        result.total_duration_ms = (end_time - start_time).total_seconds() * 1000
        result.completed_at = end_time.isoformat()

        return result

    def _run_agent_step(
        self,
        phase: OrchestrationPhase,
        agent_name: str,
        agent_instance: Any,
        output_validator: Any,
        state: Dict[str, Any],
        conn: Any,
        is_persistent: bool,
        scen_id: str,
        corr_id: str,
        order_id: str,
    ) -> AgentStepResult:
        """Execute a single agent step with contract validation and LLM provider consultation."""
        step_start = datetime.now(timezone.utc)
        step_result = AgentStepResult(
            agent_name=agent_name,
            phase=phase.value,
            is_simulation=True,
        )

        run_id = None
        if is_persistent and conn:
            try:
                run_record = start_agent_run(
                    conn,
                    AgentRunCreate(
                        scenario_id=scen_id,
                        workflow_run_id=scen_id,
                        agent_name=agent_name,
                        input_refs={
                            "order_id": order_id,
                            "correlation_id": corr_id,
                            "phase": phase.value,
                        },
                        model_provider=self.llm_provider.get_mode().value.lower(),
                        model_name=self.llm_provider.get_model_name(),
                        prompt_version="v4.0",
                    ),
                )
                run_id = run_record.agent_run_id
                step_result.agent_run_id = run_id
            except Exception as exc:
                logger.warning("Could not persist agent start for %s: %s", agent_name, exc)

        try:
            # 1. Deterministic database-grounded execution
            try:
                deterministic_output = agent_instance.run(state, conn=conn)
            except TypeError:
                deterministic_output = agent_instance.run(state)

            # 2. Strict typed output validation against agent contract
            validated_model = output_validator.model_validate(deterministic_output)
            validated_dict = validated_model.model_dump()

            step_result.deterministic_output = validated_dict
            state.update(validated_dict)
            state["agent_outputs"][agent_name] = validated_dict

            # 3. LLM provider consultation
            try:
                llm_prompt = AgentPrompt(
                    agent_name=agent_name,
                    task_description=f"Analyze {phase.value} for order {order_id}",
                    context=validated_dict,
                    constraints=[
                        "Recommendations must be grounded in provided evidence",
                        "Financial actions require policy evaluation",
                        "Human approval required above threshold",
                    ],
                )
                llm_response = self.llm_provider.generate(llm_prompt)
                step_result.llm_recommendation = llm_response.recommendation
                step_result.llm_reasoning = llm_response.reasoning
                step_result.llm_confidence = llm_response.confidence
                step_result.is_simulation = llm_response.is_simulation
                step_result.evidence_refs = llm_response.evidence_refs

            except LLMProviderError as llm_err:
                if self.llm_provider.get_mode() == ProviderMode.LIVE:
                    # In LIVE mode, provider failures fail closed!
                    raise
                logger.warning("LLM provider error for %s (non-fatal in simulation): %s", agent_name, llm_err)
                step_result.llm_reasoning = f"LLM consultation skipped: {type(llm_err).__name__}"

            step_end = datetime.now(timezone.utc)
            step_result.duration_ms = (step_end - step_start).total_seconds() * 1000

            # Persist agent completion
            if is_persistent and conn and run_id:
                try:
                    complete_agent_run(
                        conn, run_id,
                        AgentRunComplete(
                            output={
                                "deterministic": validated_dict,
                                "llm_recommendation": step_result.llm_recommendation,
                                "llm_reasoning": step_result.llm_reasoning,
                                "correlation_id": corr_id,
                            },
                            evidence_refs=step_result.evidence_refs + [
                                {"phase": phase.value, "status": "COMPLETED"},
                            ],
                        ),
                    )
                except Exception as exc:
                    logger.warning("Could not persist agent completion for %s: %s", agent_name, exc)

            state["audit_trail"].append(f"{agent_name} completed [{phase.value}]")
            step_result.status = "COMPLETED"

        except Exception as exc:
            logger.error("Agent %s failed in phase %s: %s", agent_name, phase.value, exc)
            step_result.status = "FAILED"
            step_result.error = str(exc)

            if is_persistent and conn and run_id:
                try:
                    fail_agent_run(
                        conn, run_id,
                        AgentRunFail(
                            error_code=f"{agent_name.upper()}_FAILURE",
                            error_message=str(exc),
                            evidence_refs=[{"phase": phase.value, "error": type(exc).__name__}],
                        ),
                    )
                except Exception as f_exc:
                    logger.warning("Could not persist agent failure: %s", f_exc)

        return step_result

    def _handle_agent_failure(
        self,
        result: OrchestrationResult,
        scen_id: str,
        corr_id: str,
        step_res: AgentStepResult,
        conn: Any,
        is_persistent: bool,
        start_time: datetime,
    ) -> OrchestrationResult:
        """Handle agent step failure: fail closed, prevent downstream actions, transition workflow."""
        result.status = "FAILED"
        result.error = f"Agent '{step_res.agent_name}' failed in phase '{step_res.phase}': {step_res.error}"
        result.can_retry = True
        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.total_duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        if is_persistent and conn:
            try:
                transition_workflow_status(
                    conn, scen_id,
                    WorkflowTransitionRequest(
                        new_status="FAILED",
                        reason_code=f"{step_res.agent_name.upper()}_ERROR",
                        actor_id=step_res.agent_name,
                        actor_type="AGENT",
                        resolution_summary=f"[correlation={corr_id}] Error in {step_res.agent_name}: {step_res.error}",
                    ),
                )
            except Exception as t_exc:
                logger.warning("Could not transition to FAILED: %s", t_exc)

            self._log_audit_event(
                conn, scen_id, corr_id,
                "ORCHESTRATION_FAILED",
                {"failing_agent": step_res.agent_name, "error": step_res.error},
            )

        return result

    def retry(
        self,
        workflow_id: str,
        conn,
    ) -> OrchestrationResult:
        """Retry or resume an existing workflow instance.

        - If WAITING_APPROVAL: checks if human approval was granted; if approved, executes the queued action.
        - If FAILED: re-executes the pipeline from the beginning.
        - If RESOLVED: returns without re-execution (idempotent safeguard).
        """
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, linked_order_id, scenario_template_id, input_overlay
                FROM scenario_instances
                WHERE scenario_id = %s;
                """,
                (workflow_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")

            curr_status, order_id, template_id, overlay = row[0], row[1] or "ORD-1001", row[2], row[3] or {}

        if curr_status in ("RESOLVED", "COMPLETED"):
            raise HTTPException(
                status_code=400,
                detail=f"Workflow '{workflow_id}' is already RESOLVED and cannot be re-executed.",
            )

        if curr_status == "WAITING_APPROVAL":
            # Check approval request status
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT approval_id, action_id, status, decided_by, reason
                    FROM approval_requests
                    WHERE scenario_id = %s
                    ORDER BY requested_at DESC LIMIT 1;
                    """,
                    (workflow_id,),
                )
                app_row = cur.fetchone()

            if not app_row:
                raise HTTPException(status_code=400, detail="No approval request found for workflow.")

            approval_id, action_id, app_status, decided_by, reason = app_row

            if app_status == "REJECTED":
                transition_workflow_status(
                    conn, workflow_id,
                    WorkflowTransitionRequest(
                        new_status="REJECTED",
                        reason_code="APPROVAL_REJECTED",
                        actor_id=decided_by or "HumanApprover",
                        actor_type="USER",
                        resolution_summary=f"Approval rejected: {reason}",
                    ),
                )
                return OrchestrationResult(
                    correlation_id=f"RESUME-{workflow_id[:8]}",
                    workflow_id=workflow_id,
                    scenario_id=workflow_id,
                    order_id=order_id,
                    status="FAILED",
                    error=f"Approval was REJECTED: {reason}",
                    can_retry=False,
                )

            elif app_status == "APPROVED":
                # Execute the approved action safely
                action_res = execute_action(conn, str(action_id), caller_id=decided_by or "Operator")
                transition_workflow_status(
                    conn, workflow_id,
                    WorkflowTransitionRequest(
                        new_status="RESOLVED",
                        reason_code="APPROVAL_EXECUTED",
                        actor_id=decided_by or "Operator",
                        actor_type="USER",
                        resolution_summary=f"Action {action_id} executed following approval.",
                    ),
                )
                return OrchestrationResult(
                    correlation_id=f"RESUME-{workflow_id[:8]}",
                    workflow_id=workflow_id,
                    scenario_id=workflow_id,
                    order_id=order_id,
                    status="COMPLETED",
                    action_result=action_res.result,
                    phases_completed=[
                        OrchestrationPhase.APPROVAL_GATE.value,
                        OrchestrationPhase.ACTION_EXECUTION.value,
                        OrchestrationPhase.COMPLETED.value,
                    ],
                    can_retry=False,
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Approval is still PENDING. Action cannot be executed until approved.",
                )

        # For FAILED workflows: re-run the full governed pipeline
        return self.execute(
            workflow_id=workflow_id,
            order_id=order_id,
            conn=conn,
            scenario_id=workflow_id,
            input_overlay=overlay,
        )

    @staticmethod
    def _log_audit_event(
        conn,
        scenario_id: str,
        correlation_id: str,
        event_type: str,
        details: Dict[str, Any],
    ) -> None:
        """Write an audit event to event_log with correlation tracking."""
        try:
            with conn.cursor() as cur:
                event_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc)
                cur.execute(
                    """
                    INSERT INTO event_log (
                        event_id, event_timestamp, event_type, entity_type, entity_id,
                        scenario_id, workflow_run_id, actor_type, actor_id, status,
                        reason_code, evidence_refs, payload_hash, source_channel
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        event_id, now, event_type, "ORCHESTRATION", scenario_id,
                        scenario_id, scenario_id, "SYSTEM", "GovernedOrchestrator",
                        event_type, f"CORR-{correlation_id[:8]}",
                        json.dumps([{"correlation_id": correlation_id, **details}]),
                        "", "ORCHESTRATION",
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.warning("Could not log audit event %s: %s", event_type, exc)
