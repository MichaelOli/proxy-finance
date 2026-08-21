"""
BBParser — orquestrador do parser do Banco do Brasil.

Implementa DocumentParser (Strategy) e delega para sub-módulos (SRP):
  - bb_resumo      → Resumo + Período
  - bb_posicao     → Posição da Carteira
  - bb_distribuicao → Distribuição da Carteira
  - bb_liquidez    → Liquidez da Carteira
  - bb_rentabilidade → Rentabilidade + Períodos de Referência
"""
from loguru import logger

from app.domain.models.portfolio import BankInfo, PortfolioData
from app.domain.ports.document_parser import DocumentParser
from app.parsers.bb.bb_distribuicao import parse_distribuicao_carteira
from app.parsers.bb.bb_liquidez import parse_liquidez_carteira
from app.parsers.bb.bb_posicao import parse_posicao_carteira
from app.parsers.bb.bb_rentabilidade import parse_rentabilidade
from app.parsers.bb.bb_resumo import parse_resumo


_CODIGO = "001"
_BANK_NAME = "Banco do Brasil"


class BBParser(DocumentParser):
    """
    Parser completo para extratos do Banco do Brasil.
    Cada seção é extraída por um sub-módulo independente.
    """

    @property
    def bank_codigo(self) -> str:
        return _CODIGO

    def parse(self, text: str) -> PortfolioData:
        logger.info("BBParser: iniciando parsing do extrato.")

        periodo, resumo = parse_resumo(text)
        posicao = parse_posicao_carteira(text)
        distribuicao = parse_distribuicao_carteira(text)
        liquidez = parse_liquidez_carteira(text)
        rentabilidade, periodos_referencia = parse_rentabilidade(text)

        data = PortfolioData(
            banco=BankInfo(nome=_BANK_NAME, codigo=_CODIGO),
            periodo=periodo,
            resumo=resumo,
            posicao_carteira=posicao,
            distribuicao_carteira=distribuicao,
            liquidez_carteira=liquidez,
            rentabilidade=rentabilidade,
            periodos_referencia=periodos_referencia,
        )

        logger.info(
            "BBParser: parsing concluído — {} ativos em posição, {} classes distribuição.",
            len(posicao),
            len(distribuicao),
        )
        return data
