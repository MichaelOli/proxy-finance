"""
Sub-parser: Histórico de rentabilidade da carteira Safra (página 2).

Extrai:
- Meses de referência
- CARTEIRA: valores mensais e acumulados (Ano/12M/24M/36M)
- % CDI EQUIVALENTE: idem
- Índices de mercado: CDI, IBOVESPA, DOLAR
"""
import re

from app.domain.models.safra_portfolio import SafraHistorico, SafraHistoricoLinha

# Seção da página 2: entre "Histórico de rentabilidade" e a próxima seção
_SECTION_START = re.compile(r"Histórico de rentabilidade acumulada|Rentabilidade histórica da carteira")
_SECTION_END = re.compile(r"Rentabilidade Histórica de Produtos|-- 2 of 12 --")

# Meses no formato "Ago/24", "Set/24", ..., "Jul/25"
_MES_RE = re.compile(r"[A-Za-z]{3}/\d{2}")

# Valor numérico BR ou traço isolado
_V = r"(-?[\d\.]+,\d+|-)"

# 16 valores por linha: 12 mensais + 4 acumulados (Ano, 12M, 24M, 36M)
_ROW_RE = re.compile(
    r"(CARTEIRA|% CDI EQUIVALENTE|CDI|IBOVESPA|DOLAR)\s+"
    + r"\s+".join([_V] * 16)
)


def _extract_section(text: str) -> str:
    m_start = _SECTION_START.search(text)
    if not m_start:
        return text
    m_end = _SECTION_END.search(text, m_start.end())
    end_pos = m_end.start() if m_end else len(text)
    return text[m_start.start():end_pos]


def parse_historico(text: str) -> SafraHistorico:
    """
    Extrai o histórico de rentabilidade da carteira (página 2).
    """
    section = _extract_section(text)

    meses = _MES_RE.findall(section)
    # Primeiros 12 matches únicos e ordenados são os meses de referência
    seen: set[str] = set()
    meses_referencia: list[str] = []
    for m in meses:
        if m not in seen:
            seen.add(m)
            meses_referencia.append(m)
        if len(meses_referencia) == 12:
            break

    linhas: list[SafraHistoricoLinha] = []
    for row in _ROW_RE.finditer(section):
        descricao = row.group(1)
        vals = [row.group(i) for i in range(2, 18)]  # 16 valores
        linhas.append(
            SafraHistoricoLinha(
                descricao=descricao,
                valores_mensais=vals[:12],
                acumulado_ano=vals[12],
                acumulado_12m=vals[13],
                acumulado_24m=vals[14],
                acumulado_36m=vals[15],
            )
        )

    return SafraHistorico(
        meses_referencia=meses_referencia,
        linhas=linhas,
    )
