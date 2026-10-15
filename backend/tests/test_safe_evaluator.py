"""Unit tests for the SafeExpressionEvaluator (Task P6.1).

Verifies safe AST evaluation of business rules and ensures strict rejection of
hostile code injection, dunder access, builtins, and resource exhaustion attacks.
"""

import pytest
from app.core.safe_evaluator import (
    SafeEvaluationError,
    SafeExpressionEvaluator,
    evaluate_condition_safely,
)


class TestSafeExpressionEvaluator:
    """Test suite for safe rule condition evaluation."""

    def test_valid_numeric_comparisons(self):
        ctx = {"available_qty": 150.0, "requested_qty": 100.0}
        assert evaluate_condition_safely("available_qty >= requested_qty", ctx) is True

        ctx = {"available_qty": 50.0, "requested_qty": 100.0}
        assert evaluate_condition_safely("available_qty >= requested_qty", ctx) is False

    def test_arithmetic_in_conditions(self):
        ctx = {"usage": 110.0, "rolling_baseline": 100.0}
        # 110 <= 100 * 1.15 -> 110 <= 115 -> True
        assert evaluate_condition_safely("usage <= rolling_baseline * 1.15", ctx) is True

        ctx = {"usage": 120.0, "rolling_baseline": 100.0}
        assert evaluate_condition_safely("usage <= rolling_baseline * 1.15", ctx) is False

    def test_boolean_and_or_not_operators(self):
        ctx = {"a": True, "b": False, "c": True}
        assert evaluate_condition_safely("a and not b", ctx) is True
        assert evaluate_condition_safely("a and b", ctx) is False
        assert evaluate_condition_safely("b or c", ctx) is True
        assert evaluate_condition_safely("a AND NOT b", ctx) is True  # Normalized case

    def test_attribute_access_on_dictionaries(self):
        ctx = {
            "supplier": {"status": "ACTIVE", "tier": "STRATEGIC"},
            "offer": {"status": "ACTIVE", "unit_price": 450.0},
        }
        assert evaluate_condition_safely("supplier.status == 'ACTIVE' and offer.status == 'ACTIVE'", ctx) is True
        assert evaluate_condition_safely("supplier.tier == 'PREFERRED'", ctx) is False

    def test_safe_functions_allowlist(self):
        ctx = {"price_a": 500, "price_b": 420, "budget": 450}
        assert evaluate_condition_safely("min(price_a, price_b) <= budget", ctx) is True
        assert evaluate_condition_safely("max(price_a, price_b) <= budget", ctx) is False
        assert evaluate_condition_safely("round(420.456, 1) == 420.5", {}) is True

    # --- Negative & Hostile Expression Tests ---

    def test_reject_arbitrary_function_invocation(self):
        with pytest.raises(SafeEvaluationError, match="not in the safe functions allowlist"):
            evaluate_condition_safely("open('/etc/passwd')", {})

    def test_reject_import_attempt(self):
        with pytest.raises(SafeEvaluationError):
            evaluate_condition_safely("__import__('os').system('ls')", {})

    def test_reject_dunder_attribute_traversal(self):
        with pytest.raises(SafeEvaluationError, match="strictly forbidden"):
            evaluate_condition_safely("x.__class__.__bases__", {"x": "test"})

    def test_reject_power_operator(self):
        with pytest.raises(SafeEvaluationError, match="prohibited"):
            evaluate_condition_safely("9 ** 9 ** 9", {})

    def test_reject_string_repetition_bomb(self):
        with pytest.raises(SafeEvaluationError, match="String repetition"):
            evaluate_condition_safely("'A' * 1000000", {})

    def test_reject_lambda_or_comprehension(self):
        with pytest.raises(SafeEvaluationError, match="Unsupported or unsafe syntax construct"):
            evaluate_condition_safely("[x for x in [1, 2, 3]]", {})

    def test_reject_empty_or_whitespace_expression(self):
        with pytest.raises(SafeEvaluationError, match="Empty condition expression"):
            evaluate_condition_safely("   ", {})

    def test_reject_oversized_expression(self):
        long_expr = "1 + " * 300 + "1"
        with pytest.raises(SafeEvaluationError, match="exceeds maximum"):
            evaluate_condition_safely(long_expr, {})
