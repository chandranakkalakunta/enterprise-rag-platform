"""Firestore user profiles (Phase 5.1 / ADR-0009).

Collection layout:
  users/{uid}
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from google.cloud import firestore

from app.core.config import Settings, parse_csv_set

logger = logging.getLogger("erp.api.users")

USERS_COLLECTION = "users"

Role = Literal["viewer", "content_admin", "admin"]
VALID_ROLES: frozenset[str] = frozenset({"viewer", "content_admin", "admin"})


class FirestoreClientLike(Protocol):
    def collection(self, name: str) -> Any: ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def resolve_bootstrap_role(email: str, settings: Settings, existing_role: str | None) -> Role:
    """Map email to role using ADMIN_EMAILS / CONTENT_ADMIN_EMAILS / existing / viewer.

    Bootstrap lists re-assert elevated roles on every login when still listed.
    Emails not on bootstrap lists keep an existing valid role, else default viewer.
    """
    email_l = (email or "").strip().lower()
    admins = parse_csv_set(settings.admin_emails)
    content_admins = parse_csv_set(settings.content_admin_emails)

    if email_l in admins:
        return "admin"
    if email_l in content_admins:
        return "content_admin"
    if existing_role in VALID_ROLES:
        return existing_role  # type: ignore[return-value]
    return "viewer"


def resolve_or_create_user(
    client: FirestoreClientLike,
    *,
    uid: str,
    email: str,
    display_name: str,
    photo_url: str | None,
    settings: Settings,
) -> dict[str, Any]:
    """Upsert users/{uid}; return profile dict including role.

    Updates last_login_at always. Re-applies bootstrap role when email is listed.
    """
    if not uid:
        raise ValueError("uid is required")
    email_l = (email or "").strip().lower()
    if not email_l:
        raise ValueError("email is required")

    ref = client.collection(USERS_COLLECTION).document(uid)
    snap = ref.get()
    now = _utc_now()
    existing: dict[str, Any] = snap.to_dict() if snap.exists else {}
    existing_role = existing.get("role") if existing else None
    role = resolve_bootstrap_role(email_l, settings, existing_role)

    display = (display_name or existing.get("display_name") or email_l.split("@")[0]).strip()
    photo = photo_url if photo_url is not None else existing.get("photo_url")

    if snap.exists:
        update: dict[str, Any] = {
            "email": email_l,
            "display_name": display,
            "photo_url": photo,
            "role": role,
            "last_login_at": now,
        }
        ref.update(update)
        profile = {**existing, **update, "uid": uid}
    else:
        profile = {
            "uid": uid,
            "email": email_l,
            "display_name": display,
            "photo_url": photo,
            "role": role,
            "created_at": now,
            "last_login_at": now,
        }
        ref.set(profile)

    logger.info(
        "user_upsert uid_hash=%s role=%s created=%s",
        # avoid raw PII in logs — short stable hash of uid
        hex(hash(uid) & 0xFFFFFFFF)[2:],
        role,
        not snap.exists,
    )
    return profile
