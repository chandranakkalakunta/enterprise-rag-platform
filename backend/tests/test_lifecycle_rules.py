"""Unit tests for pure lifecycle state machine (Phase 2.4)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.lifecycle_rules import (
    ConflictError,
    InvalidIdError,
    NotFoundError,
    plan_publish,
    plan_retire,
    validate_ids,
)

NOW = datetime(2026, 7, 17, 12, 0, 0, tzinfo=timezone.utc)


def test_validate_ids_ok() -> None:
    validate_ids("doc-1", "ver-1")


def test_validate_ids_empty() -> None:
    with pytest.raises(InvalidIdError):
        validate_ids("", "ver-1")
    with pytest.raises(InvalidIdError):
        validate_ids("doc", "  ")


def test_validate_ids_path_injection() -> None:
    with pytest.raises(InvalidIdError):
        validate_ids("../etc", "ver")
    with pytest.raises(InvalidIdError):
        validate_ids("doc", "a/b")


def test_plan_publish_ready_success() -> None:
    plan = plan_publish(
        document={"document_id": "d1", "active_version_id": None},
        version={"version_id": "v1", "document_id": "d1", "status": "ready"},
        document_id="d1",
        version_id="v1",
        actor="dev-bypass",
        now=NOW,
    )
    assert plan.version_updates["status"] == "published"
    assert plan.version_updates["published_by"] == "dev-bypass"
    assert plan.version_updates["published_at"] == NOW
    assert plan.document_updates["active_version_id"] == "v1"
    assert plan.previous_published_version_id is None
    assert plan.previous_version_updates is None


def test_plan_publish_retires_previous_published() -> None:
    plan = plan_publish(
        document={"document_id": "d1", "active_version_id": "v-old"},
        version={"version_id": "v-new", "document_id": "d1", "status": "ready"},
        document_id="d1",
        version_id="v-new",
        actor="admin",
        now=NOW,
        previous_version={
            "version_id": "v-old",
            "document_id": "d1",
            "status": "published",
        },
    )
    assert plan.previous_published_version_id == "v-old"
    assert plan.previous_version_updates is not None
    assert plan.previous_version_updates["status"] == "retired"
    assert plan.previous_version_updates["retired_by"] == "admin"
    assert plan.document_updates["active_version_id"] == "v-new"


def test_plan_publish_not_found_document() -> None:
    with pytest.raises(NotFoundError, match="Document"):
        plan_publish(
            document=None,
            version={"status": "ready"},
            document_id="d1",
            version_id="v1",
            actor="a",
            now=NOW,
        )


def test_plan_publish_not_found_version() -> None:
    with pytest.raises(NotFoundError, match="Version"):
        plan_publish(
            document={"document_id": "d1"},
            version=None,
            document_id="d1",
            version_id="v1",
            actor="a",
            now=NOW,
        )


@pytest.mark.parametrize(
    "status",
    ["processing", "failed", "published", "retired", None],
)
def test_plan_publish_illegal_status(status: str | None) -> None:
    with pytest.raises(ConflictError, match="Cannot publish"):
        plan_publish(
            document={"document_id": "d1", "active_version_id": None},
            version={"version_id": "v1", "document_id": "d1", "status": status},
            document_id="d1",
            version_id="v1",
            actor="a",
            now=NOW,
        )


def test_plan_retire_published_clears_pointer() -> None:
    plan = plan_retire(
        document={"document_id": "d1", "active_version_id": "v1"},
        version={"version_id": "v1", "document_id": "d1", "status": "published"},
        document_id="d1",
        version_id="v1",
        actor="ops",
        now=NOW,
    )
    assert plan.version_updates["status"] == "retired"
    assert plan.cleared_active_pointer is True
    assert plan.document_updates["active_version_id"] is None
    assert plan.version_updates["retired_by"] == "ops"


def test_plan_retire_ready_without_active() -> None:
    plan = plan_retire(
        document={"document_id": "d1", "active_version_id": "other"},
        version={"version_id": "v1", "document_id": "d1", "status": "ready"},
        document_id="d1",
        version_id="v1",
        actor="ops",
        now=NOW,
    )
    assert plan.cleared_active_pointer is False
    assert "active_version_id" not in plan.document_updates
    assert plan.version_updates["status"] == "retired"


@pytest.mark.parametrize("status", ["processing", "failed", "retired"])
def test_plan_retire_illegal_status(status: str) -> None:
    with pytest.raises(ConflictError, match="Cannot retire"):
        plan_retire(
            document={"document_id": "d1"},
            version={"version_id": "v1", "document_id": "d1", "status": status},
            document_id="d1",
            version_id="v1",
            actor="a",
            now=NOW,
        )
