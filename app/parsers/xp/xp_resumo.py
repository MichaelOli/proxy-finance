"""
Sub-parser: Resumo XP (página 1).

Extrai:
- Patrimônio total bruto, rentabilidade e ganho do mês/24M
- Data de referência
- Benchmarks (Portfólio, CDI, Ibovespa, IPCA, Dólar)
- Estatísticas históricas (meses positivos/negativos, retorno max/min, CDI, volatilidade)
- Por período (MÊS, ANO, 12M, 24M): ganho, rentabilidade, %CDI, movimentações
"""
import re
from typing import Optional

from app.domain.models.xp_portfolio import (
    XpBenchmark,
    XpEstatisticasHistoricas,
    XpPeriodoResumo,
    XpResumo,
)

# Linha de cabeçalho: PATRIMÔNIO TOTAL BRUTO: RENT MÊS: GANHO MÊS: RENT(24M) GANHO(24M)
_HEADER_RE = re.compile(
    r"R\$\s+([\d\.,]+)"           # patrimônio total bruto
    r"\s+([\d,]+%)"               # rentabilidade mês
    r"\s+R\$\s+([\d\.,]+)"        # ganho mês
    r"\s+([\d,]+%|-)"             # rentabilidade 24M
    r"\s+R\$\s+([\d\.,]+|-)"      # ganho 24M
)

_DATA_REF_RE = re.compile(r"Data de referência:\s+(\d{2}/\d{2}/\d{4})")

_BENCHMARK_RE = re.compile(
    r"^(Portfólio|CDI|Ibovespa|IPCA|Dólar)\s+"
    r"(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s*$",
    re.MULTILINE,
)

_MESES_POS_NEG_RE = re.compile(
    r"Movimentações\s+(\d+)\s+(\d+)"
)

_RETORNO_MAX_MIN_RE = re.compile(
    r"Retorno Mensal Máximo\s+Retorno Mensal Mínimo\r?\n"
    r"[^\n]*\r?\n"          # linha intermediária (período ANO)
    r"([\d,]+%)\s+([\d,]+%)"
)

_MESES_CDI_RE = re.compile(
    r"Meses Acima do CDI\s+Meses Abaixo do CDI\s+(\d+)\s+(\d+)"
)

_VOLATILIDADE_RE = re.compile(
    r"Volatilidade\(últimos 12M\)\s+Volatilidade\(últimos 24M\)\s+([\d,]+%)\s+([\d,]+%)"
)

# Linha por período: MÊS/ANO/12M com valores reais
_PERIODO_COM_VALOR_RE = re.compile(
    r"^(MÊS|ANO|12M)\s+"
    r"R\$\s+([\d\.,]+)\s+"   # ganho financeiro
    r"([\d,]+%)\s+"           # rentabilidade
    r"([\d,]+%)\s+"           # %CDI
    r"R\$\s+([\d\.,]+)\s*$",  # movimentações
    re.MULTILINE,
)

# Linha 24M (pode ter conteúdo adicional na mesma linha por causa do layout do PDF)
_PERIODO_24M_RE = re.compile(r"^24M\s+-\s+-\s+-\s+-", re.MULTILINE)


def _opt_pct(v: str) -> Optional[str]:
    """Retorna None se '-', caso contrário a string como veio do PDF."""
    return None if v.strip() == "-" else v.strip()


def _opt_money(v: str) -> Optional[str]:
    """Retorna None se '-', caso contrário o valor sem 'R$ ' prefix."""
    v = v.strip()
    return None if v == "-" else v


def parse_resumo(text: str) -> tuple[str, XpResumo]:
    """
    Retorna (data_referencia, XpResumo).
    Raises ValueError se os campos obrigatórios não forem encontrados.
    """
    # Data de referência
    m = _DATA_REF_RE.search(text)
    data_ref = m.group(1) if m else ""

    # Cabeçalho patrimonial
    m = _HEADER_RE.search(text)
    if not m:
        raise ValueError("XP: cabeçalho patrimonial não encontrado.")
    patrimonio = m.group(1)
    rent_mes = m.group(2)
    ganho_mes = m.group(3)
    rent_24m = _opt_pct(m.group(4))
    ganho_24m = _opt_money(m.group(5))

    # Benchmarks — deduplicar por nome (primeira ocorrência = página 1)
    benchmarks_dict: dict[str, XpBenchmark] = {}
    for bm in _BENCHMARK_RE.finditer(text):
        nome = bm.group(1)
        if nome not in benchmarks_dict:
            benchmarks_dict[nome] = XpBenchmark(
                nome=nome,
                mes=_opt_pct(bm.group(2)),
                ano=_opt_pct(bm.group(3)),
                doze_m=_opt_pct(bm.group(4)),
                vinte_quatro_m=_opt_pct(bm.group(5)),
            )
    benchmarks = list(benchmarks_dict.values())

    # Estatísticas históricas
    mp = _MESES_POS_NEG_RE.search(text)
    rmm = _RETORNO_MAX_MIN_RE.search(text)
    mcdi = _MESES_CDI_RE.search(text)
    vol = _VOLATILIDADE_RE.search(text)

    estatisticas = XpEstatisticasHistoricas(
        meses_positivos=mp.group(1) if mp else "0",
        meses_negativos=mp.group(2) if mp else "0",
        retorno_mensal_maximo=rmm.group(1) if rmm else "0,00%",
        retorno_mensal_minimo=rmm.group(2) if rmm else "0,00%",
        meses_acima_cdi=mcdi.group(1) if mcdi else "0",
        meses_abaixo_cdi=mcdi.group(2) if mcdi else "0",
        volatilidade_12m=vol.group(1) if vol else "0,00%",
        volatilidade_24m=vol.group(2) if vol else "0,00%",
    )

    # Por período
    por_periodo: list[XpPeriodoResumo] = []
    for pm in _PERIODO_COM_VALOR_RE.finditer(text):
        por_periodo.append(
            XpPeriodoResumo(
                periodo=pm.group(1),
                ganho_financeiro=pm.group(2),
                rentabilidade=pm.group(3),
                percentual_cdi=pm.group(4),
                movimentacoes=pm.group(5),
            )
        )
    # 24M: pode não ter valores
    if _PERIODO_24M_RE.search(text):
        por_periodo.append(XpPeriodoResumo(periodo="24M"))

    resumo = XpResumo(
        patrimonio_total_bruto=patrimonio,
        rentabilidade_mes=rent_mes,
        ganho_mes=ganho_mes,
        rentabilidade_24m=rent_24m,
        ganho_24m=ganho_24m,
        benchmarks=benchmarks,
        estatisticas_historicas=estatisticas,
        por_periodo=por_periodo,
    )
    return data_ref, resumo
