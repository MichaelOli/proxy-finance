"""
Sub-parser: Pág. 9 — Posição consolidada por devedor/garantidor.

"""
import re

from loguru import logger

from app.domain.models.btg_portfolio import BtgDevedorConsolidado

_SECTION_START_RE = re.compile(
    r"Posição consolidada por devedor/garantidor",
    re.IGNORECASE,
)
_SECTION_END_RE = re.compile(
    r"Os principais números",
    re.IGNORECASE,
)

_DEVEDOR_RE = re.compile(
    r"^([A-ZÁÉÍÓÚÀ-Ú][^\n]+?)\s+"
    r"R\$\s*([\d\.]+,\d+)\s+"
    r"(-?[\d,]+%)\s*$",
    re.MULTILINE,
)


def parse_posicao_consolidada(full_text: str) -> list[BtgDevedorConsolidado]:
    """Extrai a posição consolidada por devedor (pág. 9)."""
    m_start = _SECTION_START_RE.search(full_text)
    if not m_start:
        logger.warning("BtgPosicaoConsolidada: seção não encontrada")
        return []

    section = full_text[m_start.start():]
    m_end = _SECTION_END_RE.search(section)
    if m_end:
        section = section[: m_end.start()]

    result: list[BtgDevedorConsolidado] = []
    for m in _DEVEDOR_RE.finditer(section):
        devedor = m.group(1).strip()
        # Ignora linhas de cabeçalho
        if devedor in ("Saldo Bruto", "Renda fixa", "Percentual"):
            continue
        result.append(BtgDevedorConsolidado(
            devedor=devedor,
            saldo_bruto=m.group(2),
            percentual=m.group(3),
        ))

    logger.debug("BtgPosicaoConsolidada: {} devedores", len(result))
    return result
