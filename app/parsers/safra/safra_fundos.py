"""
Sub-parser: Detalhamento de Fundos de Investimentos Safra (páginas 6–7).

Extrai para cada fundo:
  - nome, CNPJ, classe (RENDA FIXA / RENDA VARIÁVEL)
  - qtde de cotas, valor de cota, saldo aplicado, saldo bruto, impostos, saldo líquido
  - movimentações (Saldo Anterior / Saldo Atual) com dados completos

Estratégia de associação:
  1. Monta mapa nome → CNPJ a partir das linhas "Fundo: COD - NOME - CNPJ: XXX"
  2. Extrai tabela-resumo de cada fundo (linha com qtde_cotas, valor_cota, ...)
  3. Extrai blocos de movimentação ("Saldo Anterior" / "Saldo Atual")
  4. Associa movimentações a fundos pelo valor_bruto do "Saldo Atual"
"""
import re

from app.domain.models.safra_portfolio import SafraFundo, SafraFundoMovimentacao

_SECTION_START = re.compile(r"Detalhamento de Fundos de Investimentos")
_SECTION_END = re.compile(r"Detalhamento de Poupança|-- 8 of 12 --")

# Exemplo: "Fundo: CLB - ORION SETORIAL BANCOS FIC FIA - CNPJ: 12.345.678/0001-10"
_CNPJ_REF_RE = re.compile(
    r"Fundo:\s*\w+\s*-\s*([^-\n]+?)\s*-\s*CNPJ:\s*([\d./-]+)"
)

# Classes de ativo no cabeçalho da tabela-resumo
_CLASSE_RE = re.compile(r"^(RENDA FIXA|RENDA VARIÁVEL)\s*$", re.MULTILINE)

_V = r"(-?[\d\.]+,\d+)"   # apenas números (sem traço) para tabela-resumo de fundos
_V6 = r"(-?[\d\.]+,\d+)"  # cotas têm mais casas decimais, mesma pattern
_VA = r"(-?[\d\.]+,\d+|-)"  # valor ou traço (para movimentações)

# Linha da tabela-resumo: NOME  qtde_cotas  valor_cota  saldo_aplicado  saldo_bruto  impostos  saldo_liquido
_FUNDO_SUMMARY_RE = re.compile(
    r"^([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9 /\.]+?)\s+"
    + r"\s+".join([_V6] * 6)
    + r"\s*$",
    re.MULTILINE,
)

# Linha de movimentação: "30/06/2025 Saldo Anterior  -  -  valor_cotas  qtde  bruto  imp_inc  imp_prev  liq"
_MOV_RE = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(Saldo Anterior|Saldo Atual)\s+"
    + r"\s+".join([_VA] * 8)
)


def _extract_section(text: str) -> str:
    m_start = _SECTION_START.search(text)
    if not m_start:
        return ""
    m_end = _SECTION_END.search(text, m_start.end())
    end_pos = m_end.start() if m_end else len(text)
    return text[m_start.start():end_pos]


def parse_fundos(text: str) -> list[SafraFundo]:
    """
    Extrai o detalhamento de fundos (páginas 6–7).
    """
    section = _extract_section(text)
    if not section:
        return []

    # 1. Mapa nome → CNPJ
    cnpj_map: dict[str, str] = {}
    for m in _CNPJ_REF_RE.finditer(section):
        nome = m.group(1).strip()
        cnpj = m.group(2).strip()
        cnpj_map[nome] = cnpj

    # 2. Tabela-resumo: determina classe pelo subtítulo que precede cada linha
    fundos_summary: list[dict] = []
    pos = 0
    current_classe = ""
    for m_classe in _CLASSE_RE.finditer(section):
        current_classe = m_classe.group(1)

    # Associa classe a cada fundo pela ordem de aparição (RENDA FIXA primeiro, depois RENDA VARIÁVEL)
    classes_order: list[str] = [m.group(1) for m in _CLASSE_RE.finditer(section)]
    fundo_rows = list(_FUNDO_SUMMARY_RE.finditer(section))

    # Determina a classe de cada fundo pela posição no texto
    fundo_com_classe: list[tuple[str, str]] = []
    classe_idx = 0
    classe_positions = [(m.start(), m.group(1)) for m in _CLASSE_RE.finditer(section)]

    for row in fundo_rows:
        row_pos = row.start()
        # Classe é a última classe cujo marcador aparece antes desta linha
        classe_atual = ""
        for cp, cn in classe_positions:
            if cp < row_pos:
                classe_atual = cn
            else:
                break
        nome_fundo = row.group(1).strip()
        fundo_com_classe.append((nome_fundo, classe_atual))
        g = [row.group(i) for i in range(2, 8)]
        fundos_summary.append({
            "nome": nome_fundo,
            "classe": classe_atual,
            "quantidade_cotas": g[0],
            "valor_cota": g[1],
            "saldo_aplicado": g[2],
            "saldo_bruto": g[3],
            "impostos_previstos": g[4],
            "saldo_liquido": g[5],
            "cnpj": cnpj_map.get(nome_fundo, ""),
        })

    # 3. Extrai todos os blocos de movimentação
    movimentacoes_por_saldo: dict[str, list[SafraFundoMovimentacao]] = {}
    current_mov: list[SafraFundoMovimentacao] = []
    current_saldo_atual = ""

    for m_mov in _MOV_RE.finditer(section):
        data = m_mov.group(1)
        historico = m_mov.group(2)
        g = [m_mov.group(i) for i in range(3, 11)]

        mov = SafraFundoMovimentacao(
            data=data,
            historico=historico,
            aplicacoes=g[0],
            resgates=g[1],
            valor_cotas=g[2],
            quantidade_cotas=g[3],
            valor_bruto=g[4],
            impostos_incorridos=g[5],
            impostos_previstos=g[6],
            valor_liquido=g[7],
        )

        if historico == "Saldo Anterior":
            if current_mov and current_saldo_atual:
                movimentacoes_por_saldo[current_saldo_atual] = list(current_mov)
            current_mov = [mov]
            current_saldo_atual = ""
        else:  # Saldo Atual
            current_mov.append(mov)
            current_saldo_atual = g[4]  # valor_bruto do Saldo Atual

    if current_mov and current_saldo_atual:
        movimentacoes_por_saldo[current_saldo_atual] = list(current_mov)

    # 4. Monta os objetos SafraFundo associando movimentações pelo saldo_bruto
    fundos: list[SafraFundo] = []
    for fs in fundos_summary:
        movs = movimentacoes_por_saldo.get(fs["saldo_bruto"], [])
        fundos.append(
            SafraFundo(
                nome=fs["nome"],
                cnpj=fs["cnpj"],
                classe=fs["classe"],
                quantidade_cotas=fs["quantidade_cotas"],
                valor_cota=fs["valor_cota"],
                saldo_aplicado=fs["saldo_aplicado"],
                saldo_bruto=fs["saldo_bruto"],
                impostos_previstos=fs["impostos_previstos"],
                saldo_liquido=fs["saldo_liquido"],
                movimentacoes=movs,
            )
        )

    return fundos
