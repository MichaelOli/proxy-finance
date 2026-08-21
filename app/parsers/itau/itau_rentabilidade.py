"""
Sub-parser: Pág. 2 — Histórico de rentabilidade mensal.
"""
import re

from loguru import logger

from app.domain.models.itau_portfolio import ItauMesHistorico, ItauRentabilidade

# Linha de meses — sequência de abreviações
_MESES_RE = re.compile(
    r"((?:Jan|Fev|Mar|Abr|Maio|Jun|Jul|Ago|Set|Out|Nov|Dez)/\d{2}"
    r"(?:\s+(?:Jan|Fev|Mar|Abr|Maio|Jun|Jul|Ago|Set|Out|Nov|Dez)/\d{2}){3,})"
)

# Linha "INDICADOR valor1 valor2 ..." — indicador PRIMEIRO, depois valores
_LINHA_RE = re.compile(
    r"^(Carteira|CDI|IBOV|IPCA|dólar)\s+(-?[\d,]+(?:\s+-?[\d,]+){3,})\s*$",
    re.MULTILINE,
)

_NUM_RE = re.compile(r"-?[\d]+,\d+")


def _block_p2(text: str) -> str:
    """Isola o texto da pág. 2 (entre '2 de 16' e '3 de 16')."""
    m_start = re.search(r"\b2\s+de\s+16\b", text)
    m_end   = re.search(r"\b3\s+de\s+16\b", text)
    if m_start and m_end:
        return text[m_start.end(): m_end.start()]
    if m_start:
        return text[m_start.end(): m_start.end() + 2000]
    return text[1500:4000]


def parse_rentabilidade(text: str) -> ItauRentabilidade:
    """Extrai o histórico mensal de rentabilidade (página 2)."""
    bloco = _block_p2(text)

    # Meses (na mesma linha, espaço-separados)
    m = _MESES_RE.search(bloco)
    meses: list[str] = m.group(1).split() if m else []

    # Valores por indicador
    dados: dict[str, list[str]] = {}
    for m in _LINHA_RE.finditer(bloco):
        indicador = m.group(1)
        valores   = _NUM_RE.findall(m.group(2))
        dados[indicador] = valores

    if not meses or not dados.get("Carteira"):
        logger.warning("itau_rentabilidade: meses ou Carteira não encontrados.")
        return ItauRentabilidade(historico=[])

    n = min(len(meses), len(dados["Carteira"]))
    historico: list[ItauMesHistorico] = []
    for i in range(n):
        historico.append(ItauMesHistorico(
            mes=meses[i],
            carteira=_get(dados, "Carteira", i),
            cdi=_get(dados, "CDI", i),
            ibov=_get(dados, "IBOV", i),
            ipca=_get(dados, "IPCA", i),
            dolar=_get(dados, "dólar", i),
        ))

    logger.debug("itau_rentabilidade: {} meses extraídos.", len(historico))
    return ItauRentabilidade(historico=historico)


def _get(dados: dict[str, list[str]], chave: str, idx: int) -> str:
    lst = dados.get(chave, [])
    return lst[idx] if idx < len(lst) else "-"
