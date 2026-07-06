"""FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import admin, auth, payments, plans, servers, sub, subscriptions, users
from app.core.config import get_settings
from app.core.db import get_session_factory
from app.core.logging import setup_logging
from app.core.security import hash_password
from app.models import AdminUser, Plan
from app.schemas.common import err

logger = logging.getLogger(__name__)


async def bootstrap_admin() -> None:
    """Create the first admin user from env if the table is empty."""
    settings = get_settings()
    if not settings.admin_bootstrap_password:
        return
    async with get_session_factory()() as session:
        existing = await session.scalar(select(AdminUser).limit(1))
        if existing is None:
            session.add(
                AdminUser(
                    username=settings.admin_bootstrap_username,
                    password_hash=hash_password(settings.admin_bootstrap_password),
                    role="superadmin",
                )
            )
            await session.commit()
            logger.info("bootstrap admin user created: %s", settings.admin_bootstrap_username)


async def seed_default_plans() -> None:
    """Create the 3 standard plans on first boot; admins manage them afterwards."""
    async with get_session_factory()() as session:
        existing = await session.scalar(select(Plan).limit(1))
        if existing is not None:
            return
        session.add_all(
            [
                Plan(
                    name="1 oylik",
                    description="30 kunlik standart obuna",
                    price=3, currency="USDT", duration_days=30,
                    traffic_limit_gb=0, device_hint=3, sort_order=1,
                ),
                Plan(
                    name="3 oylik",
                    description="90 kun · chegirma bilan",
                    price=8, currency="USDT", duration_days=90,
                    traffic_limit_gb=0, device_hint=3,
                    discount_percent=11, is_popular=True, sort_order=2,
                ),
                Plan(
                    name="12 oylik",
                    description="365 kun · maksimal chegirma",
                    price=28, currency="USDT", duration_days=365,
                    traffic_limit_gb=0, device_hint=3,
                    discount_percent=22, sort_order=3,
                ),
            ]
        )
        await session.commit()
        logger.info("default plans seeded")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await bootstrap_admin()
    await seed_default_plans()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="VPN Platform API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_exc_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=err(code=f"http_{exc.status_code}", message=str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exc_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=err(code="validation_error", message=str(exc.errors()[:3])),
        )

    @app.exception_handler(Exception)
    async def unhandled_exc_handler(request: Request, exc: Exception):
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500, content=err(code="internal_error", message="Internal server error")
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(plans.router)
    app.include_router(subscriptions.router)
    app.include_router(payments.router)
    app.include_router(servers.router)
    app.include_router(sub.router)
    app.include_router(admin.router)
    return app


app = create_app()
