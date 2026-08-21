"""
XpParser — Strategy concreto para XP Investimentos.

Implementa DocumentParser usando o padrão Template Method:
  parse() define a sequência fixa de chamadas aos sub-parsers (xp_resumo →
  xp_historico → xp_evolucao → xp_composicao → xp_posicao).
Cada sub-parser tem SRP: extrai apenas sua seção do texto.
"""
from loguru import logger

from app.domain.models.portfolio import BankInfo
from app.domain.models.xp_portfolio import XpPortfolioData
from app.domain.ports.document_parser import DocumentParser
from app.parsers.xp.xp_composicao import parse_composicao
from app.parsers.xp.xp_evolucao import parse_evolucao
from app.parsers.xp.xp_historico import parse_historico
from app.parsers.xp.xp_posicao import parse_posicao
from app.parsers.xp.xp_resumo import parse_resumo

_BANK_INFO = BankInfo(nome="XP Investimentos", codigo="102")


class XpParser(DocumentParser):
    """
    Parser para extratos da XP Investimentos.
    Código COMPE: 102
    """

    @property
    def bank_codigo(self) -> str:
        return "102"

    def parse(self, text: str) -> XpPortfolioData:
        """
        Template: sequência fixa, cada passo delegado a seu sub-parser.

        Args:
            text: Texto bruto extraído do PDF via pdfplumber.

        Returns:
            XpPortfolioData completamente preenchido.

        Raises:
            ValueError: Se seções obrigatórias não forem encontradas.
        """
        logger.debug("XpParser: iniciando parse ({} chars).", len(text))

        data_ref, resumo = parse_resumo(text)
        logger.debug("XpParser: resumo extraído — patrimônio={}.", resumo.patrimonio_total_bruto)

        historico = parse_historico(text)
        logger.debug("XpParser: histórico extraído — {} anos.", len(historico))

        evolucao = parse_evolucao(text)
        logger.debug("XpParser: evolução extraída — {} meses.", len(evolucao))

        composicao = parse_composicao(text)
        logger.debug("XpParser: composição extraída — {} estratégias.", len(composicao))

        posicao = parse_posicao(text)
        logger.debug("XpParser: posição extraída — {} estratégias.", len(posicao))

        return XpPortfolioData(
            banco=_BANK_INFO,
            data_referencia=data_ref,
            resumo=resumo,
            historico_anual=historico,
            evolucao_patrimonial=evolucao,
            composicao=composicao,
            posicao_detalhada=posicao,
        )
