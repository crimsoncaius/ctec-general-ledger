import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import delete, or_, select

from app.config import get_settings
from app.deps import AccessContext, DbSession, require
from app.models import (
    AuditEvent,
    Company,
    Membership,
    OperationJob,
    Permission,
    Role,
    RolePermission,
    SavedView,
    User,
    UserPreference,
)
from app.schemas import (
    AdminUserCreate,
    CompanySettingsOut,
    CompanySettingsUpdate,
    MembershipOut,
    MembershipUpdate,
    OperationOut,
    OperationRequest,
    PermissionOut,
    PreferenceOut,
    PreferenceUpsert,
    RoleCreate,
    RoleOut,
    RolePermissionsUpdate,
    SavedViewCreate,
    SavedViewOut,
)
from app.security import hash_password
from app.services.audit import record_audit
from app.services.operations import run_operation

router = APIRouter(prefix="/administration", tags=["administration"])


@router.get("/company", response_model=CompanySettingsOut)
def company_settings(
    db: DbSession,
    context: AccessContext = Depends(require("company.manage")),
) -> Company:
    company = db.get(Company, context.company_id)
    if company is None:
        raise HTTPException(404, "Company not found")
    return company


@router.put("/company", response_model=CompanySettingsOut)
def update_company_settings(
    payload: CompanySettingsUpdate,
    db: DbSession,
    context: AccessContext = Depends(require("company.manage")),
) -> Company:
    company = db.get(Company, context.company_id)
    if company is None:
        raise HTTPException(404, "Company not found")
    try:
        ZoneInfo(payload.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(422, "Unknown IANA timezone") from exc
    before = {
        "name": company.name,
        "timezone": company.timezone,
        "rounding_places": company.rounding_places,
        "use_bankers_rounding": company.use_bankers_rounding,
    }
    company.name = payload.name
    company.timezone = payload.timezone
    company.rounding_places = payload.rounding_places
    company.use_bankers_rounding = payload.use_bankers_rounding
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="administration.company_updated",
        entity_type="company",
        entity_id=str(company.id),
        before=before,
        after=payload.model_dump(),
    )
    db.commit()
    return company


@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions(
    db: DbSession,
    context: AccessContext = Depends(require("users.manage")),
) -> list[Permission]:
    return list(db.scalars(select(Permission).order_by(Permission.code)).all())


@router.get("/users", response_model=list[MembershipOut])
def list_users(
    db: DbSession,
    context: AccessContext = Depends(require("users.manage")),
) -> list[MembershipOut]:
    rows = db.execute(
        select(Membership, User, Role)
        .join(User, User.id == Membership.user_id)
        .join(Role, (Role.id == Membership.role_id) & (Role.company_id == Membership.company_id))
        .where(Membership.company_id == context.company_id)
        .order_by(User.display_name)
    ).all()
    return [
        MembershipOut(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            role_id=role.id,
            role_name=role.name,
            active=membership.active,
        )
        for membership, user, role in rows
    ]


@router.post("/users", response_model=MembershipOut, status_code=201)
def add_user(
    payload: AdminUserCreate,
    db: DbSession,
    context: AccessContext = Depends(require("users.manage")),
) -> MembershipOut:
    role = db.scalar(
        select(Role).where(Role.company_id == context.company_id, Role.id == payload.role_id)
    )
    if role is None:
        raise HTTPException(422, "Role must belong to this company")
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        user = User(
            email=payload.email.lower(),
            display_name=payload.display_name,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        db.flush()
    existing = db.get(Membership, (context.company_id, user.id))
    if existing is not None:
        raise HTTPException(409, "User already has a membership in this company")
    membership = Membership(company_id=context.company_id, user_id=user.id, role_id=role.id)
    db.add(membership)
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="administration.user_added",
        entity_type="membership",
        entity_id=str(user.id),
        after={"email": user.email, "role": role.name},
    )
    db.commit()
    return MembershipOut(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role_id=role.id,
        role_name=role.name,
        active=True,
    )


@router.put("/users/{user_id}", response_model=MembershipOut)
def update_membership(
    user_id: uuid.UUID,
    payload: MembershipUpdate,
    db: DbSession,
    context: AccessContext = Depends(require("users.manage")),
) -> MembershipOut:
    membership = db.get(Membership, (context.company_id, user_id))
    role = db.scalar(
        select(Role).where(Role.company_id == context.company_id, Role.id == payload.role_id)
    )
    user = db.get(User, user_id)
    if membership is None or role is None or user is None:
        raise HTTPException(404, "Membership or role not found")
    if user.id == context.user.id and not payload.active:
        raise HTTPException(409, "You cannot deactivate your current company membership")
    before = {"role_id": str(membership.role_id), "active": membership.active}
    membership.role_id = role.id
    membership.active = payload.active
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="administration.membership_updated",
        entity_type="membership",
        entity_id=str(user.id),
        before=before,
        after={"role_id": str(role.id), "active": membership.active},
    )
    db.commit()
    return MembershipOut(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role_id=role.id,
        role_name=role.name,
        active=membership.active,
    )


@router.get("/roles", response_model=list[RoleOut])
def list_roles(
    db: DbSession, context: AccessContext = Depends(require("users.manage"))
) -> list[Role]:
    return list(
        db.scalars(
            select(Role).where(Role.company_id == context.company_id).order_by(Role.name)
        ).all()
    )


@router.get("/roles/{role_id}/permissions")
def role_permissions(
    role_id: uuid.UUID,
    db: DbSession,
    context: AccessContext = Depends(require("users.manage")),
) -> dict[str, object]:
    role = db.scalar(select(Role).where(Role.company_id == context.company_id, Role.id == role_id))
    if role is None:
        raise HTTPException(404, "Role not found")
    permissions = list(
        db.scalars(
            select(RolePermission.permission_code)
            .where(
                RolePermission.company_id == context.company_id,
                RolePermission.role_id == role.id,
            )
            .order_by(RolePermission.permission_code)
        ).all()
    )
    return {"role_id": role.id, "permissions": permissions}


def _validate_permissions(db: DbSession, values: list[str]) -> set[str]:
    requested = set(values)
    existing = set(db.scalars(select(Permission.code).where(Permission.code.in_(requested))).all())
    missing = requested - existing
    if missing:
        raise HTTPException(422, f"Unknown permissions: {', '.join(sorted(missing))}")
    return requested


@router.post("/roles", response_model=RoleOut, status_code=201)
def add_role(
    payload: RoleCreate,
    db: DbSession,
    context: AccessContext = Depends(require("users.manage")),
) -> Role:
    permissions = _validate_permissions(db, payload.permissions)
    role = Role(company_id=context.company_id, name=payload.name)
    db.add(role)
    db.flush()
    db.add_all(
        RolePermission(company_id=context.company_id, role_id=role.id, permission_code=code)
        for code in permissions
    )
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="administration.role_created",
        entity_type="role",
        entity_id=str(role.id),
        after={"name": role.name, "permissions": sorted(permissions)},
    )
    db.commit()
    return role


@router.put("/roles/{role_id}/permissions")
def update_role_permissions(
    role_id: uuid.UUID,
    payload: RolePermissionsUpdate,
    db: DbSession,
    context: AccessContext = Depends(require("users.manage")),
) -> dict[str, object]:
    role = db.scalar(select(Role).where(Role.company_id == context.company_id, Role.id == role_id))
    if role is None:
        raise HTTPException(404, "Role not found")
    permissions = _validate_permissions(db, payload.permissions)
    db.execute(
        delete(RolePermission).where(
            RolePermission.company_id == context.company_id, RolePermission.role_id == role.id
        )
    )
    db.add_all(
        RolePermission(company_id=context.company_id, role_id=role.id, permission_code=code)
        for code in permissions
    )
    record_audit(
        db,
        company_id=context.company_id,
        actor_id=context.user.id,
        action="administration.role_permissions_updated",
        entity_type="role",
        entity_id=str(role.id),
        after={"permissions": sorted(permissions)},
    )
    db.commit()
    return {"role_id": role.id, "permissions": sorted(permissions)}


@router.get("/saved-views", response_model=list[SavedViewOut])
def saved_views(
    db: DbSession,
    resource: str | None = None,
    context: AccessContext = Depends(require("preferences.manage")),
) -> list[SavedView]:
    statement = select(SavedView).where(
        SavedView.company_id == context.company_id,
        or_(SavedView.user_id == context.user.id, SavedView.shared.is_(True)),
    )
    if resource:
        statement = statement.where(SavedView.resource == resource)
    return list(db.scalars(statement.order_by(SavedView.resource, SavedView.name)).all())


@router.post("/saved-views", response_model=SavedViewOut, status_code=201)
def save_view(
    payload: SavedViewCreate,
    db: DbSession,
    context: AccessContext = Depends(require("preferences.manage")),
) -> SavedView:
    view = SavedView(company_id=context.company_id, user_id=context.user.id, **payload.model_dump())
    db.add(view)
    db.commit()
    return view


@router.get("/preferences", response_model=list[PreferenceOut])
def preferences(
    db: DbSession,
    context: AccessContext = Depends(require("preferences.manage")),
) -> list[UserPreference]:
    return list(
        db.scalars(
            select(UserPreference).where(
                UserPreference.company_id == context.company_id,
                UserPreference.user_id == context.user.id,
            )
        ).all()
    )


@router.put("/preferences/{key}", response_model=PreferenceOut)
def set_preference(
    key: str,
    payload: PreferenceUpsert,
    db: DbSession,
    context: AccessContext = Depends(require("preferences.manage")),
) -> UserPreference:
    if not key or len(key) > 80:
        raise HTTPException(422, "Invalid preference key")
    preference = db.get(UserPreference, (context.company_id, context.user.id, key))
    if preference is None:
        preference = UserPreference(
            company_id=context.company_id,
            user_id=context.user.id,
            key=key,
            value=payload.value,
        )
        db.add(preference)
    else:
        preference.value = payload.value
    db.commit()
    return preference


@router.get("/audit")
def audit_history(
    db: DbSession,
    limit: int = 100,
    context: AccessContext = Depends(require("audit.view")),
) -> list[dict[str, object]]:
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.company_id == context.company_id)
        .order_by(AuditEvent.occurred_at.desc())
        .limit(min(max(limit, 1), 500))
    ).all()
    return [
        {
            "id": event.id,
            "occurred_at": event.occurred_at,
            "actor_id": event.actor_id,
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "before": event.before,
            "after": event.after,
            "metadata": event.metadata_json,
            "correlation_id": event.correlation_id,
        }
        for event in events
    ]


@router.post("/operations", response_model=OperationOut, status_code=202)
def start_operation(
    payload: OperationRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
    context: AccessContext = Depends(require("administration.organize")),
) -> OperationJob:
    job = OperationJob(
        company_id=context.company_id,
        kind=payload.kind,
        requested_by_id=context.user.id,
        parameters=payload.parameters,
    )
    db.add(job)
    db.commit()
    if get_settings().inline_operation_jobs:
        background_tasks.add_task(run_operation, job.id)
    return job


@router.get("/operations", response_model=list[OperationOut])
def list_operations(
    db: DbSession,
    context: AccessContext = Depends(require("audit.view")),
) -> list[OperationJob]:
    return list(
        db.scalars(
            select(OperationJob)
            .where(OperationJob.company_id == context.company_id)
            .order_by(OperationJob.created_at.desc())
            .limit(200)
        ).all()
    )
