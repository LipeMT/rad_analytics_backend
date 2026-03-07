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
    campus: Optional[str] = Query(default=None),
    start_period: Optional[str] = Query(default=None),
    end_period: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    return await RADController.get_describe_by_periodo(
        campus=campus,
        start_period=start_period,
        end_period=end_period,
        session=session,
    )


@router.get("/activities_distribution")
async def get_activites_distribution(
    campus: Optional[str] = Query(default=None),
    start_period: Optional[str] = Query(default=None),
    end_period: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    return await RADController.get_activities_distribution(
        campus=campus,
        start_period=start_period,
        end_period=end_period,
        session=session,
    )
    
@router.get("/activities_by_period")
async def get_activites_by_period(
    campus: Optional[str] = Query(default=None),
    start_period: Optional[str] = Query(default=None),
    end_period: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    return await RADController.activites_by_period(
        campus=campus,
        start_period=start_period,
        end_period=end_period,
        session=session,
    )

@router.get("/docents_by_activity")
async def get_docents_by_activity(
    campus: Optional[str] = Query(default=None),
    start_period: Optional[str] = Query(default=None),
    end_period: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    return await RADController.docents_by_activity(
        campus=campus,
        start_period=start_period,
        end_period=end_period,
        session=session,
    )