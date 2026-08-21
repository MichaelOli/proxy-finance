"""
Sub-parser responsável pela seção RESUMO do extrato Banco do Brasil.

"""
import re

from loguru import logger

from app.domain.models.portfolio import (
    Carteira,
    DistribuicaoPorClasse,
    DistribuicaoPorRisco,
    Evolucao,
    Periodo,
    Resumo,
    SaldoBrutoData,
)



def _norm(v: str) -> str:
    """'1.234,56' → '1234.56'"""
    return v.replace(".", "").replace(",", ".")


def parse_periodo(text: str) -> Periodo:
    pattern = re.compile(
        r"Per[ií]odo\s+(\d{2}/\d{2}/\d{4})\s+at[eé]\s+(\d{2}/\d{2}/\d{4})",
        re.IGNORECASE,
    )
    m = pattern.search(text)
    if not m:
        raise ValueError("Período não encontrado no texto do extrato BB.")
    return Periodo(inicio=m.group(1), fim=m.group(2))


def parse_carteira(text: str) -> Carteira:
    """
    Extrai os dados de Carteira.

    """
    # Rendimentos e Entradas: primeira linha de valores após o cabeçalho
    rend_entradas = re.search(
        r"Rendimentos\s+Entradas[^\n]*\n\s*R\$\s*([\d\.]+,\d{2})\s+R\$\s*([\d\.]+,\d{2})",
        text,
        re.IGNORECASE,
    )
    rendimentos = _norm(rend_entradas.group(1)) if rend_entradas else "0.00"
    entradas = _norm(rend_entradas.group(2)) if rend_entradas else "0.00"

    # Líquido em <data> — extrai a data da linha 3
    liq_data_m = re.search(
        r"L[ií]quido em\s+(\d{2}/\d{2}/\d{4})",
        text,
        re.IGNORECASE,
    )
    liquido_data = liq_data_m.group(1) if liq_data_m else ""

    # Datas de evolução: "em DD/MM/AAAA em DD/MM/AAAA"
    evolucao_dates_m = re.search(
        r"em\s+(\d{2}/\d{2}/\d{4})\s+em\s+(\d{2}/\d{2}/\d{4})",
        text,
        re.IGNORECASE,
    )

    if evolucao_dates_m:
        evo_inicio_data = evolucao_dates_m.group(1)
        evo_fim_data = evolucao_dates_m.group(2)

        # Valores na linha imediatamente após a linha de datas
        after_dates = text[evolucao_dates_m.end():]
        first_values_m = re.search(
            r"\s*R\$\s*([\d\.]+,\d{2})\s+R\$\s*([\d\.]+,\d{2})",
            after_dates,
            re.IGNORECASE,
        )
        if first_values_m:
            liquido_valor = _norm(first_values_m.group(1))
            retiradas = _norm(first_values_m.group(2))

            # Valores de saldo bruto (evolução) na linha seguinte 
            after_first = after_dates[first_values_m.end():]
            second_values_m = re.search(
                r"\s*R\$\s*([\d\.]+,\d{2})\s+R\$\s*([\d\.]+,\d{2})",
                after_first,
                re.IGNORECASE,
            )
            if second_values_m:
                saldo_inicio_valor = _norm(second_values_m.group(1))
                saldo_fim_valor = _norm(second_values_m.group(2))
            else:
                saldo_inicio_valor = "0.00"
                saldo_fim_valor = "0.00"
        else:
            liquido_valor = "0.00"
            retiradas = "0.00"
            saldo_inicio_valor = "0.00"
            saldo_fim_valor = "0.00"
    else:
        evo_inicio_data = ""
        evo_fim_data = ""
        liquido_valor = "0.00"
        retiradas = "0.00"
        saldo_inicio_valor = "0.00"
        saldo_fim_valor = "0.00"

    return Carteira(
        rendimentos=rendimentos,
        entradas=entradas,
        retiradas=retiradas,
        liquido=SaldoBrutoData(data=liquido_data, valor=liquido_valor),
        evolucao=Evolucao(
            saldo_bruto_inicio=SaldoBrutoData(data=evo_inicio_data, valor=saldo_inicio_valor),
            saldo_bruto_fim=SaldoBrutoData(data=evo_fim_data, valor=saldo_fim_valor),
        ),
    )


def parse_distribuicao_por_classe(text: str) -> list[DistribuicaoPorClasse]:
    """
    Extrai a distribuição por classe de ativo.
    Estratégia: encontra pares de linhas (valores -> nomes) e extrai o PRIMEIRO
    par percentual/valor de cada linha de valores como a classe.
    """
    # Restringe ao bloco de resumo (antes da seção de Posição)
    end_of_resumo = re.search(r"Posi[çc][aã]o da carteira", text, re.IGNORECASE)
    section = text[: end_of_resumo.start()] if end_of_resumo else text

    value_pat = re.compile(r"([\d,]+)%\s*-\s*R\$\s*([\d\.]+,\d{2})")
    risco_labels = {"Muito Baixo", "Baixo", "Médio", "Alto", "Muito Alto"}
    class_keywords = {"RENDA FIXA PÓS CDI", "RENDA FIXA INFLAÇÃO", "RENDA FIXA PRÉ", "RENDA VARIÁVEL"}

    lines = [ln.strip() for ln in section.splitlines()]
    items: list[DistribuicaoPorClasse] = []
    seen: set[str] = set()

    for i, line in enumerate(lines):
        pairs = value_pat.findall(line)
        if not pairs or i + 1 >= len(lines):
            continue

        name_line = lines[i + 1]

        # Identifica o nome da classe na linha de nomes
        class_name: str | None = None
        for ck in class_keywords:
            if ck in name_line.upper():
                class_name = ck
                break

        # Tenta match parcial para classes que possam ter grafia diferente
        if not class_name:
            for ck in class_keywords:
                if any(word in name_line.upper() for word in ck.split()):
                    class_name = ck
                    break

        if not class_name or class_name in seen:
            continue

        # Primeiro par = classe
        pct, valor = pairs[0]
        items.append(DistribuicaoPorClasse(
            classe=class_name,
            percentual=_norm(pct),
            valor=_norm(valor),
        ))
        seen.add(class_name)

    return items


def parse_distribuicao_por_risco(text: str) -> list[DistribuicaoPorRisco]:
    """
    Extrai a distribuição por risco.

    O risco é o SEGUNDO par percentual/valor na linha de valores quando há dois pares,
    e o nome do risco aparece junto com o nome da classe na linha seguinte.
    """
    end_of_resumo = re.search(r"Posi[çc][aã]o da carteira", text, re.IGNORECASE)
    section = text[: end_of_resumo.start()] if end_of_resumo else text

    value_pat = re.compile(r"([\d,]+)%\s*-\s*R\$\s*([\d\.]+,\d{2})")
    risco_labels = ["Muito Baixo", "Baixo", "Médio", "Alto", "Muito Alto"]

    lines = [ln.strip() for ln in section.splitlines()]
    items: list[DistribuicaoPorRisco] = []
    seen: set[str] = set()

    for i, line in enumerate(lines):
        pairs = value_pat.findall(line)
        if len(pairs) < 2 or i + 1 >= len(lines):
            continue

        name_line = lines[i + 1]

        for risco in risco_labels:
            if risco.lower() in name_line.lower() and risco not in seen:
                # Segundo par = risco
                pct, valor = pairs[1]
                items.append(DistribuicaoPorRisco(
                    risco=risco,
                    percentual=_norm(pct),
                    valor=_norm(valor),
                ))
                seen.add(risco)
                break

    return items


def parse_resumo(text: str) -> tuple[Periodo, Resumo]:
    periodo = parse_periodo(text)
    carteira = parse_carteira(text)
    dist_classe = parse_distribuicao_por_classe(text)
    dist_risco = parse_distribuicao_por_risco(text)

    return periodo, Resumo(
        carteira=carteira,
        distribuicao_por_classe=dist_classe,
        distribuicao_por_risco=dist_risco,
    )
