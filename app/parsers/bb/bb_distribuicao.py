"""
Sub-parser responsável pela seção DISTRIBUIÇÃO DA CARTEIRA do extrato Banco do Brasil.

Layout real (pdfplumber) — cada classe tem um cabeçalho seguido de linhas de ativos:

  Renda Fixa Pós Cdi Alocação: 33,63%
  ATIVO SALDO BRUTO ENTRADAS SAÍDAS ...      ← cabeçalho de colunas (ignorado)
  CRA JSL 02-31 R$ 15.432,36 R$ 1.738,53 R$ 0,00 R$ 15.597,29 R$ 0,00 R$ 15.597,29 3,04%
  RF REF DI PLUS AGIL R$ 118,70 R$ 35.071,98 ...
  ...
  Renda Fixa Inflação Alocação: 60,27%
  ...
"""
import re

from loguru import logger

from app.domain.models.portfolio import Ativo, DistribuicaoClasse


_BRL = r"R\$\s*([\d\.]+,\d{2})"


def _norm(v: str) -> str:
    return v.replace(".", "").replace(",", ".")


def parse_distribuicao_carteira(text: str) -> list[DistribuicaoClasse]:
    block = _extract_distribuicao_block(text)
    if not block:
        logger.warning("bb_distribuicao: bloco de distribuição não encontrado.")
        return []
    return _parse_classes(block)


def _extract_distribuicao_block(text: str) -> str:
    """
    O bloco de distribuição começa com o primeiro cabeçalho de classe:
    'Renda Fixa Pós Cdi Alocação:' e termina em 'Liquidez da carteira'.
    Usa este marcador específico para evitar capturar o 'Distribuição' do resumo.
    """
    start = re.search(
        r"Renda\s+Fixa\s+P[oó]s\s+Cdi\s+Aloca[çc][aã]o:",
        text,
        re.IGNORECASE,
    )
    if not start:
        logger.warning("bb_distribuicao: marcador 'Renda Fixa Pós Cdi Alocação:' não encontrado.")
        return ""

    end = re.search(r"Liquidez\s+da\s+carteira", text[start.start():], re.IGNORECASE)
    end_pos = start.start() + end.start() if end else len(text)

    return text[start.start(): end_pos]


def _parse_classes(block: str) -> list[DistribuicaoClasse]:
    """
    Divide o bloco pelos cabeçalhos de classe e processa cada sub-bloco.
    """
    class_header = re.compile(
        r"^(Renda[^\n]+?)\s+Aloca[çc][aã]o:\s*([\d,]+)%",
        re.MULTILINE | re.IGNORECASE,
    )

    headers = list(class_header.finditer(block))
    if not headers:
        logger.warning("bb_distribuicao: nenhum cabeçalho de classe encontrado.")
        return []

    classes: list[DistribuicaoClasse] = []

    for idx, header in enumerate(headers):
        classe_nome = header.group(1).strip()
        alocacao = _norm(header.group(2))

        start = header.end()
        end = headers[idx + 1].start() if idx + 1 < len(headers) else len(block)
        sub_block = block[start:end]

        ativos = _parse_ativos(sub_block)
        classes.append(
            DistribuicaoClasse(
                classe=classe_nome,
                alocacao_percentual=alocacao,
                ativos=ativos,
            )
        )

    return classes


def _parse_ativos(sub_block: str) -> list[Ativo]:
    """
    Extrai ativos de um sub-bloco de classe.
    Cada linha de ativo: NOME + 6 valores R$ + participação%.
    Usa [^\n]+? (lazy) para capturar o nome até o primeiro R$.
    """
    ativo_pattern = re.compile(
        rf"^([A-Z][^\n]{{2,50}}?)\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+{_BRL}\s+([\d,]+)%?",
        re.MULTILINE,
    )

    skip_keywords = ["total", "saldo bruto", "entradas", "saídas", "participação", "provisão", "ativo"]
    ativos: list[Ativo] = []

    for m in ativo_pattern.finditer(sub_block):
        nome = m.group(1).strip()
        if any(k in nome.lower() for k in skip_keywords):
            continue
        # Ignora linhas de cabeçalho de data (ex: "31/05/2024 30/05/2025 30/05/2025")
        if re.match(r"^\d{2}/", nome):
            continue
        ativos.append(
            Ativo(
                nome=nome,
                saldo_bruto_inicio=_norm(m.group(2)),
                entradas=_norm(m.group(3)),
                saidas=_norm(m.group(4)),
                saldo_bruto_fim=_norm(m.group(5)),
                provisao_ir_iof=_norm(m.group(6)),
                saldo_liquido=_norm(m.group(7)),
                participacao=_norm(m.group(8)),
            )
        )

    return ativos
