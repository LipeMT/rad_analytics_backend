from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from services.rad_analytics import RADAnalyticsService
from typing import Iterable, Optional, Dict, Any, Tuple, List

service = RADAnalyticsService()

class RADController:
    @staticmethod
    async def get_trend(session: AsyncSession):
        df = await service.carga_trend_anos(session)
        return df.to_dict(orient="records")

    @staticmethod
    async def get_describe(session: AsyncSession):
        desc = await service.describe(session)
        return {
            "total": desc["total"].to_dict(),
            "atividades": desc["atividades"].to_dict(),
        }

    @staticmethod
    async def get_adesao(session: AsyncSession, periodo: list[str]):
        df = await service.adesao_atividades(session, periodo_letivo=periodo)
        return df.to_dict(orient="records")

    @staticmethod
    async def get_describe_by_periodo(
        campus,
        start_period,
        end_period,
        session: AsyncSession,
    ):
        return await service.describe_by_period(session, campus, start_period=start_period, end_period=end_period)
    
    @staticmethod
    async def get_activities_distribution(
        campus,
        start_period,
        end_period,
        session: AsyncSession,
    ):
        return await service.activities_distribution(session, campus, start_period=start_period, end_period=end_period)
    
    @staticmethod
    async def activites_by_period(
        campus,
        start_period,
        end_period,
        session: AsyncSession,
    ):
        return await service.activities_by_period(session=session, campus=campus, start_period=start_period, end_period=end_period)
    
    @staticmethod
    async def docents_by_activity(
        campus,
        start_period,
        end_period,
        session: AsyncSession,
    ):
        return await service.docents_by_activity(session=session, campus=campus, start_period=start_period, end_period=end_period)

    @staticmethod
    async def docents_by_activities_intersection(
        campus,
        activities,
        start_period,
        end_period,
        session: AsyncSession,
    ):
        return await service.docents_by_activities_intersection(
            session=session,
            campus=campus,
            activities=activities,
            start_period=start_period,
            end_period=end_period,
        )
    