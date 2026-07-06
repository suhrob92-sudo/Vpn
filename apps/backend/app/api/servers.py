from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import VpnServer
from app.schemas.common import ok
from app.schemas.vpn import ServerPublicOut

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("")
async def list_servers(db: AsyncSession = Depends(get_db)):
    servers = (await db.scalars(select(VpnServer).order_by(VpnServer.id))).all()
    return ok([ServerPublicOut.model_validate(s).model_dump(mode="json") for s in servers])
