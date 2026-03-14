# app/services/rad_analytics_service.py
from __future__ import annotations

from typing import Iterable, Optional, Dict, Any, Tuple, List
from dataclasses import dataclass

import pandas as pd
import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Servidor, RAD

VALID_STATUSES = {
    "Homologado",
    "Não Validado",
    "Não Homologado",
    "Não Entregue",
    "Encaminhado",
}

ACTIVITY_COLS = [
    "aula",
    "ensino",
    "capacitacao",
    "pesquisa",
    "extensao",
    "administracao_representacao",
]


@dataclass
class RADAnalyticsService:
    """
    Service de análises do RAD.
    Mantém um cache leve em memória para acelerar chamadas subsequentes.
    """

    _df_servidor: Optional[pd.DataFrame] = None
    _df_rad: Optional[pd.DataFrame] = None

    # Carregamento de dados (com cache local)
    async def load(
        self,
        session: AsyncSession,
        force: bool = False,  # Usada para forçar o carregamento dos dados mesmo se já estiverem em cache
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Carrega `servidor` e `rad` e devolve também um DataFrame 'base'
        já unido por siape. Usa cache a menos que `force=True`.
        """
        if force or self._df_servidor is None:
            stmt_srv = select(
                Servidor.siape,
                Servidor.campus,
                Servidor.servidor,
            )
            res_srv = await session.execute(stmt_srv)
            rows_srv = list(res_srv.mappings())
            self._df_servidor = (
                pd.DataFrame(rows_srv)
                if rows_srv
                else pd.DataFrame(columns=["siape", "campus", "servidor"])
            )

        if force or self._df_rad is None:
            stmt_rad = select(
                RAD.id,
                RAD.siape,
                RAD.periodo_letivo,
                RAD.situacao,
                RAD.aula,
                RAD.ensino,
                RAD.capacitacao,
                RAD.pesquisa,
                RAD.extensao,
                RAD.administracao_representacao,
                RAD.total,
                RAD.total_nao_homologado,
            )
            res_rad = await session.execute(stmt_rad)
            rows_rad = list(res_rad.mappings())
            self._df_rad = (
                pd.DataFrame(rows_rad)
                if rows_rad
                else pd.DataFrame(
                    columns=[
                        "id",
                        "siape",
                        "periodo_letivo",
                        "situacao",
                        "aula",
                        "ensino",
                        "capacitacao",
                        "pesquisa",
                        "extensao",
                        "administracao_representacao",
                        "total",
                        "total_nao_homologado",
                    ]
                )
            )

            # garantir tipos numéricos como float (Numeric -> Decimal)
            for col in [
                "aula",
                "ensino",
                "capacitacao",
                "pesquisa",
                "extensao",
                "administracao_representacao",
                "total",
                "total_nao_homologado",
            ]:
                if col in self._df_rad.columns:
                    self._df_rad[col] = pd.to_numeric(
                        self._df_rad[col], errors="coerce"
                    ).fillna(0.0)

        base = self._df_rad.merge(self._df_servidor, on="siape", how="left")
        # extrai ano de "YYYY/n"
        base["ano"] = (
            base["periodo_letivo"]
            .astype(str)
            .str.extract(r"^(\d{4})")[0]
            .astype("Int64")
        )

        return self._df_servidor.copy(), self._df_rad.copy(), base

    # Estatística descritiva
    @staticmethod
    def _describe_numeric(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
        use = [c for c in cols if c in df.columns]
        if not use:
            return pd.DataFrame()
        desc = df[use].agg(["mean", "median", "std", "max", "min"]).T
        desc = desc.rename(
            columns={
                "mean": "média",
                "median": "mediana",
                "std": "desvio_padrão",
                "max": "máximo",
                "min": "mínimo",
            }
        )
        return desc

    async def describe(
        self,
        session: AsyncSession,
        periodo_letivo: Optional[Iterable[str]] = None,
        campus: Optional[Iterable[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Estatística descritiva de `total` e das colunas de atividade.
        Filtros opcionais por período letivo e campus.
        """
        _, _, base = await self.load(session)
        df = base.copy()
        if periodo_letivo:
            df = df[df["periodo_leivto"].isin(set(periodo_letivo))]
        if campus:
            df = df[df["campus"].isin(set(campus))]

        return {
            "total": self._describe_numeric(df, ["total"]),
            "atividades": self._describe_numeric(df, ACTIVITY_COLS),
        }

    # 1) Crescimento/retração da carga por ano
    async def carga_trend_anos(
        self,
        session: AsyncSession,
        campus: Optional[Iterable[str]] = None,
        status_validos: Optional[Iterable[str]] = None,
    ) -> pd.DataFrame:
        _, _, base = await self.load(session)
        df = base.copy()
        if campus:
            df = df[df["campus"].isin(set(campus))]
        if status_validos is None:
            status_validos = VALID_STATUSES
        df = df[df["situacao"].isin(set(status_validos))]
        df = df.dropna(subset=["periodo_letivo"])

        trend = (
            df.groupby("periodo_letivo", dropna=True)["total"]
            .agg(total_somado="sum", total_médio="mean", n_registros="count")
            .reset_index()
            .sort_values(by="periodo_letivo")
        )
        trend["variação_%_soma"] = trend["total_somado"].pct_change() * 100
        trend["variação_%_média"] = trend["total_médio"].pct_change() * 100
        trend["variação_%_soma"] = (
            trend["variação_%_soma"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        )
        trend["variação_%_média"] = (
            trend["variação_%_média"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        )
        return trend

    # 2) Atividades com maior / menor adesão
    async def adesao_atividades(
        self,
        session: AsyncSession,
        periodo_letivo: Optional[Iterable[str]] = None,
        campus: Optional[Iterable[str]] = None,
        considerar_zero: bool = False,
    ) -> pd.DataFrame:
        _, _, base = await self.load(session)
        df = base.copy()
        if periodo_letivo:
            df = df[df["periodo_letivo"].isin(set(periodo_letivo))]
        if campus:
            df = df[df["campus"].isin(set(campus))]

        # agrupar por docente e período
        grp = df.groupby(["periodo_letivo", "siape"], as_index=False)[
            ACTIVITY_COLS
        ].sum()
        total_docentes = grp["siape"].nunique()

        rows: List[Dict[str, Any]] = []
        for col in ACTIVITY_COLS:
            serie = grp[col]
            serie_pos = serie if considerar_zero else serie[serie > 0]
            rows.append(
                {
                    "atividade": col,
                    "participação_%": (
                        (serie.gt(0).sum() / total_docentes * 100)
                        if total_docentes
                        else np.nan
                    ),
                    "média_por_docente": float(
                        serie_pos.mean() if len(serie_pos) else 0.0
                    ),
                    "soma": float(serie.sum()),
                }
            )
        out = pd.DataFrame(rows).sort_values(
            ["participação_%", "soma"], ascending=[False, False]
        )
        return out

    # 3) Docentes com registro apenas do "mínimo" (threshold)
    async def docentes_minimo(
        self,
        session: AsyncSession,
        periodo_letivo: Iterable[str],
        min_total_hours: float = 40.0,
        campus: Optional[Iterable[str]] = None,
        status_validos: Optional[Iterable[str]] = None,
    ) -> pd.DataFrame:
        _, _, base = await self.load(session)
        df = base.copy()
        df = df[df["periodo_letivo"].isin(set(periodo_letivo))]
        if campus:
            df = df[df["campus"].isin(set(campus))]
        if status_validos is None:
            status_validos = VALID_STATUSES
        df = df[df["situacao"].isin(set(status_validos))]

        pivot = df.pivot_table(
            index=["siape", "servidor", "campus"],
            columns="periodo_letivo",
            values="total",
            aggfunc="sum",
            fill_value=0.0,
        )
        mask = (pivot[list(set(periodo_letivo))] < min_total_hours).all(axis=1)
        result = pivot[mask].reset_index()
        result["abaixo_do_mínimo_em_todos_os_períodos"] = True
        return result

    # 4) Taxas por campus: não entrega e não homologação por período
    async def taxas_campus(
        self,
        session: AsyncSession,
        periodo_letivo: Iterable[str],
        status_validos: Optional[Iterable[str]] = None,
    ) -> pd.DataFrame:
        df_srv, df_rad, base = await self.load(session)
        if status_validos is None:
            status_validos = VALID_STATUSES

        srv = df_srv[["siape", "campus"]].drop_duplicates()
        frames = []
        for p in set(periodo_letivo):
            rad_p = df_rad[df_rad["periodo_letivo"] == p][["siape"]].drop_duplicates()
            com_registro = rad_p.merge(srv, on="siape", how="left")

            tot_por_campus = (
                srv.groupby("campus")["siape"].nunique().rename("docentes_total")
            )
            com_reg_por_campus = (
                com_registro.groupby("campus")["siape"]
                .nunique()
                .rename("docentes_com_registro")
            )

            join = (
                pd.concat([tot_por_campus, com_reg_por_campus], axis=1)
                .fillna(0)
                .astype({"docentes_total": int, "docentes_com_registro": int})
                .reset_index()
            )
            join["docentes_sem_registro"] = (
                join["docentes_total"] - join["docentes_com_registro"]
            )
            join["taxa_não_entrega_%"] = np.where(
                join["docentes_total"] > 0,
                join["docentes_sem_registro"] / join["docentes_total"] * 100,
                np.nan,
            )

            base_p = base[base["periodo_letivo"] == p]
            por_campus = (
                base_p.groupby("campus")
                .agg(
                    registros=("id", "count"),
                    nao_homologados=(
                        "situacao",
                        lambda s: (~s.isin(status_validos)).sum(),
                    ),
                )
                .reset_index()
            )
            por_campus["taxa_não_homologação_%"] = np.where(
                por_campus["registros"] > 0,
                por_campus["nao_homologados"] / por_campus["registros"] * 100,
                np.nan,
            )

            out = join.merge(
                por_campus[
                    ["campus", "registros", "nao_homologados", "taxa_não_homologação_%"]
                ],
                on="campus",
                how="left",
            )
            out["periodo_letivo"] = p
            frames.append(out)

        return pd.concat(frames, ignore_index=True).sort_values(
            ["periodo_letivo", "campus"]
        )

    # Atalhos úteis
    async def top_campus_nao_entrega(
        self, session: AsyncSession, periodo_letivo: Iterable[str], k: int = 5
    ) -> pd.DataFrame:
        taxas = await self.taxas_campus(session, periodo_letivo)
        return (
            taxas.sort_values("taxa_não_entrega_%", ascending=False)
            .groupby("periodo_letivo")
            .head(k)
            .reset_index(drop=True)
        )

    async def top_campus_nao_homologacao(
        self, session: AsyncSession, periodo_letivo: Iterable[str], k: int = 5
    ) -> pd.DataFrame:
        taxas = await self.taxas_campus(session, periodo_letivo)
        return (
            taxas.sort_values("taxa_não_homologação_%", ascending=False)
            .groupby("periodo_letivo")
            .head(k)
            .reset_index(drop=True)
        )

    async def describe_by_period(
        self,
        session: AsyncSession,
        campus: Optional[str] = None,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
    ):
        _, _, base = await self.load(session)
        df = base.copy()

        periods = base["periodo_letivo"].unique().tolist()

        df = df[df["situacao"] == "Homologado"]

        if campus:
            df = df[df["campus"] == campus]

        if start_period in periods and end_period in periods:
            start_idx = periods.index(start_period)
            end_idx = periods.index(end_period)

            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx

            selected_periods = periods[start_idx : end_idx + 1]

            df = df[df["periodo_letivo"].isin(selected_periods)]

        if df.empty or "total" not in df.columns or "periodo_letivo" not in df.columns:
            return []

        df = df.copy()
        df["total"] = pd.to_numeric(df["total"], errors="coerce")

        grouped = df.groupby("periodo_letivo", dropna=True)

        approved = (
            grouped["total"]
            .agg(
                media="mean",
                mediana="median",
                desvio_padrao="std",
                minimo="min",
                maximo="max",
                soma="sum",
            )
            .reset_index()
            .rename(columns={"periodo_letivo": "periodo"})
            .sort_values("periodo")
        )

        not_approved = (
            grouped["total_nao_homologado"]
            .agg(
                media="mean",
                mediana="median",
                desvio_padrao="std",
                minimo="min",
                maximo="max",
                soma="sum",
            )
            .reset_index()
            .rename(columns={"periodo_letivo": "periodo"})
            .sort_values("periodo")
        )

        approved["desvio_padrao"] = approved["desvio_padrao"].fillna(0.0)
        not_approved["desvio_padrao"] = not_approved["desvio_padrao"].fillna(0.0)

        approved = approved.to_dict(orient="records")
        not_approved = not_approved.to_dict(orient="records")

        return {"homologado": approved, "nao_homologado": not_approved}
        return approved

    async def activities_distribution(
        self,
        session: AsyncSession,
        campus: Optional[str] = None,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
    ):
        _, _, base = await self.load(session)
        df = base.copy()

        periods = base["periodo_letivo"].unique().tolist()

        # Só homologado
        df = df[df["situacao"] == "Homologado"]

        # Filtro por campus
        if campus:
            df = df[df["campus"] == campus]

        # Filtro por faixa de períodos
        if start_period in periods and end_period in periods:
            start_idx = periods.index(start_period)
            end_idx = periods.index(end_period)

            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx

            selected_periods = periods[start_idx : end_idx + 1]
            df = df[df["periodo_letivo"].isin(selected_periods)]

        if df.empty:
            return {}

        # Colunas das atividades a partir de ACTIVITY_COLS
        activity_cols = [c for c in ACTIVITY_COLS if c in df.columns]

        if not activity_cols:
            return {}

        df[activity_cols] = df[activity_cols].apply(pd.to_numeric, errors="coerce")

        # Média geral de cada atividade
        means = df[activity_cols].sum().fillna(0.0)

        return {col: float(means[col]) for col in activity_cols}

    async def activities_by_period(
        self,
        session: AsyncSession,
        campus: Optional[str] = None,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
    ):
        _, _, base = await self.load(session)
        df = base.copy()

        periods = base["periodo_letivo"].unique().tolist()
        
        if start_period in periods and end_period in periods:
            start_idx = periods.index(start_period)
            end_idx = periods.index(end_period)

            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx

            selected_periods = periods[start_idx : end_idx + 1]
            df = df[df["periodo_letivo"].isin(selected_periods)]

        df = df[df["situacao"] == "Homologado"]

        if campus:
            df = df[df["campus"] == campus]

        activity_cols = [c for c in ACTIVITY_COLS if c in df.columns]

        if not activity_cols:
            return {}

        df[activity_cols] = df[activity_cols].apply(pd.to_numeric, errors="coerce")

        grouped = (
            df.groupby("periodo_letivo", dropna=True)[activity_cols].sum().fillna(0.0)
        )

        return grouped.to_dict(orient="index")

    async def docents_by_activity(
        self,
        session: AsyncSession,
        campus: Optional[str] = None,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
    ):
        _, _, base = await self.load(session)
        df = base.copy()

        periods = base["periodo_letivo"].unique().tolist()
        
        if start_period in periods and end_period in periods:
            start_idx = periods.index(start_period)
            end_idx = periods.index(end_period)

            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx

            selected_periods = periods[start_idx : end_idx + 1]
            df = df[df["periodo_letivo"].isin(selected_periods)]

        df = df[df["situacao"] == "Homologado"]

        if campus:
            df = df[df["campus"] == campus]

        activity_cols = [c for c in ACTIVITY_COLS if c in df.columns]

        if not activity_cols:
            return {}

        df[activity_cols] = df[activity_cols].apply(pd.to_numeric, errors="coerce")

        grouped = df.groupby("periodo_letivo", dropna=True)
        result = {}
        for period, group in grouped:
            counts = {}
            for col in activity_cols:
                counts[col] = group[group[col] > 0]["siape"].nunique()
            result[period] = counts

        return result

    async def docents_by_activities_intersection(
        self,
        session: AsyncSession,
        activities: Optional[Iterable[str]] = None,
        campus: Optional[str] = None,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
    ):
        """Retorna número de docentes por período que têm horas em todas as atividades listadas."""
        _, _, base = await self.load(session)
        df = base.copy()

        periods = base["periodo_letivo"].unique().tolist()

        if start_period in periods and end_period in periods:
            start_idx = periods.index(start_period)
            end_idx = periods.index(end_period)
            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx
            selected_periods = periods[start_idx : end_idx + 1]
            df = df[df["periodo_letivo"].isin(selected_periods)]

        df = df[df["situacao"] == "Homologado"]

        if campus:
            df = df[df["campus"] == campus]

        default_activities = [c for c in ACTIVITY_COLS if c in df.columns]
        activity_cols = list(activities) if activities else default_activities
        activity_cols = [c for c in activity_cols if c in ACTIVITY_COLS and c in df.columns]

        if not activity_cols:
            return {}

        df[activity_cols] = df[activity_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)

        # Somar por docente+período e contar docentes que têm >0 em todas as atividades
        docents = (
            df.groupby(["periodo_letivo", "siape"], dropna=False)[activity_cols]
            .sum()
            .reset_index()
        )

        docents["all_positive"] = docents[activity_cols].gt(0).all(axis=1)

        intersection = (
            docents[docents["all_positive"]]
            .groupby("periodo_letivo")
            ["siape"]
            .nunique()
            .to_dict()
        )

        # Garantir todos os períodos presentes, mesmo com 0
        result = {}
        for period in sorted(docents["periodo_letivo"].unique(), key=str):
            result[period] = int(intersection.get(period, 0))

        return result
