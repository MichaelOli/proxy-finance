"""
Modelos Pydantic exclusivos da XP Investimentos.
Todos os campos monetários e percentuais são str para preservar os valores exatos do PDF.
Campos opcionais usam `= None` explícito (Pydantic v2).
"""
from typing import Optional

from pydantic import BaseModel

from app.domain.models.portfolio import BasePortfolioData


# ---------------------------------------------------------------------------
# Resumo (página 1)
# ---------------------------------------------------------------------------

class XpBenchmark(BaseModel):
    nome: str
    mes: Optional[str] = None
    ano: Optional[str] = None
    doze_m: Optional[str] = None
    vinte_quatro_m: Optional[str] = None


class XpEstatisticasHistoricas(BaseModel):
    meses_positivos: str
    meses_negativos: str
    retorno_mensal_maximo: str
    retorno_mensal_minimo: str
    meses_acima_cdi: str
    meses_abaixo_cdi: str
    volatilidade_12m: str
    volatilidade_24m: str


class XpPeriodoResumo(BaseModel):
    periodo: str                        # "MÊS", "ANO", "12M", "24M"
    ganho_financeiro: Optional[str] = None
    rentabilidade: Optional[str] = None
    percentual_cdi: Optional[str] = None
    movimentacoes: Optional[str] = None


class XpResumo(BaseModel):
    patrimonio_total_bruto: str
    rentabilidade_mes: str
    ganho_mes: str
    rentabilidade_24m: Optional[str] = None
    ganho_24m: Optional[str] = None
    benchmarks: list[XpBenchmark]
    estatisticas_historicas: XpEstatisticasHistoricas
    por_periodo: list[XpPeriodoResumo]


# ---------------------------------------------------------------------------
# Histórico anual (página 2)
# ---------------------------------------------------------------------------

class XpMesHistorico(BaseModel):
    mes: str                              # "Jan", "Fev", ..., "Dez"
    rentabilidade: Optional[str] = None   # "1,19%" ou None se "-"
    percentual_cdi: Optional[str] = None  # "118,29%" ou None se "-"


class XpAnoHistorico(BaseModel):
    ano: str
    rentabilidade_no_ano: str             # coluna "Ano" do Portfólio
    acumulado: Optional[str] = None       # coluna "Acum."
    meses: list[XpMesHistorico]


# ---------------------------------------------------------------------------
# Evolução patrimonial (página 3)
# ---------------------------------------------------------------------------

class XpEvolucaoMes(BaseModel):
    data: str               # "jul./25"
    patrimonio_inicial: str
    movimentacoes: str
    ir: str
    iof: str
    patrimonio_final: str
    ganho_financeiro: str
    rentabilidade: str
    percentual_cdi: str


# ---------------------------------------------------------------------------
# Composição por estratégia (páginas 4–5)
# ---------------------------------------------------------------------------

class XpEstrategia(BaseModel):
    nome: str
    percentual_alocacao: str
    saldo_bruto: str
    rentabilidade_mes: Optional[str] = None
    rentabilidade_ano: Optional[str] = None
    rentabilidade_12m: Optional[str] = None
    rentabilidade_24m: Optional[str] = None


# ---------------------------------------------------------------------------
# Posição detalhada por ativo (páginas 6–9)
# ---------------------------------------------------------------------------

class XpAtivo(BaseModel):
    nome: str
    saldo_bruto: str
    quantidade: str
    percentual_alocacao: str
    rentabilidade_mes: Optional[str] = None
    percentual_cdi_mes: Optional[str] = None
    rentabilidade_ano: Optional[str] = None
    percentual_cdi_ano: Optional[str] = None
    rentabilidade_24m: Optional[str] = None
    percentual_cdi_24m: Optional[str] = None


class XpEstrategiaDetalhada(BaseModel):
    estrategia: str
    saldo_bruto_estrategia: str
    percentual_alocacao_estrategia: str
    ativos: list[XpAtivo]


# ---------------------------------------------------------------------------
# Model raiz XP
# ---------------------------------------------------------------------------

class XpPortfolioData(BasePortfolioData):
    data_referencia: str
    resumo: XpResumo
    historico_anual: list[XpAnoHistorico]
    evolucao_patrimonial: list[XpEvolucaoMes]
    composicao: list[XpEstrategia]
    posicao_detalhada: list[XpEstrategiaDetalhada]
