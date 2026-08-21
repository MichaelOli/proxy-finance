"""
Sub-parser: Págs. 7-8 — Rentabilidade completa por classe de ativos e ativo individual.

Estratégia: caminhada linha-a-linha para detectar ativos por padrão de nome,
depois coleta os valores nas linhas adjacentes.
"""
import re
from typing import Optional

from loguru import logger

from app.domain.models.btg_portfolio import BtgAtivoPosicao, BtgClassePosicao

# ---------------------------------------------------------------------------
# Delimitadores de seção
# ---------------------------------------------------------------------------
_SECTION_START_RE = re.compile(r"A rentabilidade completa", re.IGNORECASE)
_SECTION_END_RE = re.compile(r"Posição consolidada por devedor", re.IGNORECASE)

# Cabeçalho de cada classe: "Em Rend  Fix  59,29% do Total R$ 440.372,63"
# Usa [^\n]+? (não-guloso) para parar antes do percentual
_CLASS_HEADER_RE = re.compile(
    r"Em\s+([^\n]+?)\s+([\d,]+%)\s+do\s+Total\s+R\$\s*([\d\.]+,\d+)",
)

# Linha total da classe
_CLASS_TOTAL_RE = re.compile(
    r"^Total\s+([\d\.]+,\d+)\s+([\d,]+)\s+(-?[\d\.]+,\d+)\s+(-?[\d\.]+,\d+)\s+(-)\s+(-?[\d\.]+,\d+)\s*$",
    re.MULTILINE,
)

# ---------------------------------------------------------------------------
# Padrões de asset por linha
# ---------------------------------------------------------------------------
# Usa [^\n]+? para incluir "| CDI | YEAR" no nome e parar no saldo com ponto decimal
_CDB_LINE_RE = re.compile(
    r"^(BANCO BTG PACTUAL S A\s*-\s*CDB-[^\n]+?)\s+"
    r"([\d\.]+,\d+)\s+"           # saldo bruto (tem ponto como milhar)
    r"([\d,]+)"                    # %PL (sem ponto, ex: 20,37)
    r"(?:\s+([\d,]+%)\s+([-\d,]+%)\s+(-)\s+([-\d,]+%))?"   # % inline (opcional)
    r"(?:\s+(\d{2}/\d{2}/\d{4}))?"  # data_inicial (opcional)
    r"\s*$",
    re.MULTILINE,
)

# Ativo genérico: "NOME  SALDO  %PL  [DATA]"
# Ignora linhas de estratégia/header/total
_GENERIC_ASSET_RE = re.compile(
    r"^([A-Z][^\n]+?)\s+([\d\.]+,\d+)\s+([\d,]+)"
    r"(?:\s+(\d{2}/\d{2}/\d{4}))?\s*$",
    re.MULTILINE,
)

# Linha de valores R$ (Mês, Ano, 12M, Acum)
_RS_LINE_RE = re.compile(
    r"^(-?[\d\.]+,\d+)\s+(-?[\d\.]+,\d+)\s+(-)\s+(-?[\d\.]+,\d+)\s*$",
)

# Linha de valores % (Mês%, Ano%, 12M%, Acum%)
_PCT_LINE_RE = re.compile(
    r"^(-?[\d,]+%)\s+(-?[\d,]+%|-)\s+(-)\s+(-?[\d,]+%)\s*$",
)

# Linhas a ignorar (não são ativos)
_IGNORE_PREFIXES = (
    "Ativo", "Total", "CDI", "SAC:", "Página", "Relatório",
    "Período", "Por classe", "A rentabilidade", "Em ",
    "Pós-", "Alternativo",
)

_PAGE_BREAK_PREFIXES = ("SAC:", "Página", "Relatório", "Período", "Ativo")


def _normalize_class_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"Rend\s+Fix\s*", "Renda Fixa", name)
    name = re.sub(r"Previdênci\s*$", "Previdência", name)
    return name


def _next_value_line(lines: list[str], start: int, max_skip: int = 8) -> str:
    """
    Retorna o conteúdo da próxima linha que não seja cabeçalho de quebra de página.
    """
    for j in range(start, min(start + max_skip, len(lines))):
        line = lines[j].strip()
        if not line:
            continue
        if any(line.startswith(p) for p in _PAGE_BREAK_PREFIXES):
            continue
        return line
    return ""


def _is_ignorable(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    for prefix in _IGNORE_PREFIXES:
        if stripped.startswith(prefix):
            return True
    return False


def _parse_assets_from_lines(lines: list[str]) -> list[BtgAtivoPosicao]:
    """
    Caminha pelas linhas da seção de uma classe extraindo ativos.
    Para cada asset encontrado, busca valores % e R$ nas linhas adjacentes.
    """
    ativos: list[BtgAtivoPosicao] = []
    n = len(lines)

    i = 0
    while i < n:
        line = lines[i].strip()

        # --- CDB asset ---
        m_cdb = _CDB_LINE_RE.match(line)
        if m_cdb:
            nome = m_cdb.group(1).strip()
            saldo = m_cdb.group(2)
            pl_pct = m_cdb.group(3)
            inline_mes = m_cdb.group(4)
            inline_ano = m_cdb.group(5)
            inline_12m = m_cdb.group(6)
            inline_acum = m_cdb.group(7)
            data = m_cdb.group(8)

            # R$ values: próxima linha com dados (pula linhas de quebra de página)
            mes_rs = ano_rs = doze_rs = acum_rs = None
            if i + 1 < n:
                next_line = _next_value_line(lines, i + 1)
                rs_m = _RS_LINE_RE.match(next_line)
                if rs_m:
                    mes_rs, ano_rs, doze_rs, acum_rs = (
                        rs_m.group(1), rs_m.group(2), rs_m.group(3), rs_m.group(4)
                    )

            # % values: linha anterior (se não há inline)
            mes_pct = inline_mes
            ano_pct = inline_ano
            doze_pct = inline_12m
            acum_pct = inline_acum
            if not inline_mes and i > 0:
                pct_m = _PCT_LINE_RE.match(lines[i - 1].strip())
                if pct_m:
                    mes_pct, ano_pct, doze_pct, acum_pct = (
                        pct_m.group(1), pct_m.group(2), pct_m.group(3), pct_m.group(4)
                    )

            ativos.append(BtgAtivoPosicao(
                nome=nome,
                saldo_bruto=saldo,
                saldo_pl_pct=pl_pct,
                mes_pct=mes_pct,
                ano_pct=ano_pct,
                doze_meses_pct=doze_pct,
                acumulado_pct=acum_pct,
                mes_rs=mes_rs,
                ano_rs=ano_rs,
                doze_meses_rs=doze_rs,
                acumulado_rs=acum_rs,
                data_inicial=data,
            ))
            i += 1
            continue

        # --- Ativo genérico (XBT, Fundo, Previdência) ---
        if not _is_ignorable(line):
            m_gen = _GENERIC_ASSET_RE.match(line)
            if m_gen:
                nome = m_gen.group(1).strip()
                saldo = m_gen.group(2)
                pl_pct = m_gen.group(3)
                data_gen = m_gen.group(4)  # data_inicial opcional

                # R$ values: próxima linha
                mes_rs = ano_rs = doze_rs = acum_rs = None
                if i + 1 < n:
                    rs_m = _RS_LINE_RE.match(lines[i + 1].strip())
                    if rs_m:
                        mes_rs, ano_rs, doze_rs, acum_rs = (
                            rs_m.group(1), rs_m.group(2), rs_m.group(3), rs_m.group(4)
                        )

                # % values: linha anterior
                mes_pct = ano_pct = doze_pct = acum_pct = None
                if i > 0:
                    pct_m = _PCT_LINE_RE.match(lines[i - 1].strip())
                    if pct_m:
                        mes_pct, ano_pct, doze_pct, acum_pct = (
                            pct_m.group(1), pct_m.group(2), pct_m.group(3), pct_m.group(4)
                        )

                ativos.append(BtgAtivoPosicao(
                    nome=nome,
                    saldo_bruto=saldo,
                    saldo_pl_pct=pl_pct,
                    mes_pct=mes_pct,
                    ano_pct=ano_pct,
                    doze_meses_pct=doze_pct,
                    acumulado_pct=acum_pct,
                    mes_rs=mes_rs,
                    ano_rs=ano_rs,
                    doze_meses_rs=doze_rs,
                    acumulado_rs=acum_rs,
                    data_inicial=data_gen,
                ))
                i += 1
                continue

        i += 1

    return ativos


def parse_posicao_rentabilidade(full_text: str) -> list[BtgClassePosicao]:
    """Extrai todas as classes de ativos com seus ativos e valores (págs. 7-8)."""
    m_start = _SECTION_START_RE.search(full_text)
    if not m_start:
        logger.warning("BtgPosicaoRentabilidade: seção não encontrada")
        return []

    section = full_text[m_start.start():]
    m_end = _SECTION_END_RE.search(section)
    if m_end:
        section = section[: m_end.start()]

    class_matches = list(_CLASS_HEADER_RE.finditer(section))
    if not class_matches:
        logger.warning("BtgPosicaoRentabilidade: nenhuma classe encontrada")
        return []

    classes: list[BtgClassePosicao] = []
    for idx, class_m in enumerate(class_matches):
        nome_classe = _normalize_class_name(class_m.group(1))
        pct_total = class_m.group(2)
        valor_total = class_m.group(3)

        start_pos = class_m.end()
        end_pos = class_matches[idx + 1].start() if idx + 1 < len(class_matches) else len(section)
        class_text = section[start_pos:end_pos]

        total_m = _CLASS_TOTAL_RE.search(class_text)
        lines = class_text.splitlines()
        ativos = _parse_assets_from_lines(lines)

        classes.append(BtgClassePosicao(
            nome_classe=nome_classe,
            percentual_total=pct_total,
            valor_total=valor_total,
            ativos=ativos,
            total_mes_rs=total_m.group(3) if total_m else None,
            total_ano_rs=total_m.group(4) if total_m else None,
            total_12m_rs=total_m.group(5) if total_m else None,
            total_acum_rs=total_m.group(6) if total_m else None,
        ))

        logger.debug(
            "BtgPosicaoRentabilidade: classe='{}' → {} ativos",
            nome_classe,
            len(ativos),
        )

    return classes
