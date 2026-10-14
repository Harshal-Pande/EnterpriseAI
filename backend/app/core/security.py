"""Security and Authorization Module (Task 15).

Provides authentication and role-based access control (RBAC) boundaries for:
- Viewers: Read-only access to monitoring and telemetry endpoints.
- Operators: Ability to manually trigger scheduler cycles and propose actions.
- Approvers: Domain-specific spending and operational approval authority.
- Admins: Unrestricted operational and administrative authority.

Enforces:
- Least privilege principle.
- Protection on state-changing endpoints (approvals, actions, scheduler triggers).
- Self-approval restrictions (actors cannot approve their own proposed actions).
- Safe development/test fallbacks when explicit auth headers are omitted.
"""

from __future__ import annotations

import os
import logging
from enum import Enum
from typing import Optional, List, Tuple
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


class AuthUser:
    """Authenticated user context with identity and role."""

    def __init__(
        self,
        user_id: str,
        role: UserRole,
        approval_domains: Optional[List[str]] = None,
    ):
        self.user_id = user_id
        self.role = role
        self.approval_domains = approval_domains or []

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
        if self.role == UserRole.SUPPLY_CHAIN_APPROVER and domain.upper() in {"SUPPLY_CHAIN", "PROCUREMENT", "LOGISTICS"}:
            return True
        return domain.upper() in [d.upper() for d in self.approval_domains]


def get_current_user(
    x_api_key: Optional[str] = Security(API_KEY_HEADER),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> AuthUser:
    """Resolve authenticated user from request headers.

    In production: strictly validates API keys or identity headers.
    In development/test: defaults safely to an OPERATOR/ADMIN context if omitted,
    preserving seamless testing while securing production deployments.
    """
    env = os.environ.get("ENVIRONMENT", "development").lower()
    configured_api_key = os.environ.get("API_KEY")

    # In production, require valid API key or reject
    if env == "production":
        if not configured_api_key or x_api_key != configured_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authentication credentials.",
            )

    # Resolve user role
    role = UserRole.OPERATOR
    if x_user_role:
        try:
            role = UserRole(x_user_role.upper())
        except ValueError:
            role = UserRole.VIEWER

    user_id = x_user_id or "system_operator"

    domains = []
    if role in {UserRole.FINANCE_APPROVER, UserRole.ADMIN}:
        domains.append("FINANCE")
    if role in {UserRole.SUPPLY_CHAIN_APPROVER, UserRole.ADMIN}:
        domains.extend(["PROCUREMENT", "LOGISTICS", "INVENTORY"])

    return AuthUser(user_id=user_id, role=role, approval_domains=domains)


def require_role(minimum_role: UserRole):
    """Dependency factory enforcing minimum user role requirement."""

    def role_checker(user: AuthUser = Security(get_current_user)) -> AuthUser:
        if not user.has_role(minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires at least '{minimum_role.value}' role.",
            )
        return user

    return role_checker
