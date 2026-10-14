"""LangGraph orchestration graph with integrated PostgreSQL persistence.

Coordinates specialist-agent executions (Supervisor, Inventory, Procurement, Finance, Logistics).
When a database connection and workflow ID are provided, records persistent agent runs in agent_runs
and validates state transitions in scenario_instances and event_log.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from app.agents.finance import FinanceAgent
from app.agents.inventory import InventoryAgent
from app.agents.logistics import LogisticsAgent
from app.agents.procurement import ProcurementAgent
from app.agents.supervisor import SupervisorAgent
from app.models.agent_run import AgentRunComplete, AgentRunCreate, AgentRunFail
from app.models.workflow import WorkflowTransitionRequest
from app.orchestration.state import WorkflowState
from app.services.agent_run_service import complete_agent_run, fail_agent_run, start_agent_run
from app.services.workflow_service import transition_workflow_status

logger = logging.getLogger("enterpriseai.orchestration")


class WorkflowGraph:
    """Execution graph coordinating specialist agents with optional PostgreSQL persistence."""

    def __init__(self):
        self.supervisor = SupervisorAgent()
        self.inventory = InventoryAgent()
        self.procurement = ProcurementAgent()
        self.finance = FinanceAgent()
        self.logistics = LogisticsAgent()

    def run_workflow(self, initial_state: WorkflowState, conn=None) -> WorkflowState:
        """Execute the workflow through specialist agents.

        If a database connection is provided and the workflow_id/scenario_id maps
        to a persistent scenario instance, each agent's execution is durably recorded
        in agent_runs and workflow state transitions are recorded in scenario_instances.
        """
        scenario_id_str = initial_state.get("scenario_id") or initial_state.get("workflow_id")
        order_id = initial_state.get("order_id", "UNKNOWN")
        logger.info("Executing workflow for order %s (scenario: %s)", order_id, scenario_id_str)

        is_persistent = False
        if conn and scenario_id_str:
            try:
                uuid.UUID(scenario_id_str)
                is_persistent = True
            except ValueError:
                is_persistent = False

        state = dict(initial_state)
        state.setdefault("audit_trail", [])
        state.setdefault("agent_outputs", {})

        # 1. Transition workflow to RUNNING in PostgreSQL if persistent
        if is_persistent and conn:
            try:
                transition_workflow_status(
                    conn,
                    scenario_id_str,
                    WorkflowTransitionRequest(
                        new_status="RUNNING",
                        reason_code="PIPELINE_START",
                        actor_id="WorkflowGraph",
                        actor_type="SYSTEM",
                        note=f"Starting multi-agent execution pipeline for order {order_id}",
                    ),
                )
            except Exception as exc:
                logger.warning("Could not transition workflow to RUNNING: %s", exc)

        state["status"] = "running"
        pipeline = [
            ("InventoryAgent", self.inventory),
            ("ProcurementAgent", self.procurement),
            ("FinanceAgent", self.finance),
            ("LogisticsAgent", self.logistics),
            ("SupervisorAgent", self.supervisor),
        ]

        for agent_name, agent_instance in pipeline:
            state["current_agent"] = agent_name
            run_id = None

            # Persist agent start
            if is_persistent and conn:
                try:
                    run_record = start_agent_run(
                        conn,
                        AgentRunCreate(
                            scenario_id=scenario_id_str,
                            workflow_run_id=scenario_id_str,
                            agent_name=agent_name,
                            input_refs={"order_id": order_id, "state_snapshot": {k: v for k, v in state.items() if k != "agent_outputs"}},
                            model_provider="deterministic",
                            model_name=f"{agent_name.lower()}-v1",
                            prompt_version="v1.0",
                        ),
                    )
                    run_id = run_record.agent_run_id
                except Exception as exc:
                    logger.warning("Could not persist agent start for %s: %s", agent_name, exc)

            try:
                # Execute specialist agent logic with database grounding
                try:
                    step_output = agent_instance.run(state, conn=conn)
                except TypeError:
                    step_output = agent_instance.run(state)
                state.update(step_output)
                state["agent_outputs"][agent_name] = step_output
                state["audit_trail"].append(f"{agent_name} executed successfully")

                # Persist agent success
                if is_persistent and conn and run_id:
                    complete_agent_run(
                        conn,
                        run_id,
                        AgentRunComplete(
                            output=step_output,
                            evidence_refs=[{"step": agent_name, "status": "COMPLETED"}],
                        ),
                    )
            except Exception as exc:
                logger.error("Agent %s failed during workflow: %s", agent_name, exc)
                state["status"] = "failed"
                state["error"] = str(exc)
                state["audit_trail"].append(f"{agent_name} failed: {exc}")

                # Persist agent failure
                if is_persistent and conn and run_id:
                    fail_agent_run(
                        conn,
                        run_id,
                        AgentRunFail(
                            error_code=f"{agent_name.upper()}_FAILURE",
                            error_message=str(exc),
                            evidence_refs=[{"step": agent_name, "error": type(exc).__name__}],
                        ),
                    )

                # Persist workflow failure
                if is_persistent and conn:
                    try:
                        transition_workflow_status(
                            conn,
                            scenario_id_str,
                            WorkflowTransitionRequest(
                                new_status="FAILED",
                                reason_code=f"{agent_name.upper()}_ERROR",
                                actor_id=agent_name,
                                actor_type="AGENT",
                                resolution_summary=f"Execution halted due to error in {agent_name}: {exc}",
                            ),
                        )
                    except Exception as trans_exc:
                        logger.warning("Could not transition workflow to FAILED: %s", trans_exc)

                return state

        # All agents completed successfully -> mark workflow RESOLVED
        state["status"] = "completed"
        if is_persistent and conn:
            try:
                transition_workflow_status(
                    conn,
                    scenario_id_str,
                    WorkflowTransitionRequest(
                        new_status="RESOLVED",
                        reason_code="PIPELINE_COMPLETED",
                        actor_id="WorkflowGraph",
                        actor_type="SYSTEM",
                        resolution_summary="All specialist agents completed execution successfully.",
                    ),
                )
            except Exception as exc:
                logger.warning("Could not transition workflow to RESOLVED: %s", exc)

        return state
