"""Phase 5.1 — auth helpers, domain gate, role bootstrap, /me, protected 401."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import (
    TokenVerificationError,
    authenticate_request,
    email_domain_allowed,
    verify_google_id_token,
)
from app.core.config import Settings, get_settings, parse_csv_set
from app.main import app
from app.services.users import resolve_bootstrap_role, resolve_or_create_user


@pytest.fixture(autouse=True)
def _clear_settings() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_parse_csv_set() -> None:
    assert parse_csv_set("a@x.com, B@Y.com") == {"a@x.com", "b@y.com"}
    assert parse_csv_set("") == set()
    assert parse_csv_set("  ,  ") == set()


def test_email_domain_allowed() -> None:
    settings = Settings(allowed_email_domains="chandraailabs.com,gmail.com")
    assert email_domain_allowed("user@chandraailabs.com", settings)
    assert email_domain_allowed("User@Gmail.com", settings)
    assert not email_domain_allowed("user@evil.com", settings)
    assert not email_domain_allowed("nodomain", settings)


def test_resolve_bootstrap_role_admin_and_content() -> None:
    settings = Settings(
        admin_emails="admin@chandraailabs.com",
        content_admin_emails="ops@gmail.com",
    )
    assert resolve_bootstrap_role("admin@chandraailabs.com", settings, None) == "admin"
    assert resolve_bootstrap_role("ops@gmail.com", settings, None) == "content_admin"
    assert resolve_bootstrap_role("new@gmail.com", settings, None) == "viewer"
    assert resolve_bootstrap_role("new@gmail.com", settings, "content_admin") == "content_admin"
    # admin list wins over existing
    assert resolve_bootstrap_role("admin@chandraailabs.com", settings, "viewer") == "admin"


def test_resolve_or_create_user_new_and_update() -> None:
    settings = Settings(admin_emails="boss@gmail.com")
    client = MagicMock()
    ref = MagicMock()
    client.collection.return_value.document.return_value = ref

    # create path
    snap_new = MagicMock()
    snap_new.exists = False
    ref.get.return_value = snap_new

    profile = resolve_or_create_user(
        client,
        uid="uid-1",
        email="boss@gmail.com",
        display_name="Boss",
        photo_url="https://example.com/p.jpg",
        settings=settings,
    )
    assert profile["role"] == "admin"
    assert profile["email"] == "boss@gmail.com"
    ref.set.assert_called_once()

    # update path
    snap_old = MagicMock()
    snap_old.exists = True
    snap_old.to_dict.return_value = {
        "uid": "uid-1",
        "email": "boss@gmail.com",
        "display_name": "Old",
        "role": "viewer",
        "photo_url": None,
    }
    ref.get.return_value = snap_old
    ref.set.reset_mock()
    updated = resolve_or_create_user(
        client,
        uid="uid-1",
        email="boss@gmail.com",
        display_name="Boss",
        photo_url=None,
        settings=settings,
    )
    assert updated["role"] == "admin"
    ref.update.assert_called_once()
    ref.set.assert_not_called()


def test_verify_google_id_token_rejects_empty_client() -> None:
    with pytest.raises(TokenVerificationError, match="not configured"):
        verify_google_id_token("tok", "")


def test_verify_google_id_token_success() -> None:
    claims = {
        "iss": "https://accounts.google.com",
        "sub": "sub-123",
        "email": "u@gmail.com",
        "email_verified": True,
        "name": "U",
        "picture": "https://example.com/a.png",
    }
    with patch("app.core.auth.id_token.verify_oauth2_token", return_value=claims):
        out = verify_google_id_token("good-token", "client-id.apps.googleusercontent.com")
    assert out["sub"] == "sub-123"


def test_verify_google_id_token_unverified_email() -> None:
    claims = {
        "iss": "https://accounts.google.com",
        "sub": "sub-123",
        "email": "u@gmail.com",
        "email_verified": False,
    }
    with patch("app.core.auth.id_token.verify_oauth2_token", return_value=claims):
        with pytest.raises(TokenVerificationError, match="not verified"):
            verify_google_id_token("tok", "client-id")


def test_authenticate_dev_bypass() -> None:
    settings = Settings(auth_dev_bypass=True)
    ctx = authenticate_request(settings, None)
    assert ctx.auth_mode == "dev_bypass"
    assert ctx.role == "admin"


def test_authenticate_domain_denied() -> None:
    settings = Settings(
        auth_dev_bypass=False,
        google_oauth_client_id="client-id",
        allowed_email_domains="chandraailabs.com,gmail.com",
    )
    claims = {
        "iss": "https://accounts.google.com",
        "sub": "x",
        "email": "x@evil.com",
        "email_verified": True,
        "name": "X",
    }
    with patch("app.core.auth.verify_google_id_token", return_value=claims):
        with pytest.raises(Exception) as exc_info:
            authenticate_request(settings, "Bearer fake")
    # FastAPI HTTPException
    assert exc_info.value.status_code == 403


def test_authenticate_google_upserts_user() -> None:
    settings = Settings(
        auth_dev_bypass=False,
        google_oauth_client_id="client-id",
        admin_emails="admin@gmail.com",
        allowed_email_domains="gmail.com",
        gcp_project_id="p",
    )
    claims = {
        "iss": "https://accounts.google.com",
        "sub": "uid-99",
        "email": "admin@gmail.com",
        "email_verified": True,
        "name": "Admin",
        "picture": None,
    }
    profile = {
        "uid": "uid-99",
        "email": "admin@gmail.com",
        "display_name": "Admin",
        "photo_url": None,
        "role": "admin",
    }
    with (
        patch("app.core.auth.verify_google_id_token", return_value=claims),
        patch("app.core.auth.resolve_or_create_user", return_value=profile) as upsert,
    ):
        ctx = authenticate_request(settings, "Bearer id-token", firestore_client=MagicMock())
    assert ctx.role == "admin"
    assert ctx.email == "admin@gmail.com"
    assert ctx.uid == "uid-99"
    assert ctx.auth_mode == "google_id_token"
    upsert.assert_called_once()


def test_me_dev_bypass() -> None:
    get_settings.cache_clear()
    with patch.dict("os.environ", {"AUTH_DEV_BYPASS": "true"}, clear=False):
        get_settings.cache_clear()
        client = TestClient(app)
        res = client.get("/api/v1/me")
    assert res.status_code == 200
    body = res.json()
    assert body["uid"] == "dev-bypass"
    assert body["email"] == "dev@chandraailabs.com"
    assert body["role"] == "admin"
    assert "name" in body
    assert "picture" in body


def test_me_unauthorized_when_bypass_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "false")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    get_settings.cache_clear()
    client = TestClient(app)
    res = client.get("/api/v1/me")
    assert res.status_code == 401


def test_me_with_mocked_google(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "false")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("ADMIN_EMAILS", "viewer@gmail.com")
    monkeypatch.setenv("ALLOWED_EMAIL_DOMAINS", "gmail.com")
    get_settings.cache_clear()

    claims = {
        "iss": "https://accounts.google.com",
        "sub": "uid-me",
        "email": "viewer@gmail.com",
        "email_verified": True,
        "name": "Viewer User",
        "picture": "https://example.com/p.png",
    }
    profile = {
        "uid": "uid-me",
        "email": "viewer@gmail.com",
        "display_name": "Viewer User",
        "photo_url": "https://example.com/p.png",
        "role": "admin",
    }
    with (
        patch("app.core.auth.verify_google_id_token", return_value=claims),
        patch("app.core.auth.resolve_or_create_user", return_value=profile),
        patch("app.core.auth.firestore.Client", return_value=MagicMock()),
    ):
        client = TestClient(app)
        res = client.get(
            "/api/v1/me",
            headers={"Authorization": "Bearer fake-id-token"},
        )
    assert res.status_code == 200
    assert res.json() == {
        "uid": "uid-me",
        "email": "viewer@gmail.com",
        "name": "Viewer User",
        "picture": "https://example.com/p.png",
        "role": "admin",
    }


def test_search_requires_auth_when_bypass_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "false")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    get_settings.cache_clear()
    client = TestClient(app)
    res = client.post("/api/v1/query/search", json={"query": "hello"})
    assert res.status_code == 401


def test_health_public_when_bypass_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "false")
    get_settings.cache_clear()
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_upload_forbidden_for_viewer_role(monkeypatch: pytest.MonkeyPatch) -> None:
    """content_admin/admin only for upload when real auth path is used."""
    monkeypatch.setenv("AUTH_DEV_BYPASS", "false")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("ALLOWED_EMAIL_DOMAINS", "gmail.com")
    get_settings.cache_clear()

    claims = {
        "iss": "https://accounts.google.com",
        "sub": "uid-v",
        "email": "v@gmail.com",
        "email_verified": True,
        "name": "V",
    }
    profile = {
        "uid": "uid-v",
        "email": "v@gmail.com",
        "display_name": "V",
        "photo_url": None,
        "role": "viewer",
    }
    with (
        patch("app.core.auth.verify_google_id_token", return_value=claims),
        patch("app.core.auth.resolve_or_create_user", return_value=profile),
        patch("app.core.auth.firestore.Client", return_value=MagicMock()),
    ):
        client = TestClient(app)
        from io import BytesIO

        res = client.post(
            "/api/v1/documents/upload",
            files={"file": ("a.md", BytesIO(b"# a"), "text/markdown")},
            headers={"Authorization": "Bearer tok"},
        )
    assert res.status_code == 403
