"""
Sub-parser: Págs. 4-6 — Rentabilidade por estratégia, retornos mensais/anuais e estatísticas.

Pág. 4: Blocos por estratégia (Pós-fixado, Alternativo …) com % e R$ por período.
Pág. 5: Tabela retornos mensais (Jan-Dez + No ano + Acumulado) e retornos anuais.
Págs. 5-6: Estatísticas (Maior/Menor Rent Mensal, Volatilidade, Meses +/-/acima CDI).

Desafio: "Pós-fixado" aparece como "Pós- xado" ou "Pós-\\w*xado" por ligaduras de fonte.
"""
import re

from loguru import logger

from app.domain.models.btg_portfolio import (
    BtgEstatisticas,
    BtgEstrategia,
    BtgRetornoMensal,
)

# ---------------------------------------------------------------------------
# Pág. 4 — Rentabilidade por estratégia
# ---------------------------------------------------------------------------

_ESTRATEGIA_SECTION_START = re.compile(
    r"E,?\s+quando\s+abrimos\s+a\s+rentabilidade",
    re.IGNORECASE,
)
_ESTRATEGIA_SECTION_END = re.compile(
    r"Os retornos mensais",
    re.IGNORECASE,
)

_PCT = r"(-?[\d,]+%|-)"
_BRL_VAL = r"R\$\s*([\d\.]+,\d+)"
_BRL_SIGNED_VAL = r"-?R\$\s*[\d\.]+,\d+"

# Linha 1: portfolio% mês% ano% 12m% acum% (5 percentuais na mesma linha)
_STRAT_PCT_LINE_RE = re.compile(
    r"^(-?[\d,]+%)\s+(-?[\d,]+%)\s+(-?[\d,]+%)\s+(-?[\d,]+%)\s+(-?[\d,]+%)\s*$",
    re.MULTILINE,
)
# Linha 2: nome da estratégia (linha após a linha de %)
_STRAT_NAME_RE = re.compile(
    r"^(Pós-[^\n]+|Alternativo|Rend[^\n]{0,30}|[A-ZÀ-Ú][a-záéíóúàèìòùâêîôûãõ]{2,}[^\n]{0,40})\s*$",
    re.MULTILINE,
)
# Linha 3: R$ valor R$ mes R$ ano R$ 12m R$ acum (pode ter -R$)
_STRAT_RS_LINE_RE = re.compile(
    r"^" + _BRL_VAL + r"\s+(-?R\$\s*[\d\.]+,\d+)\s+(-?R\$\s*[\d\.]+,\d+)"
    r"\s+(-?R\$\s*[\d\.]+,\d+)\s+(-?R\$\s*[\d\.]+,\d+)\s*$",
    re.MULTILINE,
)
# Linha 4: CDI cdi_mes% cdi_ano% cdi_12m% cdi_acum%
_CDI_LINE_RE = re.compile(
    r"^CDI\s+(-?[\d,]+%)\s+(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s*$",
    re.MULTILINE,
)


def _extract_rs_value(raw: str) -> str:
    """Remove o prefixo 'R$ ' ou '-R$ ' e retorna apenas o número com sinal."""
    raw = raw.strip()
    if raw.startswith("-R$") or raw.startswith("-R$"):
        num = re.sub(r"-?R\$\s*", "", raw)
        return f"-{num}"
    return re.sub(r"R\$\s*", "", raw)


def parse_estrategias(full_text: str) -> list[BtgEstrategia]:
    """Extrai os blocos de rentabilidade por estratégia (pág. 4)."""
    m_start = _ESTRATEGIA_SECTION_START.search(full_text)
    if not m_start:
        logger.warning("BtgRetornos: seção estratégias não encontrada")
        return []

    section = full_text[m_start.start():]
    m_end = _ESTRATEGIA_SECTION_END.search(section)
    if m_end:
        section = section[: m_end.start()]

    # Coletar todas as linhas de % (cada bloco começa com 5 %)
    pct_matches = list(_STRAT_PCT_LINE_RE.finditer(section))
    rs_matches = list(_STRAT_RS_LINE_RE.finditer(section))
    cdi_matches = list(_CDI_LINE_RE.finditer(section))

    estrategias: list[BtgEstrategia] = []
    for i, m_pct in enumerate(pct_matches):
        # Nome: próxima linha não-numérica após a linha de %
        pos_after_pct = m_pct.end()
        # Pega até 120 chars após para achar o nome
        snippet = section[pos_after_pct: pos_after_pct + 200]
        name_m = re.search(
            r"^\s*(Pós-[^\n]*|Alternativo[^\n]*|[A-ZÀ-Ú][a-záéíóú][^\n]{0,40})\s*\n",
            snippet,
            re.MULTILINE,
        )
        nome = name_m.group(1).strip() if name_m else f"Estratégia {i+1}"
        nome = re.sub(r"Pós-\s*\w*xado", "Pós-fixado", nome)

        rs_m = rs_matches[i] if i < len(rs_matches) else None
        cdi_m = cdi_matches[i] if i < len(cdi_matches) else None

        estrategias.append(BtgEstrategia(
            nome=nome,
            portfolio_pct=m_pct.group(1),
            mes_pct=m_pct.group(2),
            ano_pct=m_pct.group(3),
            doze_meses_pct=m_pct.group(4),
            acumulado_pct=m_pct.group(5),
            valor_rs=rs_m.group(1) if rs_m else "",
            mes_rs=_extract_rs_value(rs_m.group(2)) if rs_m else "",
            ano_rs=_extract_rs_value(rs_m.group(3)) if rs_m else "",
            doze_meses_rs=_extract_rs_value(rs_m.group(4)) if rs_m else "",
            acumulado_rs=_extract_rs_value(rs_m.group(5)) if rs_m else "",
            cdi_mes_pct=cdi_m.group(1) if cdi_m else "",
            cdi_ano_pct=cdi_m.group(2) if cdi_m else "",
            cdi_12m_pct=cdi_m.group(3) if cdi_m else "",
            cdi_acum_pct=cdi_m.group(4) if cdi_m else "",
        ))

    logger.debug("BtgRetornos: {} estratégias extraídas", len(estrategias))
    return estrategias


# ---------------------------------------------------------------------------
# Pág. 5 — Retornos mensais
# ---------------------------------------------------------------------------


_RETORNO_MENSAL_SECTION_RE = re.compile(
    r"Os retornos mensais.+?(?=Os retornos anuais)",
    re.DOTALL,
)

_RETORNO_ROW_RE = re.compile(
    r"^(20\d{2}|CDI|%\s*do\s*CDI)\s+"
    r"(-|[-\d,]+%?)\s+(-|[-\d,]+%?)\s+(-|[-\d,]+%?)\s+(-|[-\d,]+%?)\s+"
    r"(-|[-\d,]+%?)\s+(-|[-\d,]+%?)\s+(-|[-\d,]+%?)\s+(-|[-\d,]+%?)\s+"
    r"(-|[-\d,]+%?)\s+(-|[-\d,]+%?)\s+(-|[-\d,]+%?)\s+(-|[-\d,]+%?)\s+"
    r"(-|[-\d,]+%?)\s+(-|[-\d,]+%?)\s*$",
    re.MULTILINE,
)


def parse_retornos_mensais(full_text: str) -> list[BtgRetornoMensal]:
    """Extrai a tabela de retornos mensais (pág. 5)."""
    m_sec = _RETORNO_MENSAL_SECTION_RE.search(full_text)
    section = m_sec.group() if m_sec else full_text

    result: list[BtgRetornoMensal] = []
    for m in _RETORNO_ROW_RE.finditer(section):
        g = m.groups()
        result.append(BtgRetornoMensal(
            indicador=g[0].strip(),
            jan=g[1], fev=g[2], mar=g[3], abr=g[4],
            mai=g[5], jun=g[6], jul=g[7], ago=g[8],
            set=g[9], out=g[10], nov=g[11], dez=g[12],
            no_ano=g[13], acumulado=g[14],
        ))
    logger.debug("BtgRetornos: {} linhas de retorno mensal", len(result))
    return result


# ---------------------------------------------------------------------------
# Págs. 5-6 — Estatísticas
# ---------------------------------------------------------------------------
_STAT_VALUE_RE = re.compile(r"(-?[\d,]+%?|-)")

_STAT_ROWS = [
    ("maior_rent_mensal",      r"Maior Rentabilidade Mensal"),
    ("menor_rent_mensal",      r"Menor Rentabilidade Mensal"),
    ("volatilidade",           r"Volatilidade"),
    ("meses_retorno_positivo", r"Número de meses com retorno positivo"),
    ("meses_retorno_negativo", r"Número de meses com retorno negativo"),
    ("meses_acima_cdi",        r"Número de meses acim[^\n]+ do CDI"),
    ("meses_abaixo_cdi",       r"Número de meses abaixo do CDI"),
]


def _parse_stat_row(text: str, label_re: str) -> list[str]:
    m = re.search(label_re + r"\s+(.+)$", text, re.MULTILINE)
    if not m:
        return []
    return _STAT_VALUE_RE.findall(m.group(1))


def parse_estatisticas(full_text: str) -> BtgEstatisticas:
    """Extrai as estatísticas de desempenho (págs. 5-6)."""
    m_start = re.search(r"Estatísticas", full_text)
    section = full_text[m_start.start():] if m_start else full_text

    rows = {field: _parse_stat_row(section, pattern) for field, pattern in _STAT_ROWS}

    return BtgEstatisticas(
        maior_rent_mensal=rows["maior_rent_mensal"],
        menor_rent_mensal=rows["menor_rent_mensal"],
        volatilidade=rows["volatilidade"],
        meses_retorno_positivo=rows["meses_retorno_positivo"],
        meses_retorno_negativo=rows["meses_retorno_negativo"],
        meses_acima_cdi=rows["meses_acima_cdi"],
        meses_abaixo_cdi=rows["meses_abaixo_cdi"],
    )
