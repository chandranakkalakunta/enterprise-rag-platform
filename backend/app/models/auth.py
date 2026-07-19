"""Auth / identity API models (Phase 5.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RoleLiteral = Literal["viewer", "content_admin", "admin"]


class MeResponse(BaseModel):
    """GET /api/v1/me response — backend source of truth for UI role display."""

    uid: str = Field(..., description="Google subject (sub)")
    email: str = Field(..., description="Verified email (lowercased)")
    name: str = Field(..., description="Display name")
    picture: str | None = Field(default=None, description="Profile photo URL")
    role: RoleLiteral = Field(..., description="RBAC role from Firestore")
