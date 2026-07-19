"""AuthN / AuthZ dependencies (Phase 5.1 / ADR-0009).

- Google ID token verification (audience = GOOGLE_OAUTH_CLIENT_ID)
- Domain allowlist (ALLOWED_EMAIL_DOMAINS)
- Firestore users/{uid} upsert + role bootstrap
- AUTH_DEV_BYPASS=true: local/test only fake admin (never for shared envs)

Backend is the source of truth for roles. Frontend must not authorize alone.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated, Callable

from fastapi import Depends, Header, HTTPException, status
from google.auth.transport import requests as google_requests
from google.cloud import firestore
from google.oauth2 import id_token

from app.core.config import Settings, get_settings, parse_csv_set
from app.services.users import Role, resolve_or_create_user

logger = logging.getLogger("erp.api.auth")


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Authenticated caller identity (backend-resolved role)."""

    uid: str
    email: str
    display_name: str
    photo_url: str | None
    role: Role
    subject: str  # audit actor (email preferred)
    auth_mode: str  # "google_id_token" | "dev_bypass"


class TokenVerificationError(Exception):
    """Raised when Google ID token verification fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def email_domain_allowed(email: str, settings: Settings) -> bool:
    """Return True if email domain is in ALLOWED_EMAIL_DOMAINS."""
    email_l = (email or "").strip().lower()
    if "@" not in email_l:
        return False
    domain = email_l.rsplit("@", 1)[-1]
    allowed = parse_csv_set(settings.allowed_email_domains)
    return domain in allowed


def verify_google_id_token(token: str, client_id: str) -> dict:
    """Verify a Google ID token and return claims.

    Raises TokenVerificationError on any validation failure.
    """
    if not token or not token.strip():
        raise TokenVerificationError("Empty ID token")
    if not client_id or not client_id.strip():
        raise TokenVerificationError("GOOGLE_OAUTH_CLIENT_ID is not configured")

    try:
        request = google_requests.Request()
        claims = id_token.verify_oauth2_token(
            token.strip(),
            request,
            audience=client_id.strip(),
        )
    except ValueError as exc:
        raise TokenVerificationError(f"Invalid Google ID token: {exc}") from exc
    except Exception as exc:  # network / library errors
        raise TokenVerificationError(f"Token verification failed: {exc}") from exc

    if not isinstance(claims, dict):
        raise TokenVerificationError("Unexpected token claims type")

    # Optional issuer check (Google)
    iss = claims.get("iss")
    if iss not in ("accounts.google.com", "https://accounts.google.com"):
        raise TokenVerificationError(f"Invalid token issuer: {iss}")

    if not claims.get("email"):
        raise TokenVerificationError("Token missing email claim")

    if not claims.get("email_verified"):
        raise TokenVerificationError("Email not verified by Google")

    if not claims.get("sub"):
        raise TokenVerificationError("Token missing sub (uid)")

    return claims


def _dev_bypass_context() -> AuthContext:
    return AuthContext(
        uid="dev-bypass",
        email="dev@chandraailabs.com",
        display_name="Dev Bypass",
        photo_url=None,
        role="admin",
        subject="dev@chandraailabs.com",
        auth_mode="dev_bypass",
    )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized("Missing or invalid Authorization header (Bearer required)")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise _unauthorized("Empty bearer token")
    return token


def authenticate_request(
    settings: Settings,
    authorization: str | None,
    *,
    firestore_client: firestore.Client | None = None,
) -> AuthContext:
    """Resolve AuthContext from Authorization header or dev bypass.

    Pure-ish helper for tests (optional injected Firestore client).
    """
    if settings.auth_dev_bypass:
        return _dev_bypass_context()

    token = _extract_bearer(authorization)

    try:
        claims = verify_google_id_token(token, settings.google_oauth_client_id)
    except TokenVerificationError as exc:
        logger.info("auth_token_rejected reason=%s", exc.message)
        raise _unauthorized(exc.message) from exc

    email = str(claims["email"]).strip().lower()
    uid = str(claims["sub"])
    if not email_domain_allowed(email, settings):
        logger.info("auth_domain_denied domain=%s", email.rsplit("@", 1)[-1])
        raise _forbidden(
            f"Email domain not allowed. Allowed: {settings.allowed_email_domains}"
        )

    display_name = str(claims.get("name") or email.split("@")[0])
    photo_url = claims.get("picture")
    if photo_url is not None:
        photo_url = str(photo_url)

    client = firestore_client or firestore.Client(project=settings.gcp_project_id)
    try:
        profile = resolve_or_create_user(
            client,
            uid=uid,
            email=email,
            display_name=display_name,
            photo_url=photo_url,
            settings=settings,
        )
    except Exception as exc:
        logger.exception("user_upsert_failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"User profile store unavailable: {exc}",
        ) from exc

    role = profile.get("role") or "viewer"
    if role not in ("viewer", "content_admin", "admin"):
        role = "viewer"

    return AuthContext(
        uid=uid,
        email=email,
        display_name=str(profile.get("display_name") or display_name),
        photo_url=profile.get("photo_url"),
        role=role,  # type: ignore[arg-type]
        subject=email,
        auth_mode="google_id_token",
    )


async def require_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> AuthContext:
    """Require any authenticated allowlisted user (viewer+)."""
    return authenticate_request(settings, authorization)


def require_roles(*allowed: str) -> Callable:
    """Dependency factory: require authenticated user with one of ``allowed`` roles."""

    allowed_set = frozenset(allowed)

    async def _dep(
        settings: Annotated[Settings, Depends(get_settings)],
        authorization: Annotated[str | None, Header()] = None,
    ) -> AuthContext:
        ctx = authenticate_request(settings, authorization)
        if ctx.role not in allowed_set:
            raise _forbidden(
                f"Requires role in {sorted(allowed_set)}; current role is {ctx.role}"
            )
        return ctx

    return _dep


# Content mutations: content_admin or admin
require_content_auth = require_roles("content_admin", "admin")
# Upload uses the same role gate (ADR-0009 MVP)
require_upload_auth = require_content_auth


def roles_for_me(ctx: AuthContext) -> dict:
    """Serialize AuthContext for GET /api/v1/me."""
    return {
        "uid": ctx.uid,
        "email": ctx.email,
        "name": ctx.display_name,
        "picture": ctx.photo_url,
        "role": ctx.role,
    }
