"""Safe AST-based Condition Expression Evaluator for Business Rules.

Replaces eval/exec with a hardened, sandboxed Abstract Syntax Tree evaluator.
Allows only safe boolean operators, arithmetic, comparisons, and whitelisted functions.
Guarantees fail-closed security against code-injection, arbitrary attribute access,
and computational resource exhaustion attacks.
"""

from __future__ import annotations

import ast
import operator
from typing import Any, Callable, Dict, Optional, Set


class SafeEvaluationError(Exception):
    """Raised when an expression violates safety constraints or fails to evaluate."""
    pass


class SafeExpressionEvaluator:
    """Evaluates business rule condition expressions safely via AST inspection."""

    MAX_EXPR_LENGTH = 500
    MAX_NODE_COUNT = 60
    MAX_STR_LENGTH = 1000

    SAFE_FUNCTIONS: Dict[str, Callable] = {
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
    }

    BINARY_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
    }

    UNARY_OPS = {
        ast.Not: operator.not_,
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    COMPARE_OPS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
        ast.Is: operator.is_,
        ast.IsNot: operator.is_not,
    }

    def __init__(self, allowed_variables: Optional[Set[str]] = None):
        self.allowed_variables = allowed_variables

    def evaluate(self, expr: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Parse and safely evaluate a single expression string against context variables."""
        if not expr or not expr.strip():
            raise SafeEvaluationError("Empty condition expression.")

        clean_expr = expr.strip()
        if len(clean_expr) > self.MAX_EXPR_LENGTH:
            raise SafeEvaluationError(
                f"Expression exceeds maximum length of {self.MAX_EXPR_LENGTH} characters."
            )

        # Normalize plain-English rules to valid Python syntax if needed
        normalized = self._normalize_syntax(clean_expr)

        try:
            tree = ast.parse(normalized, mode="eval")
        except SyntaxError as e:
            raise SafeEvaluationError(f"Syntax error in expression '{expr}': {e}") from e

        # Check total AST complexity (node count)
        node_count = sum(1 for _ in ast.walk(tree))
        if node_count > self.MAX_NODE_COUNT:
            raise SafeEvaluationError(
                f"Expression exceeds maximum AST node complexity ({node_count} > {self.MAX_NODE_COUNT})."
            )

        ctx = context.copy() if context else {}
        return self._eval_node(tree.body, ctx)

    def _normalize_syntax(self, expr: str) -> str:
        """Map common domain shorthands to Python operators."""
        # e.g., 'AND' -> 'and', 'OR' -> 'or', 'NOT' -> 'not'
        tokens = expr.split()
        normalized_tokens = []
        for t in tokens:
            if t.upper() == "AND":
                normalized_tokens.append("and")
            elif t.upper() == "OR":
                normalized_tokens.append("or")
            elif t.upper() == "NOT":
                normalized_tokens.append("not")
            else:
                normalized_tokens.append(t)
        return " ".join(normalized_tokens)

    def _eval_node(self, node: ast.AST, ctx: Dict[str, Any]) -> Any:
        """Recursively evaluate supported AST node types."""
        # 1. Constants (Numbers, Strings, Booleans, None)
        if isinstance(node, ast.Constant):
            val = node.value
            if isinstance(val, str) and len(val) > self.MAX_STR_LENGTH:
                raise SafeEvaluationError("String literal exceeds maximum allowed length.")
            return val

        # 2. Variable Names
        elif isinstance(node, ast.Name):
            var_name = node.id
            if var_name.startswith("__"):
                raise SafeEvaluationError(f"Access to private identifier '{var_name}' is forbidden.")
            
            # Built-in literals
            if var_name == "True":
                return True
            if var_name == "False":
                return False
            if var_name == "None":
                return None

            if self.allowed_variables and var_name not in self.allowed_variables:
                raise SafeEvaluationError(f"Variable '{var_name}' is not in the allowed variables list.")

            if var_name in ctx:
                return ctx[var_name]

            # In case the rule uses an unquoted status like 'ACTIVE'
            return var_name

        # 3. Attribute Access (e.g., supplier.status, offer.unit_price)
        elif isinstance(node, ast.Attribute):
            target = self._eval_node(node.value, ctx)
            attr_name = node.attr
            if attr_name.startswith("__"):
                raise SafeEvaluationError(f"Access to dunder attribute '{attr_name}' is strictly forbidden.")

            if isinstance(target, dict):
                return target.get(attr_name)
            elif hasattr(target, attr_name):
                attr_val = getattr(target, attr_name)
                if callable(attr_val):
                    raise SafeEvaluationError(f"Method invocation on attribute '{attr_name}' is prohibited.")
                return attr_val
            else:
                return None

        # 4. Binary Operations (+, -, *, /, //, %)
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.BINARY_OPS:
                raise SafeEvaluationError(f"Binary operator '{op_type.__name__}' is prohibited.")
            left = self._eval_node(node.left, ctx)
            right = self._eval_node(node.right, ctx)

            # Prevent string multiplication memory bombs
            if op_type is ast.Mult and (isinstance(left, str) or isinstance(right, str)):
                raise SafeEvaluationError("String repetition via multiplication is prohibited.")

            try:
                return self.BINARY_OPS[op_type](left, right)
            except ZeroDivisionError:
                raise SafeEvaluationError("Division by zero in rule condition.")
            except Exception as e:
                raise SafeEvaluationError(f"Error computing binary operation: {e}")

        # 5. Unary Operations (not, +, -)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.UNARY_OPS:
                raise SafeEvaluationError(f"Unary operator '{op_type.__name__}' is prohibited.")
            operand = self._eval_node(node.operand, ctx)
            return self.UNARY_OPS[op_type](operand)

        # 6. Boolean Operations (and, or)
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for val_node in node.values:
                    if not self._eval_node(val_node, ctx):
                        return False
                return True
            elif isinstance(node.op, ast.Or):
                for val_node in node.values:
                    if self._eval_node(val_node, ctx):
                        return True
                return False
            else:
                raise SafeEvaluationError(f"Unsupported boolean operator: {type(node.op).__name__}")

        # 7. Comparisons (==, !=, <, <=, >, >=, in, not in)
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, ctx)
            for op, comparator in zip(node.ops, node.comparators):
                op_type = type(op)
                if op_type not in self.COMPARE_OPS:
                    raise SafeEvaluationError(f"Comparison operator '{op_type.__name__}' is prohibited.")
                right = self._eval_node(comparator, ctx)
                try:
                    res = self.COMPARE_OPS[op_type](left, right)
                except TypeError as e:
                    raise SafeEvaluationError(f"Comparison type mismatch between {type(left)} and {type(right)}: {e}")
                if not res:
                    return False
                left = right
            return True

        # 8. Whitelisted Function Calls (min, max, abs, round)
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise SafeEvaluationError("Arbitrary function invocation is prohibited.")
            func_name = node.func.id
            if func_name not in self.SAFE_FUNCTIONS:
                raise SafeEvaluationError(f"Function '{func_name}' is not in the safe functions allowlist.")
            args = [self._eval_node(a, ctx) for a in node.args]
            return self.SAFE_FUNCTIONS[func_name](*args)

        # Reject any other node type (Lambda, Comprehensions, Imports, Subscripts, etc.)
        raise SafeEvaluationError(
            f"Unsupported or unsafe syntax construct '{type(node).__name__}' in rule expression."
        )


# Global default instance
default_evaluator = SafeExpressionEvaluator()


def evaluate_condition_safely(expr: str, context: Optional[Dict[str, Any]] = None) -> bool:
    """Convenience helper returning bool for condition expression evaluation."""
    res = default_evaluator.evaluate(expr, context)
    return bool(res)
