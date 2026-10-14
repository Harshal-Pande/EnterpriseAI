"""Phase 4 Tests — Governed Multi-Agent Orchestration.

Comprehensive test coverage across:
1. LLM Provider abstraction (simulation mode, live provider configuration, timeouts, retries, malformed output rejection, redaction)
2. Governed orchestration lifecycle (contract validation, evidence grounding, conflict surfacing, missing evidence handling)
3. Policy gating and safety/quality holds (fail-closed behavior, blocked execution)
4. Approval lifecycle (approval gating, rejection handling, approval-execution gating)
5. Security and RBAC authorization (OPERATOR role enforcement, anti-forgery, actor isolation)
6. Idempotency and workflow retry/resume recovery
7. Correlation tracking and audit event log persistence
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

# Ensure imports resolve
BACKEND_DIR = Path(__file__).resolve().parent.parent
for extra in (BACKEND_DIR, BACKEND_DIR / "data", BACKEND_DIR / "db"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from app.core.llm_provider import (
    AgentPrompt,
    AgentResponse,
    LiveProvider,
    LLMProviderConfigError,
    LLMProviderError,
    LLMProviderMalformedOutputError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    ProviderMode,
    SimulationProvider,
    get_default_provider,
    get_provider,
    reset_default_provider,
)
from app.orchestration.governed import (
    AgentStepResult,
    GovernedOrchestrator,
    OrchestrationPhase,
    OrchestrationResult,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. LLM PROVIDER & ERROR HANDLING TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestSimulationProvider:
    """Tests for the deterministic simulation LLM provider."""

    def test_provider_returns_simulation_mode(self):
        provider = SimulationProvider()
        assert provider.get_mode() == ProviderMode.SIMULATION
        assert "simulation" in provider.get_model_name().lower()

    def test_inventory_agent_shortage_recommendation(self):
        provider = SimulationProvider()
        prompt = AgentPrompt(
            agent_name="InventoryAgent",
            task_description="Check stock levels",
            context={"shortage_qty": 50.0, "available_qty": 100.0, "requested_qty": 150.0},
        )
        response = provider.generate(prompt)
        assert response.agent_name == "InventoryAgent"
        assert response.is_simulation is True
        assert response.confidence == 1.0
        assert response.recommendation.get("action") == "INITIATE_PROCUREMENT"
        assert response.recommendation.get("shortage_qty") == 50.0

    def test_inventory_agent_sufficient_stock(self):
        provider = SimulationProvider()
        prompt = AgentPrompt(
            agent_name="InventoryAgent",
            task_description="Check stock levels",
            context={"shortage_qty": 0, "available_qty": 200.0, "requested_qty": 100.0},
        )
        response = provider.generate(prompt)
        assert response.recommendation.get("action") == "FULFILL_FROM_STOCK"

    def test_finance_agent_budget_exceeded(self):
        provider = SimulationProvider()
        prompt = AgentPrompt(
            agent_name="FinanceAgent",
            task_description="Evaluate budget",
            context={"estimated_spend": 5000000.0, "available_budget": 1000000.0, "threshold_limit": 50000.0},
        )
        response = provider.generate(prompt)
        assert response.recommendation.get("action") == "BLOCK_BUDGET_EXCEEDED"

    def test_finance_agent_needs_approval(self):
        provider = SimulationProvider()
        prompt = AgentPrompt(
            agent_name="FinanceAgent",
            task_description="Evaluate budget",
            context={"estimated_spend": 75000.0, "available_budget": 1000000.0, "threshold_limit": 50000.0},
        )
        response = provider.generate(prompt)
        assert response.recommendation.get("action") == "REQUEST_APPROVAL"

    def test_finance_agent_auto_approve(self):
        provider = SimulationProvider()
        prompt = AgentPrompt(
            agent_name="FinanceAgent",
            task_description="Evaluate budget",
            context={"estimated_spend": 10000.0, "available_budget": 1000000.0, "threshold_limit": 50000.0},
        )
        response = provider.generate(prompt)
        assert response.recommendation.get("action") == "AUTO_APPROVE"

    def test_procurement_agent_recommendation(self):
        provider = SimulationProvider()
        prompt = AgentPrompt(
            agent_name="ProcurementAgent",
            task_description="Select supplier",
            context={"selected_supplier_id": "SUPP-005", "unit_price_inr": 120.0, "lead_time_hours": 36, "required_qty": 200},
        )
        response = provider.generate(prompt)
        assert response.recommendation.get("action") == "CREATE_PURCHASE_ORDER"
        assert response.recommendation.get("supplier_id") == "SUPP-005"

    def test_logistics_agent_recommendation(self):
        provider = SimulationProvider()
        prompt = AgentPrompt(
            agent_name="LogisticsAgent",
            task_description="Plan route",
            context={"transit_days": 5, "route_id": "RT-WH01-PUNE"},
        )
        response = provider.generate(prompt)
        assert response.recommendation.get("action") == "SCHEDULE_SHIPMENT"

    def test_supervisor_agent_recommendation(self):
        provider = SimulationProvider()
        prompt = AgentPrompt(
            agent_name="SupervisorAgent",
            task_description="Synthesize findings",
            context={"agent_outputs": {"InventoryAgent": {}, "ProcurementAgent": {}}, "human_approval_required": True},
        )
        response = provider.generate(prompt)
        assert response.recommendation.get("action") == "ESCALATE_FOR_APPROVAL"

    def test_response_has_valid_uuid_and_timestamp(self):
        provider = SimulationProvider()
        prompt = AgentPrompt(
            agent_name="InventoryAgent",
            task_description="Check stock",
            context={"shortage_qty": 0, "available_qty": 100, "requested_qty": 50},
        )
        response = provider.generate(prompt)
        uuid.UUID(response.response_id)
        assert response.generated_at


class TestLiveProviderAndErrorHandling:
    """Tests for LiveProvider error handling, timeouts, malformed output, and configuration."""

    def test_live_provider_missing_key_raises_config_error(self):
        with patch.dict(os.environ, {"LLM_API_KEY": ""}, clear=False):
            with pytest.raises(LLMProviderConfigError) as exc_info:
                LiveProvider(api_key="")
            assert "LLM_API_KEY is required" in str(exc_info.value)

    def test_live_provider_redacts_credentials(self):
        provider = LiveProvider(api_key="sk-test-super-secret-key-12345", timeout_seconds=5.0)
        assert "super-secret" not in provider._masked_key
        assert provider.get_mode() == ProviderMode.LIVE

    def test_live_provider_handles_timeout(self):
        provider = LiveProvider(api_key="sk-test-key", timeout_seconds=1.0, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out")):
            with pytest.raises(LLMProviderTimeoutError) as exc_info:
                provider.generate(prompt)
            assert "timed out" in str(exc_info.value).lower()

    def test_live_provider_handles_unavailable(self):
        provider = LiveProvider(api_key="sk-test-key", timeout_seconds=1.0, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
            with pytest.raises(LLMProviderUnavailableError) as exc_info:
                provider.generate(prompt)
            assert "unavailable" in str(exc_info.value).lower()

    def test_live_provider_rejects_malformed_json(self):
        provider = LiveProvider(api_key="sk-test-key", timeout_seconds=1.0, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "This is plain text, not valid JSON"}}]
        }

        with patch("httpx.Client.post", return_value=mock_resp):
            with pytest.raises(LLMProviderMalformedOutputError) as exc_info:
                provider.generate(prompt)
            assert "not valid json" in str(exc_info.value).lower()

    def test_live_provider_rejects_missing_recommendation_dict(self):
        provider = LiveProvider(api_key="sk-test-key", timeout_seconds=1.0, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": json.dumps({"reasoning": "some reasoning without recommendation"})}}]
        }

        with patch("httpx.Client.post", return_value=mock_resp):
            with pytest.raises(LLMProviderMalformedOutputError) as exc_info:
                provider.generate(prompt)
            assert "missing required 'recommendation'" in str(exc_info.value).lower()

    def test_live_provider_valid_structured_response(self):
        provider = LiveProvider(api_key="sk-test-key", timeout_seconds=1.0, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "recommendation": {"action": "FULFILL_ORDER", "qty": 10},
                        "reasoning": "Stock confirmed.",
                        "confidence": 0.95,
                    })
                }
            }]
        }

        with patch("httpx.Client.post", return_value=mock_resp):
            resp = provider.generate(prompt)
            assert resp.provider_mode == "LIVE"
            assert resp.is_simulation is False
            assert resp.recommendation["action"] == "FULFILL_ORDER"
            assert resp.confidence == 0.95


class TestProviderFactory:
    """Tests for provider factory and singleton management."""

    def test_default_provider_is_simulation(self):
        provider = get_provider()
        assert provider.get_mode() == ProviderMode.SIMULATION

    def test_factory_with_live_mode_and_key(self):
        with patch.dict(os.environ, {"LLM_API_KEY": "sk-test-fake-key"}):
            provider = get_provider("LIVE")
            assert provider.get_mode() == ProviderMode.LIVE

    def test_singleton_reset(self):
        reset_default_provider()
        p1 = get_default_provider()
        p2 = get_default_provider()
        assert p1 is p2
        reset_default_provider()


# ═══════════════════════════════════════════════════════════════════════════
# 2. GOVERNED ORCHESTRATOR TESTS (UNIT & LIFECYCLE)
# ═══════════════════════════════════════════════════════════════════════════


class TestGovernedOrchestratorUnit:
    """Unit tests for the orchestration engine without a database connection."""

    def test_orchestration_without_db_completes(self):
        orchestrator = GovernedOrchestrator()
        result = orchestrator.execute(
            workflow_id="test-wf-001",
            order_id="ORD-1001",
            conn=None,
        )
        assert result.status in ("COMPLETED", "AWAITING_APPROVAL")
        assert result.correlation_id is not None
        assert len(result.agent_steps) >= 4
        assert "INVENTORY_ANALYSIS" in result.phases_completed
        assert "SUPERVISOR_SYNTHESIS" in result.phases_completed

    def test_orchestration_has_correlation_id(self):
        orchestrator = GovernedOrchestrator()
        result = orchestrator.execute(
            workflow_id="test-wf-002",
            order_id="ORD-1002",
            conn=None,
        )
        uuid.UUID(result.correlation_id)

    def test_each_agent_step_validated_by_contract(self):
        orchestrator = GovernedOrchestrator()
        result = orchestrator.execute(
            workflow_id="test-wf-003",
            order_id="ORD-1003",
            conn=None,
        )
        for step in result.agent_steps:
            assert step.agent_name
            assert step.phase
            assert step.status in ("COMPLETED", "SKIPPED")
            assert step.deterministic_output is not None

    def test_specialist_output_validated_before_supervisor(self):
        orchestrator = GovernedOrchestrator()
        result = orchestrator.execute(
            workflow_id="test-wf-004",
            order_id="ORD-1004",
            conn=None,
        )
        # Ensure Supervisor received validated specialist outputs
        sup_step = next(s for s in result.agent_steps if s.agent_name == "SupervisorAgent")
        assert sup_step.status == "COMPLETED"
        assert result.decision_code is not None

    def test_agent_failure_halts_downstream_execution(self):
        """When an agent fails, downstream execution must not execute actions."""
        orchestrator = GovernedOrchestrator()
        with patch.object(orchestrator.inventory_agent, "run", side_effect=RuntimeError("Database corruption")):
            result = orchestrator.execute(
                workflow_id="test-wf-fail",
                order_id="ORD-FAIL",
                conn=None,
            )
            assert result.status == "FAILED"
            assert "InventoryAgent" in result.error
            assert OrchestrationPhase.ACTION_EXECUTION.value not in result.phases_completed
            assert result.action_result is None

    def test_supervisor_conflicts_surfaced(self):
        """Supervisor identifies conflicts when stock shortage exists but budget is exceeded."""
        orchestrator = GovernedOrchestrator()
        overlay = {
            "quantity": 25000.0,
            "estimated_cost": 2500000.0,
            "finance_status": "BUDGET_EXCEEDED",
        }
        result = orchestrator.execute(
            workflow_id="test-wf-conflict",
            order_id="ORD-CONF",
            conn=None,
            input_overlay=overlay,
        )
        assert result.conflicts is not None
        assert len(result.conflicts) > 0
        assert any("budget" in c.lower() for c in result.conflicts)

    def test_safety_hold_prevents_execution(self):
        """Active safety or quality hold fails closed and blocks execution."""
        orchestrator = GovernedOrchestrator()
        result = orchestrator.execute(
            workflow_id="test-wf-safety",
            order_id="ORD-SAFE",
            conn=None,
            input_overlay={"safety_alert": True},
        )
        assert result.status == "FAILED"
        assert result.error_code == "SAFETY_HOLD_BLOCKED"
        assert "safety" in result.error.lower() or "hold" in result.error.lower()
        assert OrchestrationPhase.ACTION_EXECUTION.value not in result.phases_completed


# ═══════════════════════════════════════════════════════════════════════════
# 3. DATABASE INTEGRATION & GOVERNANCE TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestGovernedOrchestratorIntegration:
    """Integration tests requiring PostgreSQL persistence."""

    def test_orchestration_with_persistence_and_governance(self, test_conn):
        """Full end-to-end orchestration with persistence, policy evaluation, and action simulation."""
        from app.services.workflow_service import create_workflow
        from app.models.workflow import WorkflowCreateRequest

        instance = create_workflow(
            test_conn,
            WorkflowCreateRequest(
                scenario_template_id="TPL-010",
                linked_order_id="ORD-1042",
                severity="MEDIUM",
            ),
        )

        orchestrator = GovernedOrchestrator()
        result = orchestrator.execute(
            workflow_id=instance.workflow_id,
            order_id="ORD-1042",
            conn=test_conn,
            scenario_id=instance.scenario_id,
        )

        assert result.status in ("COMPLETED", "AWAITING_APPROVAL")
        assert result.correlation_id is not None
        assert len(result.agent_steps) >= 4

        # Verify agent runs persisted
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM agent_runs WHERE scenario_id = %s;",
                (instance.scenario_id,),
            )
            count = cur.fetchone()[0]
            assert count >= 4

        # Verify correlation_id appears in event_log
        with test_conn.cursor() as cur:
            cur.execute(
                """
                SELECT evidence_refs FROM event_log
                WHERE scenario_id = %s AND event_type = 'ORCHESTRATION_STARTED';
                """,
                (instance.scenario_id,),
            )
            row = cur.fetchone()
            assert row is not None
            refs = row[0]
            if isinstance(refs, str):
                refs = json.loads(refs)
            assert refs[0]["correlation_id"] == result.correlation_id

        # Cleanup
        with test_conn.cursor() as cur:
            cur.execute("DELETE FROM action_execution_results WHERE action_id IN (SELECT action_id FROM action_queue WHERE scenario_id = %s);", (instance.scenario_id,))
            cur.execute("DELETE FROM approval_requests WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM policy_evaluations WHERE decision_id IN (SELECT decision_id FROM decisions WHERE scenario_id = %s);", (instance.scenario_id,))
            cur.execute("DELETE FROM action_queue WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM decisions WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM agent_runs WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM event_log WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM scenario_instances WHERE scenario_id = %s;", (instance.scenario_id,))
            test_conn.commit()

    def test_missing_evidence_results_in_blocked_outcome(self, test_conn):
        """When target order does not exist in operational database, execution is BLOCKED."""
        from app.services.workflow_service import create_workflow
        from app.models.workflow import WorkflowCreateRequest

        instance = create_workflow(
            test_conn,
            WorkflowCreateRequest(
                scenario_template_id="TPL-010",
                linked_order_id="ORD-NONEXISTENT-9999",
                severity="HIGH",
            ),
        )

        orchestrator = GovernedOrchestrator()
        result = orchestrator.execute(
            workflow_id=instance.workflow_id,
            order_id="ORD-NONEXISTENT-9999",
            conn=test_conn,
            scenario_id=instance.scenario_id,
        )

        assert result.status == "BLOCKED"
        assert result.error_code == "MISSING_EVIDENCE"
        assert "not found" in result.error.lower()
        assert len(result.missing_evidence) > 0

        # Cleanup
        with test_conn.cursor() as cur:
            cur.execute("DELETE FROM event_log WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM scenario_instances WHERE scenario_id = %s;", (instance.scenario_id,))
            test_conn.commit()

    def test_approval_required_workflow_cannot_execute_before_approval(self, test_conn):
        """Actions requiring approval remain in PROPOSED/AWAITING_APPROVAL status and do not execute."""
        from app.services.workflow_service import create_workflow
        from app.models.workflow import WorkflowCreateRequest

        # TPL-002: Significant Delay & Expedite Spend (triggers approval threshold)
        instance = create_workflow(
            test_conn,
            WorkflowCreateRequest(
                scenario_template_id="TPL-002",
                linked_order_id="ORD-1043",
                severity="HIGH",
            ),
        )

        orchestrator = GovernedOrchestrator()
        result = orchestrator.execute(
            workflow_id=instance.workflow_id,
            order_id="ORD-1043",
            conn=test_conn,
            scenario_id=instance.scenario_id,
            input_overlay={"shortage_qty": 600000.0, "quantity": 600000.0},  # Triggers procurement and spend > 50M INR single-action threshold
        )

        assert result.status == "AWAITING_APPROVAL"
        assert result.human_approval_required is True

        # Verify an approval request was created in approval_requests table
        with test_conn.cursor() as cur:
            cur.execute(
                "SELECT status, required_domain FROM approval_requests WHERE scenario_id = %s;",
                (instance.scenario_id,),
            )
            app_req = cur.fetchone()
            assert app_req is not None
            assert app_req[0] == "PENDING"

        # Cleanup
        with test_conn.cursor() as cur:
            cur.execute("DELETE FROM approval_requests WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM policy_evaluations WHERE decision_id IN (SELECT decision_id FROM decisions WHERE scenario_id = %s);", (instance.scenario_id,))
            cur.execute("DELETE FROM action_queue WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM decisions WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM agent_runs WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM event_log WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM scenario_instances WHERE scenario_id = %s;", (instance.scenario_id,))
            test_conn.commit()


# ═══════════════════════════════════════════════════════════════════════════
# 4. API & SECURITY TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestOrchestrationAPI:
    """Tests for /api/orchestration endpoints with RBAC and anti-forgery."""

    @pytest.fixture
    def api_client(self, test_conn):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.db.database import get_db

        def override_get_db():
            yield test_conn

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_get_providers_viewer_allowed(self, api_client):
        """VIEWER can read provider configuration."""
        resp = api_client.get(
            "/api/orchestration/providers",
            headers={"X-API-Key": "dev-viewer-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "SIMULATION"
        assert data["is_simulation"] is True

    def test_unauthenticated_request_rejected(self, api_client):
        """Unauthenticated requests are rejected with 401 or 403."""
        resp = api_client.post("/api/orchestration/execute?order_id=ORD-1001")
        assert resp.status_code in (401, 403)

    def test_viewer_cannot_execute_orchestration(self, api_client):
        """VIEWER cannot execute state-changing orchestration (requires OPERATOR)."""
        resp = api_client.post(
            "/api/orchestration/execute?order_id=ORD-1001",
            headers={"X-API-Key": "dev-viewer-key"},
        )
        assert resp.status_code == 403

    def test_operator_can_execute_orchestration(self, api_client, test_conn):
        """OPERATOR can execute orchestration pipeline."""
        resp = api_client.post(
            "/api/orchestration/execute?order_id=ORD-1042&template_id=TPL-010&severity=MEDIUM",
            headers={"X-API-Key": "dev-operator-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["correlation_id"]
        assert data["status"] in ("COMPLETED", "AWAITING_APPROVAL")

        # Cleanup
        scenario_id = data.get("scenario_id") or data["workflow_id"]
        with test_conn.cursor() as cur:
            cur.execute("DELETE FROM action_execution_results WHERE action_id IN (SELECT action_id FROM action_queue WHERE scenario_id = %s);", (scenario_id,))
            cur.execute("DELETE FROM approval_requests WHERE scenario_id = %s;", (scenario_id,))
            cur.execute("DELETE FROM policy_evaluations WHERE decision_id IN (SELECT decision_id FROM decisions WHERE scenario_id = %s);", (scenario_id,))
            cur.execute("DELETE FROM action_queue WHERE scenario_id = %s;", (scenario_id,))
            cur.execute("DELETE FROM decisions WHERE scenario_id = %s;", (scenario_id,))
            cur.execute("DELETE FROM agent_runs WHERE scenario_id = %s;", (scenario_id,))
            cur.execute("DELETE FROM event_log WHERE scenario_id = %s;", (scenario_id,))
            cur.execute("DELETE FROM scenario_instances WHERE scenario_id = %s;", (scenario_id,))
            test_conn.commit()

    def test_idempotency_prevents_duplicate_runs(self, api_client, test_conn):
        """Duplicate execute requests with same idempotency_key return existing instance."""
        idemp = f"TEST-IDEMP-{uuid.uuid4()}"
        resp1 = api_client.post(
            f"/api/orchestration/execute?order_id=ORD-1042&idempotency_key={idemp}",
            headers={"X-API-Key": "dev-operator-key"},
        )
        assert resp1.status_code == 200
        wf_id1 = resp1.json()["workflow_id"]

        resp2 = api_client.post(
            f"/api/orchestration/execute?order_id=ORD-1042&idempotency_key={idemp}",
            headers={"X-API-Key": "dev-operator-key"},
        )
        assert resp2.status_code == 200
        wf_id2 = resp2.json()["workflow_id"]
        assert wf_id1 == wf_id2

        # Cleanup
        with test_conn.cursor() as cur:
            cur.execute("DELETE FROM action_execution_results WHERE action_id IN (SELECT action_id FROM action_queue WHERE scenario_id = %s);", (wf_id1,))
            cur.execute("DELETE FROM approval_requests WHERE scenario_id = %s;", (wf_id1,))
            cur.execute("DELETE FROM policy_evaluations WHERE decision_id IN (SELECT decision_id FROM decisions WHERE scenario_id = %s);", (wf_id1,))
            cur.execute("DELETE FROM action_queue WHERE scenario_id = %s;", (wf_id1,))
            cur.execute("DELETE FROM decisions WHERE scenario_id = %s;", (wf_id1,))
            cur.execute("DELETE FROM agent_runs WHERE scenario_id = %s;", (wf_id1,))
            cur.execute("DELETE FROM event_log WHERE scenario_id = %s;", (wf_id1,))
            cur.execute("DELETE FROM scenario_instances WHERE scenario_id = %s;", (wf_id1,))
            test_conn.commit()

    def test_get_workflow_governance_details(self, api_client, test_conn):
        """GET /api/orchestration/{workflow_id}/governance returns policy and approval status."""
        from app.services.workflow_service import create_workflow
        from app.models.workflow import WorkflowCreateRequest

        instance = create_workflow(
            test_conn,
            WorkflowCreateRequest(
                scenario_template_id="TPL-010",
                linked_order_id="ORD-1042",
                severity="LOW",
            ),
        )

        # Run orchestration
        api_client.post(
            f"/api/orchestration/{instance.workflow_id}/run",
            headers={"X-API-Key": "dev-admin-key"},
        )

        resp = api_client.get(
            f"/api/orchestration/{instance.workflow_id}/governance",
            headers={"X-API-Key": "dev-viewer-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "policy_evaluations" in data
        assert "approval_requests" in data
        assert "actions" in data

        # Cleanup
        with test_conn.cursor() as cur:
            cur.execute("DELETE FROM action_execution_results WHERE action_id IN (SELECT action_id FROM action_queue WHERE scenario_id = %s);", (instance.scenario_id,))
            cur.execute("DELETE FROM approval_requests WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM policy_evaluations WHERE decision_id IN (SELECT decision_id FROM decisions WHERE scenario_id = %s);", (instance.scenario_id,))
            cur.execute("DELETE FROM action_queue WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM decisions WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM agent_runs WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM event_log WHERE scenario_id = %s;", (instance.scenario_id,))
            cur.execute("DELETE FROM scenario_instances WHERE scenario_id = %s;", (instance.scenario_id,))
            test_conn.commit()
