"""
SafraParser — Strategy concreto para Banco Safra.

Implementa DocumentParser usando o padrão Template Method:
  parse() define a sequência fixa de chamadas aos sub-parsers (safra_resumo →
  safra_historico → safra_rentabilidade_produtos → safra_posicao →
  safra_composicao → safra_fundos → safra_conta_corrente).
Cada sub-parser tem SRP: extrai apenas sua seção do texto.
"""
from loguru import logger

from app.domain.models.portfolio import BankInfo
from app.domain.models.safra_portfolio import SafraPortfolioData
from app.domain.ports.document_parser import DocumentParser
from app.parsers.safra.safra_composicao import parse_composicao
from app.parsers.safra.safra_conta_corrente import parse_conta_corrente
from app.parsers.safra.safra_fundos import parse_fundos
from app.parsers.safra.safra_historico import parse_historico
from app.parsers.safra.safra_posicao import parse_posicao
from app.parsers.safra.safra_rentabilidade_produtos import parse_rentabilidade_produtos
from app.parsers.safra.safra_resumo import parse_resumo

_CODIGO = "422"
_BANK_INFO = BankInfo(nome="Banco Safra", codigo=_CODIGO)


class SafraParser(DocumentParser):
    """
    Parser para extratos mensais do Banco Safra.
    Código COMPE: 422
    """

    @property
    def bank_codigo(self) -> str:
        return _CODIGO

    def parse(self, text: str) -> SafraPortfolioData:
        """
        Template Method: sequência fixa, cada passo delegado a seu sub-parser.

        Args:
            text: Texto bruto extraído do PDF via pdfplumber.

        Returns:
            SafraPortfolioData completamente preenchido.

        Raises:
            ValueError: Se seções obrigatórias não forem encontradas.
        """
        logger.debug("SafraParser: iniciando parse ({} chars).", len(text))

        resumo = parse_resumo(text)
        logger.debug(
            "SafraParser: resumo extraído — patrimônio_bruto={}.",
            resumo.patrimonio.saldo_bruto_brl,
        )

        historico = parse_historico(text)
        logger.debug(
            "SafraParser: histórico extraído — {} linhas.", len(historico.linhas)
        )

        rentabilidade_produtos = parse_rentabilidade_produtos(text)
        logger.debug(
            "SafraParser: rentabilidade de produtos extraída — {} linhas.",
            len(rentabilidade_produtos),
        )

        posicao = parse_posicao(text)
        logger.debug(
            "SafraParser: posição extraída — {} itens.", len(posicao)
        )

        composicao = parse_composicao(text)
        logger.debug(
            "SafraParser: composição extraída — {} itens.", len(composicao)
        )

        fundos = parse_fundos(text)
        logger.debug(
            "SafraParser: fundos extraídos — {} fundos.", len(fundos)
        )

        conta_corrente = parse_conta_corrente(text)
        logger.debug(
            "SafraParser: conta corrente extraída — {}.",
            "sim" if conta_corrente else "não encontrada",
        )

        return SafraPortfolioData(
            banco=_BANK_INFO,
            resumo=resumo,
            historico_rentabilidade=historico,
            rentabilidade_produtos=rentabilidade_produtos,
            posicao_investimentos=posicao,
            composicao=composicao,
            fundos=fundos,
            conta_corrente=conta_corrente,
        )
