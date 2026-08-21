"""
Modelos de domínio para o extrato de portfólio Itaú Unibanco (COMPE 341).

O documento "Resumo financeiro" do Itaú possui 12 páginas físicas
(correspondendo às páginas 2-13 de um relatório de 16 páginas) com as seções:
  Pág. 1  — Resumo financeiro (saldos, performance, classes de ativos, índices)
  Pág. 2  — Rentabilidade histórica mensal (12 meses)
  Pág. 3  — Alocação detalhada + tipos de produto + índices de mercado
  Págs. 4-12 — Detalhamento de Ativos por tipo de produto (1/9 a 9/9)
"""
from typing import Optional

from pydantic import BaseModel

from app.domain.models.portfolio import BankInfo


# ---------------------------------------------------------------------------
# Pág. 1 — Resumo financeiro
# ---------------------------------------------------------------------------

class ItauPerformancePeriodo(BaseModel):
    """Performance financeira de um período (ex: Ago/25 ou 2025)."""
    periodo_label: str                      # "Ago/25" ou "2025"
    datas: Optional[str] = None             # "01/08/25 à 12/08/25"
    valor_inicial_bruto: Optional[str] = None
    movimentacoes: Optional[str] = None
    lucros_perdas: Optional[str] = None


class ItauClasseAtivo(BaseModel):
    """Distribuição da carteira por classe de ativo (tabela da pág. 1)."""
    classe: str
    percentual: str
    saldo_bruto: str


class ItauIndiceMercado(BaseModel):
    """Linha de índice de referência (CDI, IPCA, IBOVESPA, dólar)."""
    indice: str
    mes: Optional[str] = None
    ano: Optional[str] = None
    doze_meses: Optional[str] = None
    vinte_quatro_meses: Optional[str] = None
    trinta_seis_meses: Optional[str] = None
    inicio: Optional[str] = None


class ItauResumo(BaseModel):
    """Seção 'Resumo financeiro' — página 1 do PDF."""
    data_posicao: str
    data_rentabilidade: str
    saldo_bruto: str
    saldo_liquido: str
    saldo_conta: Optional[str] = None
    performance_mensal: Optional[ItauPerformancePeriodo] = None
    performance_anual: Optional[ItauPerformancePeriodo] = None
    carteira_rent_mes: Optional[str] = None
    carteira_rent_ano: Optional[str] = None
    carteira_rent_12m: Optional[str] = None
    carteira_rent_24m: Optional[str] = None
    carteira_rent_36m: Optional[str] = None
    carteira_rent_inicio: Optional[str] = None
    indices_mercado: list[ItauIndiceMercado]
    classes_ativos: list[ItauClasseAtivo]


# ---------------------------------------------------------------------------
# Pág. 2 — Histórico de rentabilidade mensal
# ---------------------------------------------------------------------------

class ItauMesHistorico(BaseModel):
    """Rentabilidade de um mês para todos os indicadores."""
    mes: str          # "Set/24", "Out/24" …
    carteira: str
    cdi: str
    ibov: str
    ipca: str
    dolar: str


class ItauRentabilidade(BaseModel):
    """Seção 'Rentabilidade' — página 2 do PDF."""
    historico: list[ItauMesHistorico]


# ---------------------------------------------------------------------------
# Pág. 3 — Alocação
# ---------------------------------------------------------------------------

class ItauClasseAlocacao(BaseModel):
    """Linha da tabela de classes de ativos com rentabilidades (pág. 3)."""
    classe: str
    percentual: str
    saldo_bruto: str
    rent_mes: Optional[str] = None
    rent_ano: Optional[str] = None
    rent_12m: Optional[str] = None
    rent_24m: Optional[str] = None
    rent_inicio: Optional[str] = None


class ItauTipoProduto(BaseModel):
    """Linha de alocação por tipo de produto (pág. 3)."""
    tipo: str
    percentual: str
    saldo_bruto: str


class ItauAlocacao(BaseModel):
    """Seção 'Alocação' — página 3 do PDF."""
    classes: list[ItauClasseAlocacao]
    indices_mercado: list[ItauIndiceMercado]
    tipos_produto: list[ItauTipoProduto]


# ---------------------------------------------------------------------------
# Págs. 4-12 — Detalhamento de Ativos
# ---------------------------------------------------------------------------

class ItauAtivo(BaseModel):
    """Ativo individual com todos os campos de posição e rentabilidade."""
    nome: str
    data_vencimento: Optional[str] = None    # MM/AAAA ou DD/MM/AA
    data_inicio: Optional[str] = None
    valor_aplicado: Optional[str] = None
    quantidade: Optional[str] = None
    pu_cotacao: Optional[str] = None
    saldo_bruto: str
    saldo_liquido: str
    ir_iof: Optional[str] = None
    data_cotacao: Optional[str] = None
    alocacao_pct: Optional[str] = None
    rent_mes: Optional[str] = None
    rent_ano: Optional[str] = None
    rent_12m: Optional[str] = None
    rent_24m: Optional[str] = None
    rent_inicio: Optional[str] = None


class ItauGrupoAtivos(BaseModel):
    """
    Grupo de ativos dentro de Renda fixa e estruturados (ex: 'LIG-DI ITAU').
    Contém o subtotal do grupo e a lista de ativos individuais.
    """
    nome: str
    num_ativos: Optional[int] = None
    saldo_bruto_total: Optional[str] = None
    saldo_liquido_total: Optional[str] = None
    alocacao_pct: Optional[str] = None
    ativos: list[ItauAtivo]


class ItauSecaoAtivos(BaseModel):
    """
    Seção de ativos (ex: 'Renda fixa e estruturados', 'Fundos de investimento').
    Contém os grupos (quando há, como em RF) ou ativos diretamente (fundos/previdência).
    """
    nome: str
    saldo_bruto_total: Optional[str] = None
    saldo_liquido_total: Optional[str] = None
    alocacao_pct: Optional[str] = None
    grupos: list[ItauGrupoAtivos]


# ---------------------------------------------------------------------------
# Modelo raiz
# ---------------------------------------------------------------------------

class ItauPortfolioData(BaseModel):
    """Consolidação completa do Resumo Financeiro Itaú Unibanco."""
    banco: BankInfo           # OBRIGATÓRIO — ausência causa AttributeError em runtime
    resumo: ItauResumo
    rentabilidade: ItauRentabilidade
    alocacao: ItauAlocacao
    ativos: list[ItauSecaoAtivos]
