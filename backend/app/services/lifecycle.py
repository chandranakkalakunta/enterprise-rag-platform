"""Publish / retire version orchestration with Firestore transactions (Phase 2.4)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from app.services.firestore_repo import DOCUMENTS_COLLECTION, version_ref
from app.services.lifecycle_rules import (
    ConflictError,
    InvalidIdError,
    NotFoundError,
    PublishPlan,
    RetirePlan,
    plan_publish,
    plan_retire,
    validate_ids,
)

logger = logging.getLogger("erp.api.lifecycle")


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    document_id: str
    version_id: str
    status: str
    active_version_id: str | None
    published_at: datetime | None = None
    published_by: str | None = None
    retired_at: datetime | None = None
    retired_by: str | None = None
    previous_published_version_id: str | None = None
    cleared_active_pointer: bool = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _snap_dict(snap: Any) -> dict[str, Any] | None:
    if not getattr(snap, "exists", False):
        return None
    data = snap.to_dict() or {}
    return data


@firestore.transactional
def _publish_in_transaction(
    transaction: firestore.Transaction,
    client: firestore.Client,
    document_id: str,
    version_id: str,
    actor: str,
    now: datetime,
) -> LifecycleResult:
    doc_ref = client.collection(DOCUMENTS_COLLECTION).document(document_id)
    ver_ref = version_ref(client, document_id, version_id)

    document = _snap_dict(doc_ref.get(transaction=transaction))
    version = _snap_dict(ver_ref.get(transaction=transaction))

    prev_id = (document or {}).get("active_version_id")
    previous_version: dict[str, Any] | None = None
    prev_ref = None
    if prev_id and prev_id != version_id:
        prev_ref = version_ref(client, document_id, prev_id)
        previous_version = _snap_dict(prev_ref.get(transaction=transaction))

    plan: PublishPlan = plan_publish(
        document=document,
        version=version,
        document_id=document_id,
        version_id=version_id,
        actor=actor,
        now=now,
        previous_version=previous_version,
    )

    transaction.update(ver_ref, plan.version_updates)
    transaction.update(doc_ref, plan.document_updates)
    if (
        plan.previous_published_version_id
        and plan.previous_version_updates
        and prev_ref is not None
    ):
        transaction.update(prev_ref, plan.previous_version_updates)

    logger.info(
        "version_published document_id=%s version_id=%s previous=%s actor=%s",
        document_id,
        version_id,
        plan.previous_published_version_id,
        actor,
    )
    return LifecycleResult(
        document_id=document_id,
        version_id=version_id,
        status="published",
        active_version_id=version_id,
        published_at=now,
        published_by=actor,
        previous_published_version_id=plan.previous_published_version_id,
    )


@firestore.transactional
def _retire_in_transaction(
    transaction: firestore.Transaction,
    client: firestore.Client,
    document_id: str,
    version_id: str,
    actor: str,
    now: datetime,
) -> LifecycleResult:
    doc_ref = client.collection(DOCUMENTS_COLLECTION).document(document_id)
    ver_ref = version_ref(client, document_id, version_id)

    document = _snap_dict(doc_ref.get(transaction=transaction))
    version = _snap_dict(ver_ref.get(transaction=transaction))

    plan: RetirePlan = plan_retire(
        document=document,
        version=version,
        document_id=document_id,
        version_id=version_id,
        actor=actor,
        now=now,
    )

    transaction.update(ver_ref, plan.version_updates)
    transaction.update(doc_ref, plan.document_updates)

    active = None
    if not plan.cleared_active_pointer and document:
        active = document.get("active_version_id")

    logger.info(
        "version_retired document_id=%s version_id=%s cleared_active=%s actor=%s",
        document_id,
        version_id,
        plan.cleared_active_pointer,
        actor,
    )
    return LifecycleResult(
        document_id=document_id,
        version_id=version_id,
        status="retired",
        active_version_id=active,
        published_at=version.get("published_at") if version else None,
        published_by=version.get("published_by") if version else None,
        retired_at=now,
        retired_by=actor,
        cleared_active_pointer=plan.cleared_active_pointer,
    )


def publish_version(
    client: firestore.Client,
    *,
    document_id: str,
    version_id: str,
    actor: str,
) -> LifecycleResult:
    """
    Atomically publish a ready version.

    - Version status → published
    - document.active_version_id → this version
    - Previous published active version → retired (history retained)
    """
    validate_ids(document_id, version_id)
    document_id = document_id.strip()
    version_id = version_id.strip()
    now = _utc_now()
    transaction = client.transaction()
    return _publish_in_transaction(
        transaction, client, document_id, version_id, actor, now
    )


def retire_version(
    client: firestore.Client,
    *,
    document_id: str,
    version_id: str,
    actor: str,
) -> LifecycleResult:
    """
    Atomically retire a ready or published version.

    If the version was the document's active_version_id, clear the pointer.
    Version records are never deleted.
    """
    validate_ids(document_id, version_id)
    document_id = document_id.strip()
    version_id = version_id.strip()
    now = _utc_now()
    transaction = client.transaction()
    return _retire_in_transaction(
        transaction, client, document_id, version_id, actor, now
    )


__all__ = [
    "LifecycleResult",
    "publish_version",
    "retire_version",
    "NotFoundError",
    "ConflictError",
    "InvalidIdError",
]
