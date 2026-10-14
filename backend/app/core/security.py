"""Security and Authorization Module (Task 15 Hardened).

Provides server-side authentication and role-based access control (RBAC) boundaries:
- Roles:
  * VIEWER: Read-only access to monitoring and telemetry endpoints.
  * OPERATOR: Ability to manually trigger scheduler cycles and propose actions.
  * FINANCE_APPROVER: Financial approval authority up to configured threshold limits.
  * SUPPLY_CHAIN_APPROVER: Supplier, procurement, and logistics routing approvals.
  * ADMIN: Unrestricted operational and administrative authority.

Enforces:
- Least privilege principle.
- Server-side credential-to-role mapping (client headers X-User-Role/X-User-Id cannot forge privileges).
- Protection on all state-changing endpoints (approvals, actions, scheduler triggers).
- Self-approval restrictions (actors cannot approve their own proposed actions).
- Server-side approval limit enforcement.
- Fail-closed behavior in production mode when credentials are missing or invalid.
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Dict, List, Optional, Tuple

from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger("enterpriseai.security")

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class UserRole(str, Enum):
    VIEWER = "VIEWER"
    OPERATOR = "OPERATOR"
    FINANCE_APPROVER = "FINANCE_APPROVER"
    SUPPLY_CHAIN_APPROVER = "SUPPLY_CHAIN_APPROVER"
    ADMIN = "ADMIN"


ROLE_HIERARCHY = {
    UserRole.VIEWER: 10,
    UserRole.OPERATOR: 20,
    UserRole.FINANCE_APPROVER: 30,
    UserRole.SUPPLY_CHAIN_APPROVER: 30,
    UserRole.ADMIN: 100,
}

# Standard development and testing credentials (disabled in production)
DEV_CREDENTIAL_REGISTRY: Dict[str, Tuple[UserRole, str, List[str], Optional[float]]] = {
    "dev-admin-key": (
        UserRole.ADMIN,
        "admin_user",
        ["FINANCE", "SUPPLY_CHAIN", "PROCUREMENT", "LOGISTICS"],
        None,
    ),
    "dev-finance-key": (
        UserRole.FINANCE_APPROVER,
        "finance_approver",
        ["FINANCE"],
        60000000.0,
    ),
    "dev-supply-key": (
        UserRole.SUPPLY_CHAIN_APPROVER,
        "supply_chain_approver",
        ["SUPPLY_CHAIN", "PROCUREMENT", "LOGISTICS"],
        None,
    ),
    "dev-operator-key": (
        UserRole.OPERATOR,
        "operator_user",
        [],
        None,
    ),
    "dev-viewer-key": (
        UserRole.VIEWER,
        "viewer_user",
        [],
        None,
    ),
}


class AuthUser:
    """Authenticated user context with server-verified identity, role, and permissions."""

    def __init__(
        self,
        user_id: str,
        role: UserRole,
        approval_domains: Optional[List[str]] = None,
        max_approval_amount: Optional[float] = None,
    ):
        self.user_id = user_id
        self.role = role
        self.approval_domains = approval_domains or []
        self.max_approval_amount = max_approval_amount

    def has_role(self, minimum_role: UserRole) -> bool:
        """Check if user role meets or exceeds minimum hierarchy rank."""
        if self.role == UserRole.ADMIN:
            return True
        user_rank = ROLE_HIERARCHY.get(self.role, 0)
        required_rank = ROLE_HIERARCHY.get(minimum_role, 0)
        return user_rank >= required_rank

    def can_approve_domain(self, domain: str) -> bool:
        """Check if user is authorized for a specific approval domain."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.FINANCE_APPROVER and domain.upper() == "FINANCE":
            return True
        if self.role == UserRole.SUPPLY_CHAIN_APPROVER and domain.upper() in {
            "SUPPLY_CHAIN",
            "PROCUREMENT",
            "LOGISTICS",
            "INVENTORY",
            "QUALITY",
            "SAFETY",
            "PRODUCTION",
        }:
            return True
        return domain.upper() in [d.upper() for d in self.approval_domains]

    def can_approve_amount(self, amount: float) -> bool:
        """Check if user is authorized for a specific expenditure amount."""
        if self.role == UserRole.ADMIN:
            return True
        if self.max_approval_amount is not None:
            return amount <= self.max_approval_amount
        return True


def get_credential_registry() -> Dict[str, Tuple[UserRole, str, List[str], Optional[float]]]:
    """Build the active credential-to-role mapping from server environment variables."""
    registry: Dict[str, Tuple[UserRole, str, List[str], Optional[float]]] = {}

    # Explicit role-specific environment variables
    admin_key = os.environ.get("ADMIN_API_KEY")
    if admin_key:
        registry[admin_key.strip()] = (
            UserRole.ADMIN,
            "admin_user",
            ["FINANCE", "SUPPLY_CHAIN", "PROCUREMENT", "LOGISTICS", "QUALITY", "SAFETY", "PRODUCTION"],
            None,
        )

    fin_key = os.environ.get("FINANCE_API_KEY")
    if fin_key:
        registry[fin_key.strip()] = (
            UserRole.FINANCE_APPROVER,
            "finance_approver",
            ["FINANCE"],
            60000000.0,
        )

    sc_key = os.environ.get("SUPPLY_CHAIN_API_KEY")
    if sc_key:
        registry[sc_key.strip()] = (
            UserRole.SUPPLY_CHAIN_APPROVER,
            "supply_chain_approver",
            ["SUPPLY_CHAIN", "PROCUREMENT", "LOGISTICS", "INVENTORY", "QUALITY", "SAFETY", "PRODUCTION"],
            None,
        )

    op_key = os.environ.get("OPERATOR_API_KEY")
    if op_key:
        registry[op_key.strip()] = (
            UserRole.OPERATOR,
            "operator_user",
            [],
            None,
        )

    view_key = os.environ.get("VIEWER_API_KEY")
    if view_key:
        registry[view_key.strip()] = (
            UserRole.VIEWER,
            "viewer_user",
            [],
            None,
        )

    # Legacy or generic single key fallback
    generic_key = os.environ.get("API_KEY")
    if generic_key and generic_key.strip() not in registry:
        registry[generic_key.strip()] = (
            UserRole.OPERATOR,
            "api_key_operator",
            [],
            None,
        )

    # In development or testing, merge default development credentials if not overridden
    env = (os.environ.get("APP_ENVIRONMENT") or os.environ.get("ENVIRONMENT", "development")).lower()
    if env != "production":
        for k, v in DEV_CREDENTIAL_REGISTRY.items():
            if k not in registry:
                registry[k] = v

    return registry


def get_current_user(
    x_api_key: Optional[str] = Security(API_KEY_HEADER),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> AuthUser:
    """Resolve authenticated user context from server-side credential verification.

    Security Rules:
    1. Roles and user identity are derived EXCLUSIVELY from verified credentials.
    2. Client claims in 'X-User-Role' or 'X-User-Id' are NEVER trusted to elevate privileges.
       If an inconsistent 'X-User-Role' is supplied, the request is rejected with HTTP 403.
    3. In production: missing credentials or unconfigured server keys trigger HTTP 401 / 500.
    4. In development: unauthenticated callers are assigned VIEWER (least privilege).
    """
    env = (os.environ.get("APP_ENVIRONMENT") or os.environ.get("ENVIRONMENT", "development")).lower()
    registry = get_credential_registry()

    # In production, fail closed
    if env == "production":
        if not registry:
            logger.error("Production security alert: no API keys configured in environment.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication configuration missing in production environment.",
            )
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials.",
            )
        clean_key = x_api_key.strip()
        if clean_key not in registry:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials.",
            )
        role, user_id, domains, max_amount = registry[clean_key]
    else:
        # Development / Test mode
        if x_api_key:
            clean_key = x_api_key.strip()
            if clean_key not in registry:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials.",
                )
            role, user_id, domains, max_amount = registry[clean_key]
        else:
            # Unauthenticated callers in development default to VIEWER (least privilege)
            role = UserRole.VIEWER
            user_id = "anonymous_viewer"
            domains = []
            max_amount = None

    # Anti-Forgery Gate: If client provided an X-User-Role header that does not match authenticated role
    if x_user_role:
        client_role_claimed = x_user_role.strip().upper()
        if client_role_claimed != role.value:
            logger.warning(
                "Attempted role forgery blocked: client claimed '%s' but authenticated credential has role '%s'",
                client_role_claimed,
                role.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Client role claim '{client_role_claimed}' does not match authenticated role '{role.value}'.",
            )

    return AuthUser(
        user_id=user_id,
        role=role,
        approval_domains=domains,
        max_approval_amount=max_amount,
    )


def require_role(minimum_role: UserRole):
    """FastAPI dependency factory enforcing minimum role requirement."""

    def role_checker(user: AuthUser = Security(get_current_user)) -> AuthUser:
        if not user.has_role(minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires at least '{minimum_role.value}' role.",
            )
        return user

    return role_checker


def authenticate_ws_credentials(
    api_key: Optional[str] = None,
    token: Optional[str] = None,
) -> AuthUser:
    """Authenticate WebSocket client credentials from query parameter or initial frame.

    Security Rules:
    1. Credentials must match registered server keys in the credential registry.
    2. In production, missing or unknown credentials immediately fail closed (HTTP 401).
    3. In development/testing, unauthenticated callers are assigned VIEWER (least privilege).
    4. Client role claims are derived strictly server-side from registered keys.
    """
    effective_key = (api_key or token or "").strip()
    env = (os.environ.get("APP_ENVIRONMENT") or os.environ.get("ENVIRONMENT", "development")).lower()
    registry = get_credential_registry()

    if env == "production":
        if not registry:
            logger.error("Production security alert: no API keys configured for WebSocket authentication.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication configuration missing in production environment.",
            )
        if not effective_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials for WebSocket connection.",
            )
        if effective_key not in registry:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials for WebSocket connection.",
            )
        role, user_id, domains, max_amount = registry[effective_key]
    else:
        if effective_key:
            if effective_key not in registry:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials for WebSocket connection.",
                )
            role, user_id, domains, max_amount = registry[effective_key]
        else:
            role = UserRole.VIEWER
            user_id = "anonymous_ws_viewer"
            domains = []
            max_amount = None

    return AuthUser(
        user_id=user_id,
        role=role,
        approval_domains=domains,
        max_approval_amount=max_amount,
    )

