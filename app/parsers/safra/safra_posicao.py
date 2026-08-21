"""
Sub-parser: Posição de investimentos Safra (página 4).

"""
import re

from app.domain.models.safra_portfolio import SafraPosicaoItem

_SECTION_START = re.compile(r"Posição de Investimentos")
_SECTION_END = re.compile(r"Investimentos Resumo Composição|-- 4 of 12 --")

_SUBTOTAIS = {"RENDA FIXA", "RENDA VARIÁVEL", "POUPANÇA", "POUPANCA"}

_V = r"(-?[\d\.]+,\d+|-)"

# 9 valores por linha
_ROW_RE = re.compile(
    r"^([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9 /\.]+?)\s+"
    + r"\s+".join([_V] * 9)
    + r"\s*$",
    re.MULTILINE,
)


def _extract_section(text: str) -> str:
    m_start = _SECTION_START.search(text)
    if not m_start:
        return ""
    m_end = _SECTION_END.search(text, m_start.end())
    end_pos = m_end.start() if m_end else len(text)
    return text[m_start.start():end_pos]


def parse_posicao(text: str) -> list[SafraPosicaoItem]:
    """
    Extrai a posição de investimentos (página 4).
    Deduplica "POUPANCA" (variante sem acento de "POUPANÇA").
    """
    section = _extract_section(text)
    if not section:
        return []

    itens: list[SafraPosicaoItem] = []
    seen: set[str] = set()

    for row in _ROW_RE.finditer(section):
        descricao = row.group(1).strip()

        if descricao.upper() == "POUPANCA":
            continue
        if descricao in seen:
            continue
        seen.add(descricao)

        g = [row.group(i) for i in range(2, 11)]
        itens.append(
            SafraPosicaoItem(
                descricao=descricao,
                eh_subtotal=descricao.upper() in _SUBTOTAIS,
                saldo_bruto=g[0],
                impostos=g[1],
                saldo_liquido=g[2],
                percentual_pl=g[3],
                rentabilidade_mes=g[4],
                rentabilidade_ano=g[5],
                rentabilidade_12m=g[6],
                rentabilidade_24m=g[7],
                rentabilidade_36m=g[8],
            )
        )

    return itens
