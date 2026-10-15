"""Core Configuration and Environment Validation Module (Phase P11).

Provides:
- Startup configuration audit and validation
- Strict rejection of insecure default credentials in non-development environments
- Centralized timeout, rate-limiting, and pagination thresholds
"""

from __future__ import annotations

import logging
import os
from typing import List, Tuple

logger = logging.getLogger("enterpriseai.config")

# Timeout & Limit Constants
DEFAULT_STATEMENT_TIMEOUT_MS = int(os.environ.get("DB_STATEMENT_TIMEOUT_MS", "15000"))
DEFAULT_LOCK_TIMEOUT_MS = int(os.environ.get("DB_LOCK_TIMEOUT_MS", "5000"))
DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 500

# Known insecure development defaults to detect
INSECURE_DEFAULT_PATTERNS: List[Tuple[str, str]] = [
    ("ADMIN_API_KEY", "dev-admin-key"),
    ("OPERATOR_API_KEY", "dev-operator-key"),
    ("FINANCE_API_KEY", "dev-finance-key"),
    ("SUPPLY_CHAIN_API_KEY", "dev-supply-key"),
    ("VIEWER_API_KEY", "dev-viewer-key"),
    ("API_KEY", "dev-operator-key"),
]


def audit_configuration_security() -> List[str]:
    """Inspect environment variables for insecure or default credential strings.

    Returns a list of unsafe variable names ONLY (never variable values).
    """
    unsafe_vars: List[str] = []

    for var_name, default_val in INSECURE_DEFAULT_PATTERNS:
        val = os.environ.get(var_name)
        if val and val.strip() == default_val:
            unsafe_vars.append(var_name)

    # Database URL check for common dev passwords
    db_url = os.environ.get("DATABASE_URL", "")
    if ("enterprise_dev_pass" in db_url) or (":1234@" in db_url and "test" not in db_url.lower()):
        unsafe_vars.append("DATABASE_URL")

    # Blockchain key check
    eth_key = os.environ.get("BLOCKCHAIN_PRIVATE_KEY", "")
    sim_chain = os.environ.get("SIMULATE_BLOCKCHAIN", "true").lower() in ("true", "1")
    if not sim_chain and (not eth_key or eth_key.startswith("0x0000")):
        unsafe_vars.append("BLOCKCHAIN_PRIVATE_KEY")

    return unsafe_vars


def validate_startup_config() -> None:
    """Validate configuration on application startup.

    Rules:
    - If APP_ENVIRONMENT is 'production' or 'staging', refuses to start with default
      credentials, raising a RuntimeError listing only the names of unsafe variables.
    - If APP_ENVIRONMENT is 'development' or 'test', emits a clean warning if defaults are present.
    """
    env = (os.environ.get("APP_ENVIRONMENT") or os.environ.get("ENVIRONMENT", "development")).lower()
    unsafe = audit_configuration_security()

    if env in ("production", "staging"):
        if unsafe:
            msg = (
                f"FATAL: Refusing startup in '{env}' mode due to insecure default credentials. "
                f"Unsafe variables detected: {', '.join(unsafe)}. "
                f"Rotate these secrets with cryptographically random keys."
            )
            logger.critical(msg)
            raise RuntimeError(msg)
    else:
        if unsafe:
            logger.warning(
                "DEVELOPMENT ENVIRONMENT NOTICE: Running with dev default credentials for: %s",
                ", ".join(unsafe),
            )
        else:
            logger.info("Configuration validated: zero default credentials detected in %s environment.", env)
