"""Test fixtures. Environment must be configured before importing app modules
because settings are cached at first use."""
import os
import tempfile

_tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.update(
    {
        "DATABASE_URL_OVERRIDE": f"sqlite+aiosqlite:///{_tmpdb.name}",
        "BOT_TOKEN": "12345:TEST-BOT-TOKEN-abcdefghijklmnopqrstuvwx",
        "CRYPTOBOT_API_TOKEN": "999:test-cryptobot-token",
        "CRYPTOBOT_WEBHOOK_SECRET": "hooksecret",
        "JWT_SECRET": "test-jwt-secret",
        "ENCRYPTION_KEY": "6ycMBbwr8Q5DJi-JLK9upvSFcIUf9pXQZ_r2K0YbHRk=",
        "SUB_BASE_URL": "https://vpn.test",
        "ADMIN_BOOTSTRAP_PASSWORD": "",
    }
)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.db import get_engine, reset_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(autouse=True)
async def clean_db():
    """Fresh schema per test."""
    reset_engine()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
