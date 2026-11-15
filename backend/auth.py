
import os
import uuid
import hmac
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status

logger = logging.getLogger("scrapescout.auth")

DEFAULT_DEV_SECRET = "scrapescout-development-secret-key-32bytes-min"
JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_HOURS = 24


def get_environment() -> str:
    """Return the normalized application environment."""
    return os.getenv(
        "ENVIRONMENT",
        os.getenv("APP_ENV", "development"),
    ).strip().lower()


def is_production() -> bool:
    """Return True when running in a production environment."""
    return get_environment() in ("production", "prod")


def local_auth_enabled() -> bool:
    """Allow in-memory demo accounts only outside production."""
    return not is_production()


def get_jwt_secret() -> str:
    """
    Retrieve and validate the JWT signing secret.

    Production requires an explicitly configured secret of at least
    32 characters. The development fallback is never allowed in production.
    """
    secret = (
        os.getenv("JWT_SECRET_KEY")
        or os.getenv("SUPABASE_JWT_SECRET")
    )

    if is_production():
        if not secret or secret == DEFAULT_DEV_SECRET:
            raise RuntimeError(
                "Insecure configuration: Production environment requires "
                "an explicitly configured JWT_SECRET_KEY or "
                "SUPABASE_JWT_SECRET."
            )

        if len(secret) < 32:
            raise RuntimeError(
                "Insecure configuration: Production JWT secret "
                "must be at least 32 characters long."
            )

        return secret

    return secret or DEFAULT_DEV_SECRET


# Retained for compatibility with existing imports.
# Token creation and validation always call get_jwt_secret().
JWT_SECRET_KEY = (
    os.getenv("JWT_SECRET_KEY")
    or os.getenv("SUPABASE_JWT_SECRET")
    or DEFAULT_DEV_SECRET
)


@dataclass
class CurrentUser:
    id: str
    email: str
    role: str = "viewer"
    full_name: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = os.urandom(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100_000,
    )

    return f"{salt.hex()}${password_hash.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its stored hash."""
    try:
        salt_hex, hash_hex = hashed_password.split("$")

        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            100_000,
        )

        return hmac.compare_digest(expected_hash, actual_hash)

    except (ValueError, TypeError):
        return False


# ============================================================
# LOCAL DEVELOPMENT USERS
# ============================================================

_local_users = {
    "admin@scrapescout.com": {
        "id": "a0000000-0000-0000-0000-000000000001",
        "email": "admin@scrapescout.com",
        "password_hash": hash_password(
            "Admin@123",
            salt=b"scrapescout_salt",
        ),
        "role": "admin",
        "full_name": "System Administrator",
    },
    "viewer@scrapescout.com": {
        "id": "a0000000-0000-0000-0000-000000000002",
        "email": "viewer@scrapescout.com",
        "password_hash": hash_password(
            "Viewer@123",
            salt=b"scrapescout_salt",
        ),
        "role": "viewer",
        "full_name": "Project Viewer",
    },
}


def get_local_user(email: str) -> Optional[dict]:
    """
    Retrieve a local development account.

    Local accounts are deliberately unavailable in production.
    """
    if not local_auth_enabled():
        return None

    return _local_users.get(email.strip().lower())


def add_local_user(
    email: str,
    password: str,
    role: str = "viewer",
    full_name: Optional[str] = None,
) -> dict:
    """Create a local account outside production."""
    if not local_auth_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local account registration is disabled in production.",
        )

    if role not in ("admin", "viewer"):
        raise ValueError("Invalid user role.")

    email_clean = email.strip().lower()

    if email_clean in _local_users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    user_record = {
        "id": str(uuid.uuid4()),
        "email": email_clean,
        "password_hash": hash_password(password),
        "role": role,
        "full_name": full_name or email_clean.split("@")[0].title(),
    }

    _local_users[email_clean] = user_record

    return user_record


# ============================================================
# JWT TOKEN MANAGEMENT
# ============================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed backend JWT access token."""
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        or timedelta(hours=DEFAULT_ACCESS_TOKEN_EXPIRE_HOURS)
    )

    to_encode.update({
        "exp": expire,
        "iat": now,
    })

    return jwt.encode(
        to_encode,
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a backend or supported Supabase JWT."""
    secrets_to_try = [get_jwt_secret()]

    supabase_secret = os.getenv("SUPABASE_JWT_SECRET")

    if (
        supabase_secret
        and supabase_secret not in secrets_to_try
    ):
        secrets_to_try.append(supabase_secret)

    for index, secret in enumerate(secrets_to_try):
        try:
            return jwt.decode(
                token,
                secret,
                algorithms=[JWT_ALGORITHM],
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except jwt.PyJWTError:
            if index == len(secrets_to_try) - 1:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ============================================================
# FASTAPI SECURITY DEPENDENCIES
# ============================================================

def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> CurrentUser:
    """
    Extract and validate the authenticated user.

    Authentication is mandatory in production, even if AUTH_REQUIRED
    has accidentally been omitted from the deployment configuration.
    """
    auth_required = (
        is_production()
        or os.getenv("AUTH_REQUIRED", "false").strip().lower() == "true"
    )

    if not authorization:
        if auth_required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return CurrentUser(
            id="00000000-0000-0000-0000-000000000000",
            email="guest@scrapescout.local",
            role="viewer",
            full_name="Guest User",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Must be Bearer <token>.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)

    user_id = (
        payload.get("sub")
        or payload.get("id")
        or str(payload.get("user_id", ""))
    )

    email = payload.get("email", "")
    role = payload.get("role", "viewer")

    metadata = payload.get("user_metadata") or {}
    full_name = payload.get("full_name") or metadata.get("full_name")

    if (
        not user_id
        or not isinstance(email, str)
        or not email.strip()
        or role not in ("admin", "viewer")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        id=str(user_id),
        email=email,
        role=role,
        full_name=full_name,
    )


def require_authenticated(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Require a non-guest authenticated user."""
    if current_user.email == "guest@scrapescout.local":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for this operation.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return current_user


def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Require an authenticated administrator."""
    if current_user.email == "guest@scrapescout.local":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for administrator access.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )

    return current_user
