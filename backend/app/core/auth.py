"""Temporary auth dependency for Phase 2.1.

Full Google OAuth + domain allowlist + content_admin role checks land later
(BL-SEC-01 / BL-SEC-02). Until then:

- AUTH_DEV_BYPASS=true (default): accept requests without a Bearer token.
- AUTH_DEV_BYPASS=false: require Authorization: Bearer matching UPLOAD_BEARER_TOKEN.

Do not treat this as production authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Minimal caller identity for audit fields (hashed later; plain for stub)."""

    subject: str
    auth_mode: str  # "dev_bypass" | "bearer_token"


async def require_upload_auth(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> AuthContext:
    """Protect upload routes with temporary Bearer-or-bypass gate."""
    if settings.auth_dev_bypass:
        return AuthContext(subject="dev-bypass", auth_mode="dev_bypass")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header (Bearer required)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ").strip()
    expected = (settings.upload_bearer_token or "").strip()
    if not expected or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthContext(subject="bearer-token", auth_mode="bearer_token")
