"""
Sub-parser: Pág. 3 — Alocação.

Texto real (pdfplumber, layout de duas colunas mesclado):
  - Classes de ativos: linhas independentes no início do bloco
  - Tipos de produtos: aparecem no meio de linhas de índices (CDI, IPCA)
  - Índices de mercado: à esquerda da tabela de tipos

"""
import re

from loguru import logger

from app.domain.models.itau_portfolio import (
    ItauAlocacao,
    ItauClasseAlocacao,
    ItauIndiceMercado,
    ItauTipoProduto,
)

_NUM   = r"(-?[\d,]+|-)"
_BRL   = r"R\$\s*([\d\.]+,\d+)"

# Linha de classe de ativos
_CLASSE_RE = re.compile(
    r"^(Pós-fixado|Prefixado|Inflação|Renda Fixa Ativo|Multimercado"
    r"|Renda variável|Internacional|Alternativos Ilíquidos)"
    r"\s+([\d,]+)\s+([\d\.]+,\d+)"
    r"\s+" + _NUM + r"\s+" + _NUM
    + r"\s+" + _NUM + r"\s+" + _NUM
    + r"\s+" + _NUM,
    re.MULTILINE,
)

# Índices de mercado
_INDICE_RE = re.compile(
    r"^(CDI|IPCA|IBOVESPA|dólar)\s+\(%\)\s+"
    + _NUM + r"\s+" + _NUM + r"\s+" + _NUM + r"\s+" + _NUM + r"\s+" + _NUM,
    re.MULTILINE,
)

# Tipos de produtos
_TIPO_RE = re.compile(
    r"(Renda fixa e estruturados|Fundos de investimento|Previdência|Renda variável)"
    r"\s+([\d,]+)\s+" + _BRL,
)


def _block_p3(text: str) -> str:
    """Isola o texto da pág. 3"""
    m_start = re.search(r"\b3\s+de\s+16\b", text)
    m_end   = re.search(r"\b4\s+de\s+16\b", text)
    if m_start and m_end:
        return text[m_start.end(): m_end.start()]
    if m_start:
        return text[m_start.end(): m_start.end() + 2500]
    return text[4000:7000]


def parse_alocacao(text: str) -> ItauAlocacao:
    """Extrai a seção de Alocação (página 3)."""
    bloco = _block_p3(text)

    classes: list[ItauClasseAlocacao] = []
    for m in _CLASSE_RE.finditer(bloco):
        classes.append(ItauClasseAlocacao(
            classe=m.group(1),
            percentual=m.group(2),
            saldo_bruto=m.group(3),
            rent_mes=_n(m.group(4)),
            rent_ano=_n(m.group(5)),
            rent_12m=_n(m.group(6)),
            rent_24m=_n(m.group(7)),
            rent_inicio=_n(m.group(8)),
        ))

    indices: list[ItauIndiceMercado] = []
    for m in _INDICE_RE.finditer(bloco):
        indices.append(ItauIndiceMercado(
            indice=m.group(1),
            mes=_n(m.group(2)),
            ano=_n(m.group(3)),
            doze_meses=_n(m.group(4)),
            vinte_quatro_meses=_n(m.group(5)),
            inicio=_n(m.group(6)),
        ))

    # Tipos de produtos (sem âncora ^ — aparecem no meio de linhas)
    tipos: list[ItauTipoProduto] = []
    seen_tipos: set[str] = set()
    for m in _TIPO_RE.finditer(bloco):
        tipo = m.group(1)
        if tipo not in seen_tipos:
            tipos.append(ItauTipoProduto(
                tipo=tipo,
                percentual=m.group(2),
                saldo_bruto=m.group(3),
            ))
            seen_tipos.add(tipo)

    logger.debug(
        "itau_alocacao: {} classes, {} indices, {} tipos.",
        len(classes), len(indices), len(tipos),
    )

    return ItauAlocacao(
        classes=classes,
        indices_mercado=indices,
        tipos_produto=tipos,
    )


def _n(val: str) -> str | None:
    return None if val.strip() == "-" else val.strip()
