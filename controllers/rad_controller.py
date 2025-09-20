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
    async def get_describe_totais_por_periodo(
        campus,
        session: AsyncSession,
    ):
        return await service.describe_totais_homologados_por_periodo(session, campus)
    