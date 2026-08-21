"""
Sub-parser: Págs. 2-3 — Histórico de movimentações e rentabilidade mensal dos últimos 12M.

Pág. 2: tabela de movimentações mensais (Data, Patrimônio inicial, Movimentações, IR Pago,
        Patrimônio final, Ganho, Portfolio%, CDI).

Pág. 3: tabela comparativa de rentabilidade (Rent. do portfólio R$, Portfólio %, CDI, Dólar, Ibovespa)
        com colunas por mês.
"""
import re

from loguru import logger

from app.domain.models.btg_portfolio import BtgHistoricoMes, BtgRentabilidadeMensalItem

# ---------------------------------------------------------------------------
# Pág. 2 — Movimentações mensais
# ---------------------------------------------------------------------------
# Movimentações pode ser negativa: "-R$ 13.851,79"
_BRL_SIGNED = r"-?R\$\s*([\d\.]+,\d+)"
_PCT = r"(-?[\d,]+%)"

_MOV_RE = re.compile(
    r"^([A-Za-záéíóúÁÉÍÓÚ]{3}/\d{2})\s+"     # Data (Dez/25, Nov/25 etc.)
    r"R\$\s*([\d\.]+,\d+)\s+"                  # Patrimônio inicial
    r"(-?R\$\s*[\d\.]+,\d+)\s+"               # Movimentações (pode ser negativo)
    r"R\$\s*([\d\.]+,\d+)\s+"                  # IR Pago
    r"R\$\s*([\d\.]+,\d+)\s+"                  # Patrimônio final
    r"R\$\s*([\d\.]+,\d+)\s+"                  # Ganho
    r"(-?[\d,]+%)\s+"                          # Portfolio%
    r"(-?[\d,]+%)\s*$",                         # CDI%
    re.MULTILINE,
)

# ---------------------------------------------------------------------------
# Pág. 3 — Rentabilidade mensal dos últimos 12M
# ---------------------------------------------------------------------------

_RENT_12M_SECTION_START = re.compile(
    r"Rentabilidade dos últimos 12 meses",
)
_RENT_12M_SECTION_END = re.compile(
    r"E,\s+quando abrimos|A rentabilidade por estratégia",
)

# Cada linha da tabela inicia com um label seguido de valores numéricos/percentuais
_RENT_12M_ROW_RE = re.compile(
    r"^(Rent(?:\.|abilidade)?\s+do\s+portfólio\s+R\$|"
    r"Portfólio\s+%|CDI|Dólar|Ibovesp\w*)\s+(.+)$",
    re.MULTILINE | re.IGNORECASE,
)

_RENT_12M_VALUE_RE = re.compile(r"(-?[\d\.]+,\d+%?|-)")


def parse_historico_movimentacoes(full_text: str) -> list[BtgHistoricoMes]:
    """Extrai as linhas de movimentação mensal (pág. 2)."""
    result: list[BtgHistoricoMes] = []
    for m in _MOV_RE.finditer(full_text):
        result.append(BtgHistoricoMes(
            data=m.group(1),
            patrimonio_inicial=m.group(2),
            movimentacoes=m.group(3).strip(),
            ir_pago=m.group(4),
            patrimonio_final=m.group(5),
            ganho=m.group(6),
            portfolio_pct=m.group(7),
            cdi_pct=m.group(8),
        ))
    logger.debug("BtgHistorico: {} meses de movimentação", len(result))
    return result


def parse_rentabilidade_12m(full_text: str) -> list[BtgRentabilidadeMensalItem]:
    """Extrai a tabela de rentabilidade comparativa dos últimos 12M (pág. 3)."""
    # Isola a seção entre o título e o início da próxima seção
    m_start = _RENT_12M_SECTION_START.search(full_text)
    if not m_start:
        logger.warning("BtgHistorico: seção rentabilidade 12M não encontrada")
        return []

    section_text = full_text[m_start.start():]
    m_end = _RENT_12M_SECTION_END.search(section_text)
    if m_end:
        section_text = section_text[: m_end.start()]

    result: list[BtgRentabilidadeMensalItem] = []
    for m in _RENT_12M_ROW_RE.finditer(section_text):
        label = m.group(1).strip()
        values_raw = m.group(2).strip()
        valores = _RENT_12M_VALUE_RE.findall(values_raw)
        result.append(BtgRentabilidadeMensalItem(
            indicador=label,
            valores=valores,
        ))
    logger.debug("BtgHistorico: {} linhas de rentabilidade 12M", len(result))
    return result
