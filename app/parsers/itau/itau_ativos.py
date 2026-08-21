"""
Sub-parser: Págs. 4-12 — Detalhamento de Ativos por tipo de produto (1/9 a 9/9).
"""
import re
from typing import Optional

from loguru import logger

from app.domain.models.itau_portfolio import (
    ItauAtivo,
    ItauGrupoAtivos,
    ItauSecaoAtivos,
)

# ---------------------------------------------------------------------------
# Regex de estrutura
# ---------------------------------------------------------------------------

# Cabeçalho de page break
_PAGEBREAK_HEADER_RE = re.compile(
    r"Detalhamento de Ativos - tipo produto\s*\n"
    r"\(\d+/\d+\)\s*\n"
    r"Data da posição:[^\n]+\n"
    r"Data de rentabilidade:[^\n]+\n"
    r"[^\n]+\n"          # linha longa de headers
    r"Ativos\s*\n"
    r"[^\n]+\n",         # linha "vencto (R$) ... Início"
    re.MULTILINE,
)

# Seção header — formato:
# "NOME_SECAO - - - - SALDO_BRUTO SALDO_LIQ IR - ALOC_DATA_INICIO - - - - -"
_SECAO_HEADER_RE = re.compile(
    r"^(Renda fixa e estruturados|Fundos de investimento|Previdência|Renda variável)"
    r"\s+-\s+-\s+-\s+-\s+"
    r"([\d\.]+,\d+)\s+"            # saldo_bruto
    r"([\d\.]+,\d+)\s+"            # saldo_liq
    r"([\d\.]+,\d+)\s+-\s+"        # ir_iof
    r"(\d+,\d{2})"                  # aloc_pct (concatenado com data_inicio)
    r"(\d{2}/\d{2}/\d{2})",         # data_inicio
    re.MULTILINE,
)

# Grupo header linha 1: "NOME -" (apenas nomes de grupos RF conhecidos)
_GRUPO_NOME_RE = re.compile(
    r"^(ITAUVEST|LCA-DI ITAU|LIG-DI ITAU|LIG-PRE ITAU|LIG-IPCA ITAU"
    r"|NTN-B JUROS|NTN-B PRINCIPAL|NTN-B)\s*-\s*$",
    re.MULTILINE,
)

# Grupo header linha 2 (totais do grupo):
# "- VALOR QTD - SALDO SALDO_LIQ - - ALOC ..."
_GRUPO_TOTAIS_RE = re.compile(
    r"^-\s+([\d\.]+,\d+)\s+"         # valor_aplic
    r"([\d\.]+)\s+-\s+"              # qtd
    r"([\d\.]+,\d+)\s+"              # saldo_bruto
    r"([\d\.]+,\d+)\s+-\s+-\s+"     # saldo_liq
    r"(\d+,\d{2})",                  # aloc_pct
    re.MULTILINE,
)

# Grupo header linha 3: "N ativos"
_GRUPO_NATIVOS_RE = re.compile(r"^(\d+)\s+ativos\s*$", re.MULTILINE)

# -------------------------------------------------------------------
# Regex CORE para qualquer linha de ativo:
# Ancora nos 3 valores financeiros + data_cotacao + aloc+data_inicio
# (saldo_bruto saldo_liq ir_iof) são sempre tres decimais seguidos
# de uma data DD/MM/YY sem espaço para aloc
# -------------------------------------------------------------------
_CORE_RE = re.compile(
    r"([\d\.]+,\d+)\s+"              # saldo_bruto
    r"([\d\.]+,\d+)\s+"              # saldo_liquido
    r"([\d\.]+,\d+)\s+"              # ir_iof
    r"(\d{2}/\d{2}/\d{2})\s+"       # data_cotacao  ← \s+ separa da aloc_pct
    r"(\d+,\d{2})"                   # aloc_pct (sem espaço antes do data_inicio)
    r"(\d{2}/\d{2}/\d{2})\s+"       # data_inicio
    r"((?:-?[\d]+,\d+|-)\s*"         # rents (até 5, separados por \s*)
    r"(?:-?[\d]+,\d+|-)\s*"
    r"(?:-?[\d]+,\d+|-)\s*"
    r"(?:-?[\d]+,\d+|-)\s*"
    r"(?:-?[\d]+,\d+|-))",
)

# Regex para extrair rents individuais (incluindo negativos concatenados)
_RENT_VAL_RE = re.compile(r"-?[\d]+,\d+|-")

# Regex para linhas de seção previdência (header diferente):
# "Regime Tributário Valor aplicado..."
_PREV_HEADER_RE = re.compile(
    r"^Regime\s*\nTributário",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Parser principal
# ---------------------------------------------------------------------------

def parse_ativos(text: str) -> list[ItauSecaoAtivos]:
    """Extrai todas as seções de ativos das páginas 4-12."""
    bloco = _extract_ativos_block(text)
    bloco = _remove_pagebreak_headers(bloco)

    secoes: list[ItauSecaoAtivos] = []
    positions = list(_SECAO_HEADER_RE.finditer(bloco))

    for i, m_sec in enumerate(positions):
        nome_secao = m_sec.group(1)
        saldo_bruto_sec = m_sec.group(2)
        saldo_liq_sec   = m_sec.group(3)
        aloc_sec        = m_sec.group(5)

        fim = positions[i + 1].start() if i + 1 < len(positions) else len(bloco)
        txt_secao = bloco[m_sec.end(): fim]

        if nome_secao == "Renda fixa e estruturados":
            grupos = _parse_grupos_rf(txt_secao)
        else:
            ativos = _parse_ativos_genericos(txt_secao)
            grupos = [ItauGrupoAtivos(
                nome=nome_secao,
                saldo_bruto_total=saldo_bruto_sec,
                saldo_liquido_total=saldo_liq_sec,
                alocacao_pct=aloc_sec,
                ativos=ativos,
            )]

        secoes.append(ItauSecaoAtivos(
            nome=nome_secao,
            saldo_bruto_total=saldo_bruto_sec,
            saldo_liquido_total=saldo_liq_sec,
            alocacao_pct=aloc_sec,
            grupos=grupos,
        ))

    logger.debug("itau_ativos: {} seções extraídas.", len(secoes))
    return secoes


# ---------------------------------------------------------------------------
# Renda fixa — grupos e ativos
# ---------------------------------------------------------------------------

def _parse_grupos_rf(texto: str) -> list[ItauGrupoAtivos]:
    grupos: list[ItauGrupoAtivos] = []
    matches_nome = list(_GRUPO_NOME_RE.finditer(texto))

    for i, m_nome in enumerate(matches_nome):
        nome_grupo = m_nome.group(1)
        txt_after  = texto[m_nome.end(): m_nome.end() + 500]

        # Busca totais na linha seguinte ao nome
        m_tot = _GRUPO_TOTAIS_RE.search(txt_after)
        saldo_bruto = m_tot.group(3) if m_tot else None
        saldo_liq   = m_tot.group(4) if m_tot else None
        aloc        = m_tot.group(5) if m_tot else None

        # Busca "N ativos" na linha após os totais
        m_n = _GRUPO_NATIVOS_RE.search(txt_after)
        num_ativos = int(m_n.group(1)) if m_n else None

        # Texto deste grupo até o próximo
        fim = matches_nome[i + 1].start() if i + 1 < len(matches_nome) else len(texto)
        txt_grupo = texto[m_nome.end(): fim]

        ativos = _parse_ativos_genericos(txt_grupo)

        grupos.append(ItauGrupoAtivos(
            nome=nome_grupo,
            num_ativos=num_ativos,
            saldo_bruto_total=saldo_bruto,
            saldo_liquido_total=saldo_liq,
            alocacao_pct=aloc,
            ativos=ativos,
        ))

    # Ativos sem grupo explícito (CDB, CRA, CRI, DEB)
    if matches_nome:
        txt_apos_grupos = texto[matches_nome[-1].end():]
    else:
        txt_apos_grupos = texto

    ativos_soltos = _parse_ativos_genericos(txt_apos_grupos)
    if ativos_soltos:
        grupos.append(ItauGrupoAtivos(nome="Outros (RF)", ativos=ativos_soltos))

    return grupos


# ---------------------------------------------------------------------------
# Parser genérico de ativos via _CORE_RE
# ---------------------------------------------------------------------------

def _parse_ativos_genericos(texto: str) -> list[ItauAtivo]:
    """
    Extrai ativos usando o padrão CORE (âncora nos 3 saldos + data_cotacao).
    """
    ativos: list[ItauAtivo] = []
    linhas = texto.split("\n")
    # Monta texto indexado para conseguir olhar para trás
    texto_norm = texto

    for m in _CORE_RE.finditer(texto_norm):
        saldo_bruto  = m.group(1)
        saldo_liq    = m.group(2)
        ir_iof       = m.group(3)
        data_cotacao = m.group(4)
        aloc_pct     = m.group(5)
        data_inicio  = m.group(6)
        rents_raw    = m.group(7)

        rents = _RENT_VAL_RE.findall(rents_raw)
        r = [v for v in rents if v != ""]
        rent_mes    = r[0] if len(r) > 0 else None
        rent_ano    = r[1] if len(r) > 1 else None
        rent_12m    = _n(r[2]) if len(r) > 2 else None
        rent_24m    = _n(r[3]) if len(r) > 3 else None
        rent_inicio = _n(r[4]) if len(r) > 4 else None

        # Nome: texto na(s) linha(s) antes do match
        nome = _extract_name(texto_norm, m.start())
        # Data de vencimento: possível DD/MM/YY no início da linha de dados
        data_vencto, valor_aplic, qtd, pu = _extract_pre_core(texto_norm, m.start())

        ativos.append(ItauAtivo(
            nome=nome,
            data_vencimento=data_vencto,
            data_inicio=data_inicio,
            valor_aplicado=valor_aplic,
            quantidade=qtd,
            pu_cotacao=pu,
            saldo_bruto=saldo_bruto,
            saldo_liquido=saldo_liq,
            ir_iof=ir_iof,
            data_cotacao=data_cotacao,
            alocacao_pct=aloc_pct,
            rent_mes=rent_mes,
            rent_ano=rent_ano,
            rent_12m=rent_12m,
            rent_24m=rent_24m,
            rent_inicio=rent_inicio,
        ))

    return ativos


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Padrão para a parte ANTES do core (desde o início da linha ou nome anterior)
# Tenta capturar: [vencto_dd] valor_aplic qtd pu
_PRE_CORE_RF_RE = re.compile(
    r"(\d{2}/\d{2}/\d{2})\s+"        # vencto_dd
    r"([\d\.]+,\d+)\s+"              # valor_aplic
    r"([\d\.]+(?:,\d+)?)\s+"         # qtd
    r"([\d\.]+,\d+)\s*$",            # pu_cotacao
)

# Padrão para asset sem vencto (fundos, prev, RV):
# "- VALOR QTD PU"
_PRE_CORE_FUND_RE = re.compile(
    r"-\s+([\d\.]+,\d+)\s+"          # valor_aplic
    r"([\d\.]+,\d+)\s+"              # qtd (pode ter decimais)
    r"([\d\.]+,\d+)\s*$",            # pu_cotacao
)


def _extract_pre_core(
    texto: str,
    pos_core: int,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Extrai vencto_dd, valor_aplic, qtd, pu a partir do trecho imediatamente
    antes do core (saldo_bruto).
    """
    # Pega até 200 chars antes do match core
    trecho = texto[max(0, pos_core - 200): pos_core]
    # Última linha do trecho (pode incluir nome + dados pré-saldo)
    ultima_linha = trecho.rsplit("\n", 1)[-1] if "\n" in trecho else trecho

    m = _PRE_CORE_RF_RE.search(ultima_linha)
    if m:
        return m.group(1), m.group(2), m.group(3), m.group(4)

    m = _PRE_CORE_FUND_RE.search(ultima_linha)
    if m:
        return None, m.group(1), m.group(2), m.group(3)

    return None, None, None, None


def _extract_name(texto: str, pos_core: int) -> str:
    """
    Extrai o nome do ativo a partir das linhas antes do match core.
    Estratégia:
      1. Pega as 2 linhas imediatamente antes do match.
      2. A última linha não-vazia que começa com letra ou '(' é o nome.
         Se começar com dígito/hífen, pode ser linha de dados — tem que pega a anterior.
    """
    trecho = texto[max(0, pos_core - 300): pos_core]
    linhas = [l.strip() for l in trecho.split("\n") if l.strip()]
    if not linhas:
        return ""

    # Remove linhas de totais de grupo ("N ativos", "- 17.640,84 ...")
    for linha in reversed(linhas):
        if re.match(r"^\d+\s+ativos\s*$", linha):
            continue
        if re.match(r"^-\s+[\d\.]", linha):
            continue
        # Linha que começa com letra ou '(' é um nome candidato
        if re.match(r"^[A-Za-zÀ-ú\(]", linha):
            # Remove sufixo " -" do grupo header se presente
            nome = re.sub(r"\s+-\s*$", "", linha).strip()
            return nome

    return linhas[-1] if linhas else ""


def _extract_ativos_block(text: str) -> str:
    """Retorna o texto a partir do marcador '4 de 16'."""
    m = re.search(r"\b4\s+de\s+16\b", text)
    return text[m.start():] if m else text[7000:]


def _remove_pagebreak_headers(text: str) -> str:
    """Remove os cabeçalhos repetidos de page break."""
    # Remove o bloco de header de cada página de detalhamento
    text = _PAGEBREAK_HEADER_RE.sub("\n", text)
    # Remove linha "Regime Tributário" (aparece antes da seção Previdência)
    text = _PREV_HEADER_RE.sub("\n", text)
    # Colapsa linhas em branco
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _n(val: str) -> Optional[str]:
    return None if val.strip() == "-" else val.strip()
