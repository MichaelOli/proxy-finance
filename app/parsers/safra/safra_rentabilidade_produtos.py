"""
Sub-parser: Rentabilidade histórica de produtos Safra (página 3).

Extrai linhas de rentabilidade por classe de ativo (RENDA FIXA, MULTIMERCADO,
RENDA VARIÁVEL, POUPANÇA) e por fundo individual, com os mesmos 16 valores
da tabela do histórico (12 mensais + Ano/12M/24M/36M acumulados).

Valores podem conter "-" para períodos sem dados (ex: fundos encerrados).
"""
import re

from app.domain.models.safra_portfolio import SafraProdutoLinha

_SECTION_START = re.compile(r"Rentabilidade Histórica de Produtos")
_SECTION_END = re.compile(r"Posição de Investimentos|-- 3 of 12 --")

# Classes de ativo que representam subtotais
_SUBTOTAIS = {"RENDA FIXA", "MULTIMERCADO", "RENDA VARIÁVEL", "POUPANÇA", "POUPANCA"}

_V = r"(-?[\d\.]+,\d+|-)"

# Linha: <DESCRICAO> <16 valores separados por espaço/tab>
# A descrição pode conter letras maiúsculas, espaços, acentos e alguns especiais
_ROW_RE = re.compile(
    r"^([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9 %/\.]+?)\s+"
    + r"\s+".join([_V] * 16)
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


def _opt(v: str) -> str | None:
    return None if v.strip() == "-" else v.strip()


def parse_rentabilidade_produtos(text: str) -> list[SafraProdutoLinha]:
    """
    Extrai todas as linhas de rentabilidade de produtos (página 3).
    Deduplica linhas "POUPANCA" (variante sem acento de "POUPANÇA").
    """
    section = _extract_section(text)
    if not section:
        return []

    linhas: list[SafraProdutoLinha] = []
    seen_descricoes: set[str] = set()

    for row in _ROW_RE.finditer(section):
        descricao = row.group(1).strip()

        # Ignora duplicata sem acento (POUPANCA == POUPANÇA)
        if descricao.upper() == "POUPANCA":
            continue
        if descricao in seen_descricoes:
            continue
        seen_descricoes.add(descricao)

        vals = [row.group(i) for i in range(2, 18)]
        linhas.append(
            SafraProdutoLinha(
                descricao=descricao,
                eh_subtotal=descricao.upper() in _SUBTOTAIS,
                valores_mensais=vals[:12],
                acumulado_ano=_opt(vals[12]),
                acumulado_12m=_opt(vals[13]),
                acumulado_24m=_opt(vals[14]),
                acumulado_36m=_opt(vals[15]),
            )
        )

    return linhas
