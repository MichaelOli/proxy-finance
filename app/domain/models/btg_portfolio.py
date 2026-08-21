"""
Modelos de domínio para o extrato de portfólio BTG Pactual (COMPE 208).

O documento "Relatório de Performance" do BTG possui 12 páginas com as seções:
  Pág. 1  — Resumo (patrimônio, performance, distribuição, liquidez)
  Pág. 2  — Histórico de movimentações mensais
  Págs. 3 — Rentabilidade mensal dos últimos 12 meses (tabela)
  Págs. 4 — Rentabilidade por estratégia
  Págs. 5-6 — Retornos mensais/anuais + estatísticas
  Págs. 7-8 — Rentabilidade completa por classe e ativo
  Pág. 9  — Posição consolidada por devedor/garantidor
  Págs. 10-11 — Principais números por mercado e estratégia
  Pág. 12 — Disclaimer
"""
from typing import Optional

from pydantic import BaseModel

from app.domain.models.portfolio import BankInfo


# ---------------------------------------------------------------------------
# Pág. 1 — Resumo
# ---------------------------------------------------------------------------

class BtgDistribuicaoClasse(BaseModel):
    """Distribuição por classe de ativos (tabela canto superior-direito da pág. 1)."""
    estrategia: str
    percentual: str
    valor_financeiro: str


class BtgRentabilidadePeriodo(BaseModel):
    """Linha da tabela de rentabilidade (Mês, Ano, 3 Meses etc.) da pág. 1."""
    periodo: str
    retorno_rs: str
    portfolio_pct: str
    cdi_pct: str
    ipca_pct: str
    dolar_pct: str


class BtgLiquidezFaixa(BaseModel):
    """Faixa de liquidez (pág. 1 — seção Liquidez)."""
    faixa: str
    percentual: str
    valor_financeiro: str


class BtgResumo(BaseModel):
    """Dados resumidos da pág. 1 do Relatório de Performance."""
    periodo: str
    patrimonio_bruto: str
    patrimonio_liquido: str
    performance_mes_pct: str
    performance_12m_pct: str
    distribuicao: list[BtgDistribuicaoClasse]
    rentabilidade: list[BtgRentabilidadePeriodo]
    liquidez: list[BtgLiquidezFaixa]


# ---------------------------------------------------------------------------
# Pág. 2 — Histórico de movimentações mensais
# ---------------------------------------------------------------------------

class BtgHistoricoMes(BaseModel):
    """Linha da tabela de movimentação mensal (pág. 2)."""
    data: str
    patrimonio_inicial: str
    movimentacoes: str
    ir_pago: str
    patrimonio_final: str
    ganho: str
    portfolio_pct: str
    cdi_pct: str


# ---------------------------------------------------------------------------
# Pág. 3 — Rentabilidade mensal dos últimos 12 meses (tabela comparativa)
# ---------------------------------------------------------------------------

class BtgRentabilidadeMensalItem(BaseModel):
    """Linha da tabela de rentabilidade mensal (pág. 3)."""
    indicador: str          # ex.: "Portfólio %", "CDI", "Dólar", "Ibovespa"
    valores: list[str]      # valores mensais na ordem do cabeçalho (Ago, Set, …)


# ---------------------------------------------------------------------------
# Págs. 4-6 — Rentabilidade por estratégia + retornos mensais/anuais + estatísticas
# ---------------------------------------------------------------------------

class BtgEstrategia(BaseModel):
    """Bloco de rentabilidade de uma estratégia (pág. 4)."""
    nome: str
    portfolio_pct: str
    mes_pct: str
    ano_pct: str
    doze_meses_pct: str
    acumulado_pct: str
    valor_rs: str
    mes_rs: str
    ano_rs: str
    doze_meses_rs: str
    acumulado_rs: str
    cdi_mes_pct: str
    cdi_ano_pct: str
    cdi_12m_pct: str
    cdi_acum_pct: str


class BtgRetornoMensal(BaseModel):
    """Linha da tabela de retornos mensais (pág. 5)."""
    indicador: str          # ex.: "2025", "CDI", "% do CDI"
    jan: Optional[str] = None
    fev: Optional[str] = None
    mar: Optional[str] = None
    abr: Optional[str] = None
    mai: Optional[str] = None
    jun: Optional[str] = None
    jul: Optional[str] = None
    ago: Optional[str] = None
    set: Optional[str] = None
    out: Optional[str] = None
    nov: Optional[str] = None
    dez: Optional[str] = None
    no_ano: Optional[str] = None
    acumulado: Optional[str] = None


class BtgEstatisticas(BaseModel):
    """Estatísticas de desempenho por período (págs. 5-6)."""
    maior_rent_mensal: list[str]    # [Mês, Ano, 12M, 24M, 36M, Acum]
    menor_rent_mensal: list[str]
    volatilidade: list[str]
    meses_retorno_positivo: list[str]
    meses_retorno_negativo: list[str]
    meses_acima_cdi: list[str]
    meses_abaixo_cdi: list[str]


# ---------------------------------------------------------------------------
# Págs. 7-8 — Rentabilidade completa por classe e ativo
# ---------------------------------------------------------------------------

class BtgAtivoPosicao(BaseModel):
    """Ativo individual dentro de uma classe (págs. 7-8)."""
    nome: str
    saldo_bruto: str
    saldo_pl_pct: str
    mes_pct: Optional[str] = None
    ano_pct: Optional[str] = None
    doze_meses_pct: Optional[str] = None
    acumulado_pct: Optional[str] = None
    mes_rs: Optional[str] = None
    ano_rs: Optional[str] = None
    doze_meses_rs: Optional[str] = None
    acumulado_rs: Optional[str] = None
    data_inicial: Optional[str] = None


class BtgClassePosicao(BaseModel):
    """Classe de ativos com seus ativos e total (págs. 7-8)."""
    nome_classe: str
    percentual_total: str
    valor_total: str
    ativos: list[BtgAtivoPosicao]
    total_mes_rs: Optional[str] = None
    total_ano_rs: Optional[str] = None
    total_12m_rs: Optional[str] = None
    total_acum_rs: Optional[str] = None


# ---------------------------------------------------------------------------
# Pág. 9 — Posição consolidada por devedor/garantidor
# ---------------------------------------------------------------------------

class BtgDevedorConsolidado(BaseModel):
    """Linha da posição consolidada de renda fixa por devedor (pág. 9)."""
    devedor: str
    saldo_bruto: str
    percentual: str


# ---------------------------------------------------------------------------
# Págs. 10-11 — Principais números por mercado e estratégia
# ---------------------------------------------------------------------------

class BtgAtivoNumeros(BaseModel):
    """Ativo individual na visão de principais números (págs. 10-11)."""
    nome: str
    data_inicial: Optional[str] = None
    quantidade: Optional[str] = None
    vencimento: Optional[str] = None
    taxa: Optional[str] = None
    resgate: Optional[str] = None
    saldo_bruto: str
    preco_medio: Optional[str] = None
    saldo_liquido: Optional[str] = None
    valor_aplicado: Optional[str] = None


class BtgClasseNumeros(BaseModel):
    """Classe de ativos na visão de principais números (págs. 10-11)."""
    nome_classe: str
    percentual_total: str
    valor_total: str
    ativos: list[BtgAtivoNumeros]
    total_saldo_bruto: Optional[str] = None
    total_saldo_liquido: Optional[str] = None
    total_valor_aplicado: Optional[str] = None


# ---------------------------------------------------------------------------
# Modelo raiz
# ---------------------------------------------------------------------------

class BtgPortfolioData(BaseModel):
    """Consolidação completa do Relatório de Performance BTG Pactual."""
    banco: BankInfo
    resumo: BtgResumo
    historico_movimentacoes: list[BtgHistoricoMes]
    rentabilidade_mensal_12m: list[BtgRentabilidadeMensalItem]
    estrategias: list[BtgEstrategia]
    retornos_mensais: list[BtgRetornoMensal]
    estatisticas: BtgEstatisticas
    posicao_rentabilidade: list[BtgClassePosicao]
    posicao_consolidada: list[BtgDevedorConsolidado]
    numeros_mercado: list[BtgClasseNumeros]
