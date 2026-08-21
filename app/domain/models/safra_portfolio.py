"""
Modelos Pydantic exclusivos do Banco Safra.
Todos os campos monetários e percentuais são str para preservar os valores exatos do PDF.
Campos opcionais usam `= None` explícito (Pydantic v2).
"""
from typing import Optional

from pydantic import BaseModel

from app.domain.models.portfolio import BasePortfolioData, BankInfo


# ---------------------------------------------------------------------------
# Resumo (página 1)
# ---------------------------------------------------------------------------

class SafraPatrimonio(BaseModel):
    saldo_bruto_brl: str   # "409.429,39"
    saldo_bruto_usd: str   # "73.084,98"
    impostos: str          # "3.427,81"
    saldo_liquido: str     # "406.001,58"


class SafraRentabilidadeCarteira(BaseModel):
    mes_pct: str
    mes_pct_cdi: str
    ano_pct: str
    ano_pct_cdi: str
    doze_meses_pct: str
    doze_meses_pct_cdi: str
    vinte_quatro_meses_pct: str
    vinte_quatro_meses_pct_cdi: str
    trinta_seis_meses_pct: str
    trinta_seis_meses_pct_cdi: str


class SafraComposicaoClasse(BaseModel):
    classe: str       # "Renda fixa", "Renda variável", "Poupança"
    percentual: str   # "82.21"


class SafraResumo(BaseModel):
    agencia: str
    conta: str
    data_posicao: str
    patrimonio: SafraPatrimonio
    rentabilidade_carteira: SafraRentabilidadeCarteira
    composicao_por_classe: list[SafraComposicaoClasse]


# ---------------------------------------------------------------------------
# Histórico de rentabilidade da carteira (página 2)
# ---------------------------------------------------------------------------

class SafraHistoricoLinha(BaseModel):
    descricao: str            # "CARTEIRA", "% CDI EQUIVALENTE", "CDI", "IBOVESPA", "DOLAR"
    valores_mensais: list[str]  # 12 valores mensais (Ago/24 → Jul/25)
    acumulado_ano: str
    acumulado_12m: str
    acumulado_24m: str
    acumulado_36m: str


class SafraHistorico(BaseModel):
    meses_referencia: list[str]    # ["Ago/24", "Set/24", ..., "Jul/25"]
    linhas: list[SafraHistoricoLinha]


# ---------------------------------------------------------------------------
# Rentabilidade histórica de produtos (página 3)
# ---------------------------------------------------------------------------

class SafraProdutoLinha(BaseModel):
    descricao: str
    eh_subtotal: bool              # True para "RENDA FIXA", "RENDA VARIÁVEL", etc.
    valores_mensais: list[str]     # podem conter "-" para períodos sem dados
    acumulado_ano: Optional[str] = None
    acumulado_12m: Optional[str] = None
    acumulado_24m: Optional[str] = None
    acumulado_36m: Optional[str] = None


# ---------------------------------------------------------------------------
# Posição de investimentos (página 4)
# ---------------------------------------------------------------------------

class SafraPosicaoItem(BaseModel):
    descricao: str
    eh_subtotal: bool
    saldo_bruto: str
    impostos: str
    saldo_liquido: str
    percentual_pl: str
    rentabilidade_mes: str
    rentabilidade_ano: str
    rentabilidade_12m: str
    rentabilidade_24m: str
    rentabilidade_36m: str


# ---------------------------------------------------------------------------
# Investimentos resumo composição / movimentação (página 5)
# ---------------------------------------------------------------------------

class SafraComposicaoItem(BaseModel):
    descricao: str
    eh_subtotal: bool
    saldo_bruto_anterior: str
    aplicacoes: str
    resgates: str
    impostos_incorridos: str
    rendimento_mes: str
    saldo_bruto_atual: str
    impostos_previstos: str
    saldo_liquido_atual: str


# ---------------------------------------------------------------------------
# Detalhamento de fundos (páginas 6–7)
# ---------------------------------------------------------------------------

class SafraFundoMovimentacao(BaseModel):
    data: str
    historico: str          # "Saldo Anterior" | "Saldo Atual"
    aplicacoes: str
    resgates: str
    valor_cotas: str
    quantidade_cotas: str
    valor_bruto: str
    impostos_incorridos: str
    impostos_previstos: str
    valor_liquido: str


class SafraFundo(BaseModel):
    nome: str
    cnpj: str
    classe: str             # "RENDA FIXA" | "RENDA VARIÁVEL"
    quantidade_cotas: str
    valor_cota: str
    saldo_aplicado: str
    saldo_bruto: str
    impostos_previstos: str
    saldo_liquido: str
    movimentacoes: list[SafraFundoMovimentacao]


# ---------------------------------------------------------------------------
# Conta corrente (página 9)
# ---------------------------------------------------------------------------

class SafraContaCorrente(BaseModel):
    saldo_disponivel: str
    saldo_poupanca_plus: Optional[str] = None
    saldo_total: str


# ---------------------------------------------------------------------------
# Model raiz Safra
# ---------------------------------------------------------------------------

class SafraPortfolioData(BasePortfolioData):
    banco: BankInfo
    resumo: SafraResumo
    historico_rentabilidade: SafraHistorico
    rentabilidade_produtos: list[SafraProdutoLinha]
    posicao_investimentos: list[SafraPosicaoItem]
    composicao: list[SafraComposicaoItem]
    fundos: list[SafraFundo]
    conta_corrente: Optional[SafraContaCorrente] = None
