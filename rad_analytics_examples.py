# rad_analytics_examples.py
"""
Exemplos de uso + visualização para RADAnalyticsService.

Como usar:
1) Ajuste os imports de sessão conforme seu projeto (db.database.SessionLocal).
2) Rode:  python -m asyncio run rad_analytics_examples.py
   ou:    python rad_analytics_examples.py
3) As saídas (CSV e PNG) serão salvas na pasta ./reports

Obs.: Todos os exemplos são resilientes a conjuntos de dados vazios.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, List

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # backend não interativo para salvar figuras
import matplotlib.pyplot as plt

# Ajuste estes imports conforme sua base de código
from db.database import SessionLocal  # AsyncSession factory (ex.: async sessionmaker)
from services.rad_analytics import RADAnalyticsService

# ---------- Configuração de diretórios ----------
REPORTS_DIR = Path("./reports").resolve()
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")

def _save_df(df: pd.DataFrame, name: str) -> Path:
    path = REPORTS_DIR / f"{name}-{_timestamp()}.csv"
    df.to_csv(path, index=False)
    print(f"[CSV] Salvo: {path}")
    return path

def _save_fig(name: str) -> Path:
    path = REPORTS_DIR / f"{name}-{_timestamp()}.png"
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"[FIG] Salvo: {path}")
    return path

# ---------- Visualizações auxiliares ----------
def _plot_bar(df: pd.DataFrame, x: str, y: str, title: str):
    if df.empty or x not in df.columns or y not in df.columns:
        print(f"[WARN] Sem dados para plot '{title}'.")
        return None
    plt.figure(figsize=(10, 5))
    plt.bar(df[x].astype(str), df[y])
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)
    return _save_fig(title.replace(" ", "_").lower())

def _plot_line(df: pd.DataFrame, x: str, y_cols: List[str], title: str):
    if df.empty or x not in df.columns:
        print(f"[WARN] Sem dados para plot '{title}'.")
        return None
    plt.figure(figsize=(11, 6))
    for y in y_cols:
        if y in df.columns:
            plt.plot(df[x], df[y], marker="o", label=y)
    plt.title(title)
    plt.xlabel(x)
    plt.legend()
    return _save_fig(title.replace(" ", "_").lower())

# ---------- Exemplos por função ----------
async def exemplo_describe(service: RADAnalyticsService):
    """
    Estatística descritiva: total e colunas de atividade.
    """
    async with SessionLocal() as session:
        out = await service.describe(session)
    # Salva CSVs
    if isinstance(out, dict):
        for k, df in out.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                _save_df(df.reset_index().rename(columns={"index": "variável"}), f"describe_{k}")
    print("[OK] exemplo_describe finalizado.")

async def exemplo_carga_trend_anos(service: RADAnalyticsService, campus: Optional[Iterable[str]] = None):
    """
    Série temporal por ano da carga total.
    """
    async with SessionLocal() as session:
        trend = await service.carga_trend_anos(session, campus=campus)
    if not trend.empty:
        _save_df(trend, "carga_trend_anos")
        _plot_line(trend, "ano", ["total_somado", "total_médio"], "Carga por Ano (Somada e Média)")
        _plot_line(trend, "ano", ["variação_%_soma", "variação_%_média"], "Variação % Ano a Ano")
    print("[OK] exemplo_carga_trend_anos finalizado.")

async def exemplo_adesao_atividades(service: RADAnalyticsService, periodo_letivo: Optional[Iterable[str]] = None, campus: Optional[Iterable[str]] = None):
    """
    Ranking de adesão por atividade.
    """
    async with SessionLocal() as session:
        adesao = await service.adesao_atividades(session, periodo_letivo=periodo_letivo, campus=campus)
    if not adesao.empty:
        _save_df(adesao, "adesao_atividades")
        _plot_bar(adesao, "atividade", "participação_%", "Participação (%) por Atividade")
        _plot_bar(adesao, "atividade", "soma", "Soma de Horas por Atividade")
    print("[OK] exemplo_adesao_atividades finalizado.")

async def exemplo_docentes_minimo(service: RADAnalyticsService, periodos: Iterable[str], min_total_hours: float = 40.0, campus: Optional[Iterable[str]] = None):
    """
    Docentes que ficaram abaixo do mínimo em TODOS os períodos selecionados.
    """
    async with SessionLocal() as session:
        res = await service.docentes_minimo(session, periodos, min_total_hours=min_total_hours, campus=campus)
    if not res.empty:
        _save_df(res, f"docentes_minimo_{min_total_hours}h")
        # Contagem por campus (se existir)
        if "campus" in res.columns:
            contagem = res.groupby("campus").size().reset_index(name="qtd_docentes")
            _save_df(contagem, "docentes_minimo_por_campus")
            _plot_bar(contagem, "campus", "qtd_docentes", "Docentes abaixo do mínimo por Campus")
    print("[OK] exemplo_docentes_minimo finalizado.")

async def exemplo_taxas_campus(service: RADAnalyticsService, periodos: Iterable[str]):
    """
    Taxas por campus: não entrega e não homologação por período.
    """
    async with SessionLocal() as session:
        taxas = await service.taxas_campus(session, periodos)
    if not taxas.empty:
        _save_df(taxas, "taxas_campus")
        # Exemplo de gráfico para um período (o mais recente)
        ult = taxas["periodo_letivo"].dropna().astype(str).unique().tolist()
        if ult:
            ult_periodo = sorted(ult)[-1]
            base_ult = taxas[taxas["periodo_letivo"] == ult_periodo]
            _plot_bar(base_ult, "campus", "taxa_não_entrega_%", f"Taxa Não Entrega (%) — {ult_periodo}")
            _plot_bar(base_ult, "campus", "taxa_não_homologação_%", f"Taxa Não Homologação (%) — {ult_periodo}")
    print("[OK] exemplo_taxas_campus finalizado.")

async def exemplo_tops(service: RADAnalyticsService, periodos: Iterable[str], k: int = 5):
    """
    Top K campi por não entrega e por não homologação.
    """
    async with SessionLocal() as session:
        top_ne = await service.top_campus_nao_entrega(session, periodos, k=k)
        top_nh = await service.top_campus_nao_homologacao(session, periodos, k=k)
    if not top_ne.empty:
        _save_df(top_ne, f"top_{k}_nao_entrega")
        # Gráfico: barras por período concatenado (campus como label)
        lab = top_ne.apply(lambda r: f"{r['periodo_letivo']} | {r['campus']}", axis=1)
        df_plot = pd.DataFrame({"label": lab, "taxa": top_ne["taxa_não_entrega_%"].astype(float)})
        _plot_bar(df_plot, "label", "taxa", f"Top {k} — Taxa Não Entrega (%)")
    if not top_nh.empty:
        _save_df(top_nh, f"top_{k}_nao_homologacao")
        lab = top_nh.apply(lambda r: f"{r['periodo_letivo']} | {r['campus']}", axis=1)
        df_plot = pd.DataFrame({"label": lab, "taxa": top_nh["taxa_não_homologação_%"].astype(float)})
        _plot_bar(df_plot, "label", "taxa", f"Top {k} — Taxa Não Homologação (%)")
    print("[OK] exemplo_tops finalizado.")

# ---------- Utilitário: rodar tudo de forma inteligente ----------
async def run_todos_os_exemplos():
    service = RADAnalyticsService()
    # Carrega uma vez para derivar filtros úteis
    async with SessionLocal() as session:
        _srv, _rad, base = await service.load(session, force=True)

    # Derivar amostras de filtros dinâmicos
    periodos = (
        base["periodo_letivo"].dropna().astype(str).unique().tolist()
        if not base.empty and "periodo_letivo" in base.columns else []
    )
    # Seleciona até 6 períodos mais recentes para exemplos
    periodos_selec = sorted(periodos)[-6:] if periodos else []
    campuses = (
        base["campus"].dropna().astype(str).unique().tolist()
        if not base.empty and "campus" in base.columns else []
    )
    campus_exemplo = campuses[:3] if campuses else None

    print(f"[INFO] Períodos detectados: {periodos_selec if periodos_selec else '—'}")
    print(f"[INFO] Campi detectados: {campus_exemplo if campus_exemplo else '—'}")

    # 1) describe
    await exemplo_describe(service)

    # 2) carga_trend_anos (com e sem filtro de campus)
    await exemplo_carga_trend_anos(service)  # geral
    if campus_exemplo:
        await exemplo_carga_trend_anos(service, campus=campus_exemplo)  # filtrado

    # 3) adesao_atividades (últimos períodos se existirem)
    if periodos_selec:
        await exemplo_adesao_atividades(service, periodo_letivo=periodos_selec, campus=campus_exemplo)
    else:
        await exemplo_adesao_atividades(service)

    # 4) docentes_minimo (se houver ao menos 2 períodos)
    if len(periodos_selec) >= 2:
        await exemplo_docentes_minimo(service, periodos=periodos_selec[-2:], min_total_hours=40.0, campus=campus_exemplo)

    # 5) taxas_campus (usar últimos 2–4 períodos se possível)
    if periodos_selec:
        alvo = periodos_selec[-4:] if len(periodos_selec) > 4 else periodos_selec
        await exemplo_taxas_campus(service, periodos=alvo)

    # 6) tops
    if periodos_selec:
        await exemplo_tops(service, periodos=periodos_selec, k=5)

    print("\n[FINALIZADO] Exemplos executados. Verifique a pasta ./reports.")

# ---------- Execução direta ----------
if __name__ == "__main__":
    try:
        asyncio.run(run_todos_os_exemplos())
    except RuntimeError:
        # Compatibilidade com Python<3.11 em alguns ambientes
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_todos_os_exemplos())
