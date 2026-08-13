import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Membership, Permission, Role, RolePermission, User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


@dataclass(frozen=True)
class AccessContext:
    user: User
    company_id: uuid.UUID
    role: Role
    capabilities: frozenset[str]


def current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    try:
        user_id = uuid.UUID(decode_access_token(credentials.credentials))
    except (ValueError, jwt.PyJWTError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc
    user = db.get(User, user_id)
    if user is None or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is inactive")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def access_context(
    db: DbSession,
    user: CurrentUser,
    x_company_id: Annotated[str | None, Header()] = None,
) -> AccessContext:
    if not x_company_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "X-Company-ID header is required")
    try:
        company_id = uuid.UUID(x_company_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid company identifier") from exc
    row = db.execute(
        select(Membership, Role)
        .join(Role, (Role.id == Membership.role_id) & (Role.company_id == Membership.company_id))
        .where(
            Membership.company_id == company_id,
            Membership.user_id == user.id,
            Membership.active.is_(True),
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this company")
    membership, role = row
    capabilities = frozenset(
        db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_code == Permission.code)
            .where(
                RolePermission.company_id == company_id,
                RolePermission.role_id == membership.role_id,
            )
        ).all()
    )
    return AccessContext(user=user, company_id=company_id, role=role, capabilities=capabilities)


Access = Annotated[AccessContext, Depends(access_context)]


def require(capability: str):  # type: ignore[no-untyped-def]
    def dependency(context: Access) -> AccessContext:
        if capability not in context.capabilities:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Capability required: {capability}")
        return context

    return dependency
