"""
Sub-parser: Posição detalhada por ativo XP (páginas 6–9).
"""
import re
from typing import Optional

from app.domain.models.xp_portfolio import XpAtivo, XpEstrategiaDetalhada

# Cabeçalhos repetidos a cada nova página
_PAGE_HEADER_RE = re.compile(
    r"POSIÇÃO DETALHADA\s*\n"
    r"PRECIFICAÇÃO DE RENDA FIXA: NA CURVA\s*\n"
    r"POSIÇÃO DETALHADA DOS ATIVOS\s*\n"
    r"MÊS ATUAL\s+ANO\s+24 MESES\s*\n"
    r"Estratégia\s+Saldo Bruto\s+Qtd\.\s+%Aloc\.\s+Rent\.\s+%CDI\s+Rent\.\s+%CDI\s+Rent\.\s+%CDI\s*\n",
    re.MULTILINE,
)

# Rodapé de página (número de página e nota)
_PAGE_FOOTER_RE = re.compile(
    r"Relatório de Investimentos\s+Data de referência:.*?\n\d{2}\s*\n",
    re.MULTILINE,
)
_AVISO_RE = re.compile(r"\*Aviso!.*", re.DOTALL)

# Linha de estratégia: nome  R$ saldo  -  %aloc  rent_mes  %cdi_mes  rent_ano  %cdi_ano  -  -
_STRATEGY_ROW_RE = re.compile(
    r"^(Pós Fixado|Inflação|Pré Fixado|Caixa|Proventos)\s+"
    r"R\$\s+([\d\.,]+)\s+-\s+"           # saldo + qtd ("-")
    r"([\d,]+%)\s+"                      # %aloc
    r"(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s+"  # rent_mes + %cdi_mes
    r"(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s+"  # rent_ano + %cdi_ano
    r"(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s*$",# rent_24m + %cdi_24m
    re.MULTILINE,
)

# Linha de dados de ativo (começa com R$)
_ASSET_DATA_RE = re.compile(
    r"^R\$\s+([\d\.,]+)\s+"              # saldo bruto
    r"([\d\.]+)\s+"                      # quantidade
    r"([\d,]+%)\s+"                      # %aloc
    r"(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s+"  # rent_mes + %cdi_mes
    r"(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s+"  # rent_ano + %cdi_ano
    r"(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s*$",# rent_24m + %cdi_24m
    re.MULTILINE,
)

# Linha single-line: nome + dados na mesma linha
_ASSET_SINGLE_RE = re.compile(
    r"^(.+?)\s+"
    r"R\$\s+([\d\.,]+)\s+"
    r"([\d\.]+)\s+"
    r"([\d,]+%)\s+"
    r"(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s+"
    r"(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s+"
    r"(-?[\d,]+%|-)\s+(-?[\d,]+%|-)\s*$",
    re.MULTILINE,
)


def _opt(v: str) -> Optional[str]:
    return None if v.strip() == "-" else v.strip()


def _clean_text(text: str) -> str:
    """Remove cabeçalhos e rodapés repetidos de página."""
    text = _PAGE_HEADER_RE.sub("", text)
    text = _PAGE_FOOTER_RE.sub("", text)
    # Remove linhas de aviso (cada uma individualmente, sem DOTALL)
    text = re.sub(r"^\*Aviso!.*$", "", text, flags=re.MULTILINE)
    return text


def _parse_ativos_from_lines(lines: list[str]) -> list[XpAtivo]:
    """
    Percorre as linhas de um bloco de estratégia e extrai os ativos.
    Suporta nomes em linha única e nomes divididos em 2+ linhas.
    """
    ativos: list[XpAtivo] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Tenta linha única (nome + dados juntos)
        ms = _ASSET_SINGLE_RE.match(line)
        if ms:
            ativos.append(
                XpAtivo(
                    nome=ms.group(1).strip(),
                    saldo_bruto=ms.group(2),
                    quantidade=ms.group(3),
                    percentual_alocacao=ms.group(4),
                    rentabilidade_mes=_opt(ms.group(5)),
                    percentual_cdi_mes=_opt(ms.group(6)),
                    rentabilidade_ano=_opt(ms.group(7)),
                    percentual_cdi_ano=_opt(ms.group(8)),
                    rentabilidade_24m=_opt(ms.group(9)),
                    percentual_cdi_24m=_opt(ms.group(10)),
                )
            )
            i += 1
            continue

        # Verifica se próxima linha é linha de dados (multi-line)
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            md = _ASSET_DATA_RE.match(next_line)
            if md:
                name_prefix = line
                # Consome possível sufixo do nome (linha seguinte que não é dado)
                name_suffix = ""
                skip = 2
                if i + 2 < len(lines):
                    suffix_candidate = lines[i + 2].strip()
                    if (suffix_candidate
                            and not _ASSET_DATA_RE.match(suffix_candidate)
                            and not _ASSET_SINGLE_RE.match(suffix_candidate)
                            and not _STRATEGY_ROW_RE.match(suffix_candidate)):
                        name_suffix = suffix_candidate
                        skip = 3
                nome = f"{name_prefix} {name_suffix}".strip() if name_suffix else name_prefix
                ativos.append(
                    XpAtivo(
                        nome=nome,
                        saldo_bruto=md.group(1),
                        quantidade=md.group(2),
                        percentual_alocacao=md.group(3),
                        rentabilidade_mes=_opt(md.group(4)),
                        percentual_cdi_mes=_opt(md.group(5)),
                        rentabilidade_ano=_opt(md.group(6)),
                        percentual_cdi_ano=_opt(md.group(7)),
                        rentabilidade_24m=_opt(md.group(8)),
                        percentual_cdi_24m=_opt(md.group(9)),
                    )
                )
                i += skip
                continue

        i += 1
    return ativos


def parse_posicao(text: str) -> list[XpEstrategiaDetalhada]:
    """
    Extrai a posição detalhada de todas as estratégias e seus ativos.
    """
    clean = _clean_text(text)
    lines = clean.split("\n")

    result: list[XpEstrategiaDetalhada] = []
    current_strategy: Optional[XpEstrategiaDetalhada] = None
    current_lines: list[str] = []

    for line in lines:
        ms = _STRATEGY_ROW_RE.match(line.strip())
        if ms:
            # Salva estratégia anterior
            if current_strategy is not None:
                current_strategy.ativos.extend(_parse_ativos_from_lines(current_lines))
                result.append(current_strategy)
            current_strategy = XpEstrategiaDetalhada(
                estrategia=ms.group(1),
                saldo_bruto_estrategia=ms.group(2),
                percentual_alocacao_estrategia=ms.group(3),
                ativos=[],
            )
            current_lines = []
        elif current_strategy is not None:
            current_lines.append(line)

    # Última estratégia
    if current_strategy is not None:
        current_strategy.ativos.extend(_parse_ativos_from_lines(current_lines))
        result.append(current_strategy)

    return result
