from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import User


def test_unknown_user_and_wrong_password_return_the_same_generic_error(
    client: TestClient,
) -> None:
    unknown = client.post(
        "/api/v1/auth/token",
        json={"email": "does-not-exist@example.com", "password": "not-the-password"},
    )
    wrong = client.post(
        "/api/v1/auth/token",
        json={"email": "admin@example.com", "password": "not-the-password"},
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": "Invalid credentials"}


def test_five_failures_lock_the_account_until_the_lock_is_cleared(client: TestClient) -> None:
    email = "preparer@example.com"
    try:
        responses = [
            client.post(
                "/api/v1/auth/token",
                json={"email": email, "password": "definitely-wrong"},
            )
            for _ in range(5)
        ]
        assert all(response.status_code == 401 for response in responses)

        locked = client.post(
            "/api/v1/auth/token",
            json={"email": email, "password": "CTec-Demo-Prepare-2026!"},
        )
        assert locked.status_code == 423
        assert locked.json()["detail"] == "Account is temporarily locked"

        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            assert user is not None
            assert user.failed_attempts == 0
            assert user.locked_until is not None and user.locked_until > datetime.now(UTC)
    finally:
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            assert user is not None
            user.failed_attempts = 0
            user.locked_until = None
            db.commit()


def test_disabled_user_cannot_log_in_or_continue_using_an_existing_token(
    client: TestClient,
    preparer_token: str,
) -> None:
    email = "preparer@example.com"
    try:
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            assert user is not None
            user.active = False
            db.commit()

        login = client.post(
            "/api/v1/auth/token",
            json={"email": email, "password": "CTec-Demo-Prepare-2026!"},
        )
        assert login.status_code == 401
        assert login.json()["detail"] == "Invalid credentials"

        existing_session = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {preparer_token}"}
        )
        assert existing_session.status_code == 401
        assert existing_session.json()["detail"] == "Account is inactive"
    finally:
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            assert user is not None
            user.active = True
            db.commit()


def test_expired_malformed_and_wrong_type_tokens_are_rejected(client: TestClient) -> None:
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "type": "access",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    wrong_type = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "type": "refresh",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    for token in (expired, wrong_type, "not-a-jwt"):
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired token"
