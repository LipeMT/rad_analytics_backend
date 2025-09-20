from fastapi import APIRouter, Depends, Query
from typing import AsyncGenerator, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import SessionLocal
from controllers.rad_controller import RADController

router = APIRouter(prefix="/rad", tags=["RAD"])


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


@router.get("/trend")
async def trend(session: AsyncSession = Depends(get_session)):
    return await RADController.get_trend(session)


@router.get("/describe")
async def describe(session: AsyncSession = Depends(get_session)):
    return await RADController.get_describe(session)


@router.get("/describe_by_period")
async def get_describe_totais_por_periodo(
    campus: Optional[List[str]] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    return await RADController.get_describe_totais_por_periodo(campus, session)
