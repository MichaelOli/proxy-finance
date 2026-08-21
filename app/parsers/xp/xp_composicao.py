"""
Sub-parser: Composição por estratégia XP (páginas 4–5).

Cada linha da tabela tem:
  nome (percentual%) R$ saldo_bruto  rent_mes  rent_ano  rent_12m  rent_24m

Artefato do PDF: percentagens do gráfico aparecem antes do nome (ex: "100,00% Pré Fixado").
O parser normaliza removendo esses prefixos.
Valores "-" são convertidos para None no modelo.
"""
import re
from typing import Optional

from app.domain.models.xp_portfolio import XpEstrategia

_ESTRATEGIA_RE = re.compile(
    r"(?:[\d,]+%\s+)?"                          # prefixo artefato do gráfico (opcional)
    r"(Pós Fixado|Inflação|Pré Fixado|Caixa|Proventos)"
    r"\s+\(([\d,]+%)\)"                          # percentual de alocação
    r"\s+R\$\s+([\d\.,]+)"                       # saldo bruto
    r"\s+(-?[\d,]+%|-)"                          # rentabilidade mês
    r"\s+(-?[\d,]+%|-)"                          # rentabilidade ano
    r"\s+(-?[\d,]+%|-)"                          # rentabilidade 12M
    r"\s+(-?[\d,]+%|-)",                         # rentabilidade 24M
    re.MULTILINE,
)


def _opt(v: str) -> Optional[str]:
    return None if v.strip() == "-" else v.strip()


def parse_composicao(text: str) -> list[XpEstrategia]:
    estrategias: list[XpEstrategia] = []
    for m in _ESTRATEGIA_RE.finditer(text):
        estrategias.append(
            XpEstrategia(
                nome=m.group(1),
                percentual_alocacao=m.group(2),
                saldo_bruto=m.group(3),
                rentabilidade_mes=_opt(m.group(4)),
                rentabilidade_ano=_opt(m.group(5)),
                rentabilidade_12m=_opt(m.group(6)),
                rentabilidade_24m=_opt(m.group(7)),
            )
        )
    return estrategias
