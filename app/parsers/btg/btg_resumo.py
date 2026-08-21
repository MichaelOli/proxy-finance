"""
Sub-parser: Pág. 1 — Resumo do Relatório de Performance BTG Pactual.

Extrai do texto concatenado de todas as páginas:
  - Período do relatório
  - Patrimônio bruto e líquido
  - Performance do mês e dos últimos 12 meses
  - Distribuição por classe de ativos
  - Tabela de rentabilidade (Mês, Ano, 3 Meses, etc.)
  - Faixas de liquidez
"""
import re

from loguru import logger

from app.domain.models.btg_portfolio import (
    BtgDistribuicaoClasse,
    BtgLiquidezFaixa,
    BtgRentabilidadePeriodo,
    BtgResumo,
)

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------
_BRL = r"R\$\s*([\d\.]+,\d+)"
_PCT = r"(-?[\d,]+%)"

_PERIODO_RE = re.compile(r"Período de (\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})")

# Patrimônio bruto aparece na linha "R$ 742.745,67 1,14%" (valor + % na mesma linha)
_PATRIM_BRUTO_RE = re.compile(r"^" + _BRL + r"\s+" + _PCT + r"\s*$", re.MULTILINE)

# Patrimônio líquido aparece isolado na sua linha antes de "A rentabilidade nos últimos 12"
_PATRIM_LIQ_RE = re.compile(
    r"Patrimônio líquido[^\n]*\n[^\n]*\n" + _BRL,
    re.DOTALL,
)

# Performance de mês: mesma linha do patrimônio bruto (segundo grupo do _PATRIM_BRUTO_RE)
# Performance 12M: "A rentabilidade nos últimos 12 meses\nfoi de\n5,90%"
_PERF_12M_RE = re.compile(
    r"A rentabilidade nos últimos 12 meses\s+foi de\s+(" + r"[\d,]+" + r"%)",
    re.DOTALL,
)

# Distribuição"
# Usa [^0-9%\n]+? para parar antes dos dígitos da percentagem.
_DIST_RE = re.compile(
    r"^([^0-9%\n]{3,40}?)\s+(\d+,\d+%)\s+" + _BRL + r"\s*$",
    re.MULTILINE,
)
_DIST_TOTAL_RE = re.compile(
    r"^Total\s+(\d+,\d+%)\s+" + _BRL + r"\s*$", re.MULTILINE
)

# Rentabilidade"
# Linhas "Mês" e "Ano" possuem dados de liquidez ao final; não usar âncora $
_RENT_RE = re.compile(
    r"^(Mês|Ano|3 Meses|6 Meses|12 Meses|24 Meses|36 Meses|Acumulad\w*)"
    r"\s+" + _BRL + r"\s+" + _PCT + r"\s+" + _PCT + r"\s+" + _PCT + r"\s+" + _PCT,
    re.MULTILINE,
)

# Liquidez
_LIQUID_RE = re.compile(
    r"(De 0[^\n%]{2,25}?|Acim[^\n%]{2,30}?de 5 anos)\s+(\d+,\d+%)\s+R\$\s*([\d\.]+,\d+)",
)

# Mapeamento de faixas de liquidez
_FAIXAS_LIQUIDEZ_CONHECIDAS = [
    (r"De\s*0.*?1\s*di", "De 0 a 1 dia"),
    (r"De\s*2.*?30\s*di", "De 2 a 30 dias"),
    (r"De\s*31.*?180\s*di", "De 31 a 180 dias"),
    (r"De\s*181.*?360\s*di", "De 181 a 360 dias"),
    (r"De\s*1.*?5\s*ano", "De 1 a 5 anos"),
    (r"Acim.*?5\s*ano", "Acima de 5 anos"),
]


def _normalizar_faixa_liquidez(faixa: str) -> str:
    """
    Normaliza nomes de faixas de liquidez que vem corrompidos do PDF.
    
    """
    faixa_limpa = re.sub(r"\s+", " ", faixa).strip()
    
    for pattern, nome_correto in _FAIXAS_LIQUIDEZ_CONHECIDAS:
        if re.search(pattern, faixa_limpa, re.IGNORECASE):
            return nome_correto
    
    return faixa_limpa


def parse_resumo(full_text: str) -> BtgResumo:
    """Extrai os dados da pág. 1 a partir do texto completo do PDF."""

    # Período
    m = _PERIODO_RE.search(full_text)
    periodo = f"{m.group(1)} a {m.group(2)}" if m else ""
    if not m:
        logger.warning("BtgResumo: período não encontrado")

    # Patrimônio bruto + performance do mês (na mesma linha)
    m_bruto = _PATRIM_BRUTO_RE.search(full_text)
    patrimonio_bruto = m_bruto.group(1) if m_bruto else ""
    performance_mes = m_bruto.group(2) if m_bruto else ""

    # Patrimônio líquido
    m_liq = _PATRIM_LIQ_RE.search(full_text)
    patrimonio_liquido = m_liq.group(1) if m_liq else ""

    # Performance 12M
    m_12m = _PERF_12M_RE.search(full_text)
    performance_12m = m_12m.group(1) if m_12m else ""

    # Distribuição por classe (excluindo Total)
    distribuicao: list[BtgDistribuicaoClasse] = []
    # Cabeçalho da tabela termina em "Estratégi  % Valor Financeiro", depois começam as linhas
    dist_section = re.search(
        r"Distribuição por classe de ativos.+?(?=Patrimônio líquido)",
        full_text, re.DOTALL,
    )
    if dist_section:
        for m_d in _DIST_RE.finditer(dist_section.group()):
            estrategia = m_d.group(1).strip()
            # Normaliza o nome garbled "Pós- xado" → "Pós-fixado"
            estrategia = re.sub(r"Pós-\s*\w*xado", "Pós-fixado", estrategia)
            distribuicao.append(BtgDistribuicaoClasse(
                estrategia=estrategia,
                percentual=m_d.group(2),
                valor_financeiro=m_d.group(3),
            ))
    logger.debug("BtgResumo: {} classes de distribuição encontradas", len(distribuicao))

    # Rentabilidade por período
    rentabilidade: list[BtgRentabilidadePeriodo] = []
    for m_r in _RENT_RE.finditer(full_text):
        rentabilidade.append(BtgRentabilidadePeriodo(
            periodo=m_r.group(1),
            retorno_rs=m_r.group(2),
            portfolio_pct=m_r.group(3),
            cdi_pct=m_r.group(4),
            ipca_pct=m_r.group(5),
            dolar_pct=m_r.group(6),
        ))
    logger.debug("BtgResumo: {} períodos de rentabilidade", len(rentabilidade))

       # Liquidez
    liquidez: list[BtgLiquidezFaixa] = []
    for m_l in _LIQUID_RE.finditer(full_text):
        faixa = m_l.group(1).strip()
        faixa_norm = _normalizar_faixa_liquidez(faixa)
        liquidez.append(BtgLiquidezFaixa(
            faixa=faixa_norm,
            percentual=m_l.group(2),
            valor_financeiro=m_l.group(3),
        ))
    logger.debug("BtgResumo: {} faixas de liquidez", len(liquidez))

    return BtgResumo(
        periodo=periodo,
        patrimonio_bruto=patrimonio_bruto,
        patrimonio_liquido=patrimonio_liquido,
        performance_mes_pct=performance_mes,
        performance_12m_pct=performance_12m,
        distribuicao=distribuicao,
        rentabilidade=rentabilidade,
        liquidez=liquidez,
    )
