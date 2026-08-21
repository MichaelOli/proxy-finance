"""
Sub-parser: Pág. 1 — Resumo financeiro.

"""
import re

from loguru import logger

from app.domain.models.itau_portfolio import (
    ItauClasseAtivo,
    ItauIndiceMercado,
    ItauPerformancePeriodo,
    ItauResumo,
)

# ---------------------------------------------------------------------------
# Padrões
# ---------------------------------------------------------------------------

_DATA_POSICAO_RE  = re.compile(r"Data da posição[:\s]+([\d/]+)")
_DATA_RENT_RE     = re.compile(r"Data de rentabilidade[:\s]+([\d/]+)")

# Os três saldos estão na mesma linha separados por espaço
_TRES_SALDOS_RE = re.compile(
    r"R\$\s*([\d\.]+,\d+)\s+R\$\s*([\d\.]+,\d+)\s+R\$\s*([\d\.]+,\d+)"
)

# Rentabilidade da Carteira: "Carteira (%) 0,82 9,91 11,20 22,94 37,58 18,09"
_CART_RENT_RE = re.compile(
    r"Carteira \(%\)\s+(-?[\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)"
    r"\s+(-?[\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)"
)

# Classes de ativos — podem aparecer no meio de linhas (layout de duas colunas)
# Pós-fixado, Prefixado, Inflação, Renda Fixa Ativo, Multimercado, Renda variável,
# Internacional, Alternativos Ilíquidos
_CLASSE_RE = re.compile(
    r"(Pós-fixado|Prefixado|Inflação|Renda Fixa Ativo|Multimercado"
    r"|Renda variável|Internacional|Alternativos Ilíquidos)"
    r"\s+([\d,]+)\s+([\d\.]+,\d+)"
)

# Índices de mercado pág. 1 (6 colunas: Ago/25, 2025, 12m, 24m, 36m, Início)
_INDICE_RE = re.compile(
    r"^(CDI|Carteira/CDI|IPCA|IBOVESPA|dólar)\s+\(%\)\s+"
    r"(-?[\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)",
    re.MULTILINE,
)

# Datas de período (ex: "01/08/25 à 12/08/25")
_PERIODO_RE = re.compile(r"(\d{2}/\d{2}/\d{2})\s+à\s+(\d{2}/\d{2}/\d{2})")


def _block_p1(text: str) -> str:
    """Retorna o bloco da pág. 1 (até '2 de 16')."""
    m = re.search(r"\b2\s+de\s+16\b", text)
    return text[: m.start()] if m else text[:3000]


def parse_resumo(text: str) -> ItauResumo:
    """Extrai o Resumo financeiro (página 1)."""
    bloco = _block_p1(text)

    # Datas
    m = _DATA_POSICAO_RE.search(bloco)
    data_posicao = m.group(1) if m else ""

    m = _DATA_RENT_RE.search(bloco)
    data_rentabilidade = m.group(1) if m else ""

    # Saldos (3 na mesma linha)
    saldo_bruto = saldo_liquido = saldo_conta = ""
    m = _TRES_SALDOS_RE.search(bloco)
    if m:
        saldo_bruto   = m.group(1)
        saldo_liquido = m.group(2)
        saldo_conta   = m.group(3)

    # Performance dos períodos
    periodos = _PERIODO_RE.findall(bloco)
    perf_mensal = perf_anual = None
    if periodos:
        perf_mensal = ItauPerformancePeriodo(
            periodo_label="Ago/25",
            datas=f"{periodos[0][0]} à {periodos[0][1]}",
        )
    if len(periodos) > 1:
        perf_anual = ItauPerformancePeriodo(
            periodo_label="2025",
            datas=f"{periodos[1][0]} à {periodos[1][1]}",
        )

    # Rentabilidades da carteira
    rent_mes = rent_ano = rent_12m = rent_24m = rent_36m = rent_inicio = None
    m = _CART_RENT_RE.search(bloco)
    if m:
        rent_mes, rent_ano, rent_12m, rent_24m, rent_36m, rent_inicio = m.groups()

    # Índices de mercado
    indices: list[ItauIndiceMercado] = []
    for m in _INDICE_RE.finditer(bloco):
        indices.append(ItauIndiceMercado(
            indice=m.group(1),
            mes=m.group(2),
            ano=m.group(3),
            doze_meses=m.group(4),
            vinte_quatro_meses=m.group(5),
            trinta_seis_meses=m.group(6),
            inicio=m.group(7),
        ))

    # Classes de ativos 
    classes: list[ItauClasseAtivo] = []
    seen: set[str] = set()
    for m in _CLASSE_RE.finditer(bloco):
        nome = m.group(1)
        if nome not in seen:
            classes.append(ItauClasseAtivo(
                classe=nome,
                percentual=m.group(2),
                saldo_bruto=m.group(3),
            ))
            seen.add(nome)

    logger.debug(
        "itau_resumo: saldo_bruto={}, {} classes, {} indices.",
        saldo_bruto, len(classes), len(indices),
    )

    return ItauResumo(
        data_posicao=data_posicao,
        data_rentabilidade=data_rentabilidade,
        saldo_bruto=saldo_bruto,
        saldo_liquido=saldo_liquido,
        saldo_conta=saldo_conta or None,
        performance_mensal=perf_mensal,
        performance_anual=perf_anual,
        carteira_rent_mes=rent_mes,
        carteira_rent_ano=rent_ano,
        carteira_rent_12m=rent_12m,
        carteira_rent_24m=rent_24m,
        carteira_rent_36m=rent_36m,
        carteira_rent_inicio=rent_inicio,
        indices_mercado=indices,
        classes_ativos=classes,
    )
