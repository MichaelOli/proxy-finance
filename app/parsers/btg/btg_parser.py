"""
BtgParser — Strategy concreto para BTG Pactual.

Implementa DocumentParser:
  parse() define a sequência fixa de chamadas aos sub-parsers (
  btg_resumo -> btg_historico -> 
  btg_retornos -> btg_posicao_rentabilidade -> 
  btg_posicao_consolidada -> btg_numeros_mercado
  ).
  Cada sub-parser tem SRP: extrai apenas sua seção do texto.
"""
from loguru import logger

from app.domain.models.btg_portfolio import BtgPortfolioData
from app.domain.models.portfolio import BankInfo
from app.domain.ports.document_parser import DocumentParser
from app.parsers.btg.btg_historico import (
    parse_historico_movimentacoes,
    parse_rentabilidade_12m,
)
from app.parsers.btg.btg_numeros_mercado import parse_numeros_mercado
from app.parsers.btg.btg_posicao_consolidada import parse_posicao_consolidada
from app.parsers.btg.btg_posicao_rentabilidade import parse_posicao_rentabilidade
from app.parsers.btg.btg_resumo import parse_resumo
from app.parsers.btg.btg_retornos import parse_estatisticas, parse_estrategias, parse_retornos_mensais

_CODIGO = "208"
_BANK_INFO = BankInfo(nome="BTG Pactual", codigo=_CODIGO)


class BtgParser(DocumentParser):
    """
    Parser para o Relatório de Performance BTG Pactual.
    Código COMPE: 208
    """

    @property
    def bank_codigo(self) -> str:
        return _CODIGO

    def parse(self, text: str) -> BtgPortfolioData:
        """
        Template Method: sequência fixa, cada passo delegado a seu sub-parser.

        Args:
            text: Texto bruto extraído do PDF via pdfplumber (todas as páginas concatenadas).

        Returns:
            BtgPortfolioData completamente preenchido.

        Raises:
            ValueError: Se seções obrigatórias não forem encontradas.
        """
        text = text.replace("\x00", " ")

        logger.debug("BtgParser: iniciando parse ({} chars).", len(text))

        resumo = parse_resumo(text)
        logger.debug(
            "BtgParser: resumo — patrimônio_bruto={}, performance_mes={}.",
            resumo.patrimonio_bruto,
            resumo.performance_mes_pct,
        )

        historico_mov = parse_historico_movimentacoes(text)
        logger.debug("BtgParser: {} movimentações extraídas.", len(historico_mov))

        rent_12m = parse_rentabilidade_12m(text)
        logger.debug("BtgParser: {} linhas de rentabilidade 12M.", len(rent_12m))

        estrategias = parse_estrategias(text)
        logger.debug("BtgParser: {} estratégias extraídas.", len(estrategias))

        retornos_mensais = parse_retornos_mensais(text)
        logger.debug("BtgParser: {} linhas de retornos mensais.", len(retornos_mensais))

        estatisticas = parse_estatisticas(text)
        logger.debug("BtgParser: estatísticas extraídas.")

        posicao_rent = parse_posicao_rentabilidade(text)
        logger.debug("BtgParser: {} classes de posição (rent.).", len(posicao_rent))

        posicao_consol = parse_posicao_consolidada(text)
        logger.debug("BtgParser: {} devedores consolidados.", len(posicao_consol))

        numeros = parse_numeros_mercado(text)
        logger.debug("BtgParser: {} classes de números.", len(numeros))

        return BtgPortfolioData(
            banco=_BANK_INFO,
            resumo=resumo,
            historico_movimentacoes=historico_mov,
            rentabilidade_mensal_12m=rent_12m,
            estrategias=estrategias,
            retornos_mensais=retornos_mensais,
            estatisticas=estatisticas,
            posicao_rentabilidade=posicao_rent,
            posicao_consolidada=posicao_consol,
            numeros_mercado=numeros,
        )
