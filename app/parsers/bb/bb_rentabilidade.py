"""
Sub-parser responsável pela seção RENTABILIDADE do extrato Banco do Brasil.
"""
import re

from loguru import logger

from app.domain.models.portfolio import (
    Periodo,
    PeriodosReferencia,
    Rentabilidade,
    RentabilidadePercentualItem,
    RentabilidadeReaisItem,
)


_BRL = r"R\$\s*([\d\.]+,\d{2})"
_PCT_VAL = r"([\d,]+)%?"


def _norm(v: str) -> str:
    return v.replace(".", "").replace(",", ".")


def parse_rentabilidade(text: str) -> tuple[Rentabilidade, PeriodosReferencia]:
    block = _extract_block(text, "RENTABILIDADE")
    if not block:
        logger.warning("bb_rentabilidade: bloco não encontrado.")
        return (
            Rentabilidade(por_classe_percentual=[], por_classe_reais=[]),
            PeriodosReferencia(),
        )

    por_pct = _parse_percentual(block)
    por_reais = _parse_reais(block)
    periodos = _parse_periodos_referencia(text)

    return Rentabilidade(por_classe_percentual=por_pct, por_classe_reais=por_reais), periodos


def _extract_block(text: str, start_marker: str) -> str:
    start = re.search(start_marker, text, re.IGNORECASE)
    if not start:
        return ""
    return text[start.start():]


def _parse_percentual(block: str) -> list[RentabilidadePercentualItem]:
    """
    Tabela em % 
    Usa [^\n]+? (lazy) para capturar o nome da classe até o primeiro percentual.
    Precisa de delimitador após o nome: espaço + dígito.
    """
    pattern = re.compile(
        rf"^(RENDA[^\n]+?)\s+"
        rf"([\d,]+)%\s+([\d,]+)%\s+([\d,]+)%\s+([\d,]+)%\s+([\d,]+)%\s+([\d,]+)%\s+"
        rf"{_BRL}\s+([\d,]+)%",
        re.MULTILINE | re.IGNORECASE,
    )

    items: list[RentabilidadePercentualItem] = []
    for m in pattern.finditer(block):
        items.append(
            RentabilidadePercentualItem(
                classe=m.group(1).strip(),
                periodo_apurado=_norm(m.group(2)),
                no_mes=_norm(m.group(3)),
                mes_anterior=_norm(m.group(4)),
                ultimos_3_meses=_norm(m.group(5)),
                ultimos_6_meses=_norm(m.group(6)),
                ultimos_12_meses=_norm(m.group(7)),
                saldo_bruto=_norm(m.group(8)),
                participacao=_norm(m.group(9)),
            )
        )

    return items


def _parse_reais(block: str) -> list[RentabilidadeReaisItem]:
    """
    Tabela em R$ — formato: CLASSE R$ val R$ val R$ val R$ val R$ val R$ val R$ val
    """
    pattern = re.compile(
        rf"^(RENDA[^\n]+?)\s+"
        rf"{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}",
        re.MULTILINE | re.IGNORECASE,
    )

    items: list[RentabilidadeReaisItem] = []
    for m in pattern.finditer(block):
        items.append(
            RentabilidadeReaisItem(
                classe=m.group(1).strip(),
                periodo_apurado=_norm(m.group(2)),
                dia=_norm(m.group(3)),
                no_mes=_norm(m.group(4)),
                mes_anterior=_norm(m.group(5)),
                ultimos_3_meses=_norm(m.group(6)),
                ultimos_6_meses=_norm(m.group(7)),
                ultimos_12_meses=_norm(m.group(8)),
            )
        )

    return items


def _parse_periodos_referencia(text: str) -> PeriodosReferencia:
    """
    Estratégia:
      1. Encontra todos os "entre <data> e" → datas de início (na ordem: 3m, 6m, 12m)
      2. Encontra a linha com 3 datas adjacentes após as datas de início → fim de cada período
    """
    # Encontra as 3 datas de início ("entre X e")
    start_dates = re.findall(r"entre\s+(\d{2}/\d{2}/\d{4})\s+e\b", text, re.IGNORECASE)

    if not start_dates:
        return PeriodosReferencia()

    # Encontra TODAS as linhas com exatamente 3 datas (e nada mais).
    # Usa a ÚLTIMA ocorrência pois o cabeçalho de tabela de datas também tem 3 datas,
    # mas a linha do rodapé de rentabilidade ("30/05/2025 30/05/2025 30/05/2025") é a última.
    all_end_lines = re.findall(
        r"^(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s*$",
        text,
        re.MULTILINE,
    )

    if all_end_lines:
        last = all_end_lines[-1]
        fim_dates = list(last)
    else:
        # Fallback: usa a data mais recente encontrada no texto como fim universal
        all_dates = re.findall(r"\d{2}/\d{2}/\d{4}", text)
        fim_universal = all_dates[-1] if all_dates else ""
        fim_dates = [fim_universal] * 3

    periodos: list[Periodo | None] = [None, None, None]
    for i, (start, fim) in enumerate(zip(start_dates[:3], fim_dates[:3])):
        periodos[i] = Periodo(inicio=start, fim=fim)

    return PeriodosReferencia(
        ultimos_3_meses=periodos[0],
        ultimos_6_meses=periodos[1],
        ultimos_12_meses=periodos[2],
    )
