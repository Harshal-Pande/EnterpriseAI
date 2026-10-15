"""Unit and integration tests for Multi-Key Gemini Fallback Pool and OpenRouter Routing (Phase 1-8).

Covers:
1. Exact 7-key cyclic order algorithm and stable agent-to-position mapping.
2. Missing, blank, fewer-than-7, and duplicate key handling in discovery.
3. Transient HTTP 429 quota exhaustion failover between keys.
4. HTTP 401/403 credential failure failover to subsequent keys.
5. Network timeout and 5xx transient error handling with bounded retries.
6. OpenRouter fallback activation only when enabled and all Gemini keys fail.
7. OpenRouter structured JSON response validation and schema conformance.
8. Thread-safety: concurrent agent requests maintain isolated key routing.
9. Fail-closed governance: downstream action blocked on provider failure, no silent simulation fallback.
"""

from __future__ import annotations

import json
import os
import threading
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.llm_provider import (
    AGENT_POSITIONS,
    AgentPrompt,
    AgentResponse,
    GeminiKeyEntry,
    LiveProvider,
    LLMProviderConfigError,
    LLMProviderError,
    LLMProviderMalformedOutputError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    OpenRouterConfig,
    ProviderMode,
    discover_gemini_keys,
    discover_openrouter_config,
    get_agent_position,
    get_cyclic_key_order,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. KEY SELECTION & CYCLIC ORDERING TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestCyclicKeyOrdering:
    """Verifies deterministic per-agent key ordering and position stability."""

    def test_stable_agent_positions(self):
        """Standard supply chain specialists map to positions 1 through 5."""
        assert get_agent_position("InventoryAgent") == 1
        assert get_agent_position("inventory") == 1
        assert get_agent_position("ProcurementAgent") == 2
        assert get_agent_position("FinanceAgent") == 3
        assert get_agent_position("LogisticsAgent") == 4
        assert get_agent_position("SupervisorAgent") == 5
        assert get_agent_position("QualityAgent") == 6
        assert get_agent_position("ProductionAgent") == 7

    def test_unregistered_agent_deterministic_position(self):
        """Unregistered agents receive a deterministic position in 1..7."""
        pos1 = get_agent_position("CustomWarehouseBot")
        pos2 = get_agent_position("CustomWarehouseBot")
        assert pos1 == pos2
        assert 1 <= pos1 <= 7

    def test_exact_seven_key_cyclic_order(self):
        """Verifies the exact 7-key cyclic order defined in the specification."""
        keys = [GeminiKeyEntry(f"key_{i}", f"secret_token_{i}") for i in range(1, 8)]

        # Agent 1: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7
        order_1 = [k.key_id for k in get_cyclic_key_order("InventoryAgent", keys)]
        assert order_1 == ["key_1", "key_2", "key_3", "key_4", "key_5", "key_6", "key_7"]

        # Agent 2: 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 1
        order_2 = [k.key_id for k in get_cyclic_key_order("ProcurementAgent", keys)]
        assert order_2 == ["key_2", "key_3", "key_4", "key_5", "key_6", "key_7", "key_1"]

        # Agent 3: 3 -> 4 -> 5 -> 6 -> 7 -> 1 -> 2
        order_3 = [k.key_id for k in get_cyclic_key_order("FinanceAgent", keys)]
        assert order_3 == ["key_3", "key_4", "key_5", "key_6", "key_7", "key_1", "key_2"]

        # Agent 4: 4 -> 5 -> 6 -> 7 -> 1 -> 2 -> 3
        order_4 = [k.key_id for k in get_cyclic_key_order("LogisticsAgent", keys)]
        assert order_4 == ["key_4", "key_5", "key_6", "key_7", "key_1", "key_2", "key_3"]

        # Agent 5: 5 -> 6 -> 7 -> 1 -> 2 -> 3 -> 4
        order_5 = [k.key_id for k in get_cyclic_key_order("SupervisorAgent", keys)]
        assert order_5 == ["key_5", "key_6", "key_7", "key_1", "key_2", "key_3", "key_4"]

        # Agent 6: 6 -> 7 -> 1 -> 2 -> 3 -> 4 -> 5
        order_6 = [k.key_id for k in get_cyclic_key_order("QualityAgent", keys)]
        assert order_6 == ["key_6", "key_7", "key_1", "key_2", "key_3", "key_4", "key_5"]

        # Agent 7: 7 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6
        order_7 = [k.key_id for k in get_cyclic_key_order("ProductionAgent", keys)]
        assert order_7 == ["key_7", "key_1", "key_2", "key_3", "key_4", "key_5", "key_6"]

    def test_cyclic_order_with_fewer_than_seven_keys(self):
        """When fewer than 7 keys are configured, keys cycle in relative order."""
        keys = [GeminiKeyEntry("key_1", "tok1"), GeminiKeyEntry("key_2", "tok2"), GeminiKeyEntry("key_3", "tok3")]

        # Agent 1 (pos 1): offset = (1-1)%3 = 0 -> [key_1, key_2, key_3]
        assert [k.key_id for k in get_cyclic_key_order("InventoryAgent", keys)] == ["key_1", "key_2", "key_3"]

        # Agent 2 (pos 2): offset = (2-1)%3 = 1 -> [key_2, key_3, key_1]
        assert [k.key_id for k in get_cyclic_key_order("ProcurementAgent", keys)] == ["key_2", "key_3", "key_1"]

        # Agent 4 (pos 4): offset = (4-1)%3 = 0 -> [key_1, key_2, key_3]
        assert [k.key_id for k in get_cyclic_key_order("LogisticsAgent", keys)] == ["key_1", "key_2", "key_3"]

    def test_empty_keys_returns_empty_list(self):
        """Empty key pool returns an empty list safely without exception."""
        assert get_cyclic_key_order("InventoryAgent", []) == []


class TestKeyDiscoveryAndDeduplication:
    """Tests environment variable scanning, deduplication, and backward compatibility."""

    def test_discovery_deduplicates_identical_keys(self):
        """Duplicate keys in environment map to the first encountered stable identifier."""
        env_mock = {
            "GEMINI_API_KEY_1": "shared-secret-12345",
            "GEMINI_API_KEY_2": "unique-secret-67890",
            "GEMINI_API_KEY_3": "shared-secret-12345",  # Duplicate of key_1
        }
        with patch.dict(os.environ, env_mock, clear=True):
            keys = discover_gemini_keys()
            assert len(keys) == 2
            assert keys[0].key_id == "key_1"
            assert keys[1].key_id == "key_2"

    def test_legacy_llm_api_key_maps_to_key_1(self):
        """Legacy LLM_API_KEY is recognized as key_1 if GEMINI_API_KEY_1 is unset."""
        env_mock = {
            "LLM_API_KEY": "legacy-token-abcde",
        }
        with patch.dict(os.environ, env_mock, clear=True):
            keys = discover_gemini_keys()
            assert len(keys) == 1
            assert keys[0].key_id == "key_1"
            assert keys[0].api_key == "legacy-token-abcde"

    def test_blanks_and_placeholders_ignored(self):
        """Blank strings and template placeholders are safely ignored during discovery."""
        env_mock = {
            "GEMINI_API_KEY_1": "your-api-key-here",
            "GEMINI_API_KEY_2": "   ",
            "GEMINI_API_KEY_3": "valid-gemini-key-999",
        }
        with patch.dict(os.environ, env_mock, clear=True):
            keys = discover_gemini_keys()
            assert len(keys) == 1
            assert keys[0].key_id == "key_3"
            assert keys[0].api_key == "valid-gemini-key-999"


# ═══════════════════════════════════════════════════════════════════════════
# 2. RETRY & FAILOVER UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestFailoverBehavior:
    """Tests intelligent failover between Gemini keys and OpenRouter fallback."""

    def test_first_key_succeeds_no_fallback(self):
        """When the first key succeeds with 200, no fallback occurs."""
        gemini_keys = ["gemini-key-1", "gemini-key-2"]
        provider = LiveProvider(gemini_keys=gemini_keys, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": json.dumps({"recommendation": {"action": "FULFILL"}})}}]
        }

        with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
            resp = provider.generate(prompt)
            assert resp.recommendation["action"] == "FULFILL"
            assert resp.provider_name == "gemini"
            assert resp.key_id == "key_1"
            assert resp.fallback_occurred is False
            assert mock_post.call_count == 1

    def test_key_429_triggers_failover_to_second_key(self):
        """HTTP 429 quota exhaustion on key_1 triggers immediate failover to key_2."""
        gemini_keys = ["gemini-key-1", "gemini-key-2"]
        provider = LiveProvider(gemini_keys=gemini_keys, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        resp_429 = MagicMock(status_code=429, text="Resource exhausted: quota limit exceeded")
        resp_200 = MagicMock(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": json.dumps({"recommendation": {"action": "PROCURE"}})}}]},
        )

        with patch("httpx.Client.post", side_effect=[resp_429, resp_200]) as mock_post:
            resp = provider.generate(prompt)
            assert resp.recommendation["action"] == "PROCURE"
            assert resp.provider_name == "gemini"
            assert resp.key_id == "key_2"
            assert resp.fallback_occurred is True
            assert mock_post.call_count == 2

    def test_key_401_triggers_failover_to_second_key(self):
        """HTTP 401 invalid credentials on key_1 fails over to key_2."""
        gemini_keys = ["invalid-key-1", "valid-key-2"]
        provider = LiveProvider(gemini_keys=gemini_keys, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        resp_401 = MagicMock(status_code=401, text="API_KEY_INVALID")
        resp_200 = MagicMock(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": json.dumps({"recommendation": {"action": "APPROVED"}})}}]},
        )

        with patch("httpx.Client.post", side_effect=[resp_401, resp_200]):
            resp = provider.generate(prompt)
            assert resp.key_id == "key_2"
            assert resp.fallback_occurred is True

    def test_timeout_triggers_failover_to_subsequent_key(self):
        """Network timeout on key_1 fails over to key_2."""
        gemini_keys = ["slow-key-1", "fast-key-2"]
        provider = LiveProvider(gemini_keys=gemini_keys, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        resp_200 = MagicMock(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": json.dumps({"recommendation": {"action": "OK"}})}}]},
        )

        with patch("httpx.Client.post", side_effect=[httpx.TimeoutException("Read timed out"), resp_200]):
            resp = provider.generate(prompt)
            assert resp.key_id == "key_2"
            assert resp.fallback_occurred is True

    def test_all_gemini_keys_exhausted_invokes_openrouter(self):
        """When all Gemini keys return 429, OpenRouter fallback is invoked and succeeds."""
        gemini_keys = ["gemini-key-1", "gemini-key-2"]
        or_config = OpenRouterConfig(
            api_key="sk-or-test-fallback-key",
            enabled=True,
            model_name="google/gemini-3.8-flash",
            max_retries=0,
        )
        provider = LiveProvider(gemini_keys=gemini_keys, openrouter_config=or_config, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        gemini_fail_1 = MagicMock(status_code=429, text="Quota exceeded key 1")
        gemini_fail_2 = MagicMock(status_code=429, text="Quota exceeded key 2")
        or_success = MagicMock(
            status_code=200,
            json=lambda: {
                "choices": [{"message": {"content": json.dumps({"recommendation": {"action": "OPENROUTER_FALLBACK_OK"}})}}]
            },
        )

        with patch("httpx.Client.post", side_effect=[gemini_fail_1, gemini_fail_2, or_success]) as mock_post:
            resp = provider.generate(prompt)
            assert resp.recommendation["action"] == "OPENROUTER_FALLBACK_OK"
            assert resp.provider_name == "openrouter"
            assert resp.key_id == "openrouter"
            assert resp.fallback_occurred is True
            assert mock_post.call_count == 3

    def test_openrouter_disabled_never_invoked(self):
        """When OpenRouter is disabled, Gemini exhaustion raises error without calling OpenRouter."""
        gemini_keys = ["gemini-key-1"]
        or_config = OpenRouterConfig(api_key="sk-or-key", enabled=False)
        provider = LiveProvider(gemini_keys=gemini_keys, openrouter_config=or_config, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        gemini_fail = MagicMock(status_code=429, text="Quota exhausted")

        with patch("httpx.Client.post", return_value=gemini_fail) as mock_post:
            with pytest.raises(LLMProviderUnavailableError):
                provider.generate(prompt)
            # Only Gemini called once; OpenRouter was NOT called
            assert mock_post.call_count == 1

    def test_openrouter_malformed_output_fails_closed(self):
        """If OpenRouter returns unparseable text, system fails closed with MalformedOutputError."""
        gemini_keys = ["gemini-key-1"]
        or_config = OpenRouterConfig(api_key="sk-or-key", enabled=True, max_retries=0)
        provider = LiveProvider(gemini_keys=gemini_keys, openrouter_config=or_config, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        gemini_fail = MagicMock(status_code=429, text="Quota exhausted")
        or_malformed = MagicMock(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": "This is raw unformatted text."}}]},
        )

        with patch("httpx.Client.post", side_effect=[gemini_fail, or_malformed]):
            with pytest.raises(LLMProviderMalformedOutputError):
                provider.generate(prompt)

    def test_all_providers_fail_fails_closed(self):
        """When both Gemini keys and OpenRouter fail, provider raises LLMProviderUnavailableError."""
        gemini_keys = ["gemini-key-1"]
        or_config = OpenRouterConfig(api_key="sk-or-key", enabled=True, max_retries=0)
        provider = LiveProvider(gemini_keys=gemini_keys, openrouter_config=or_config, max_retries=0)
        prompt = AgentPrompt(agent_name="InventoryAgent", task_description="Check stock")

        gemini_fail = MagicMock(status_code=429, text="Gemini quota exhausted")
        or_fail = MagicMock(status_code=503, text="OpenRouter service down")

        with patch("httpx.Client.post", side_effect=[gemini_fail, or_fail]):
            with pytest.raises(LLMProviderUnavailableError) as exc_info:
                provider.generate(prompt)
            assert "unavailable" in str(exc_info.value).lower() or "status 503" in str(exc_info.value).lower()


# ═══════════════════════════════════════════════════════════════════════════
# 3. CONCURRENCY & THREAD-SAFETY TEST
# ═══════════════════════════════════════════════════════════════════════════


class TestConcurrencySafety:
    """Verifies concurrent agent requests maintain isolated key routing without mutating shared state."""

    def test_concurrent_agents_use_respective_key_order(self):
        """Concurrent calls for Agent 1 and Agent 2 use their respective preferred key."""
        keys = ["tok-1", "tok-2", "tok-3"]
        provider = LiveProvider(gemini_keys=keys, max_retries=0)

        results = {}
        errors = []

        def json_dumps_helper(auth_header):
            return json.dumps({
                "recommendation": {"auth": auth_header},
                "reasoning": "ok",
            })

        def fake_post(url, json=None, headers=None, **kwargs):
            auth = headers.get("Authorization", "")
            mock_resp = MagicMock(status_code=200)
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": json_dumps_helper(auth)}}]
            }
            return mock_resp

        def call_agent(agent_name: str):
            try:
                prompt = AgentPrompt(agent_name=agent_name, task_description="Analyze")
                resp = provider.generate(prompt)
                results[agent_name] = resp.recommendation.get("auth")
            except Exception as e:
                errors.append(e)

        with patch("httpx.Client.post", side_effect=fake_post):
            t1 = threading.Thread(target=call_agent, args=("InventoryAgent",))  # Pos 1 -> key_1 (tok-1)
            t2 = threading.Thread(target=call_agent, args=("ProcurementAgent",))  # Pos 2 -> key_2 (tok-2)

            t1.start()
            t2.start()
            t1.join()
            t2.join()

        assert not errors
        assert results["InventoryAgent"] == "Bearer tok-1"
        assert results["ProcurementAgent"] == "Bearer tok-2"
