"""
FinanceService — orquestra o fluxo completo de parsing de um extrato financeiro.

Fluxo:
  1. BankIdentificationService identifica o banco (código COMPE)
  2. ParserFactory seleciona o parser correto
  3. PdfTextExtractorGateway extrai o texto do PDF localmente
  4. Parser aplica regex no texto e retorna PortfolioData estruturado
"""
from typing import Optional

from loguru import logger

from app.adapters.pdf_text_extractor_gateway import PdfTextExtractorGateway
from app.core.exceptions import ParsingError
from app.domain.models.portfolio import BasePortfolioData
from app.domain.ports.document_text_extractor import DocumentTextExtractor
from app.parsers.parser_factory import ParserFactory
from app.services.bank_identification_service import BankIdentificationService



class FinanceService:
    """
    Orquestra identificação de banco + OCR + parsing regex.
    Recebe dependências via construtor para facilitar testes (Dependency Injection).
    """

    def __init__(
        self,
        text_extractor: Optional[DocumentTextExtractor] = None,
        identification_service: Optional[BankIdentificationService] = None,
    ) -> None:
        self._extractor: DocumentTextExtractor = text_extractor or PdfTextExtractorGateway()
        self._identifier = identification_service or BankIdentificationService()

    async def parse_document(
        self,
        file_bytes: bytes,
        filename: str,
        bank_codigo_hint: Optional[str] = None,
    ) -> BasePortfolioData:
        """
        Processa o documento e retorna o JSON estruturado.

        Args:
            file_bytes: Conteúdo binário do arquivo enviado.
            filename: Nome original do arquivo.
            bank_codigo_hint: Código COMPE fornecido pelo cliente (opcional).
                              Se fornecido, pula a identificação automática.

        Returns:
            Subtipo de BasePortfolioData completamente preenchido.

        Raises:
            BankNotIdentifiedError: Se não foi possível identificar o banco.
            UnsupportedBankError: Se o banco identificado não tem parser.
            ExtractionError: Se houve falha na leitura ou extracao do PDF.
        """
        # 1. Identificação do banco
        logger.info("FinanceService: identificando banco para '{}'.", filename)
        codigo = self._identifier.identify(
            file_bytes=file_bytes,
            filename=filename,
            bank_codigo_hint=bank_codigo_hint,
        )
        logger.info("FinanceService: banco identificado codigo={}.", codigo)

        # 2. Seleção do parser
        parser = ParserFactory.get_parser(codigo)

        # 3. Extração de texto local
        logger.info("FinanceService: extraindo texto de '{}'.", filename)
        text = await self._extractor.extract_text(file_bytes=file_bytes, filename=filename)

        # 4. Parsing regex
        logger.info("FinanceService: aplicando parser '{}'.", type(parser).__name__)
        try:
            return parser.parse(text)
        except ValueError as exc:
            raise ParsingError(codigo=codigo, detail=str(exc)) from exc
