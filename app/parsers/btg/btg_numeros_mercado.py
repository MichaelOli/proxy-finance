"""
Sub-parser: Págs. 10-11 — Principais números por mercado e estratégia.

"""
import re

from loguru import logger

from app.domain.models.btg_portfolio import BtgAtivoNumeros, BtgClasseNumeros

_SECTION_START_RE = re.compile(
    r"Os principais números de cada Mercado",
    re.IGNORECASE,
)

_CLASS_HEADER_RE = re.compile(
    r"Em\s+([^\n]+?)\s+([\d,]+%)\s+do\s+Total\s+R\$\s*([\d\.]+,\d+)",
)

_CLASS_TOTAL_RE = re.compile(
    r"^TOTAL\s+R\$\s*([\d\.]+,\d+)(?:\s+R\$\s*([\d\.]+,\d+))?(?:\s+R\$\s*([\d\.]+,\d+))?\s*$",
    re.MULTILINE,
)

# Renda Fixa CDB — linha única com: nome, data_ini, quantidade, vencimento, taxa, saldo, preco, saldo_liq, valor_ap
_CDB_NUM_RE = re.compile(
    r"^(BANCO BTG PACTUAL S A\s*-\s*CDB-\w+)\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"      # data_inicial
    r"([\d\.]+,\d+)\s+"            # quantidade
    r"(\d{2}/\d{2}/\d{4})\s+"      # vencimento
    r"(CDI|[\d,]+%[^\s]*)\s+"      # taxa
    r"R\$\s*([\d\.]+,\d+)\s+"      # saldo_bruto
    r"(-)\s+"                       # preco_medio
    r"R\$\s*([\d\.]+,\d+)\s+"      # saldo_liquido
    r"R\$\s*([\d\.]+,\d+)\s*$",    # valor_aplicado
    re.MULTILINE,
)

# Fundo de Investimento — data_ini, quantidade, resgate (D+X), saldo, preco, saldo_liq, valor_ap
_FUND_NUM_RE = re.compile(
    r"^([A-Z][^\n]+?)\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"      # data_inicial
    r"([\d\.]+,\d+)\s+"            # quantidade
    r"(D\+\d+)\s+"                 # resgate
    r"R\$\s*([\d\.]+,\d+)\s+"      # saldo_bruto
    r"(-)\s+"                       # preco_medio
    r"R\$\s*([\d\.]+,\d+)\s+"      # saldo_liquido
    r"R\$\s*([\d\.]+,\d+)\s*$",    # valor_aplicado
    re.MULTILINE,
)

# Previdência — data_ini, quantidade, saldo, preco, saldo_liq
_PREV_NUM_RE = re.compile(
    r"^([A-Z][^\n]+?)\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"      # data_inicial
    r"([\d\.]+,\d+)\s+"            # quantidade
    r"R\$\s*([\d\.]+,\d+)\s+"      # saldo_bruto
    r"(-)\s+"                       # preco_medio
    r"R\$\s*([\d\.]+,\d+)\s*$",    # saldo_liquido
    re.MULTILINE,
)

# Criptoativos (XBT Bitcoin) — quantidade, saldo, preco, valor_ap
_CRIPTO_NUM_RE = re.compile(
    r"^(XBT[^\n]+?)\s+"
    r"([\d\.]+,\d+)\s+"            # quantidade
    r"R\$\s*([\d\.]+,\d+)\s+"      # saldo_bruto
    r"(-)\s+"                       # preco_medio
    r"R\$\s*([\d\.]+,\d+)\s*$",    # valor_aplicado
    re.MULTILINE,
)


def _normalize_class(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"Rend\s+Fix\s*", "Renda Fixa", name)
    name = re.sub(r"Previdênci\s*$", "Previdência", name)
    return name


def _parse_class_ativos(class_name: str, class_text: str) -> list[BtgAtivoNumeros]:
    """Extrai ativos de um bloco de classe de acordo com o tipo."""
    ativos: list[BtgAtivoNumeros] = []

    if "Criptoativos" in class_name or "Cripto" in class_name:
        for m in _CRIPTO_NUM_RE.finditer(class_text):
            ativos.append(BtgAtivoNumeros(
                nome=m.group(1).strip(),
                quantidade=m.group(2),
                saldo_bruto=m.group(3),
                preco_medio=m.group(4),
                valor_aplicado=m.group(5),
            ))

    elif "Renda Fixa" in class_name or "Fix" in class_name:
        for m in _CDB_NUM_RE.finditer(class_text):
            ativos.append(BtgAtivoNumeros(
                nome=m.group(1).strip(),
                data_inicial=m.group(2),
                quantidade=m.group(3),
                vencimento=m.group(4),
                taxa=m.group(5),
                saldo_bruto=m.group(6),
                preco_medio=m.group(7),
                saldo_liquido=m.group(8),
                valor_aplicado=m.group(9),
            ))

    elif "Fundo" in class_name:
        for m in _FUND_NUM_RE.finditer(class_text):
            ativos.append(BtgAtivoNumeros(
                nome=m.group(1).strip(),
                data_inicial=m.group(2),
                quantidade=m.group(3),
                resgate=m.group(4),
                saldo_bruto=m.group(5),
                preco_medio=m.group(6),
                saldo_liquido=m.group(7),
                valor_aplicado=m.group(8),
            ))

    elif "Previdência" in class_name or "Previdenci" in class_name:
        for m in _PREV_NUM_RE.finditer(class_text):
            ativos.append(BtgAtivoNumeros(
                nome=m.group(1).strip(),
                data_inicial=m.group(2),
                quantidade=m.group(3),
                saldo_bruto=m.group(4),
                preco_medio=m.group(5),
                saldo_liquido=m.group(6),
            ))

    return ativos


def parse_numeros_mercado(full_text: str) -> list[BtgClasseNumeros]:
    """Extrai os principais números por mercado e estratégia (págs. 10-11)."""
    m_start = _SECTION_START_RE.search(full_text)
    if not m_start:
        logger.warning("BtgNumerosM: seção 'Os principais números' não encontrada")
        return []

    section = full_text[m_start.start():]

    class_matches = list(_CLASS_HEADER_RE.finditer(section))
    if not class_matches:
        logger.warning("BtgNumerosM: nenhuma classe encontrada")
        return []

    classes: list[BtgClasseNumeros] = []
    for idx, class_m in enumerate(class_matches):
        nome_classe = _normalize_class(class_m.group(1))
        pct_total = class_m.group(2)
        valor_total = class_m.group(3)

        start_pos = class_m.end()
        end_pos = class_matches[idx + 1].start() if idx + 1 < len(class_matches) else len(section)
        class_text = section[start_pos:end_pos]

        # Total
        total_m = _CLASS_TOTAL_RE.search(class_text)
        total_saldo = total_m.group(1) if total_m else None
        total_liq = total_m.group(2) if total_m else None
        total_ap = total_m.group(3) if total_m else None

        ativos = _parse_class_ativos(nome_classe, class_text)

        classes.append(BtgClasseNumeros(
            nome_classe=nome_classe,
            percentual_total=pct_total,
            valor_total=valor_total,
            ativos=ativos,
            total_saldo_bruto=total_saldo,
            total_saldo_liquido=total_liq,
            total_valor_aplicado=total_ap,
        ))

        logger.debug(
            "BtgNumerosM: classe='{}' → {} ativos",
            nome_classe,
            len(ativos),
        )

    return classes
