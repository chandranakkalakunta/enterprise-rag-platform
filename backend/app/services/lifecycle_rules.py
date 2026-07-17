"""Pure version lifecycle rules (ADR-0003 / Phase 2.4).

No FastAPI / Firestore / GCS dependencies — unit-testable state machine.

Valid transitions (Phase 2.4):
  ready → published   (publish)
  ready → retired     (retire without ever publishing)
  published → retired (retire / supersede on new publish)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

STATUS_PROCESSING = "processing"
STATUS_READY = "ready"
STATUS_FAILED = "failed"
STATUS_PUBLISHED = "published"
STATUS_RETIRED = "retired"

PUBLISHABLE_STATUSES = frozenset({STATUS_READY})
RETIRABLE_STATUSES = frozenset({STATUS_READY, STATUS_PUBLISHED})


class LifecycleError(Exception):
    """Base lifecycle domain error."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(LifecycleError):
    """Document or version does not exist (or version not under document)."""


class ConflictError(LifecycleError):
    """Illegal state transition (HTTP 409)."""


class InvalidIdError(LifecycleError):
    """Malformed document_id or version_id (HTTP 400)."""


def validate_ids(document_id: str, version_id: str) -> None:
    """Reject empty or path-like IDs early."""
    for name, value in (("document_id", document_id), ("version_id", version_id)):
        if value is None or not str(value).strip():
            raise InvalidIdError(f"{name} is required")
        v = str(value).strip()
        if "/" in v or "\\" in v or ".." in v:
            raise InvalidIdError(f"{name} contains invalid characters")
        if len(v) > 128:
            raise InvalidIdError(f"{name} is too long")


@dataclass(frozen=True, slots=True)
class PublishPlan:
    """Concrete updates to apply atomically on publish."""

    version_id: str
    document_id: str
    version_updates: dict[str, Any]
    document_updates: dict[str, Any]
    previous_published_version_id: str | None
    previous_version_updates: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class RetirePlan:
    """Concrete updates to apply atomically on retire."""

    version_id: str
    document_id: str
    version_updates: dict[str, Any]
    document_updates: dict[str, Any]
    cleared_active_pointer: bool


def plan_publish(
    *,
    document: dict[str, Any] | None,
    version: dict[str, Any] | None,
    document_id: str,
    version_id: str,
    actor: str,
    now: datetime,
    previous_version: dict[str, Any] | None = None,
) -> PublishPlan:
    """
    Validate publish and build update plan.

    ``previous_version`` is the document currently pointed to by
    ``active_version_id`` (if any and different from the version being published).
    """
    if document is None:
        raise NotFoundError(f"Document not found: {document_id}")
    if version is None:
        raise NotFoundError(
            f"Version not found: {version_id} under document {document_id}"
        )

    if version.get("document_id") not in (None, document_id):
        raise NotFoundError(
            f"Version not found: {version_id} under document {document_id}"
        )
    if version.get("version_id") not in (None, version_id):
        raise NotFoundError(
            f"Version not found: {version_id} under document {document_id}"
        )

    status = version.get("status")
    if status not in PUBLISHABLE_STATUSES:
        raise ConflictError(
            f"Cannot publish version in status '{status}' "
            f"(allowed: {', '.join(sorted(PUBLISHABLE_STATUSES))})"
        )

    version_updates: dict[str, Any] = {
        "status": STATUS_PUBLISHED,
        "published_at": now,
        "published_by": actor,
        "updated_at": now,
        "retired_at": None,
        "retired_by": None,
    }
    document_updates: dict[str, Any] = {
        "active_version_id": version_id,
        "updated_at": now,
    }

    prev_id = document.get("active_version_id")
    prev_updates: dict[str, Any] | None = None
    previous_published_version_id: str | None = None

    if prev_id and prev_id != version_id and previous_version is not None:
        if previous_version.get("status") == STATUS_PUBLISHED:
            previous_published_version_id = prev_id
            prev_updates = {
                "status": STATUS_RETIRED,
                "retired_at": now,
                "retired_by": actor,
                "updated_at": now,
            }

    return PublishPlan(
        version_id=version_id,
        document_id=document_id,
        version_updates=version_updates,
        document_updates=document_updates,
        previous_published_version_id=previous_published_version_id,
        previous_version_updates=prev_updates,
    )


def plan_retire(
    *,
    document: dict[str, Any] | None,
    version: dict[str, Any] | None,
    document_id: str,
    version_id: str,
    actor: str,
    now: datetime,
) -> RetirePlan:
    """Validate retire and build update plan."""
    if document is None:
        raise NotFoundError(f"Document not found: {document_id}")
    if version is None:
        raise NotFoundError(
            f"Version not found: {version_id} under document {document_id}"
        )

    if version.get("document_id") not in (None, document_id):
        raise NotFoundError(
            f"Version not found: {version_id} under document {document_id}"
        )

    status = version.get("status")
    if status not in RETIRABLE_STATUSES:
        raise ConflictError(
            f"Cannot retire version in status '{status}' "
            f"(allowed: {', '.join(sorted(RETIRABLE_STATUSES))})"
        )

    version_updates: dict[str, Any] = {
        "status": STATUS_RETIRED,
        "retired_at": now,
        "retired_by": actor,
        "updated_at": now,
    }

    cleared = document.get("active_version_id") == version_id
    document_updates: dict[str, Any] = {"updated_at": now}
    if cleared:
        document_updates["active_version_id"] = None

    return RetirePlan(
        version_id=version_id,
        document_id=document_id,
        version_updates=version_updates,
        document_updates=document_updates,
        cleared_active_pointer=cleared,
    )
