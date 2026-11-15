import os

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request


PUBLIC_PATHS = {
    "/",
    "/test-db",
    "/auth/login",
    "/auth/register",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/docs/oauth2-redirect",
}


def authentication_is_required() -> bool:
    """Require authentication in production or when explicitly enabled."""
    environment = (
        os.getenv("ENVIRONMENT")
        or os.getenv("APP_ENV")
        or "development"
    ).strip().lower()

    return (
        environment in {"production", "prod"}
        or os.getenv("AUTH_REQUIRED", "false").strip().lower() == "true"
    )


class ProductionAuthMiddleware:
    """
    Protect application API routes when authentication is enabled.

    Public routes remain accessible. Existing route-level dependencies
    continue to enforce administrator permissions.
    """

    def __init__(self, app, auth_validator):
        self.app = app
        self.auth_validator = auth_validator

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)

        if request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        path = request.url.path.rstrip("/") or "/"

        if path in PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        if not authentication_is_required():
            await self.app(scope, receive, send)
            return

        try:
            self.auth_validator(
                request.headers.get("authorization")
            )
        except HTTPException as exc:
            response = JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
