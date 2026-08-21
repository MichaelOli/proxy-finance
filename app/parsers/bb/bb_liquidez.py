"""
Sub-parser responsável pela seção LIQUIDEZ DA CARTEIRA do extrato Banco do Brasil.

Layout real (pdfplumber):
  0 R$ 29.130,22 R$ 0,00 R$ 29.130,22 R$ 29.126,05 5,68%
  De 4 a 30 R$ 136.701,59 R$ 0,00 R$ 136.701,59 R$ 136.701,59 26,68%
  Acima de 360 R$ 346.596,24 R$ 0,00 R$ 346.596,24 R$ 346.596,24 67,64%
  CARTEIRA R$ 512.428,05 R$ 0,00 R$ 512.428,05 R$ 512.423,88 100,00%
"""
import re

from loguru import logger

from app.domain.models.portfolio import LiquidezCarteira, LiquidezFaixa, LiquidezTotal


_BRL = r"R\$\s*([\d\.]+,\d{2})"
_PCT = r"([\d,]+)%"


def _norm(v: str) -> str:
    return v.replace(".", "").replace(",", ".")


def parse_liquidez_carteira(text: str) -> LiquidezCarteira:
    block = _extract_block(text, "Liquidez da carteira", ["ReRnEtaNbilTidAadBeILIDADE", "RENTABILIDADE"])
    if not block:
        logger.warning("bb_liquidez: bloco 'Liquidez da carteira' não encontrado.")
        return LiquidezCarteira(faixas=[], total=_empty_total())

    faixas = _parse_faixas(block)
    total = _parse_total(block)

    return LiquidezCarteira(faixas=faixas, total=total)


def _extract_block(text: str, start_marker: str, end_markers: list[str]) -> str:
    start = re.search(re.escape(start_marker), text, re.IGNORECASE)
    if not start:
        # Fallback: case-insensitive partial match
        start = re.search(r"Liquidez\s+da\s+carteira", text, re.IGNORECASE)
    if not start:
        return ""
    end_pos = len(text)
    for marker in end_markers:
        m = re.search(marker, text[start.end():], re.IGNORECASE)
        if m:
            candidate = start.end() + m.start()
            if candidate < end_pos:
                end_pos = candidate
    return text[start.start(): end_pos]


def _parse_faixas(block: str) -> list[LiquidezFaixa]:
    """
    Linhas de prazo: '0', 'De X a Y', 'Acima de Z'.
    Padrão: prazo + 4 valores R$ + PCT%.
    """
    prazo_pattern = re.compile(
        rf"^(0|De\s+\d+\s+a\s+\d+|Acima\s+de\s+\d+)\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_PCT}",
        re.MULTILINE | re.IGNORECASE,
    )

    faixas: list[LiquidezFaixa] = []
    for m in prazo_pattern.finditer(block):
        faixas.append(
            LiquidezFaixa(
                prazo_dias=m.group(1).strip(),
                total_bruto=_norm(m.group(2)),
                bruto_bloqueado=_norm(m.group(3)),
                bruto_disponivel=_norm(m.group(4)),
                liquido_disponivel=_norm(m.group(5)),
                participacao=_norm(m.group(6)),
            )
        )

    return faixas


def _parse_total(block: str) -> LiquidezTotal:
    """
    Linha de total — rotulada como 'CARTEIRA' ou 'Total' no PDF do BB.
    """
    total_pattern = re.compile(
        rf"(?:Total|CARTEIRA)\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_PCT}",
        re.IGNORECASE,
    )
    m = total_pattern.search(block)
    if not m:
        return _empty_total()

    return LiquidezTotal(
        total_bruto=_norm(m.group(1)),
        bruto_bloqueado=_norm(m.group(2)),
        bruto_disponivel=_norm(m.group(3)),
        liquido_disponivel=_norm(m.group(4)),
        participacao=_norm(m.group(5)),
    )


def _empty_total() -> LiquidezTotal:
    return LiquidezTotal(
        total_bruto="0.00",
        bruto_bloqueado="0.00",
        bruto_disponivel="0.00",
        liquido_disponivel="0.00",
        participacao="0.00",
    )
