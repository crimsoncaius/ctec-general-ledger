import os
import secrets

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import hash_password
from app.seed import seed


def main() -> None:
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com").strip().lower()
    display_name = os.environ.get(
        "BOOTSTRAP_ADMIN_DISPLAY_NAME", "Production Administrator"
    ).strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not password:
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD is required")

    seed(
        admin_email=email,
        admin_password=password,
        admin_display_name=display_name,
        disable_non_admin=True,
    )

    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == email))
        if admin is None:
            raise RuntimeError(f"Administrator user {email!r} was not found after seeding")
        admin.display_name = display_name
        admin.password_hash = hash_password(password)
        admin.active = True
        admin.failed_attempts = 0
        admin.locked_until = None

        disabled = 0
        for user in db.scalars(select(User).where(User.id != admin.id)).all():
            user.active = False
            user.password_hash = hash_password(secrets.token_urlsafe(32))
            disabled += 1
        db.commit()

    print(f"Bootstrapped administrator {email}; disabled {disabled} other users")


if __name__ == "__main__":
    main()
