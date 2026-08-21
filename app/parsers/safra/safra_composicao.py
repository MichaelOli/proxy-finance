"""
Sub-parser: Investimentos Resumo Composição / Movimentação Safra (página 5).

"""
import re

from app.domain.models.safra_portfolio import SafraComposicaoItem

_SECTION_START = re.compile(r"Investimentos Resumo Composição")
_SECTION_END = re.compile(r"Detalhamento de Fundos|-- 5 of 12 --")

_SUBTOTAIS = {"RENDA FIXA", "RENDA VARIÁVEL", "POUPANÇA", "POUPANCA"}

_V = r"(-?[\d\.]+,\d+|-)"

# 8 valores por linha
_ROW_RE = re.compile(
    r"^([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9 /\.]+?)\s+"
    + r"\s+".join([_V] * 8)
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


def parse_composicao(text: str) -> list[SafraComposicaoItem]:
    """
    Extrai a composição / movimentação do mês (página 5).
    Deduplica "POUPANCA" (variante sem acento).
    """
    section = _extract_section(text)
    if not section:
        return []

    itens: list[SafraComposicaoItem] = []
    seen: set[str] = set()

    for row in _ROW_RE.finditer(section):
        descricao = row.group(1).strip()

        if descricao.upper() == "POUPANCA":
            continue
        if descricao in seen:
            continue
        seen.add(descricao)

        g = [row.group(i) for i in range(2, 10)]
        itens.append(
            SafraComposicaoItem(
                descricao=descricao,
                eh_subtotal=descricao.upper() in _SUBTOTAIS,
                saldo_bruto_anterior=g[0],
                aplicacoes=g[1],
                resgates=g[2],
                impostos_incorridos=g[3],
                rendimento_mes=g[4],
                saldo_bruto_atual=g[5],
                impostos_previstos=g[6],
                saldo_liquido_atual=g[7],
            )
        )

    return itens
