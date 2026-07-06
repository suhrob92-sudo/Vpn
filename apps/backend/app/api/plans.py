from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Plan
from app.schemas.billing import PlanOut
from app.schemas.common import ok

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("")
async def list_plans(db: AsyncSession = Depends(get_db)):
    plans = (
        await db.scalars(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order, Plan.id)
        )
    ).all()
    return ok([PlanOut.model_validate(p).model_dump(mode="json") for p in plans])
