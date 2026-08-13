from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Company, Membership, Permission, Role, RolePermission, User
from app.schemas import CompanyAccessOut, MeOut, TokenRequest, TokenResponse
from app.security import create_access_token, verify_password
from app.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/token", response_model=TokenResponse)
def login(payload: TokenRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    now = datetime.now(UTC)
    if user is None or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if user.locked_until is not None and user.locked_until > now:
        raise HTTPException(status.HTTP_423_LOCKED, "Account is temporarily locked")
    if not verify_password(payload.password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
            user.failed_attempts = 0
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    record_audit(
        db,
        company_id=None,
        actor_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=str(user.id),
    )
    db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser, db: DbSession) -> MeOut:
    rows = db.execute(
        select(Membership, Role, Company)
        .join(Role, (Role.id == Membership.role_id) & (Role.company_id == Membership.company_id))
        .join(Company, Company.id == Membership.company_id)
        .where(Membership.user_id == user.id, Membership.active.is_(True), Company.active.is_(True))
        .order_by(Company.name)
    ).all()
    companies: list[CompanyAccessOut] = []
    for _membership, role, company in rows:
        capabilities = list(
            db.scalars(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_code == Permission.code)
                .where(
                    RolePermission.company_id == company.id,
                    RolePermission.role_id == role.id,
                )
                .order_by(Permission.code)
            ).all()
        )
        companies.append(
            CompanyAccessOut(
                id=company.id,
                code=company.code,
                name=company.name,
                base_currency_code=company.base_currency_code,
                role=role.name,
                capabilities=capabilities,
            )
        )
    return MeOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        companies=companies,
    )
