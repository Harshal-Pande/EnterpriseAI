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
from typing import Any, Dict, List, Optional, Tuple

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
    provider_name: Optional[str] = Field(default=None, description="Active provider: gemini, openrouter, or simulation")
    key_id: Optional[str] = Field(default=None, description="Safe key identifier, e.g. key_1, key_2, openrouter")
    fallback_occurred: bool = Field(default=False, description="True if key or provider failover occurred")


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
            provider_name="simulation",
            key_id="sim_local",
            fallback_occurred=False,
        )


# ═══════════════════════════════════════════════════════════════════════════
# GEMINI KEY POOL & AGENT CYCLIC ROUTING
# ═══════════════════════════════════════════════════════════════════════════


class GeminiKeyEntry:
    """Safe wrapper around a Gemini API key with stable identifier and redacted repr."""

    def __init__(self, key_id: str, api_key: str):
        self.key_id = key_id  # e.g. "key_1", "key_2"
        self.api_key = api_key.strip()
        self._masked_key = (
            f"{self.api_key[:4]}...{self.api_key[-3:]}"
            if len(self.api_key) > 8
            else "***"
        )

    def __repr__(self) -> str:
        return f"<GeminiKeyEntry id={self.key_id} key={self._masked_key}>"

    def __str__(self) -> str:
        return self.__repr__()

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, GeminiKeyEntry):
            return self.api_key == other.api_key
        return False

    def __hash__(self) -> int:
        return hash(self.api_key)


class OpenRouterConfig(BaseModel):
    """Configuration for OpenRouter fallback routing."""

    api_key: Optional[str] = Field(default=None, description="OpenRouter API key")
    base_url: str = Field(default="https://openrouter.ai/api/v1", description="OpenRouter API base URL")
    model_name: str = Field(default="google/gemini-3.8-flash", description="Model identifier on OpenRouter")
    enabled: bool = Field(default=False, description="Whether OpenRouter fallback is active")
    max_tokens: int = Field(default=1024, description="Max tokens bound to avoid credit reservation 402 errors")
    timeout_seconds: float = Field(default=15.0, description="HTTP timeout for OpenRouter calls")
    max_retries: int = Field(default=2, description="Max transient retries for OpenRouter")


AGENT_POSITIONS: Dict[str, int] = {
    "inventoryagent": 1,
    "inventory": 1,
    "procurementagent": 2,
    "procurement": 2,
    "financeagent": 3,
    "finance": 3,
    "logisticsagent": 4,
    "logistics": 4,
    "supervisoragent": 5,
    "supervisor": 5,
    "qualityagent": 6,
    "quality": 6,
    "productionagent": 7,
    "production": 7,
}


def get_agent_position(agent_name: str) -> int:
    """Return deterministic 1-based position for an agent name."""
    norm = agent_name.lower().strip()
    if norm in AGENT_POSITIONS:
        return AGENT_POSITIONS[norm]
    # Stable deterministic hash mapping into 1..7 for any additional/unregistered agent
    return (abs(hash(norm)) % 7) + 1


def get_cyclic_key_order(agent_name: str, keys: List[GeminiKeyEntry]) -> List[GeminiKeyEntry]:
    """Return keys ordered according to the agent's deterministic cyclic priority.

    Ordering formula:
        offset = (position - 1) % len(keys)
        order = keys[offset:] + keys[:offset]
    """
    if not keys:
        return []
    pos = get_agent_position(agent_name)
    offset = (pos - 1) % len(keys)
    return keys[offset:] + keys[:offset]


def discover_gemini_keys() -> List[GeminiKeyEntry]:
    """Discover and deduplicate configured Gemini API keys from environment."""
    raw_keys: List[Tuple[str, str]] = []

    # 1. Check GEMINI_API_KEY_1 through GEMINI_API_KEY_7
    for i in range(1, 8):
        k = os.environ.get(f"GEMINI_API_KEY_{i}", "").strip()
        if k and not k.startswith("your-") and not k.startswith("placeholder"):
            raw_keys.append((f"key_{i}", k))

    # 2. Check legacy / generic LLM_API_KEY if key_1 not already assigned
    legacy_key = os.environ.get("LLM_API_KEY", "").strip()
    if legacy_key and not any(rk[1] == legacy_key for rk in raw_keys):
        if not any(rk[0] == "key_1" for rk in raw_keys):
            raw_keys.insert(0, ("key_1", legacy_key))
        else:
            raw_keys.append((f"key_{len(raw_keys) + 1}", legacy_key))

    # 3. Check agent-specific variables if any
    agent_env_vars = [
        ("INVENTORY_GEMINI_API_KEY", "inventory"),
        ("PROCUREMENT_GEMINI_API_KEY", "procurement"),
        ("FINANCE_GEMINI_API_KEY", "finance"),
        ("LOGISTICS_GEMINI_API_KEY", "logistics"),
        ("SUPERVISOR_GEMINI_API_KEY", "supervisor"),
    ]
    for env_var, _ in agent_env_vars:
        val = os.environ.get(env_var, "").strip()
        if val and not any(rk[1] == val for rk in raw_keys):
            raw_keys.append((f"key_{len(raw_keys) + 1}", val))

    # Deduplicate while preserving first encountered identifier
    seen_keys: set = set()
    entries: List[GeminiKeyEntry] = []
    for key_id, k_val in raw_keys:
        if k_val not in seen_keys:
            seen_keys.add(k_val)
            entries.append(GeminiKeyEntry(key_id=key_id, api_key=k_val))

    return entries


def discover_openrouter_config() -> OpenRouterConfig:
    """Discover OpenRouter settings from environment."""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip() or None
    enabled_str = os.environ.get("OPENROUTER_ENABLED", "").lower().strip()
    enabled = enabled_str in ("true", "1", "yes")
    # If key is provided and OPENROUTER_ENABLED is not explicitly false, auto-enable
    if key and enabled_str == "":
        enabled = True

    base_url = os.environ.get("OPENROUTER_API_BASE_URL", "https://openrouter.ai/api/v1").strip().rstrip("/")
    model_name = os.environ.get("OPENROUTER_MODEL", "google/gemini-3.8-flash").strip()
    try:
        max_tokens = int(os.environ.get("OPENROUTER_MAX_TOKENS", "1024"))
    except ValueError:
        max_tokens = 1024

    try:
        timeout = float(os.environ.get("OPENROUTER_TIMEOUT_SECONDS", "15.0"))
    except ValueError:
        timeout = 15.0

    try:
        retries = int(os.environ.get("OPENROUTER_MAX_RETRIES", "2"))
    except ValueError:
        retries = 2

    return OpenRouterConfig(
        api_key=key,
        base_url=base_url,
        model_name=model_name,
        enabled=enabled and (key is not None),
        max_tokens=max_tokens,
        timeout_seconds=timeout,
        max_retries=retries,
    )


# ═══════════════════════════════════════════════════════════════════════════
# LIVE PROVIDER (MULTI-KEY GEMINI POOL + OPENROUTER FALLBACK)
# ═══════════════════════════════════════════════════════════════════════════


class LiveProvider(LLMProvider):
    """Configured Live LLM Provider connecting to external endpoints with multi-key routing.

    Requirements:
    - 7-key Gemini fallback pool with deterministic cyclic ordering per agent
    - Automatic bounded retry and key failover on 429, 5xx, timeouts, network issues
    - Optional OpenRouter fallback when all Gemini keys are exhausted
    - Bounded timeouts (default 10s, capped at 60s)
    - Typed JSON response validation against AgentResponse contract
    - Redacted logging (API keys and authorization headers are never logged)
    - Fails closed on any permanent failure without fabricating success
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        gemini_keys: Optional[List[str]] = None,
        openrouter_config: Optional[OpenRouterConfig] = None,
    ):
        self.base_url = (
            base_url or os.environ.get("LLM_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
        ).rstrip("/")
        self.model_name = model_name or os.environ.get("LLM_MODEL_NAME", "gemini-3.8-flash")

        # Bounded timeout: between 1.0s and 60.0s
        raw_timeout = float(
            timeout_seconds if timeout_seconds is not None else os.environ.get("LLM_TIMEOUT_SECONDS", "10.0")
        )
        self.timeout_seconds = max(1.0, min(60.0, raw_timeout))

        # Bounded retries: between 0 and 3
        raw_retries = int(
            max_retries if max_retries is not None else os.environ.get("LLM_MAX_RETRIES", "2")
        )
        self.max_retries = max(0, min(3, raw_retries))

        # Gemini key pool setup
        self.gemini_keys: List[GeminiKeyEntry] = []
        if api_key is not None:
            raw_key = api_key.strip()
            if not raw_key:
                raise LLMProviderConfigError(
                    "LLM_API_KEY is required for LIVE provider mode but was not provided or is empty."
                )
            self.gemini_keys = [GeminiKeyEntry("key_1", raw_key)]
        elif gemini_keys is not None:
            self.gemini_keys = [
                GeminiKeyEntry(f"key_{i+1}", k)
                for i, k in enumerate(gemini_keys)
                if k and k.strip()
            ]
        else:
            self.gemini_keys = discover_gemini_keys()

        # OpenRouter fallback setup
        self.openrouter_config = openrouter_config or discover_openrouter_config()

        # Validate that at least one provider credential exists
        if not self.gemini_keys and not (self.openrouter_config.enabled and self.openrouter_config.api_key):
            raise LLMProviderConfigError(
                "LLM_API_KEY is required for LIVE provider mode but was not provided or is empty."
            )

        # Backward compatibility properties for tests
        if self.gemini_keys:
            self.api_key = self.gemini_keys[0].api_key
            self._masked_key = self.gemini_keys[0]._masked_key
        elif self.openrouter_config.api_key:
            self.api_key = self.openrouter_config.api_key
            self._masked_key = (
                f"{self.api_key[:4]}...{self.api_key[-3:]}" if len(self.api_key) > 8 else "***"
            )
        else:
            self.api_key = ""
            self._masked_key = "***"

        logger.info(
            "Initialized LiveProvider: model=%s, endpoint=%s, gemini_keys_count=%d, openrouter_enabled=%s",
            self.model_name,
            self.base_url,
            len(self.gemini_keys),
            self.openrouter_config.enabled,
        )

    def get_mode(self) -> ProviderMode:
        return ProviderMode.LIVE

    def get_model_name(self) -> str:
        return self.model_name

    def generate(self, prompt: AgentPrompt) -> AgentResponse:
        """Call external LLM endpoint with cyclic Gemini key order and OpenRouter fallback."""
        agent_name = prompt.agent_name
        system_instruction = (
            f"You are the {agent_name} in an enterprise multi-agent mesh. "
            "Analyze the operational evidence provided in context and respond with a STRICT JSON object "
            "containing: 'recommendation' (object), 'reasoning' (string), 'confidence' (float 0.0-1.0), "
            "and 'evidence_refs' (array of objects)."
        )
        user_content = json.dumps({
            "task": prompt.task_description,
            "context": prompt.context,
            "constraints": prompt.constraints,
        })
        body = {
            "model": self.model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
        }

        ordered_gemini_keys = get_cyclic_key_order(agent_name, self.gemini_keys)
        last_error: Optional[Exception] = None
        fallback_occurred = False

        # ── 1. ATTEMPT GEMINI KEYS IN AGENT'S CYCLIC ORDER ─────────────────
        for idx, key_entry in enumerate(ordered_gemini_keys):
            if idx > 0:
                fallback_occurred = True

            headers = {
                "Authorization": f"Bearer {key_entry.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            url = f"{self.base_url}/chat/completions"

            # Per-key attempts: bounded by self.max_retries
            # For 429, 401, 403: fail over immediately to next key without spinning in retries
            attempts = 0
            while attempts <= self.max_retries:
                attempts += 1
                try:
                    with httpx.Client(timeout=self.timeout_seconds) as client:
                        resp = client.post(url, json=body, headers=headers)

                    if resp.status_code == 200:
                        return self._parse_and_validate_response(
                            agent_name=agent_name,
                            raw_json=resp.json(),
                            provider_name="gemini",
                            model_name=self.model_name,
                            key_id=key_entry.key_id,
                            fallback_occurred=fallback_occurred,
                        )

                    elif resp.status_code in (401, 403) or (
                        resp.status_code == 400
                        and any(
                            phrase in resp.text.lower()
                            for phrase in ("valid api key", "api_key_invalid", "api key not valid")
                        )
                    ):
                        logger.warning(
                            "Gemini key '%s' rejected with status %d (credential error: %s). Failing over to next key in cycle...",
                            key_entry.key_id,
                            resp.status_code,
                            resp.text[:100].strip(),
                        )
                        last_error = LLMProviderUnavailableError(
                            f"Gemini key '{key_entry.key_id}' rejected with status {resp.status_code}"
                        )
                        break  # Stop retrying this key; failover to next key

                    elif resp.status_code in (429,):
                        logger.warning(
                            "Gemini key '%s' rate limited/quota exhausted (status 429). Failing over to next key in cycle...",
                            key_entry.key_id,
                        )
                        last_error = LLMProviderUnavailableError(
                            f"Gemini key '{key_entry.key_id}' quota exceeded (429)"
                        )
                        break  # Stop retrying this key; failover to next key

                    elif resp.status_code in (408, 500, 502, 503, 504):
                        last_error = LLMProviderUnavailableError(
                            f"Gemini provider returned transient status {resp.status_code} for key '{key_entry.key_id}'"
                        )
                        if attempts <= self.max_retries:
                            time.sleep(0.2 * attempts)
                            continue
                        break

                    else:
                        # Non-recoverable client error (e.g. 400 Bad Request, invalid model identifier)
                        raise LLMProviderError(
                            f"Live LLM provider request failed with status {resp.status_code}: {resp.text[:200]}"
                        )

                except httpx.TimeoutException as exc:
                    last_error = LLMProviderTimeoutError(
                        f"Live LLM provider timed out after {self.timeout_seconds}s for agent '{agent_name}': {exc}"
                    )
                    if attempts <= self.max_retries:
                        time.sleep(0.2 * attempts)
                        continue
                    break

                except (httpx.ConnectError, httpx.NetworkError) as exc:
                    last_error = LLMProviderUnavailableError(
                        f"Live LLM provider unavailable at '{self.base_url}': {exc}"
                    )
                    if attempts <= self.max_retries:
                        time.sleep(0.2 * attempts)
                        continue
                    break

                except (LLMProviderError, LLMProviderMalformedOutputError):
                    raise

                except Exception as exc:
                    last_error = LLMProviderError(f"Unexpected error calling live provider: {exc}")
                    break

        # ── 2. ATTEMPT OPENROUTER FALLBACK IF CONFIGURED & ENABLED ──────────
        if self.openrouter_config.enabled and self.openrouter_config.api_key:
            fallback_occurred = True
            logger.info(
                "All Gemini keys exhausted or failed for agent '%s'. Attempting OpenRouter fallback with model '%s'...",
                agent_name,
                self.openrouter_config.model_name,
            )
            or_url = f"{self.openrouter_config.base_url}/chat/completions"
            or_headers = {
                "Authorization": f"Bearer {self.openrouter_config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://enterpriseai.internal",
                "X-Title": "Enterprise AI Supply Chain Control Room",
            }
            or_body = {
                "model": self.openrouter_config.model_name,
                "response_format": {"type": "json_object"},
                "max_tokens": self.openrouter_config.max_tokens,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.1,
            }

            or_attempts = 0
            while or_attempts <= self.openrouter_config.max_retries:
                or_attempts += 1
                try:
                    with httpx.Client(timeout=self.openrouter_config.timeout_seconds) as client:
                        or_resp = client.post(or_url, json=or_body, headers=or_headers)

                    if or_resp.status_code == 200:
                        logger.info("OpenRouter fallback succeeded for agent '%s'", agent_name)
                        return self._parse_and_validate_response(
                            agent_name=agent_name,
                            raw_json=or_resp.json(),
                            provider_name="openrouter",
                            model_name=self.openrouter_config.model_name,
                            key_id="openrouter",
                            fallback_occurred=True,
                        )
                    else:
                        logger.warning(
                            "OpenRouter attempt %d returned status %d: %s",
                            or_attempts,
                            or_resp.status_code,
                            or_resp.text[:200],
                        )
                        last_error = LLMProviderUnavailableError(
                            f"OpenRouter returned status {or_resp.status_code}"
                        )
                        if or_attempts <= self.openrouter_config.max_retries and or_resp.status_code in (408, 429, 500, 502, 503, 504):
                            time.sleep(0.3 * or_attempts)
                            continue
                        break

                except httpx.TimeoutException as exc:
                    last_error = LLMProviderTimeoutError(f"OpenRouter timed out: {exc}")
                    if or_attempts <= self.openrouter_config.max_retries:
                        time.sleep(0.3 * or_attempts)
                        continue
                    break

                except (httpx.ConnectError, httpx.NetworkError) as exc:
                    last_error = LLMProviderUnavailableError(f"OpenRouter unavailable (connection error): {exc}")
                    if or_attempts <= self.openrouter_config.max_retries:
                        time.sleep(0.3 * or_attempts)
                        continue
                    break

                except (LLMProviderError, LLMProviderMalformedOutputError):
                    raise

                except Exception as exc:
                    last_error = LLMProviderError(f"OpenRouter unexpected error: {exc}")
                    break

        # ── 3. FAIL CLOSED IF ALL OPTIONS EXHAUSTED ─────────────────────────
        if last_error:
            raise last_error
        raise LLMProviderUnavailableError(
            f"All LLM provider options exhausted for agent '{agent_name}'."
        )

    def _parse_and_validate_response(
        self,
        agent_name: str,
        raw_json: Dict[str, Any],
        provider_name: str = "gemini",
        model_name: Optional[str] = None,
        key_id: Optional[str] = None,
        fallback_occurred: bool = False,
    ) -> AgentResponse:
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
                model_name=model_name or self.model_name,
                recommendation=recommendation,
                reasoning=reasoning,
                confidence=confidence,
                evidence_refs=evidence_refs,
                is_simulation=False,
                provider_name=provider_name,
                key_id=key_id,
                fallback_occurred=fallback_occurred,
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
    via LLM_PROVIDER_MODE=LIVE and valid credentials.
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

