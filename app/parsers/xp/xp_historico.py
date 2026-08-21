"""
Sub-parser: Histórico anual XP (página 2).
"""

import re
from typing import Optional

from app.domain.models.xp_portfolio import XpAnoHistorico, XpMesHistorico

_MESES_LABELS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                 "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Extrai todos os valores percentuais ou "-" de uma linha
_VALUE_RE = re.compile(r"-?[\d,]+%|-")

# Bloco: linha do Portfólio, depois o ano, depois linha do %CDI
_YEAR_BLOCK_RE = re.compile(
    r"^Portfólio\s+(.+?)\r?\n(\d{4})\r?\n%CDI\s+(.+?)(?:\r?\n|$)",
    re.MULTILINE,
)


def _opt(v: str) -> Optional[str]:
    return None if v.strip() == "-" else v.strip()


def parse_historico(text: str) -> list[XpAnoHistorico]:
    anos: list[XpAnoHistorico] = []

    for block in _YEAR_BLOCK_RE.finditer(text):
        port_line = block.group(1)
        ano_label = block.group(2)
        cdi_line = block.group(3)

        port_vals = _VALUE_RE.findall(port_line)
        cdi_vals = _VALUE_RE.findall(cdi_line)

        # 14 valores esperados: 12 meses + Ano + Acum
        meses: list[XpMesHistorico] = []
        for i, label in enumerate(_MESES_LABELS):
            rent = _opt(port_vals[i]) if i < len(port_vals) else None
            pct_cdi = _opt(cdi_vals[i]) if i < len(cdi_vals) else None
            meses.append(XpMesHistorico(mes=label, rentabilidade=rent, percentual_cdi=pct_cdi))

        rent_ano = _opt(port_vals[12]) if len(port_vals) > 12 else None
        acum = _opt(port_vals[13]) if len(port_vals) > 13 else None

        anos.append(
            XpAnoHistorico(
                ano=ano_label,
                rentabilidade_no_ano=rent_ano or "0,00%",
                acumulado=acum,
                meses=meses,
            )
        )

    # Garante ordem cronológica crescente (mais antigo primeiro)
    anos.sort(key=lambda a: int(a.ano))
    return anos
