"""
Modelos Pydantic que representam a saída estruturada de um extrato financeiro.
Os campos monetários são armazenados como str para preservar precisão decimal do PDF.
Os campos percentuais também são str (ex: "33.63" sem o símbolo %).
"""
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Banco
# ---------------------------------------------------------------------------

class BankInfo(BaseModel):
    nome: str
    codigo: str   # Código COMPE (3 dígitos, ex: "001" para BB, "102" para XP)


# ---------------------------------------------------------------------------
# Período
# ---------------------------------------------------------------------------

class Periodo(BaseModel):
    inicio: str  # dd/mm/aaaa
    fim: str     # dd/mm/aaaa


# ---------------------------------------------------------------------------
# Seção RESUMO
# ---------------------------------------------------------------------------

class SaldoBrutoData(BaseModel):
    data: str
    valor: str


class Evolucao(BaseModel):
    saldo_bruto_inicio: SaldoBrutoData
    saldo_bruto_fim: SaldoBrutoData


class Carteira(BaseModel):
    rendimentos: str
    entradas: str
    retiradas: str
    liquido: SaldoBrutoData
    evolucao: Evolucao


class DistribuicaoPorClasse(BaseModel):
    classe: str
    percentual: str
    valor: str


class DistribuicaoPorRisco(BaseModel):
    risco: str
    percentual: str
    valor: str


class Resumo(BaseModel):
    carteira: Carteira
    distribuicao_por_classe: list[DistribuicaoPorClasse]
    distribuicao_por_risco: list[DistribuicaoPorRisco]


# ---------------------------------------------------------------------------
# Seção POSIÇÃO DA CARTEIRA
# ---------------------------------------------------------------------------

class PosicaoItem(BaseModel):
    classe: str
    saldo_bruto_inicio: str
    entradas: str
    saidas: str
    saldo_bruto_fim: str
    provisao_ir_iof: str
    saldo_liquido: str
    rentabilidade_percentual: str


# ---------------------------------------------------------------------------
# Seção DISTRIBUIÇÃO DA CARTEIRA
# ---------------------------------------------------------------------------

class Ativo(BaseModel):
    nome: str
    saldo_bruto_inicio: str
    entradas: str
    saidas: str
    saldo_bruto_fim: str
    provisao_ir_iof: str
    saldo_liquido: str
    participacao: str


class DistribuicaoClasse(BaseModel):
    classe: str
    alocacao_percentual: str
    ativos: list[Ativo]


# ---------------------------------------------------------------------------
# Seção LIQUIDEZ DA CARTEIRA
# ---------------------------------------------------------------------------

class LiquidezFaixa(BaseModel):
    prazo_dias: str
    total_bruto: str
    bruto_bloqueado: str
    bruto_disponivel: str
    liquido_disponivel: str
    participacao: str


class LiquidezTotal(BaseModel):
    total_bruto: str
    bruto_bloqueado: str
    bruto_disponivel: str
    liquido_disponivel: str
    participacao: str


class LiquidezCarteira(BaseModel):
    faixas: list[LiquidezFaixa]
    total: LiquidezTotal


# ---------------------------------------------------------------------------
# Seção RENTABILIDADE
# ---------------------------------------------------------------------------

class RentabilidadePercentualItem(BaseModel):
    classe: str
    periodo_apurado: str
    no_mes: str
    mes_anterior: str
    ultimos_3_meses: str
    ultimos_6_meses: str
    ultimos_12_meses: str
    saldo_bruto: str
    participacao: str


class RentabilidadeReaisItem(BaseModel):
    classe: str
    periodo_apurado: str
    dia: str
    no_mes: str
    mes_anterior: str
    ultimos_3_meses: str
    ultimos_6_meses: str
    ultimos_12_meses: str


class Rentabilidade(BaseModel):
    por_classe_percentual: list[RentabilidadePercentualItem]
    por_classe_reais: list[RentabilidadeReaisItem]


# ---------------------------------------------------------------------------
# Períodos de referência (rodapé da seção de rentabilidade)
# ---------------------------------------------------------------------------

class PeriodosReferencia(BaseModel):
    ultimos_3_meses: Optional[Periodo] = None
    ultimos_6_meses: Optional[Periodo] = None
    ultimos_12_meses: Optional[Periodo] = None


# ---------------------------------------------------------------------------
# Model base — compartilhado por todos os bancos (OCP + LSP)
# ---------------------------------------------------------------------------

class BasePortfolioData(BaseModel):
    """
    Base comum para todos os modelos de portfólio.
    Cada banco estende esta classe com sua estrutura específica.
    """
    banco: BankInfo


# ---------------------------------------------------------------------------
# Model raiz — PortfolioData (Banco do Brasil)
# ---------------------------------------------------------------------------

class PortfolioData(BasePortfolioData):
    banco: BankInfo
    periodo: Periodo
    resumo: Resumo
    posicao_carteira: list[PosicaoItem]
    distribuicao_carteira: list[DistribuicaoClasse]
    liquidez_carteira: LiquidezCarteira
    rentabilidade: Rentabilidade
    periodos_referencia: PeriodosReferencia
