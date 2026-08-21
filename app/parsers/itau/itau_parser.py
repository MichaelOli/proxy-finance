"""
ItauParser — Strategy concreto para Itaú Unibanco.

Implementa DocumentParser:
  parse() define a sequência fixa de chamadas aos sub-parsers (itau_resumo ->
  itau_rentabilidade -> itau_alocacao -> itau_ativos).
Cada sub-parser tem SRP: extrai apenas sua seção do documento.
"""
from loguru import logger

from app.domain.models.itau_portfolio import ItauPortfolioData
from app.domain.models.portfolio import BankInfo
from app.domain.ports.document_parser import DocumentParser
from app.parsers.itau.itau_alocacao import parse_alocacao
from app.parsers.itau.itau_ativos import parse_ativos
from app.parsers.itau.itau_rentabilidade import parse_rentabilidade
from app.parsers.itau.itau_resumo import parse_resumo

_CODIGO = "341"
_BANK_INFO = BankInfo(nome="Itaú Unibanco", codigo=_CODIGO)


class ItauParser(DocumentParser):
    """
    Parser para o Resumo Financeiro Itaú Unibanco.
    Código COMPE: 341
    """

    @property
    def bank_codigo(self) -> str:
        return _CODIGO

    def parse(self, text: str) -> ItauPortfolioData:
        """
        Template: sequência fixa, cada passo delegado a seu sub-parser.

        Args:
            text: Texto bruto extraído do PDF via pdfplumber (todas as páginas).

        Returns:
            ItauPortfolioData completamente preenchido.

        Raises:
            ValueError: Se seções obrigatórias não forem encontradas.
        """
        logger.debug("ItauParser: iniciando parse ({} chars).", len(text))

        resumo = parse_resumo(text)
        logger.debug(
            "ItauParser: resumo — saldo_bruto={}, {} classes.",
            resumo.saldo_bruto,
            len(resumo.classes_ativos),
        )

        rentabilidade = parse_rentabilidade(text)
        logger.debug(
            "ItauParser: {} meses de histórico extraídos.",
            len(rentabilidade.historico),
        )

        alocacao = parse_alocacao(text)
        logger.debug(
            "ItauParser: alocacao — {} classes, {} tipos.",
            len(alocacao.classes),
            len(alocacao.tipos_produto),
        )

        ativos = parse_ativos(text)
        total_ativos = sum(
            sum(len(g.ativos) for g in s.grupos)
            for s in ativos
        )
        logger.debug(
            "ItauParser: {} seções de ativos, {} ativos individuais.",
            len(ativos),
            total_ativos,
        )

        return ItauPortfolioData(
            banco=_BANK_INFO,
            resumo=resumo,
            rentabilidade=rentabilidade,
            alocacao=alocacao,
            ativos=ativos,
        )
