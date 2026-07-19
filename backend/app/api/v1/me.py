"""Identity API — GET /api/v1/me (Phase 5.1 / ADR-0009)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import AuthContext, require_user, roles_for_me
from app.models.auth import MeResponse

router = APIRouter(tags=["auth"])


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Current authenticated user profile and role",
    responses={
        401: {"description": "Missing or invalid Google ID token"},
        403: {"description": "Email domain not allowlisted"},
    },
)
async def get_me(
    auth: Annotated[AuthContext, Depends(require_user)],
) -> MeResponse:
    """Return uid, email, name, picture, role from backend-resolved AuthContext.

    Triggers Firestore users/{uid} upsert on first call after login.
    """
    payload = roles_for_me(auth)
    return MeResponse(**payload)
