import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from main import app
from auth import create_access_token

client = TestClient(app)


def test_login_success_local_admin():
    response = client.post("/auth/login", json={
        "email": "admin@scrapescout.com",
        "password": "Admin@123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "admin"
    assert data["user"]["email"] == "admin@scrapescout.com"


def test_login_success_local_viewer():
    response = client.post("/auth/login", json={
        "email": "viewer@scrapescout.com",
        "password": "Viewer@123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "viewer"


def test_login_invalid_password():
    response = client.post("/auth/login", json={
        "email": "admin@scrapescout.com",
        "password": "WrongPassword!99",
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_nonexistent_user():
    response = client.post("/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "SomePassword123!",
    })
    assert response.status_code == 401


def test_register_new_viewer():
    unique_email = f"user_{uuid4().hex[:8]}@example.com"
    response = client.post("/auth/register", json={
        "email": unique_email,
        "password": "Password123!",
        "full_name": "Test Viewer User",
        "role": "viewer",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == unique_email
    assert data["user"]["role"] == "viewer"
    assert "access_token" in data


def test_register_duplicate_email_returns_409():
    response = client.post("/auth/register", json={
        "email": "admin@scrapescout.com",
        "password": "Password123!",
    })
    assert response.status_code == 409


def test_get_my_profile_with_token():
    token = create_access_token({
        "sub": "test-user-id",
        "email": "test@scrapescout.com",
        "role": "viewer",
        "full_name": "Test User",
    })
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@scrapescout.com"
    assert data["role"] == "viewer"
    assert data["full_name"] == "Test User"


def test_get_my_profile_invalid_token():
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
    assert response.status_code == 401


def test_list_users_allowed_for_admin():
    admin_token = create_access_token({
        "sub": "admin-id",
        "email": "admin@scrapescout.com",
        "role": "admin",
    })
    response = client.get("/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert any(u["role"] == "admin" for u in users)


def test_list_users_forbidden_for_viewer():
    viewer_token = create_access_token({
        "sub": "viewer-id",
        "email": "viewer@scrapescout.com",
        "role": "viewer",
    })
    response = client.get("/users", headers={"Authorization": f"Bearer {viewer_token}"})
    assert response.status_code == 403
    assert "Administrator access required" in response.json()["detail"]


def test_delete_project_forbidden_for_viewer():
    viewer_token = create_access_token({
        "sub": "viewer-id",
        "email": "viewer@scrapescout.com",
        "role": "viewer",
    })
    response = client.delete(
        f"/projects/{uuid4()}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
    assert "Administrator access required" in response.json()["detail"]


def test_logout_endpoint():
    token = create_access_token({
        "sub": "user-id",
        "email": "user@scrapescout.com",
        "role": "viewer",
    })
    response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "Successfully logged out" in response.json()["message"]


def test_register_cannot_assign_admin_role():
    unique_email = f"attacker_{uuid4().hex[:8]}@example.com"

    response = client.post("/auth/register", json={
        "email": unique_email,
        "password": "Password123!",
        "full_name": "Test Security User",
        "role": "admin",
    })

    assert response.status_code == 201
    assert response.json()["user"]["role"] == "viewer"


def test_guest_cannot_access_users_endpoint():
    response = client.get("/users")

    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]


def test_guest_cannot_create_system_notification():
    response = client.post(
        "/notifications",
        json={
            "title": "Unauthorized",
            "message": "Guest must not create this.",
            "type": "warning",
        },
    )

    assert response.status_code == 401


def test_production_jwt_requires_explicit_key(monkeypatch):
    from auth import get_jwt_secret, DEFAULT_DEV_SECRET

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="Production environment requires an explicitly"):
        get_jwt_secret()


def test_production_jwt_rejects_default_dev_key(monkeypatch):
    from auth import get_jwt_secret, DEFAULT_DEV_SECRET

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", DEFAULT_DEV_SECRET)

    with pytest.raises(RuntimeError, match="Production environment requires an explicitly"):
        get_jwt_secret()


def test_production_jwt_rejects_short_key(monkeypatch):
    from auth import get_jwt_secret

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "too-short-secret-key-16b")

    with pytest.raises(RuntimeError, match="at least 32 characters long"):
        get_jwt_secret()


def test_production_jwt_accepts_valid_secure_key(monkeypatch):
    from auth import get_jwt_secret

    secure_key = "a-very-secure-production-jwt-key-with-64-characters-entropy-check-1234"
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", secure_key)

    assert get_jwt_secret() == secure_key


def test_login_issued_token_is_consistently_verifiable_by_protected_endpoints():
    """Verify that tokens issued by /auth/login can be verified by protected backend routes."""
    login_res = client.post("/auth/login", json={
        "email": "admin@scrapescout.com",
        "password": "Admin@123",
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Verify token can access /auth/me
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@scrapescout.com"
    assert me_res.json()["role"] == "admin"

    # Verify token can access other protected endpoints
    notifs_res = client.get("/notifications", headers={"Authorization": f"Bearer {token}"})
    assert notifs_res.status_code == 200


def test_supabase_auth_login_issues_consistent_backend_verifiable_token(monkeypatch):
    """
    Verify that even if Supabase Auth returns a foreign/external session token,
    the login endpoint always issues a consistent backend-verifiable JWT.
    """
    from types import SimpleNamespace

    foreign_sb_token = "foreign-supabase-session-token-not-signed-by-backend-secret"

    fake_sb_user = SimpleNamespace(
        id=str(uuid4()),
        user_metadata={"full_name": "Supabase User"},
    )
    fake_session = SimpleNamespace(access_token=foreign_sb_token)
    fake_auth_response = SimpleNamespace(user=fake_sb_user, session=fake_session)

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return fake_auth_response

    class FakeUsersTable:
        def select(self, *args, **kwargs): return self
        def eq(self, *args, **kwargs): return self
        def execute(self):
            return SimpleNamespace(data=[{"role": "viewer", "full_name": "Supabase User"}])

    class FakeSupabase:
        auth = FakeAuth()
        def table(self, name):
            return FakeUsersTable()

    monkeypatch.setattr("main.supabase", FakeSupabase())

    login_res = client.post("/auth/login", json={
        "email": "sb_user@example.com",
        "password": "Password123!",
    })
    assert login_res.status_code == 200
    issued_token = login_res.json()["access_token"]

    # The issued token must NOT be the foreign unverified token
    assert issued_token != foreign_sb_token

    # The issued token MUST be verifiable by protected backend routes
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {issued_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "sb_user@example.com"


def test_supabase_auth_register_issues_consistent_backend_verifiable_token(monkeypatch):
    """
    Verify that Supabase Auth registration always returns a consistent backend-verifiable JWT.
    """
    from types import SimpleNamespace

    foreign_sb_token = "foreign-supabase-signup-token-not-signed-by-backend"

    fake_sb_user = SimpleNamespace(id=str(uuid4()))
    fake_session = SimpleNamespace(access_token=foreign_sb_token)
    fake_auth_response = SimpleNamespace(user=fake_sb_user, session=fake_session)

    class FakeAuth:
        def sign_up(self, params):
            return fake_auth_response

    class FakeTable:
        def insert(self, record): return self
        def execute(self): return SimpleNamespace(data=[])

    class FakeSupabase:
        auth = FakeAuth()
        def table(self, name): return FakeTable()

    monkeypatch.setattr("main.supabase", FakeSupabase())

    unique_email = f"sb_reg_{uuid4().hex[:6]}@example.com"
    reg_res = client.post("/auth/register", json={
        "email": unique_email,
        "password": "Password123!",
        "full_name": "New Supabase Registered",
    })
    assert reg_res.status_code == 201
    issued_token = reg_res.json()["access_token"]

    # Must NOT be foreign token
    assert issued_token != foreign_sb_token

    # Must be verifiable by protected endpoints
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {issued_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == unique_email
