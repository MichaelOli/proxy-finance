"""
Sub-parser: Conta Corrente Safra (página 9).

Extrai:
  - Saldo Disponível
  - Saldo Poupança Plus (pode ser "-")
  - Saldo Total
"""
import re
from typing import Optional

from app.domain.models.safra_portfolio import SafraContaCorrente

_SECTION_START = re.compile(r"Conta Corrente")
_SECTION_END = re.compile(r"Notas|-- 9 of 12 --")

_SALDO_DISP_RE = re.compile(r"Saldo Disponivel\s+(-?[\d\.]+,\d+|-)")
_SALDO_POUPA_RE = re.compile(r"Saldo Poupanca Plus\s+(-?[\d\.]+,\d+|-)")
_SALDO_TOTAL_RE = re.compile(r"Saldo Total\s+(-?[\d\.]+,\d+|-)")


def _extract_section(text: str) -> str:
    m_start = _SECTION_START.search(text)
    if not m_start:
        return ""
    m_end = _SECTION_END.search(text, m_start.end())
    end_pos = m_end.start() if m_end else len(text)
    return text[m_start.start():end_pos]


def _opt(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    return None if v.strip() == "-" else v.strip()


def parse_conta_corrente(text: str) -> Optional[SafraContaCorrente]:
    """
    Extrai os saldos da conta corrente (página 9).
    Retorna None se a seção não for encontrada.
    """
    section = _extract_section(text)
    if not section:
        return None

    m_disp = _SALDO_DISP_RE.search(section)
    m_poupa = _SALDO_POUPA_RE.search(section)
    m_total = _SALDO_TOTAL_RE.search(section)

    if not m_disp or not m_total:
        return None

    return SafraContaCorrente(
        saldo_disponivel=m_disp.group(1),
        saldo_poupanca_plus=_opt(m_poupa.group(1)) if m_poupa else None,
        saldo_total=m_total.group(1),
    )
