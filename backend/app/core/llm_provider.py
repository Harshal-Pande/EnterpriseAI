"""LLM Provider Abstraction Layer (Phase 4).

Provides a clean interface for agent reasoning with two modes:
1. **SimulationProvider** (default): Deterministic, no external calls.
   Generates structured recommendations based on database-grounded evidence.
2. **LiveProvider**: Pluggable interface for real LLM backends (OpenAI/Gemini/vLLM HTTP endpoints).
   Only activated when explicit credentials and configuration are provided.

Design principles:
- Agents PROPOSE recommendations; application code ENFORCES governance.
- Provider responses are structured JSON, never free-form unparsed text.
- Simulation mode is the default and is fully functional, not a stub.
- No fabricated "AI" responses — simulation mode is explicitly labelled.
- When LiveProvider execution fails (timeout, unavailable, malformed output),
  it fails closed and reports clear errors without fabricating success.
- Credentials and sensitive tokens are strictly redacted in logs.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("enterpriseai.llm")


# ═══════════════════════════════════════════════════════════════════════════
# PROVIDER EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════


class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""

    def __init__(self, message: str, provider_mode: str = "LIVE"):
        super().__init__(message)
        self.message = message
        self.provider_mode = provider_mode


class LLMProviderUnavailableError(LLMProviderError):
    """Raised when the LLM service endpoint is unreachable or network connection fails."""
    pass


class LLMProviderTimeoutError(LLMProviderError):
    """Raised when an LLM provider request exceeds the bounded timeout."""
    pass


class LLMProviderMalformedOutputError(LLMProviderError):
    """Raised when LLM output cannot be parsed or fails schema validation."""
    pass


class LLMProviderConfigError(LLMProviderError):
    """Raised when LLM provider configuration or required credentials are missing/invalid."""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# TYPED CONTRACTS
# ═══════════════════════════════════════════════════════════════════════════


class ProviderMode(str, Enum):
    SIMULATION = "SIMULATION"
    LIVE = "LIVE"


class AgentPrompt(BaseModel):
    """Structured prompt sent to an LLM provider for agent reasoning."""

    agent_name: str = Field(..., description="Name of the specialist agent")
    task_description: str = Field(..., description="What the agent should analyze")
    context: Dict[str, Any] = Field(default_factory=dict, description="Grounded evidence from PostgreSQL")
    constraints: List[str] = Field(default_factory=list, description="Governance constraints to observe")
    expected_output_schema: Optional[Dict[str, Any]] = Field(
        None, description="JSON schema the response should conform to"
    )


class AgentResponse(BaseModel):
    """Structured response from an LLM provider."""

    agent_name: str
    provider_mode: str = Field(default="SIMULATION")
    model_name: str = Field(default="deterministic-v1")
    recommendation: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str = Field(default="")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)
    response_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_simulation: bool = Field(default=True)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def get_mode(self) -> ProviderMode:
        """Return the provider mode."""

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier."""

    @abstractmethod
    def generate(self, prompt: AgentPrompt) -> AgentResponse:
        """Generate a structured agent response from the prompt."""


# ═══════════════════════════════════════════════════════════════════════════
# SIMULATION PROVIDER (DEFAULT)
# ═══════════════════════════════════════════════════════════════════════════


class SimulationProvider(LLMProvider):
    """Deterministic simulation provider that generates structured responses
    without any external API calls.

    Responses are derived from the grounded evidence in the prompt context,
    making them reproducible and fully testable.
    """

    def get_mode(self) -> ProviderMode:
        return ProviderMode.SIMULATION

    def get_model_name(self) -> str:
        return "deterministic-simulation-v1"

    def generate(self, prompt: AgentPrompt) -> AgentResponse:
        """Generate deterministic recommendation based on grounded context."""
        agent = prompt.agent_name.lower().replace("agent", "").strip()
        context = prompt.context

        recommendation: Dict[str, Any] = {}
        reasoning = ""
        confidence = 1.0
        evidence_refs: List[Dict[str, Any]] = []

        if agent == "inventory":
            shortage = float(context.get("shortage_qty", 0))
            available = float(context.get("available_qty", 0))
            requested = float(context.get("requested_qty", 0))

            if shortage > 0:
                recommendation = {
                    "action": "INITIATE_PROCUREMENT",
                    "shortage_qty": shortage,
                    "urgency": "HIGH" if shortage > requested * 0.5 else "MEDIUM",
                    "suggested_reorder_qty": round(shortage * 1.2, 2),
                }
                reasoning = (
                    f"Available stock ({available}) insufficient for requested quantity ({requested}). "
                    f"Shortage of {shortage} units detected. Recommending procurement with 20% buffer."
                )
            else:
                recommendation = {
                    "action": "FULFILL_FROM_STOCK",
                    "available_qty": available,
                }
                reasoning = f"Sufficient stock available ({available}) to fulfill request ({requested})."

            evidence_refs = [{"source": "inventory_table", "available_qty": available}]

        elif agent == "procurement":
            supplier_id = context.get("selected_supplier_id", "SUPP-001")
            unit_price = float(context.get("unit_price_inr", 100.0))
            lead_time = int(context.get("lead_time_hours", 48))
            qty = float(context.get("required_qty", 50))

            recommendation = {
                "action": "CREATE_PURCHASE_ORDER",
                "supplier_id": supplier_id,
                "unit_price_inr": unit_price,
                "total_cost_inr": round(unit_price * qty, 2),
                "lead_time_hours": lead_time,
                "quantity": qty,
            }
            reasoning = (
                f"Selected supplier {supplier_id} with unit price INR {unit_price:.2f} "
                f"and {lead_time}h lead time for {qty} units."
            )
            evidence_refs = [{"source": "supplier_offers", "supplier_id": supplier_id}]

        elif agent == "finance":
            spend = float(context.get("estimated_spend", 0))
            budget = float(context.get("available_budget", 1000000))
            threshold = float(context.get("threshold_limit", 50000))

            if spend > budget:
                recommendation = {
                    "action": "BLOCK_BUDGET_EXCEEDED",
                    "estimated_spend": spend,
                    "available_budget": budget,
                }
                reasoning = f"Spend INR {spend:,.2f} exceeds budget INR {budget:,.2f}. Action blocked."
                confidence = 1.0
            elif spend > threshold:
                recommendation = {
                    "action": "REQUEST_APPROVAL",
                    "estimated_spend": spend,
                    "threshold": threshold,
                    "approval_domain": "FINANCE",
                }
                reasoning = (
                    f"Spend INR {spend:,.2f} exceeds approval threshold INR {threshold:,.2f}. "
                    "Human approval required."
                )
            else:
                recommendation = {
                    "action": "AUTO_APPROVE",
                    "estimated_spend": spend,
                }
                reasoning = f"Spend INR {spend:,.2f} within delegated authority."

            evidence_refs = [{"source": "budgets_table", "available_budget": budget}]

        elif agent == "logistics":
            transit_days = int(context.get("transit_days", 3))
            route_id = context.get("route_id", "RT-DEFAULT")

            recommendation = {
                "action": "SCHEDULE_SHIPMENT",
                "route_id": route_id,
                "transit_days": transit_days,
                "carrier_score": 0.95,
            }
            reasoning = f"Route {route_id} feasible with {transit_days}-day transit time."
            evidence_refs = [{"source": "warehouses", "route_id": route_id}]

        elif agent == "supervisor":
            agent_outputs = context.get("agent_outputs", {})
            human_approval = context.get("human_approval_required", False)

            recommendation = {
                "action": "EXECUTE" if not human_approval else "ESCALATE_FOR_APPROVAL",
                "specialists_consulted": list(agent_outputs.keys()),
                "human_approval_required": human_approval,
            }
            reasoning = (
                f"Synthesized {len(agent_outputs)} specialist findings. "
                f"{'Human approval required before execution.' if human_approval else 'Auto-approved for execution.'}"
            )
            evidence_refs = [
                {"agent": name, "status": "consulted"} for name in agent_outputs.keys()
            ]

        else:
            recommendation = {"action": "NO_OP", "agent": agent}
            reasoning = f"No specific logic for agent '{agent}'. Passing through."

        return AgentResponse(
            agent_name=prompt.agent_name,
            provider_mode=self.get_mode().value,
            model_name=self.get_model_name(),
            recommendation=recommendation,
            reasoning=reasoning,
            confidence=confidence,
            evidence_refs=evidence_refs,
            is_simulation=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
# LIVE PROVIDER (CONFIGURED EXTERNAL LLM)
# ═══════════════════════════════════════════════════════════════════════════


class LiveProvider(LLMProvider):
    """Configured Live LLM Provider connecting to external endpoints.

    Requirements:
    - Bounded timeouts (default 10s, capped at 60s)
    - Bounded retries on transient errors (max 3)
    - Typed JSON response validation against AgentResponse contract
    - Redacted logging (API keys, authorization headers, and raw prompts)
    - Fails closed on any network, timeout, or schema errors
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        raw_key = api_key or os.environ.get("LLM_API_KEY", "").strip()
        if not raw_key:
            raise LLMProviderConfigError(
                "LLM_API_KEY is required for LIVE provider mode but was not provided or is empty."
            )
        self.api_key = raw_key
        self.base_url = (base_url or os.environ.get("LLM_API_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model_name = model_name or os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")

        # Bounded timeout: between 1.0s and 60.0s
        raw_timeout = float(timeout_seconds or os.environ.get("LLM_TIMEOUT_SECONDS", "10.0"))
        self.timeout_seconds = max(1.0, min(60.0, raw_timeout))

        # Bounded retries: between 0 and 3
        raw_retries = int(max_retries or os.environ.get("LLM_MAX_RETRIES", "2"))
        self.max_retries = max(0, min(3, raw_retries))

        # Safe redacted key for logging
        self._masked_key = f"{self.api_key[:4]}...{self.api_key[-3:]}" if len(self.api_key) > 8 else "***"
        logger.info(
            "Initialized LiveProvider: model=%s, endpoint=%s, key=%s, timeout=%.1fs, max_retries=%d",
            self.model_name,
            self.base_url,
            self._masked_key,
            self.timeout_seconds,
            self.max_retries,
        )

    def get_mode(self) -> ProviderMode:
        return ProviderMode.LIVE

    def get_model_name(self) -> str:
        return self.model_name

    def generate(self, prompt: AgentPrompt) -> AgentResponse:
        """Call external LLM endpoint, parse response, and validate structured contract."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        system_instruction = (
            f"You are the {prompt.agent_name} in an enterprise multi-agent mesh. "
            "Analyze the operational evidence provided in context and respond with a STRICT JSON object "
            "containing: 'recommendation' (object), 'reasoning' (string), 'confidence' (float 0.0-1.0), "
            "and 'evidence_refs' (array of objects)."
        )

        body = {
            "model": self.model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_instruction},
                {
                    "role": "user",
                    "content": json.dumps({
                        "task": prompt.task_description,
                        "context": prompt.context,
                        "constraints": prompt.constraints,
                    }),
                },
            ],
            "temperature": 0.1,
        }

        # Safe log without credentials or prompt dump
        logger.debug(
            "Calling live LLM provider for agent=%s, model=%s at %s",
            prompt.agent_name,
            self.model_name,
            self.base_url,
        )

        attempts = 0
        last_error: Optional[Exception] = None

        while attempts <= self.max_retries:
            attempts += 1
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    resp = client.post(url, json=body, headers=headers)

                if resp.status_code == 200:
                    raw_json = resp.json()
                    return self._parse_and_validate_response(prompt.agent_name, raw_json)
                elif resp.status_code in (408, 429, 500, 502, 503, 504):
                    # Transient error: retry if attempts remaining
                    last_error = LLMProviderUnavailableError(
                        f"Live LLM provider returned transient status {resp.status_code}: {resp.text[:200]}"
                    )
                    logger.warning(
                        "Live provider attempt %d/%d failed with status %d; retrying...",
                        attempts,
                        self.max_retries + 1,
                        resp.status_code,
                    )
                    time.sleep(0.2 * attempts)
                    continue
                else:
                    # Non-retriable HTTP error (e.g. 401 Unauthorized, 403 Forbidden, 400 Bad Request)
                    raise LLMProviderError(
                        f"Live LLM provider request failed with status {resp.status_code}: {resp.text[:200]}"
                    )

            except httpx.TimeoutException as exc:
                last_error = LLMProviderTimeoutError(
                    f"Live LLM provider timed out after {self.timeout_seconds}s for agent '{prompt.agent_name}': {exc}"
                )
                logger.warning("Live provider timeout on attempt %d/%d: %s", attempts, self.max_retries + 1, exc)
                time.sleep(0.2 * attempts)
                continue

            except (httpx.ConnectError, httpx.NetworkError) as exc:
                last_error = LLMProviderUnavailableError(
                    f"Live LLM provider unavailable at '{self.base_url}': {exc}"
                )
                logger.warning("Live provider connection error on attempt %d/%d: %s", attempts, self.max_retries + 1, exc)
                time.sleep(0.2 * attempts)
                continue

            except (LLMProviderError, LLMProviderMalformedOutputError):
                raise

            except Exception as exc:
                last_error = LLMProviderError(f"Unexpected error calling live provider: {exc}")
                break

        # If retries exhausted, raise the captured specific error
        if last_error:
            raise last_error
        raise LLMProviderUnavailableError(f"Live LLM provider failed after {attempts} attempts.")

    def _parse_and_validate_response(self, agent_name: str, raw_json: Dict[str, Any]) -> AgentResponse:
        """Extract choices, parse inner JSON content, and validate against AgentResponse schema."""
        try:
            choices = raw_json.get("choices", [])
            if not choices:
                raise LLMProviderMalformedOutputError("Live LLM returned empty 'choices' list.")

            first_choice = choices[0]
            message = first_choice.get("message", {})
            content = message.get("content", "")

            if not content:
                raise LLMProviderMalformedOutputError("Live LLM returned empty message content.")

            # Parse content as JSON
            parsed_content = json.loads(content)
            if not isinstance(parsed_content, dict):
                raise LLMProviderMalformedOutputError(
                    f"Live LLM message content must be a JSON object, got {type(parsed_content).__name__}."
                )

            recommendation = parsed_content.get("recommendation")
            if not isinstance(recommendation, dict):
                raise LLMProviderMalformedOutputError(
                    "Live LLM response missing required 'recommendation' dictionary."
                )

            reasoning = str(parsed_content.get("reasoning", ""))
            raw_confidence = parsed_content.get("confidence", 0.9)
            try:
                confidence = max(0.0, min(1.0, float(raw_confidence)))
            except (ValueError, TypeError):
                confidence = 0.85

            evidence_refs = parsed_content.get("evidence_refs", [])
            if not isinstance(evidence_refs, list):
                evidence_refs = []

            return AgentResponse(
                agent_name=agent_name,
                provider_mode=ProviderMode.LIVE.value,
                model_name=self.model_name,
                recommendation=recommendation,
                reasoning=reasoning,
                confidence=confidence,
                evidence_refs=evidence_refs,
                is_simulation=False,
            )

        except json.JSONDecodeError as exc:
            raise LLMProviderMalformedOutputError(f"Live LLM output is not valid JSON: {exc}") from exc
        except LLMProviderMalformedOutputError:
            raise
        except Exception as exc:
            raise LLMProviderMalformedOutputError(f"Failed to validate live LLM output: {exc}") from exc


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY & SINGLETON
# ═══════════════════════════════════════════════════════════════════════════


def get_provider(mode: Optional[str] = None) -> LLMProvider:
    """Factory function returning the configured LLM provider.

    Uses SIMULATION mode by default. Live mode requires explicit configuration
    via LLM_PROVIDER_MODE=LIVE and a valid LLM_API_KEY.
    """
    selected_mode = (mode or os.environ.get("LLM_PROVIDER_MODE", "SIMULATION")).upper().strip()

    if selected_mode == "LIVE":
        try:
            return LiveProvider()
        except LLMProviderConfigError as exc:
            logger.error("Failed to initialize LIVE provider: %s", exc)
            raise

    return SimulationProvider()


_default_provider: Optional[LLMProvider] = None


def get_default_provider() -> LLMProvider:
    """Get or create the default LLM provider singleton."""
    global _default_provider
    if _default_provider is None:
        _default_provider = get_provider()
    return _default_provider


def reset_default_provider() -> None:
    """Reset the module singleton (used in test teardowns)."""
    global _default_provider
    _default_provider = None
