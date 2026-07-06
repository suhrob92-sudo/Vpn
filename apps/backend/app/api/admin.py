"""Admin API: auth (JWT access+refresh with rotation), dashboard, CRUD."""
import logging
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.config import get_settings
from app.core.crypto import encrypt_secret
from app.core.db import get_db
from app.core.ratelimit import rate_limit
from app.core.redis import get_redis
from app.core.security import create_token, decode_token, verify_password
from app.models import (
    AccessStatus,
    AdminUser,
    Payment,
    PaymentStatus,
    Plan,
    ServerStatus,
    Subscription,
    SubscriptionStatus,
    User,
    VpnAccess,
    VpnServer,
)
from app.schemas.admin import AdminLoginIn, AdminRefreshIn, AdminUserPatch
from app.schemas.billing import PaymentOut, PlanCreate, PlanOut, PlanPatch, SubscriptionOut
from app.schemas.common import ok
from app.schemas.user import UserOut
from app.schemas.vpn import ServerAdminOut, ServerCreate, ServerPatch
from app.services.vpn_manager import revoke_access
from app.services.vpn_manager.manager import panel_client
from app.services.vpn_manager.xui_client import XuiError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

_REFRESH_KEY = "admin:refresh:"


async def _store_refresh(jti: str, admin_id: int, ttl: int) -> None:
    await get_redis().set(f"{_REFRESH_KEY}{jti}", str(admin_id), ex=ttl)


async def _consume_refresh(jti: str) -> bool:
    """Single-use refresh tokens: delete on use; reuse -> rejected."""
    return bool(await get_redis().delete(f"{_REFRESH_KEY}{jti}"))


def _issue_tokens(admin: AdminUser) -> dict:
    settings = get_settings()
    access = create_token(str(admin.id), "admin_access", settings.admin_access_ttl)
    refresh = create_token(str(admin.id), "admin_refresh", settings.admin_refresh_ttl)
    return {"access_token": access, "refresh_token": refresh}


# ── Auth ────────────────────────────────────────────────────────────────────

@router.post("/auth/login", dependencies=[Depends(rate_limit("admin-login", limit=10))])
async def admin_login(body: AdminLoginIn, db: AsyncSession = Depends(get_db)):
    admin = await db.scalar(select(AdminUser).where(AdminUser.username == body.username))
    if admin is None or not verify_password(body.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if admin.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    tokens = _issue_tokens(admin)
    payload = decode_token(tokens["refresh_token"], "admin_refresh")
    await _store_refresh(payload["jti"], admin.id, get_settings().admin_refresh_ttl)
    return ok(tokens)


@router.post("/auth/refresh")
async def admin_refresh(body: AdminRefreshIn, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token, "admin_refresh")
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if not await _consume_refresh(payload["jti"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reused or revoked"
        )
    admin = await db.get(AdminUser, int(payload["sub"]))
    if admin is None or admin.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    tokens = _issue_tokens(admin)
    new_payload = decode_token(tokens["refresh_token"], "admin_refresh")
    await _store_refresh(new_payload["jti"], admin.id, get_settings().admin_refresh_ttl)
    return ok(tokens)


# ── Dashboard ───────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(
    _: AdminUser = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    month_ago = now - timedelta(days=30)

    total_users = await db.scalar(select(func.count(User.id)))
    new_users_24h = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= day_ago)
    )
    active_subs = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.expires_at > now,
        )
    )
    expired_subs = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.status == SubscriptionStatus.EXPIRED.value
        )
    )
    revenue_day = await db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.SUCCESS.value, Payment.paid_at >= day_ago
        )
    )
    revenue_month = await db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.SUCCESS.value, Payment.paid_at >= month_ago
        )
    )
    servers = (await db.scalars(select(VpnServer))).all()
    return ok(
        {
            "total_users": total_users,
            "new_users_24h": new_users_24h,
            "active_subscriptions": active_subs,
            "expired_subscriptions": expired_subs,
            "revenue_24h": str(revenue_day),
            "revenue_30d": str(revenue_month),
            "servers": [
                {"id": s.id, "name": s.name, "country": s.country, "status": s.status}
                for s in servers
            ],
        }
    )


# ── Users ───────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).order_by(User.id.desc()).limit(limit).offset(offset)
    if q:
        like = f"%{q}%"
        cond = [User.username.ilike(like), User.first_name.ilike(like)]
        if q.isdigit():
            cond.append(User.telegram_id == int(q))
        stmt = stmt.where(or_(*cond))
    if status_filter:
        stmt = stmt.where(User.status == status_filter)
    users = (await db.scalars(stmt)).all()
    return ok([UserOut.model_validate(u).model_dump(mode="json") for u in users])


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    subs = (
        await db.scalars(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.id.desc())
        )
    ).all()
    payments = (
        await db.scalars(
            select(Payment).where(Payment.user_id == user_id).order_by(Payment.id.desc())
        )
    ).all()
    return ok(
        {
            "user": UserOut.model_validate(user).model_dump(mode="json"),
            "subscriptions": [
                SubscriptionOut.model_validate(s).model_dump(mode="json") for s in subs
            ],
            "payments": [PaymentOut.model_validate(p).model_dump(mode="json") for p in payments],
        }
    )


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: int,
    body: AdminUserPatch,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.status is not None:
        if body.status not in ("ACTIVE", "SUSPENDED"):
            raise HTTPException(status_code=400, detail="status must be ACTIVE or SUSPENDED")
        user.status = body.status
        if body.status == "SUSPENDED":
            await _revoke_user_accesses(db, user_id)

    if body.bonus_days:
        sub = await db.scalar(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE.value,
            )
        )
        if sub is None:
            raise HTTPException(status_code=409, detail="User has no active subscription")
        sub.expires_at = sub.expires_at + timedelta(days=body.bonus_days)
        sub.reminder_sent_at = None

    await db.commit()
    return ok(UserOut.model_validate(user).model_dump(mode="json"))


async def _revoke_user_accesses(db: AsyncSession, user_id: int) -> None:
    rows = (
        await db.execute(
            select(VpnAccess, VpnServer)
            .join(VpnServer, VpnAccess.server_id == VpnServer.id)
            .where(
                VpnAccess.user_id == user_id,
                VpnAccess.status == AccessStatus.ACTIVE.value,
            )
        )
    ).all()
    for access, server in rows:
        await revoke_access(db, access, server)


@router.post("/users/{user_id}/revoke-access")
async def revoke_user_access(
    user_id: int,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await _revoke_user_accesses(db, user_id)
    await db.commit()
    return ok({"revoked": True})


# ── Subscriptions / payments ────────────────────────────────────────────────

@router.get("/subscriptions")
async def list_subscriptions(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Subscription).order_by(Subscription.id.desc()).limit(limit).offset(offset)
    if status_filter:
        stmt = stmt.where(Subscription.status == status_filter)
    subs = (await db.scalars(stmt)).all()
    return ok(
        [
            {
                **SubscriptionOut.model_validate(s).model_dump(mode="json"),
                "user_id": s.user_id,
            }
            for s in subs
        ]
    )


@router.get("/payments")
async def list_payments(
    status_filter: str | None = Query(default=None, alias="status"),
    provider: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Payment).order_by(Payment.id.desc()).limit(limit).offset(offset)
    if status_filter:
        stmt = stmt.where(Payment.status == status_filter)
    if provider:
        stmt = stmt.where(Payment.provider == provider)
    payments = (await db.scalars(stmt)).all()
    return ok(
        [
            {
                **PaymentOut.model_validate(p).model_dump(mode="json"),
                "user_id": p.user_id,
                "provider_payment_id": p.provider_payment_id,
            }
            for p in payments
        ]
    )


# ── Servers ─────────────────────────────────────────────────────────────────

@router.get("/servers")
async def list_servers_admin(
    _: AdminUser = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    servers = (await db.scalars(select(VpnServer).order_by(VpnServer.id))).all()
    return ok([ServerAdminOut.model_validate(s).model_dump(mode="json") for s in servers])


@router.post("/servers")
async def create_server(
    body: ServerCreate,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    server = VpnServer(
        name=body.name,
        country=body.country,
        city=body.city,
        panel_url=body.panel_url.rstrip("/"),
        panel_user=body.panel_user,
        panel_pass_encrypted=encrypt_secret(body.panel_pass),
        inbound_id=body.inbound_id,
        host=body.host,
        port=body.port,
        public_key=body.public_key,
        short_id=body.short_id,
        sni=body.sni,
        status=body.status,
    )
    db.add(server)
    await db.commit()
    return ok(ServerAdminOut.model_validate(server).model_dump(mode="json"))


@router.patch("/servers/{server_id}")
async def patch_server(
    server_id: int,
    body: ServerPatch,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    server = await db.get(VpnServer, server_id)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    data = body.model_dump(exclude_unset=True)
    if "panel_pass" in data:
        server.panel_pass_encrypted = encrypt_secret(data.pop("panel_pass"))
    if "status" in data and data["status"] not in [s.value for s in ServerStatus]:
        raise HTTPException(status_code=400, detail="Invalid status")
    for field, value in data.items():
        setattr(server, field, value)
    await db.commit()
    return ok(ServerAdminOut.model_validate(server).model_dump(mode="json"))


@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: int,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    server = await db.get(VpnServer, server_id)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    in_use = await db.scalar(
        select(func.count(VpnAccess.id)).where(
            VpnAccess.server_id == server_id,
            VpnAccess.status == AccessStatus.ACTIVE.value,
        )
    )
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"Server has {in_use} active accesses — set MAINTENANCE and migrate first",
        )
    await db.delete(server)
    await db.commit()
    return ok({"deleted": True})


@router.post("/servers/{server_id}/check")
async def check_server(
    server_id: int,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Live health check: log in to the panel and read the inbound."""
    server = await db.get(VpnServer, server_id)
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    try:
        client = panel_client(server)
        await client.login()
        inbound = await client.get_inbound(server.inbound_id)
        return ok({"reachable": True, "inbound_remark": (inbound or {}).get("remark")})
    except XuiError as exc:
        return ok({"reachable": False, "error": str(exc)})


# ── Plans ───────────────────────────────────────────────────────────────────

@router.get("/plans")
async def list_plans_admin(
    _: AdminUser = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    plans = (await db.scalars(select(Plan).order_by(Plan.sort_order, Plan.id))).all()
    return ok([PlanOut.model_validate(p).model_dump(mode="json") for p in plans])


@router.post("/plans")
async def create_plan(
    body: PlanCreate,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    plan = Plan(**body.model_dump())
    db.add(plan)
    await db.commit()
    return ok(PlanOut.model_validate(plan).model_dump(mode="json"))


@router.patch("/plans/{plan_id}")
async def patch_plan(
    plan_id: int,
    body: PlanPatch,
    _: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    await db.commit()
    return ok(PlanOut.model_validate(plan).model_dump(mode="json"))
