
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from route_security import ProductionAuthMiddleware
from main import app as scrapescout_app


def test_validator_rejects_missing_authentication(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AUTH_REQUIRED", "true")

    def validator(authorization):
        if not authorization:
            raise HTTPException(status_code=401, detail="Authentication required.")

    app = FastAPI()
    app.add_middleware(ProductionAuthMiddleware, auth_validator=validator)

    @app.get("/private")
    def private_route():
        return {"message": "private"}

    response = TestClient(app).get("/private")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_validated_request_reaches_protected_route(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AUTH_REQUIRED", "true")

    def validator(authorization):
        if authorization != "Bearer valid-test-token":
            raise HTTPException(status_code=401, detail="Authentication required.")

    app = FastAPI()
    app.add_middleware(ProductionAuthMiddleware, auth_validator=validator)

    @app.get("/private")
    def private_route():
        return {"message": "private"}

    response = TestClient(app).get(
        "/private",
        headers={"Authorization": "Bearer valid-test-token"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "private"}


def test_public_routes_remain_accessible(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_REQUIRED", "true")

    def validator(authorization):
        raise HTTPException(status_code=401, detail="Authentication required.")

    app = FastAPI()
    app.add_middleware(ProductionAuthMiddleware, auth_validator=validator)

    @app.get("/")
    def home():
        return {"message": "public"}

    @app.post("/auth/login")
    def login():
        return {"message": "login"}

    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.post("/auth/login").status_code == 200


def test_authentication_can_be_disabled_in_development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AUTH_REQUIRED", "false")

    def validator(authorization):
        raise HTTPException(status_code=401, detail="Authentication required.")

    app = FastAPI()
    app.add_middleware(ProductionAuthMiddleware, auth_validator=validator)

    @app.get("/private")
    def private_route():
        return {"message": "private"}

    response = TestClient(app).get("/private")
    assert response.status_code == 200


def test_cors_preflight_is_not_blocked_by_authentication(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_REQUIRED", "true")

    def validator(authorization):
        raise HTTPException(status_code=401, detail="Authentication required.")

    app = FastAPI()
    app.add_middleware(ProductionAuthMiddleware, auth_validator=validator)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/private")
    def private_route():
        return {"message": "private"}

    response = TestClient(app).options(
        "/private",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_real_application_requires_authentication_when_enabled(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AUTH_REQUIRED", "true")

    client = TestClient(scrapescout_app)

    # The real application's public home route must remain accessible.
    home_response = client.get("/")
    assert home_response.status_code == 200

    # The real application's protected profile route must reject missing tokens.
    profile_response = client.get("/auth/me")
    assert profile_response.status_code == 401
    assert profile_response.json()["detail"] == "Authentication required."
