"""Sanitization utilities for logs, audit events, agent runs, and errors.

Ensures that database URLs, passwords, API keys, tokens, and internal credentials
are never leaked in API responses, event logs, agent outputs, or error messages.
"""

from __future__ import annotations

import re
from typing import Any

# Sensitive key patterns to redact in dictionaries/JSON payloads
SENSITIVE_KEY_PATTERNS = re.compile(
    r"(password|passwd|secret|api_?key|token|auth|credential|database_?url|dsn|private_?key)",
    re.IGNORECASE,
)

# Common connection string / URL pattern: postgresql://user:pass@host:port/db
DB_URL_PATTERN = re.compile(
    r"(postgres(?:ql)?(?:\+[a-z0-9]+)?://)([^:@\s]+):([^@\s]+)@([^\s/:]+)(?::(\d+))?(/?[^\s]*)",
    re.IGNORECASE,
)

# Generic credential assignment pattern: key=value or key: "value"
CREDENTIAL_ASSIGN_PATTERN = re.compile(
    r"""(?i)\b(password|passwd|secret|api_?key|token|auth|bearer)\b\s*[:=]\s*['"]?([^\s,'"]+)['"]?"""
)

# Bearer token pattern
BEARER_PATTERN = re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]+)", re.IGNORECASE)


def sanitize_error_message(err: Any) -> str:
    """Sanitize error messages or exception strings to prevent leaking credentials.

    Redacts:
      - Database URLs with user/password
      - Explicit password, token, or secret assignments
      - Bearer tokens
    """
    if err is None:
        return ""
    if isinstance(err, Exception):
        raw_msg = f"{type(err).__name__}: {str(err)}"
    else:
        raw_msg = str(err)

    if not raw_msg.strip():
        return ""

    # Redact database URLs: keep scheme, user, host/db, redact password
    redacted = DB_URL_PATTERN.sub(r"\1\2:***@\4\6", raw_msg)

    # Redact bearer tokens
    redacted = BEARER_PATTERN.sub("Bearer ***", redacted)

    # Redact keyword assignments (e.g. password="foo")
    redacted = CREDENTIAL_ASSIGN_PATTERN.sub(r"\1: ***", redacted)

    return redacted.strip()


def sanitize_dict(obj: Any) -> Any:
    """Recursively sanitize dict or list structures, replacing sensitive values with '***'.

    Never mutates the original dictionary in-place; returns a cleaned copy.
    """
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            if SENSITIVE_KEY_PATTERNS.search(str(k)):
                sanitized[k] = "***"
            else:
                sanitized[k] = sanitize_dict(v)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_dict(item) for item in obj]
    elif isinstance(obj, str):
        # Also redact raw connection strings or credentials inside string values
        return sanitize_error_message(obj)
    return obj
