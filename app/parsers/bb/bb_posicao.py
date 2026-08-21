"""
Sub-parser responsável pela seção POSIÇÃO DA CARTEIRA do extrato Banco do Brasil.
"""
import re

from loguru import logger

from app.domain.models.portfolio import PosicaoItem


_BRL = r"R\$\s*([\d\.]+,\d{2})"
_PCT = r"([\d,]+)%"


def _norm(v: str) -> str:
    return v.replace(".", "").replace(",", ".")


def parse_posicao_carteira(text: str) -> list[PosicaoItem]:
    block = _extract_posicao_block(text)
    if not block:
        logger.warning("bb_posicao: bloco 'Posição da carteira' não encontrado.")
        return []

    items: list[PosicaoItem] = []

    # Usa [^\n]+ (não exclui R) para capturar a classe inteira.
    # RENDA FIXA PRÉ contém 'R' então [^R\n] falharia — usamos [^\n]+? (lazy até R$).
    line_pattern = re.compile(
        rf"^(RENDA[^\n]+?)\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_PCT}",
        re.MULTILINE | re.IGNORECASE,
    )

    for m in line_pattern.finditer(block):
        items.append(
            PosicaoItem(
                classe=m.group(1).strip(),
                saldo_bruto_inicio=_norm(m.group(2)),
                entradas=_norm(m.group(3)),
                saidas=_norm(m.group(4)),
                saldo_bruto_fim=_norm(m.group(5)),
                provisao_ir_iof=_norm(m.group(6)),
                saldo_liquido=_norm(m.group(7)),
                rentabilidade_percentual=_norm(m.group(8)),
            )
        )

    if not items:
        logger.warning("bb_posicao: nenhuma linha de posição extraída do bloco.")

    return items


def _extract_posicao_block(text: str) -> str:
    """
    Extrai o bloco entre 'Posição da carteira' e a próxima seção de alto nível.
    """
    start = re.search(r"Posi[çc][aã]o\s+da\s+carteira", text, re.IGNORECASE)
    if not start:
        return ""

    text_after_start = text[start.start():]

    # A próxima seção começa com "Renda Fixa Pós Cdi Alocação:" (distribuição)
    # ou com "Liquidez da carteira"
    end_markers = [
        r"Renda\s+Fixa\s+P[oó]s\s+Cdi\s+Aloca",
        r"Liquidez\s+da\s+carteira",
        r"ReRnEtaNbilTidAadBeILIDADE",
    ]
    end_pos = len(text_after_start)
    for marker in end_markers:
        m = re.search(marker, text_after_start[len("Posição da carteira"):], re.IGNORECASE)
        if m:
            candidate = len("Posição da carteira") + m.start()
            if candidate < end_pos:
                end_pos = candidate

    return text_after_start[:end_pos]
