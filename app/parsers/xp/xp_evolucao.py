"""
Sub-parser: Evolução patrimonial XP (página 3).

Cada linha da tabela tem:
  data  patrimonio_inicial  movimentacoes  ir  iof  patrimonio_final  ganho_financeiro  rent  %cdi

Valores monetários podem ser negativos: -R$ 366,51
Retorna N linhas (uma por mês presente no documento).
"""
import re

from app.domain.models.xp_portfolio import XpEvolucaoMes

# Valor monetário: opcional sinal, "R$ ", dígitos
_MONEY = r"-?R\$\s+[\d\.,]+"

_ROW_RE = re.compile(
    r"^(\w+\./\d{2})"                     # data: "jul./25"
    r"\s+R\$\s+([\d\.,]+)"                 # patrimônio inicial
    r"\s+(-?R\$\s+[\d\.,]+)"              # movimentações (pode ser negativo)
    r"\s+(-?R\$\s+[\d\.,]+)"              # ir
    r"\s+(-?R\$\s+[\d\.,]+)"              # iof
    r"\s+R\$\s+([\d\.,]+)"                # patrimônio final
    r"\s+R\$\s+([\d\.,]+)"                # ganho financeiro
    r"\s+(-?[\d,]+%)"                     # rentabilidade
    r"\s+([\d,]+%)\s*$",                  # %CDI
    re.MULTILINE,
)


def _clean_money(v: str) -> str:
    """Remove espaço interno em '-R$ 366,51' → '-R$366,51' mantendo sinal."""
    return v.strip().replace(" ", "")


def parse_evolucao(text: str) -> list[XpEvolucaoMes]:
    meses: list[XpEvolucaoMes] = []
    for m in _ROW_RE.finditer(text):
        meses.append(
            XpEvolucaoMes(
                data=m.group(1),
                patrimonio_inicial=m.group(2),
                movimentacoes=_clean_money(m.group(3)),
                ir=_clean_money(m.group(4)),
                iof=_clean_money(m.group(5)),
                patrimonio_final=m.group(6),
                ganho_financeiro=m.group(7),
                rentabilidade=m.group(8),
                percentual_cdi=m.group(9),
            )
        )
    return meses
