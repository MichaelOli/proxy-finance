"""
Sub-parser: Resumo Safra (página 1).

Extrai:
- Agência e conta
- Data da posição
- Patrimônio: saldo bruto BRL/USD, impostos, saldo líquido
- Rentabilidade da carteira: mês/ano/12M/24M/36M em % e %CDI
- Composição por classe: Renda fixa, Renda variável, Poupança (%)
"""
import re

from app.domain.models.safra_portfolio import (
    SafraComposicaoClasse,
    SafraPatrimonio,
    SafraRentabilidadeCarteira,
    SafraResumo,
)

_AGENCIA_CONTA_RE = re.compile(r"Agência:\s*(\d+)\s*/\s*Conta:\s*(\S+)")
_DATA_POSICAO_RE = re.compile(r"Data da posição:\s*(\d{2}/\d{2}/\d{4})")

# Valor numérico BR (positivo ou negativo) ou traço isolado
_V = r"(-?[\d\.]+,\d+|-)"

# Linha "Carteira <14 valores separados por \s+>"
# Grupos 1–14: saldo_bruto_brl, saldo_bruto_usd, impostos, saldo_liquido,
#              mes_pct, mes_pct_cdi, ano_pct, ano_pct_cdi,
#              12m_pct, 12m_pct_cdi, 24m_pct, 24m_pct_cdi, 36m_pct, 36m_pct_cdi
_CARTEIRA_RE = re.compile(
    r"Carteira\s+" + r"\s+".join([_V] * 14)
)

# "Renda fixa | 82.21 %" ou "Renda variável | 17.75 %"
_COMPOSICAO_RE = re.compile(
    r"(Renda fixa|Renda variável|Poupança)\s*\|\s*([\d.]+)\s*%",
    re.IGNORECASE,
)


def parse_resumo(text: str) -> SafraResumo:
    """
    Extrai o resumo da página 1 do extrato Safra.

    Raises:
        ValueError: Se a linha de patrimônio não for encontrada.
    """
    m_ag = _AGENCIA_CONTA_RE.search(text)
    agencia = m_ag.group(1) if m_ag else ""
    conta = m_ag.group(2) if m_ag else ""

    m_dt = _DATA_POSICAO_RE.search(text)
    data_posicao = m_dt.group(1) if m_dt else ""

    m_c = _CARTEIRA_RE.search(text)
    if not m_c:
        raise ValueError("Safra: linha de patrimônio 'Carteira' não encontrada no resumo.")

    g = [m_c.group(i) for i in range(1, 15)]

    patrimonio = SafraPatrimonio(
        saldo_bruto_brl=g[0],
        saldo_bruto_usd=g[1],
        impostos=g[2],
        saldo_liquido=g[3],
    )

    rentabilidade_carteira = SafraRentabilidadeCarteira(
        mes_pct=g[4],
        mes_pct_cdi=g[5],
        ano_pct=g[6],
        ano_pct_cdi=g[7],
        doze_meses_pct=g[8],
        doze_meses_pct_cdi=g[9],
        vinte_quatro_meses_pct=g[10],
        vinte_quatro_meses_pct_cdi=g[11],
        trinta_seis_meses_pct=g[12],
        trinta_seis_meses_pct_cdi=g[13],
    )

    composicao_por_classe = [
        SafraComposicaoClasse(classe=m.group(1), percentual=m.group(2))
        for m in _COMPOSICAO_RE.finditer(text)
    ]

    return SafraResumo(
        agencia=agencia,
        conta=conta,
        data_posicao=data_posicao,
        patrimonio=patrimonio,
        rentabilidade_carteira=rentabilidade_carteira,
        composicao_por_classe=composicao_por_classe,
    )
